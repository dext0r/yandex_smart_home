"""Implement the Yandex Smart Home event notification service (notifier)."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from contextlib import suppress
from dataclasses import dataclass
import itertools
import logging
from typing import TYPE_CHECKING, Any, Mapping, Protocol, Self, Sequence

from aiohttp import JsonPayload, hdrs
from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.const import ATTR_ENTITY_ID, EVENT_STATE_CHANGED
from homeassistant.core import HassJob
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE, async_create_clientsession
from homeassistant.helpers.event import TrackTemplate, async_call_later, async_track_template_result
from homeassistant.helpers.template import Template
from pydantic import ValidationError

from . import DOMAIN, const
from .capability import Capability
from .device import Device
from .helpers import APIError
from .property import Property
from .schema import (
    CallbackDiscoveryRequest,
    CallbackDiscoveryRequestPayload,
    CallbackRequest,
    CallbackResponse,
    CallbackStatesRequest,
    CallbackStatesRequestPayload,
    CapabilityInstanceState,
    DeviceState,
    PropertyInstanceState,
)

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State
    from homeassistant.helpers.event import EventStateChangedData, TrackTemplateResult, TrackTemplateResultInfo
    from homeassistant.helpers.typing import EventType

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


class ReportableDeviceState(Protocol):
    """Protocol type for device capabilities and properties."""

    device_id: str

    @property
    @abstractmethod
    def time_sensitive(self) -> bool:
        """Test if value changes should be reported immediately."""
        ...

    @abstractmethod
    def check_value_change(self, other: Self | None) -> bool:
        """Test if the state value differs from other state."""
        ...

    @abstractmethod
    def get_value(self) -> Any:
        """Return the current state value."""
        ...

    @abstractmethod
    def get_instance_state(self) -> CapabilityInstanceState | PropertyInstanceState | None:
        """Return a state for a state query request."""
        ...


class ReportableTemplateDeviceState(ReportableDeviceState, Protocol):
    """Protocol type for custom properties and capabilities."""

    @abstractmethod
    def new_with_value_template(self, value_template: Template) -> Self:
        """Return copy of the state with new value template."""
        ...


class PendingStates:
    """Hold states that about to be reported."""

    def __init__(self) -> None:
        """Initialize."""
        self._device_states: dict[str, list[ReportableDeviceState]] = {}
        self._lock = asyncio.Lock()

    async def async_add(
        self,
        new_states: Sequence[ReportableDeviceState],
        old_states: Sequence[ReportableDeviceState],
    ) -> list[ReportableDeviceState]:
        """Add changed states to pending and return list of them."""
        scheduled_states: list[ReportableDeviceState] = []

        async with self._lock:
            for state in new_states:
                try:
                    old_state = old_states[old_states.index(state)]
                except ValueError:
                    old_state = None
                try:
                    if state.check_value_change(old_state):
                        device_states = self._device_states.setdefault(state.device_id, [])
                        with suppress(ValueError):
                            device_states.remove(state)

                        device_states.append(state)
                        scheduled_states.append(state)
                except APIError as e:
                    _LOGGER.warning(e)

        return scheduled_states

    async def async_get_all(self) -> dict[str, list[ReportableDeviceState]]:
        """Return all states and clear pending."""
        async with self._lock:
            states = self._device_states.copy()
            self._device_states.clear()
            return states

    @property
    def empty(self) -> bool:
        """Test if pending states exist."""
        return not bool(self._device_states)

    @property
    def time_sensitive(self) -> bool:
        """Test if pending states should be sent immediately."""
        for state in itertools.chain(*self._device_states.values()):
            if state.time_sensitive:
                return True

        return False


class YandexNotifier(ABC):
    """Base class for a notifier."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: ConfigEntryData,
        config: NotifierConfig,
        track_templates: Mapping[Template, Sequence[ReportableTemplateDeviceState]],
    ):
        """Initialize."""
        self._hass = hass
        self._entry_data = entry_data
        self._config = config
        self._session = async_create_clientsession(hass)

        self._pending = PendingStates()
        self._report_states_job = HassJob(self._async_report_states)

        self._track_templates = track_templates
        self._template_changes_tracker: TrackTemplateResultInfo | None = None

        self._unsub_state_changed: CALLBACK_TYPE | None = None
        self._unsub_initial_report: CALLBACK_TYPE | None = None
        self._unsub_report_states: CALLBACK_TYPE | None = None
        self._unsub_discovery: CALLBACK_TYPE | None = None

    async def async_setup(self) -> None:
        """Set up the notifier."""
        self._unsub_state_changed = self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_state_changed)
        self._unsub_initial_report = async_call_later(
            self._hass, INITIAL_REPORT_DELAY, HassJob(self._async_initial_report)
        )
        self._unsub_discovery = async_call_later(
            self._hass, DISCOVERY_REQUEST_DELAY, HassJob(self.async_send_discovery)
        )

        if self._track_templates:
            self._template_changes_tracker = async_track_template_result(
                self._hass,
                [TrackTemplate(t, None) for t in self._track_templates],
                self._async_template_result_changed,
            )
            self._template_changes_tracker.async_refresh()

        return None

    async def async_unload(self) -> None:
        """Unload the notifier."""
        for unsub in [
            self._unsub_state_changed,
            self._unsub_initial_report,
            self._unsub_report_states,
            self._unsub_discovery,
        ]:
            if unsub:
                unsub()

        self._unsub_state_changed = None
        self._unsub_initial_report = None
        self._unsub_report_states = None
        self._unsub_discovery = None

        if self._template_changes_tracker is not None:
            self._template_changes_tracker.async_remove()
            self._template_changes_tracker = None

        return None

    async def async_send_discovery(self, *_: Any) -> None:
        """Send notification about change of devices' parameters."""
        _LOGGER.debug(self._format_log_message("Sending discovery request"))
        request = CallbackDiscoveryRequest(payload=CallbackDiscoveryRequestPayload(user_id=self._config.user_id))
        return await self._async_send_request(f"{self._base_url}/discovery", request)

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
        """Format a message."""
        return message

    async def _async_report_states(self, *_: Any) -> None:
        """Send notification about device state change."""
        states: list[DeviceState] = []

        for device_id, device_states in (await self._pending.async_get_all()).items():
            capabilities: list[CapabilityInstanceState] = []
            properties: list[PropertyInstanceState] = []

            for c in [c for c in device_states if isinstance(c, Capability)]:
                try:
                    if (capability_state := c.get_instance_state()) is not None:
                        capabilities.append(capability_state)
                except APIError as e:
                    _LOGGER.warning(e)

            for p in [p for p in device_states if isinstance(p, Property)]:
                try:
                    if (property_state := p.get_instance_state()) is not None:
                        properties.append(property_state)
                except APIError as e:
                    _LOGGER.warning(e)

            if capabilities or properties:
                states.append(
                    DeviceState(
                        id=device_id,
                        capabilities=capabilities or None,
                        properties=properties or None,
                    )
                )

        if states:
            request = CallbackStatesRequest(
                payload=CallbackStatesRequestPayload(user_id=self._config.user_id, devices=states)
            )

            asyncio.create_task(self._async_send_request(f"{self._base_url}/state", request))

        if self._pending.empty:
            self._unsub_report_states = None
        else:
            self._unsub_report_states = async_call_later(
                self._hass,
                delay=0 if self._pending.time_sensitive else REPORT_STATE_WINDOW,
                action=self._report_states_job,
            )

        return None

    # noinspection PyBroadException
    async def _async_send_request(self, url: str, request: CallbackRequest) -> None:
        """Send a request to the url."""
        try:
            _LOGGER.debug(f"Request: {url} (POST data: {request.as_json()})")

            r = await self._session.post(
                url,
                headers=self._request_headers,
                data=JsonPayload(request.as_json(), dumps=lambda p: p),
                timeout=5,
            )

            response_body, error_message = await r.read(), ""
            try:
                response = CallbackResponse.parse_raw(response_body)
                if response.error_message:
                    error_message = response.error_message
            except ValidationError:
                error_message = response_body.decode("utf-8").strip()[:100]

            if r.status != 202 or error_message:
                _LOGGER.warning(self._format_log_message(f"Notification request failed: {error_message or r.status}"))
        except ClientConnectionError as e:
            _LOGGER.warning(self._format_log_message(f"Notification request failed: {e!r}"))
        except asyncio.TimeoutError as e:
            _LOGGER.debug(self._format_log_message(f"Notification request failed: {e!r}"))
        except Exception:
            _LOGGER.exception(self._format_log_message("Unexpected exception"))

        return None

    async def _async_template_result_changed(
        self,
        event_type: EventType[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        """Handle track template changes."""
        if event_type is None:  # update during setup
            return None

        for result in updates:
            old_value_template = Template(str(result.last_result), self._hass)
            new_value_template = Template(str(result.result), self._hass)

            for state in self._track_templates[result.template]:
                old_state = state.new_with_value_template(old_value_template)
                new_state = state.new_with_value_template(new_value_template)

                for pending_state in await self._pending.async_add([new_state], [old_state]):
                    _LOGGER.debug(
                        self._format_log_message(
                            f"State report with value '{pending_state.get_value()!s}' scheduled for {pending_state}"
                        )
                    )

        return self._schedule_report_states()

    async def _async_state_changed(self, event: Event) -> None:
        """Handle state changes."""
        device_id = str(event.data.get(ATTR_ENTITY_ID))
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        if not new_state:
            return None

        new_device = Device(self._hass, self._entry_data, device_id, new_state)
        if not new_device.should_expose:
            return None

        old_states: list[ReportableDeviceState] = []
        new_states: list[ReportableDeviceState] = []

        new_states.extend(new_device.get_state_capabilities())
        new_states.extend(new_device.get_state_properties())

        if old_state:
            old_device = Device(self._hass, self._entry_data, device_id, old_state)
            old_states.extend(old_device.get_state_capabilities())
            old_states.extend(old_device.get_state_properties())

        for pending_state in await self._pending.async_add(new_states, old_states):
            _LOGGER.debug(
                self._format_log_message(
                    f"State report with value '{pending_state.get_value()!s}' scheduled for {pending_state}"
                )
            )

        return self._schedule_report_states()

    async def _async_initial_report(self, *_: Any) -> None:
        """Schedule initial report."""
        _LOGGER.debug("Reporting initial states")
        for state in self._hass.states.async_all():
            device = Device(self._hass, self._entry_data, state.entity_id, state)
            if not device.should_expose:
                continue

            await self._pending.async_add(device.get_capabilities(), [])
            await self._pending.async_add([p for p in device.get_properties() if p.report_on_startup], [])

        return self._schedule_report_states()

    def _schedule_report_states(self) -> None:
        """Schedule run report states job if there are pending states."""
        if self._pending.empty or self._unsub_report_states:
            return None

        self._unsub_report_states = async_call_later(
            self._hass,
            delay=0 if self._pending.time_sensitive else REPORT_STATE_WINDOW,
            action=self._report_states_job,
        )

        return None


class YandexDirectNotifier(YandexNotifier):
    """Notifier for direct connection."""

    @property
    def _base_url(self) -> str:
        """Return base URL."""
        return f"https://dialogs.yandex.net/api/v1/skills/{self._config.skill_id}/callback"

    @property
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""
        return {hdrs.AUTHORIZATION: f"OAuth {self._config.token}"}

    def _format_log_message(self, message: str) -> str:
        """Format a message."""
        if self._config.verbose_log:
            return f"{message} ({self._config.user_id }@{self._config.skill_id})"

        return message


class YandexCloudNotifier(YandexNotifier):
    """Notifier for cloud connection."""

    @property
    def _base_url(self) -> str:
        """Return base URL."""
        return f"{const.CLOUD_BASE_URL}/api/home_assistant/v1/callback"

    @property
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""
        return {
            hdrs.AUTHORIZATION: f"Bearer {self._config.token}",
            hdrs.USER_AGENT: f"{SERVER_SOFTWARE} {DOMAIN}/{self._entry_data.version}",
        }
