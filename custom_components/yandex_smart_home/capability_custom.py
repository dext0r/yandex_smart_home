"""Implement the Yandex Smart Home user specific capabilities."""
from abc import ABC
import itertools
import logging
from typing import Any

from homeassistant.const import STATE_OFF
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.helpers.service import async_call_from_config
from homeassistant.helpers.typing import ConfigType

from . import const
from .capability import AbstractCapability
from .capability_mode import ModeCapability
from .capability_range import RangeCapability
from .capability_toggle import ToggleCapability
from .const import (
    CONF_ENTITY_MODE_MAP,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
    ERR_DEVICE_UNREACHABLE,
    ERR_INTERNAL_ERROR,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
)
from .error import SmartHomeError
from .helpers import Config
from .schema import (
    CapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
    RangeCapabilityInstanceActionState,
    RangeCapabilityRange,
    ToggleCapabilityInstanceActionState,
)

_LOGGER = logging.getLogger(__name__)


class CustomCapability(AbstractCapability, ABC):
    """Base class for capabilities that user can set up using yaml configuration."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: Config,
        state: State,
        instance: CapabilityInstance,
        capability_config: dict[str, Any],
    ):
        super().__init__(hass, config, state)

        self.instance = instance

        self._capability_config = capability_config
        self._state_entity_id = self._capability_config.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)

    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        return bool(self._state_entity_id or self._state_value_attribute)

    def get_value(self) -> Any:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        entity_state = self.state

        if self._state_entity_id:
            state_by_entity_id = self._hass.states.get(self._state_entity_id)
            if not state_by_entity_id:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f"Entity {self._state_entity_id} not found for "
                    f"{self.instance} instance of {self.state.entity_id}",
                )

            entity_state = state_by_entity_id

        if self._state_value_attribute:
            value = entity_state.attributes.get(self._state_value_attribute)
        else:
            value = entity_state.state

        return value

    @property
    def _state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return self._capability_config.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)


class CustomModeCapability(CustomCapability, ModeCapability):
    """Mode capability that user can set up using yaml configuration."""

    @property
    def supported_ha_modes(self) -> list[str]:
        """Returns list of supported HA modes."""
        modes = self._entity_config.get(CONF_ENTITY_MODE_MAP, {}).get(self.instance, {})
        rv = list(itertools.chain(*modes.values()))
        return rv

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for the entity."""
        return None

    def get_value(self) -> ModeCapabilityMode | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        return self.get_yandex_mode_by_ha_mode(super().get_value())

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""

        await async_call_from_config(
            self._hass,
            self._capability_config[const.CONF_ENTITY_CUSTOM_MODE_SET_MODE],
            validate_config=False,
            variables={"mode": self.get_ha_mode_by_yandex_mode(state.value)},
            blocking=True,
            context=context,
        )


class CustomToggleCapability(CustomCapability, ToggleCapability):
    """Toggle capability that user can set up using yaml configuration."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported for its state."""
        return True

    def get_value(self) -> bool | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        return super().get_value() not in [STATE_OFF, False]

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        turn_on_config = self._capability_config[const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON]
        turn_off_config = self._capability_config[const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF]

        await async_call_from_config(
            self._hass,
            turn_on_config if state.value else turn_off_config,
            validate_config=False,
            blocking=True,
            context=context,
        )


class CustomRangeCapability(CustomCapability, RangeCapability):
    """Range capability that user can set up using yaml configuration."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported for its state."""
        return True

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        for key in [CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_MAX]:
            if key not in self._capability_config.get(CONF_ENTITY_RANGE, {}):
                return False

        return self._set_value_service_config is not None

    def get_value(self) -> float | None:
        """Return the current capability value."""
        return RangeCapability.get_value(self)

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
                    raise SmartHomeError(
                        ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                        f"Failed to set relative value for {self.instance.value} instance of {self.state.entity_id}. "
                        f"No state or service found.",
                    )

                value = self._get_absolute_value(state.value)

        if not config:
            raise SmartHomeError(ERR_INTERNAL_ERROR, "Missing capability service")

        await async_call_from_config(
            self._hass,
            config,
            validate_config=False,
            variables={"value": value},
            blocking=True,
            context=context,
        )

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(
            min=self._capability_config.get(CONF_ENTITY_RANGE, {}).get(
                CONF_ENTITY_RANGE_MIN, super()._default_range.min
            ),
            max=self._capability_config.get(CONF_ENTITY_RANGE, {}).get(
                CONF_ENTITY_RANGE_MAX, super()._default_range.max
            ),
            precision=self._capability_config.get(CONF_ENTITY_RANGE, {}).get(
                CONF_ENTITY_RANGE_PRECISION, super()._default_range.precision
            ),
        )

    @property
    def _set_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting value action."""
        return self._capability_config.get(const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE)

    @property
    def _increase_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting increase value action."""
        return self._capability_config.get(const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE)

    @property
    def _decrease_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting decrease value action."""
        return self._capability_config.get(const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE)

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if not self.retrievable:
            return None

        return self._convert_to_float(CustomCapability.get_value(self))
