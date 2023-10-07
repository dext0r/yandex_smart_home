"""Implement the Yandex Smart Home events notifier."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import deque
from dataclasses import dataclass
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from aiohttp import ContentTypeError
from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.const import ATTR_ENTITY_ID, EVENT_STATE_CHANGED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HassJob
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later

from . import const
from .device import Device, DeviceCallbackState

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant

    from .entry_data import ConfigEntryData

_LOGGER = logging.getLogger(__name__)

INITIAL_REPORT_DELAY = 15
DISCOVERY_REQUEST_DELAY = 5
REPORT_STATE_WINDOW = 1


@dataclass
class NotifierConfig:
    """Hold configuration variables for a notifier."""

    user_id: str
    token: str
    hass_user_id: str | None = None
    skill_id: str | None = None
    verbose_log: bool = False

    async def async_validate(self, hass: HomeAssistant) -> None:
        """Validates the configuration."""
        if self.hass_user_id:
            if await hass.auth.async_get_user(self.hass_user_id) is None:
                raise ValueError(f"User {self.hass_user_id} does not exist")

        return None


class YandexNotifier(ABC):
    """Base class for an event notifier."""

    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData, config: NotifierConfig):
        """Initialize."""
        self._hass = hass
        self._entry_data = entry_data
        self._config = config

        self._property_entities = self._get_property_entities()
        self._session = async_create_clientsession(hass)

        self._unsub_state_changed: CALLBACK_TYPE | None = None
        self._unsub_initial_report: CALLBACK_TYPE | None = None
        self._unsub_pending: CALLBACK_TYPE | None = None
        self._unsub_send_discovery: CALLBACK_TYPE | None = None

        self._pending: deque[DeviceCallbackState] = deque()
        self._report_states_job = HassJob(self._async_report_states)

    async def async_setup(self) -> None:
        """Set up the notifier."""
        self._unsub_state_changed = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._async_state_changed_event_handler
        )
        self._unsub_initial_report = async_call_later(
            self._hass, INITIAL_REPORT_DELAY, HassJob(self._async_initial_report)
        )
        self._unsub_send_discovery = async_call_later(
            self._hass, DISCOVERY_REQUEST_DELAY, HassJob(self.async_send_discovery)
        )

        return None

    async def async_unload(self) -> None:
        """Unload the notifier."""
        for unsub in [
            self._unsub_state_changed,
            self._unsub_initial_report,
            self._unsub_pending,
            self._unsub_send_discovery,
        ]:
            if unsub:
                unsub()

        self._unsub_state_changed = None
        self._unsub_initial_report = None
        self._unsub_pending = None
        self._unsub_send_discovery = None

        return None

    async def async_send_state(self, devices: list[Any]) -> None:
        """Send new device states to the Yandex."""
        return await self._async_send_callback(f"{self._base_url}/state", {"devices": devices})

    async def async_send_discovery(self, *_: Any) -> None:
        """Send discovery request."""
        _LOGGER.debug(self._format_log_message("Device list update initiated"))
        return await self._async_send_callback(f"{self._base_url}/discovery", {})

    @property
    @abstractmethod
    def _base_url(self) -> str:
        """Return base URL."""
        pass

    @property
    @abstractmethod
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""
        pass

    def _format_log_message(self, message: str) -> str:
        """Format and print a message."""
        return message

    @staticmethod
    def _log_request(url: str, data: dict[str, Any]) -> None:
        """Log a request."""
        request_json = json.dumps(data)
        _LOGGER.debug(f"Request: {url} (POST data: {request_json})")
        return None

    def _get_property_entities(self) -> dict[str, list[str]]:
        rv: dict[str, list[str]] = {}

        for entity_id, entity_config in self._entry_data.entity_config.items():
            for property_config in entity_config.get(const.CONF_ENTITY_PROPERTIES):
                property_entity_id = property_config.get(const.CONF_ENTITY_PROPERTY_ENTITY)
                if property_entity_id:
                    rv.setdefault(property_entity_id, [])
                    if entity_id not in rv[property_entity_id]:
                        rv[property_entity_id].append(entity_id)

            for custom_capabilities_config in [
                entity_config.get(const.CONF_ENTITY_CUSTOM_MODES),
                entity_config.get(const.CONF_ENTITY_CUSTOM_TOGGLES),
                entity_config.get(const.CONF_ENTITY_CUSTOM_RANGES),
            ]:
                for custom_capability in custom_capabilities_config.values():
                    state_entity_id = custom_capability.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
                    if state_entity_id:
                        rv.setdefault(state_entity_id, [])
                        rv[state_entity_id].append(entity_id)

        return rv

    async def _async_report_states(self, *_: Any) -> None:
        """Schedule new states report."""
        devices: dict[str, dict[str, Any]] = {}
        attrs = ["properties", "capabilities"]

        while len(self._pending):
            state = self._pending.popleft()

            devices.setdefault(state.device_id, dict({attr: [] for attr in attrs}, **{"id": state.device_id}))
            for attr in attrs:
                devices[state.device_id][attr][:0] = getattr(state, attr)

        await self.async_send_state(list(devices.values()))

        if len(self._pending):
            self._unsub_pending = async_call_later(self._hass, REPORT_STATE_WINDOW, self._report_states_job)
        else:
            self._unsub_pending = None

        return None

    # noinspection PyBroadException
    async def _async_send_callback(self, url: str, payload: dict[str, Any]) -> None:
        """Send a request to url with payload."""
        try:
            payload["user_id"] = self._config.user_id
            request_data = {"ts": time.time(), "payload": payload}

            self._log_request(url, request_data)
            r = await self._session.post(url, headers=self._request_headers, json=request_data, timeout=5)

            response_body, error_message = await r.read(), ""
            try:
                response_data = await r.json()
                error_message = response_data["error_message"]
            except (AttributeError, ValueError, KeyError, ContentTypeError):
                if r.status != 202:
                    error_message = str(response_body[:100])

            if r.status != 202 or error_message:
                _LOGGER.warning(
                    self._format_log_message(f"Failed to send state notification: [{r.status}] {error_message}")
                )
        except ClientConnectionError as e:
            _LOGGER.warning(self._format_log_message(f"Failed to send state notification: {e!r}"))
        except asyncio.TimeoutError as e:
            _LOGGER.debug(self._format_log_message(f"Failed to send state notification: {e!r}"))
        except Exception:
            _LOGGER.exception(self._format_log_message("Failed to send state notification"))

        return None

    async def _async_state_changed_event_handler(self, event: Event) -> None:
        """State changes event handler."""
        event_entity_id = str(event.data.get(ATTR_ENTITY_ID))
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if not old_state or old_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return
        if not new_state or new_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return

        reportable_entity_ids: set[str] = {event_entity_id}
        if event_entity_id in self._property_entities.keys():
            reportable_entity_ids.update(self._property_entities.get(event_entity_id, {}))

        for entity_id in sorted(reportable_entity_ids):
            state = new_state
            if entity_id != event_entity_id:
                state = self._hass.states.get(entity_id)
                if not state:
                    continue  # pragma: no cover

            device = Device(self._hass, self._entry_data, state.entity_id, state)
            if not device.should_expose:
                continue

            callback_state = DeviceCallbackState(device, event_entity_id)
            if entity_id == event_entity_id and entity_id not in self._property_entities.keys():
                callback_state.old_state = DeviceCallbackState(
                    Device(self._hass, self._entry_data, old_state.entity_id, old_state), event_entity_id
                )

            if callback_state.should_report:
                entity_text = entity_id
                if entity_id != event_entity_id:
                    entity_text = f"{entity_text} => {event_entity_id}"

                _LOGGER.debug(
                    self._format_log_message(f"Scheduling report state to Yandex for {entity_text}: {new_state.state}")
                )
                self._pending.append(callback_state)

                if self._unsub_pending is None:
                    delay = 0 if callback_state.should_report_immediately else REPORT_STATE_WINDOW
                    self._unsub_pending = async_call_later(self._hass, delay, self._report_states_job)

        return None

    async def _async_initial_report(self, *_: Any) -> None:
        """Schedule initial report."""
        _LOGGER.debug("Reporting initial states")
        for state in self._hass.states.async_all():
            device = Device(self._hass, self._entry_data, state.entity_id, state)
            if not device.should_expose:
                continue

            callback_state = DeviceCallbackState(device, event_entity_id=state.entity_id, initial_report=True)

            if callback_state.should_report:
                self._pending.append(callback_state)

                if self._unsub_pending is None:
                    self._unsub_pending = async_call_later(self._hass, 0, self._report_states_job)

        return None


class YandexDirectNotifier(YandexNotifier):
    """Event notifier for direct connection."""

    @property
    def _base_url(self) -> str:
        """Return base URL."""

        return f"https://dialogs.yandex.net/api/v1/skills/{self._config.skill_id}/callback"

    @property
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""

        return {"Authorization": f"OAuth {self._config.token}"}

    def _format_log_message(self, message: str) -> str:
        """Format and print a message."""

        if self._config.verbose_log:
            return f"{message} [{self._config.skill_id} | {self._config.token}]"

        return message


class YandexCloudNotifier(YandexNotifier):
    """Event notifier for cloud connection."""

    @property
    def _base_url(self) -> str:
        """Return base URL."""

        return "https://yaha-cloud.ru/api/home_assistant/v1/callback"

    @property
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""

        return {"Authorization": f"Bearer {self._config.token}"}
