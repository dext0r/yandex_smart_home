"""Implement the Yandex Smart Home event notification service (notifier)."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
import itertools
import logging
from random import randint
import re
from typing import TYPE_CHECKING, Any, Literal, Protocol, Self

from aiohttp import ClientTimeout, JsonPayload, hdrs
from aiohttp.client_exceptions import ClientConnectionError, ClientPayloadError
from homeassistant.const import ATTR_ENTITY_ID, EVENT_STATE_CHANGED
from homeassistant.core import CALLBACK_TYPE, Event, HassJob, HomeAssistant, State
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE, async_create_clientsession
from homeassistant.helpers.event import (
    EventStateChangedData,
    TrackTemplate,
    TrackTemplateResult,
    TrackTemplateResultInfo,
    async_call_later,
    async_track_template_result,
)
from homeassistant.helpers.template import Template
from pydantic import ValidationError

from . import DOMAIN
from .capability import Capability
from .const import CLOUD_BASE_URL, EntityId
from .device import Device, DeviceId
from .helpers import APIError, SmartHomePlatform
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
    from .entry_data import ConfigEntryData

_LOGGER = logging.getLogger(__name__)

INITIAL_REPORT_DELAY = timedelta(seconds=15)
DISCOVERY_REQUEST_DELAY = timedelta(seconds=5)
HEARTBEAT_REPORT_INTERVAL = timedelta(hours=1)
REPORT_STATE_WINDOW = timedelta(seconds=1)
YANDEX_BATCH_SIZE = 5
YANDEX_BATCH_INTERVAL = 0.5
YANDEX_RETRY_DELAYS = (5, 20)
YANDEX_LIMIT_PAUSE = 300
YANDEX_FAILURE_PAUSE = 60


@dataclass
class NotifierConfig:
    """Hold configuration for a notifier."""

    user_id: str
    token: str
    skill_id: str | None = None
    platform: SmartHomePlatform | None = None
    extended_log: bool = False


class ReportableDeviceState(Protocol):
    """Protocol type for device capabilities and properties."""

    device_id: str

    @property
    @abstractmethod
    def retrievable(self) -> bool:
        """Return whether the value describes a queryable state."""
        ...

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


class ReportableDeviceStateFromEntityState(ReportableDeviceState, Protocol):
    @abstractmethod
    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData, device_id: str, state: State):
        """Initialize a capability or property for the state."""
        ...


class ReportableTemplateDeviceState(ReportableDeviceState, Protocol):
    """Protocol type for custom properties and capabilities."""

    @abstractmethod
    def new_with_value(self, value: Any) -> Self:
        """Return copy of the state with new value."""
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

    async def async_restore(self, states: dict[str, list[ReportableDeviceState]]) -> None:
        """Keep current values across a pause without delivering old one-shot events."""
        async with self._lock:
            for device_id, items in list(self._device_states.items()):
                if current := [item for item in items if item.retrievable]:
                    self._device_states[device_id] = current
                else:
                    del self._device_states[device_id]
            for device_id, states_to_restore in states.items():
                pending = self._device_states.setdefault(device_id, [])
                pending.extend(state for state in states_to_restore if state not in pending)

    @property
    def empty(self) -> bool:
        """Test if pending states exist."""
        return not bool(self._device_states)

    @property
    def time_sensitive(self) -> bool:
        """Test if pending states should be sent immediately."""
        return any(state.time_sensitive for state in itertools.chain(*self._device_states.values()))


class Notifier(ABC):
    """Base class for a notifier."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: ConfigEntryData,
        config: NotifierConfig,
        track_templates: Mapping[Template, Sequence[ReportableTemplateDeviceState]],
        track_entity_states: Mapping[EntityId, Sequence[tuple[DeviceId, type[ReportableDeviceStateFromEntityState]]]],
    ):
        """Initialize."""
        self._hass = hass
        self._entry_data = entry_data
        self._config = config
        self._session = async_create_clientsession(hass)

        self._pending = PendingStates()

        self._track_entity_states = track_entity_states
        self._track_templates = track_templates
        self._template_changes_tracker: TrackTemplateResultInfo | None = None

        self._unsub_state_changed: CALLBACK_TYPE | None = None
        self._unsub_initial_report: CALLBACK_TYPE | None = None
        self._unsub_heartbeat_report: CALLBACK_TYPE | None = None
        self._unsub_report_states: CALLBACK_TYPE | None = None
        self._unsub_discovery: CALLBACK_TYPE | None = None
        self._report_task: asyncio.Task[Any] | None = None
        self._state_paused_until = 0.0
        self._unloaded = False

    @property
    def _manage_yandex_delivery(self) -> bool:
        return False

    async def async_setup(self) -> None:
        """Set up the notifier."""
        self._unloaded = False
        self._unsub_state_changed = self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_state_changed)
        self._unsub_initial_report = async_call_later(
            self._hass, INITIAL_REPORT_DELAY, HassJob(self._async_initial_report)
        )
        if not self._manage_yandex_delivery:
            self._unsub_heartbeat_report = async_call_later(
                self._hass,
                delay=HEARTBEAT_REPORT_INTERVAL + timedelta(minutes=randint(1, 15)),  # noqa: S311
                action=HassJob(self._async_hearbeat_report),
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

    async def async_unload(self) -> None:
        """Unload the notifier."""
        self._unloaded = True
        for unsub in [
            self._unsub_state_changed,
            self._unsub_initial_report,
            self._unsub_heartbeat_report,
            self._unsub_report_states,
            self._unsub_discovery,
        ]:
            if unsub:
                unsub()

        self._unsub_state_changed = None
        self._unsub_initial_report = None
        self._unsub_heartbeat_report = None
        self._unsub_report_states = None
        self._unsub_discovery = None

        if self._template_changes_tracker is not None:
            self._template_changes_tracker.async_remove()
            self._template_changes_tracker = None

        if self._report_task is not None:
            self._report_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._report_task

    async def async_send_discovery(self, *_: Any) -> None:
        """Send notification about change of devices' parameters."""
        self._debug_log("Sending discovery request")
        request = CallbackDiscoveryRequest(payload=CallbackDiscoveryRequestPayload(user_id=self._config.user_id))
        await self._async_send_request(f"{self._base_url}/discovery", request)

    @property
    @abstractmethod
    def _base_url(self) -> str:
        """Return base URL."""

    @property
    @abstractmethod
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""

    def _format_log_message(self, message: str) -> str:
        """Format a message."""
        if self._config.extended_log:
            return f"{self._entry_data.entry.title}: {message}"

        return message

    def _debug_log(self, message: str) -> None:
        """Log a debug message."""
        if self._config.extended_log:
            message = f"({self._entry_data.entry.entry_id[:6]}) {message}"

        _LOGGER.debug(message)

    async def _async_report_states(self, *_: Any) -> None:
        """Send notification about device state change."""
        if self._unloaded or self._report_task is not None:
            return
        self._unsub_report_states = None
        self._report_task = asyncio.current_task()
        try:
            await self._async_drain_states()
        finally:
            self._report_task = None
            self._schedule_report_states()

    async def _async_drain_states(self) -> None:
        pending = await self._pending.async_get_all()
        states: list[DeviceState] = []
        for device_id, device_states in pending.items():
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

        if not states:
            return

        size = YANDEX_BATCH_SIZE if self._manage_yandex_delivery else len(states)
        for offset in range(0, len(states), size):
            if offset:
                await asyncio.sleep(YANDEX_BATCH_INTERVAL)
            batch = states[offset : offset + size]
            request = CallbackStatesRequest(
                payload=CallbackStatesRequestPayload(user_id=self._config.user_id, devices=batch)
            )
            result, retry_after = await self._async_send_request(f"{self._base_url}/state", request)
            if not self._manage_yandex_delivery:
                return

            # A timeout may have delivered a button-like event; never replay such a batch.
            if all(item.retrievable for device in batch for item in pending[device.id]):
                for delay in YANDEX_RETRY_DELAYS:
                    if result != "temporary":
                        break
                    await asyncio.sleep(max(delay, retry_after))
                    result, retry_after = await self._async_send_request(f"{self._base_url}/state", request)

            if result in ("limited", "temporary"):
                pause = YANDEX_LIMIT_PAUSE if result == "limited" else YANDEX_FAILURE_PAUSE
                self._state_paused_until = self._hass.loop.time() + max(pause, retry_after)
                # Defer unsent values without replaying failed batches or queued button presses.
                unsent = {
                    device.id: [item for item in pending[device.id] if item.retrievable]
                    for device in states[offset + size :]
                }
                await self._pending.async_restore({device_id: items for device_id, items in unsent.items() if items})
                break

    async def _async_send_request(
        self, url: str, request: CallbackRequest
    ) -> tuple[Literal["ok", "temporary", "limited", "rejected"], float]:
        """Send one notification and classify the response."""
        try:
            self._debug_log(f"Request: {url} (POST data: {request.as_json()})")
            async with self._session.post(
                url,
                headers=self._request_headers,
                data=JsonPayload(request.as_json(), dumps=lambda p: p),
                timeout=ClientTimeout(total=5),
            ) as response:
                response_body = await response.read()
                status = response.status
                retry_after = response.headers.get(hdrs.RETRY_AFTER, "")

            error_code = None
            try:
                callback = CallbackResponse.model_validate_json(response_body)
                error_code = callback.error_code
                error_message = callback.error_message or error_code or ""
                if callback.status != "ok" and not error_message:
                    error_message = "callback returned an error"
            except ValidationError:
                error_message = response_body.decode("utf-8", errors="replace").strip()[:100]

            if status == 202 and not error_message:
                return "ok", 0
            _LOGGER.warning(self._format_log_message(f"State notification request failed: {error_message or status}"))
            if error_code in ("BAD_REQUEST", "UNKNOWN_USER"):
                return "rejected", 0
            if status == 429 or re.search(r"\bHTTP\s+429\b", error_message, re.IGNORECASE):
                return "limited", _retry_after_seconds(retry_after)
            if (
                500 <= status < 600
                or re.search(r"\bHTTP\s+5\d\d\b", error_message, re.IGNORECASE)
                or any(
                    reason in error_message.lower()
                    for reason in ("circuit breaker is open", "context deadline exceeded", "connection reset by peer")
                )
            ):
                return "temporary", _retry_after_seconds(retry_after)
        except (ClientConnectionError, ClientPayloadError) as e:
            _LOGGER.warning(self._format_log_message(f"State notification request failed: {e!r}"))
            return "temporary", 0
        except TimeoutError as e:
            self._debug_log(f"State notification request failed: {e!r}")
            return "temporary", 0
        except Exception:
            _LOGGER.exception(self._format_log_message("Unexpected exception"))
        return "rejected", 0

    async def _async_template_result_changed(
        self,
        event_type: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        """Handle track template changes."""
        if event_type is None:  # update during setup
            return None

        for result in updates:
            if isinstance(result.result, TemplateError):
                _LOGGER.warning(f"Error while processing template: {result.template.template}", exc_info=result.result)
                continue
            if isinstance(result.last_result, TemplateError):
                result.last_result = None

            for state in self._track_templates[result.template]:
                if self._state_paused_until > self._hass.loop.time() and not state.retrievable:
                    continue
                old_state = state.new_with_value(result.last_result)
                new_state = state.new_with_value(result.result)

                for pending_state in await self._pending.async_add([new_state], [old_state]):
                    self._debug_log(
                        f"State report with value '{pending_state.get_value()}' scheduled for {pending_state!r}"
                    )

        return self._schedule_report_states()

    async def _async_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle state changes."""
        entity_id = str(event.data.get(ATTR_ENTITY_ID))
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        if not new_state:
            return None

        old_device_states: list[ReportableDeviceState] = []
        new_device_states: list[ReportableDeviceState] = []

        for device_id, cls in self._track_entity_states.get(entity_id, []):
            new_device_states.append(cls(self._hass, self._entry_data, device_id, new_state))
            if old_state:
                old_device_states.append(cls(self._hass, self._entry_data, device_id, old_state))

        new_device = Device(self._hass, self._entry_data, entity_id, new_state)
        if new_device.should_expose:
            new_device_states.extend(new_device.get_state_capabilities())
            new_device_states.extend(new_device.get_state_properties())

            if old_state:
                old_device = Device(self._hass, self._entry_data, entity_id, old_state)
                old_device_states.extend(old_device.get_state_capabilities())
                old_device_states.extend(old_device.get_state_properties())

        if self._state_paused_until > self._hass.loop.time():
            new_device_states = [state for state in new_device_states if state.retrievable]
        for pending_state in await self._pending.async_add(new_device_states, old_device_states):
            self._debug_log(f"State report with value '{pending_state.get_value()}' scheduled for {pending_state!r}")

        return self._schedule_report_states()

    async def _async_initial_report(self, *_: Any) -> None:
        """Schedule initial report."""
        self._debug_log("Reporting initial states")
        for state in self._hass.states.async_all():
            device = Device(self._hass, self._entry_data, state.entity_id, state)
            if device.should_expose:
                await self._pending.async_add(device.get_capabilities(), [])
                await self._pending.async_add([p for p in device.get_properties() if p.heartbeat_report], [])

        return self._schedule_report_states()

    async def _async_hearbeat_report(self, *_: Any) -> None:
        """Schedule periodical state report."""
        self._debug_log("Reporting states (heartbeat)")
        for state in self._hass.states.async_all():
            device = Device(self._hass, self._entry_data, state.entity_id, state)
            if device.should_expose:
                await self._pending.async_add([p for p in device.get_properties() if p.heartbeat_report], [])

        self._unsub_heartbeat_report = async_call_later(
            self._hass,
            delay=HEARTBEAT_REPORT_INTERVAL,
            action=HassJob(self._async_hearbeat_report),
        )
        return self._schedule_report_states()

    def _schedule_report_states(self) -> None:
        """Schedule run report states job if there are pending states."""
        if self._unloaded or self._pending.empty or self._unsub_report_states or self._report_task:
            return

        delay: float | timedelta = 0 if self._pending.time_sensitive else REPORT_STATE_WINDOW
        if (paused_for := self._state_paused_until - self._hass.loop.time()) > 0:
            delay = paused_for
        self._unsub_report_states = async_call_later(
            self._hass,
            delay=delay,
            action=HassJob(self._async_report_states),
        )


class YandexDirectNotifier(Notifier):
    """Notifier for direct connection."""

    @property
    def _base_url(self) -> str:
        """Return base URL."""
        return f"https://dialogs.yandex.net/api/v1/skills/{self._config.skill_id}/callback"

    @property
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""
        return {hdrs.AUTHORIZATION: f"OAuth {self._config.token}"}


class CloudNotifier(Notifier):
    """Notifier for cloud connections."""

    @property
    def _manage_yandex_delivery(self) -> bool:
        return self._config.platform == SmartHomePlatform.YANDEX

    @property
    def _base_url(self) -> str:
        """Return base URL."""
        return f"{CLOUD_BASE_URL}/api/home_assistant/v2/callback/{self._config.platform}"

    @property
    def _request_headers(self) -> dict[str, str]:
        """Return headers for a request."""
        return {
            hdrs.AUTHORIZATION: f"Bearer {self._config.token}",
            hdrs.USER_AGENT: f"{SERVER_SOFTWARE} {DOMAIN}/{self._entry_data.component_version}",
        }


def _retry_after_seconds(value: str) -> float:
    if value.isascii() and value.isdecimal() and len(value) <= 10:
        return int(value)
    with suppress(TypeError, ValueError, OverflowError):
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        return max(0, (date - datetime.now(UTC)).total_seconds())
    return 0
