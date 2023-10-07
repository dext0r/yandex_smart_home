"""Implement the Yandex Smart Home user specific capabilities."""
from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING, Any, Protocol

from homeassistant.const import STATE_OFF
from homeassistant.core import State
from homeassistant.helpers.service import async_call_from_config

from .capability import Capability
from .capability_mode import ModeCapability
from .capability_range import RangeCapability
from .capability_toggle import ToggleCapability
from .const import (
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
    CONF_ENTITY_CUSTOM_MODE_SET_MODE,
    CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE,
    CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE,
    CONF_ENTITY_CUSTOM_RANGE_SET_VALUE,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON,
    CONF_ENTITY_MODE_MAP,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
)
from .helpers import APIError
from .schema import (
    CapabilityInstance,
    CapabilityType,
    ModeCapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
    RangeCapabilityInstance,
    RangeCapabilityInstanceActionState,
    RangeCapabilityRange,
    ResponseCode,
    ToggleCapabilityInstance,
    ToggleCapabilityInstanceActionState,
)

if TYPE_CHECKING:
    from homeassistant.core import Context, HomeAssistant
    from homeassistant.helpers import ConfigType

    from .entry_data import ConfigEntryData

_LOGGER = logging.getLogger(__name__)


class CustomCapability(Capability[Any], Protocol):
    """Base class for a capability that user can set up using yaml configuration."""

    _config: ConfigType
    _value_source: State | None

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: ConfigEntryData,
        config: ConfigType,
        instance: CapabilityInstance,
        device_id: str,
        value_source: State | None,
    ):
        """Initialize a custom capability."""
        self._hass = hass
        self._entry_data = entry_data
        self._config = config
        self._value_source = value_source

        self.device_id = device_id
        self.instance = instance

    # noinspection PyProtocol
    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        for attr in (
            CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE,
            CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
        ):
            if self._config.get(attr):
                return True

        return False

    @property
    def reportable(self) -> bool:
        """Test if the capability can report changes."""
        if not self.retrievable:
            return False

        return super().reportable

    def _get_source_value(self) -> Any:
        """Return the current capability value (unprocessed)."""
        if self._value_source is None:
            return None

        if value_attribute := self._config.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE):
            return self._value_source.attributes.get(value_attribute)

        return self._value_source.state


class CustomModeCapability(CustomCapability, ModeCapability):
    """Mode capability that user can set up using yaml configuration."""

    instance: ModeCapabilityInstance

    @property
    def supported_ha_modes(self) -> list[str]:
        """Returns list of supported HA modes."""
        modes = self._entity_config.get(CONF_ENTITY_MODE_MAP, {}).get(self.instance, {})
        rv = list(itertools.chain(*modes.values()))
        return rv

    def get_value(self) -> ModeCapabilityMode | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        return self.get_yandex_mode_by_ha_mode(self._get_source_value())

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""

        await async_call_from_config(
            self._hass,
            self._config[CONF_ENTITY_CUSTOM_MODE_SET_MODE],
            validate_config=False,
            variables={"mode": self.get_ha_mode_by_yandex_mode(state.value)},
            blocking=True,
            context=context,
        )


class CustomToggleCapability(CustomCapability, ToggleCapability):
    """Toggle capability that user can set up using yaml configuration."""

    instance: ToggleCapabilityInstance

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return True

    def get_value(self) -> bool | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        value = self._get_source_value()
        if value is None:
            return None

        return value not in [STATE_OFF, False]

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        turn_on_config = self._config[CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON]
        turn_off_config = self._config[CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF]

        await async_call_from_config(
            self._hass,
            turn_on_config if state.value else turn_off_config,
            validate_config=False,
            blocking=True,
            context=context,
        )


class CustomRangeCapability(CustomCapability, RangeCapability):
    """Range capability that user can set up using yaml configuration."""

    instance: RangeCapabilityInstance

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return True

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        for key in [CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_MAX]:
            if key not in self._config.get(CONF_ENTITY_RANGE, {}):
                return False

        return self._set_value_service_config is not None

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        config = self._set_value_service_config
        value = state.value

        if state.relative:
            if self._increase_value_service_config or self._decrease_value_service_config:
                if state.value >= 0:
                    config = self._increase_value_service_config
                else:
                    config = self._decrease_value_service_config
            else:
                if not self.retrievable:
                    raise APIError(
                        ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                        f"Failed to set relative value for {self.instance.value} instance of {self.device_id}. "
                        f"No state source or service found.",
                    )

                value = self._get_absolute_value(state.value)

        if not config:
            raise APIError(ResponseCode.INTERNAL_ERROR, "Missing capability service")

        await async_call_from_config(
            self._hass,
            config,
            validate_config=False,
            variables={"value": value},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if not self.retrievable:
            return None

        return self._convert_to_float(self._get_source_value())

    def _get_absolute_value(self, relative_value: float) -> float:
        """Return the absolute value for a relative value."""
        value = self._get_value()

        if value is None:
            if isinstance(self._value_source, State):
                if (
                    self._config.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)
                    and self._value_source.state == STATE_OFF
                ):
                    raise APIError(
                        ResponseCode.DEVICE_OFF, f"Device {self._value_source.entity_id} probably turned off"
                    )

            raise APIError(
                ResponseCode.INVALID_VALUE,
                f"Unable to get current value for {self.instance.value} instance of {self.device_id}",
            )

        return max(min(value + relative_value, self._range.max), self._range.min)

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(
            min=self._config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, super()._default_range.min),
            max=self._config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, super()._default_range.max),
            precision=self._config.get(CONF_ENTITY_RANGE, {}).get(
                CONF_ENTITY_RANGE_PRECISION, super()._default_range.precision
            ),
        )

    @property
    def _set_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting value action."""
        return self._config.get(CONF_ENTITY_CUSTOM_RANGE_SET_VALUE)

    @property
    def _increase_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting increase value action."""
        return self._config.get(CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE)

    @property
    def _decrease_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting decrease value action."""
        return self._config.get(CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE)


def get_custom_capability(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    capability_config: ConfigType,
    capability_type: CapabilityType,
    instance: str,
    device_id: str,
) -> CustomCapability:
    """Return initialized custom capability based on parameters."""
    value_source: State | None = None
    value_source_entity_id = capability_config.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
    value_source_attribute = capability_config.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)

    if value_source_entity_id or value_source_attribute:
        value_source_entity_id = value_source_entity_id or device_id

        state = hass.states.get(value_source_entity_id)
        if not state:
            raise APIError(
                ResponseCode.DEVICE_UNREACHABLE,
                f"Entity {value_source_entity_id} not found for {instance} instance of {device_id}",
            )

        value_source = state

    match capability_type:
        case CapabilityType.MODE:
            return CustomModeCapability(
                hass, entry_data, capability_config, ModeCapabilityInstance(instance), device_id, value_source
            )
        case CapabilityType.TOGGLE:
            return CustomToggleCapability(
                hass, entry_data, capability_config, ToggleCapabilityInstance(instance), device_id, value_source
            )
        case CapabilityType.RANGE:
            return CustomRangeCapability(
                hass, entry_data, capability_config, RangeCapabilityInstance(instance), device_id, value_source
            )

    raise ValueError(f"Unsupported capability type: {capability_type}")
