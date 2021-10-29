"""Implement the Yandex Smart Home custom capabilities."""
from __future__ import annotations

from abc import ABC
import itertools
import logging
from typing import Any

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.service import async_call_from_config

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
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
)
from .error import SmartHomeError
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)


class CustomCapability(AbstractCapability, ABC):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        super().__init__(hass, config, state)
        self.instance = instance
        self.capability_config = capability_config
        self.state_entity_id = self.capability_config.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
        self.retrievable = bool(self.state_entity_id or self.state_value_attribute)

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return self.capability_config.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)

    def get_value(self) -> float | str | None:
        """Return the state value of this capability for this entity."""
        if not self.retrievable:
            return None

        entity_state = self.state

        if self.state_entity_id:
            entity_state = self.hass.states.get(self.state_entity_id)
            if not entity_state:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Entity {self.state_entity_id} not found for {self.instance} instance of {self.state.entity_id}'
                )

        if self.state_value_attribute:
            value = entity_state.attributes.get(self.state_value_attribute)
        else:
            value = entity_state.state

        return value


class CustomModeCapability(CustomCapability, ModeCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        super().__init__(hass, config, state, instance, capability_config)

        self.set_mode_config = self.capability_config[const.CONF_ENTITY_CUSTOM_MODE_SET_MODE]

    @property
    def supported_ha_modes(self) -> list[str]:
        """Returns list of supported HA modes for this entity."""
        modes = self.entity_config.get(CONF_ENTITY_MODE_MAP, {}).get(self.instance, {})
        rv = list(itertools.chain(*modes.values()))
        return rv

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return None

    def get_value(self) -> str | None:
        """Return the state value of this capability for this entity."""
        if not self.retrievable:
            return None

        return self.get_yandex_mode_by_ha_mode(super().get_value())

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await async_call_from_config(
            self.hass,
            self.set_mode_config,
            validate_config=False,
            variables={'mode': self.get_ha_mode_by_yandex_mode(state['value'])},
            blocking=True,
            context=data.context
        )


class CustomToggleCapability(CustomCapability, ToggleCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        super().__init__(hass, config, state, instance, capability_config)

        self.turn_on_config = self.capability_config[const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON]
        self.turn_off_config = self.capability_config[const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF]

    def supported(self) -> bool:
        """Test if capability is supported."""
        return True

    def get_value(self) -> bool | None:
        """Return the state value of this capability for this entity."""
        if not self.retrievable:
            return None

        return super().get_value() in [STATE_ON, True]

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await async_call_from_config(
            self.hass,
            self.turn_on_config if state['value'] else self.turn_off_config,
            validate_config=False,
            blocking=True,
            context=data.context
        )


class CustomRangeCapability(CustomCapability, RangeCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        self.capability_config = capability_config

        self.set_value = self.capability_config.get(const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE)
        self.increase_value = self.capability_config.get(const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE)
        self.decrease_value = self.capability_config.get(const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE)

        super().__init__(hass, config, state, instance, capability_config)

        self.default_range = (
            self.capability_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, self.default_range[0]),
            self.capability_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, self.default_range[1]),
            self.capability_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, self.default_range[2])
        )

    def supported(self) -> bool:
        """Test if capability is supported."""
        return True

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        for key in [CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_MAX]:
            if key not in self.capability_config.get(CONF_ENTITY_RANGE, {}):
                return False

        return self.set_value is not None

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        if not self.retrievable:
            return None

        return self.float_value(super().get_value())

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value']
        service = self.set_value

        if state.get('relative'):
            if self.increase_value or self.decrease_value:
                if value >= 0:
                    service = self.increase_value
                else:
                    service = self.decrease_value
            else:
                if not self.retrievable:
                    raise SmartHomeError(
                        ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                        f'Failed to set relative value for {self.instance} instance of {self.state.entity_id}. '
                        f'No state or service found.'
                    )

                value = self.get_absolute_value(state['value'])

        await async_call_from_config(
            self.hass,
            service,
            validate_config=False,
            variables={'value': value},
            blocking=True,
            context=data.context
        )
