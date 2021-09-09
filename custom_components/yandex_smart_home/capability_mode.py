"""Implement the Yandex Smart Home modes capabilities."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any

from homeassistant.components import climate, fan, humidifier, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import CONF_ENTITY_MODE_MAP, ERR_INVALID_VALUE, STATE_NONE
from .error import SmartHomeError
from .helpers import RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_MODE = PREFIX_CAPABILITIES + 'mode'


class ModeCapability(AbstractCapability, ABC):
    """Base class of capabilities with mode functionality like thermostat mode
    or fan speed.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/mode-docpage/
    """

    type = CAPABILITIES_MODE
    modes_map_default: dict[str, list[str]] = {}
    modes_map_index_fallback: dict[int, str] = {}

    def supported(self) -> bool:
        """Test if capability is supported."""
        return bool(self.supported_yandex_modes)

    def parameters(self) -> dict[str, Any]:
        """Return parameters for a devices request."""
        return {
            'instance': self.instance,
            'modes': [{'value': v} for v in self.supported_yandex_modes],
        }

    @property
    def supported_yandex_modes(self) -> list[str]:
        """Returns list of supported Yandex modes for this entity."""
        modes = []

        for ha_value in self.supported_ha_modes:
            value = self.get_yandex_mode_by_ha_mode(ha_value, hide_warnings=True)
            if value is not None and value not in modes:
                modes.append(value)

        return modes

    @property
    def supported_ha_modes(self) -> list[str]:
        """Returns list of supported HA modes for this entity."""
        return self.state.attributes.get(self.modes_list_attribute, [])

    @property
    def modes_map(self) -> dict[str, list[str]]:
        """Return modes mapping between Yandex and HA."""
        if CONF_ENTITY_MODE_MAP in self.entity_config:
            modes = self.entity_config.get(CONF_ENTITY_MODE_MAP, {})
            if self.instance in modes:
                return modes.get(self.instance)

        return self.modes_map_default

    @property
    @abstractmethod
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        pass

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return None

    def get_yandex_mode_by_ha_mode(self, ha_mode: str, hide_warnings=False) -> str | None:
        rv = None
        for yandex_mode, names in self.modes_map.items():
            lower_names = [str(n).lower() for n in names]
            if str(ha_mode).lower() in lower_names:
                rv = yandex_mode
                break

        if rv is None and self.modes_map_index_fallback:
            try:
                rv = self.modes_map_index_fallback[self.supported_ha_modes.index(ha_mode)]
            except (IndexError, ValueError, KeyError):
                pass

        if rv is not None and ha_mode not in self.supported_ha_modes:
            err = f'Unsupported HA mode "{ha_mode}" for {self.instance} instance of {self.state.entity_id}.'
            if self.modes_list_attribute:
                err += f' Maybe it missing in entity attribute {self.modes_list_attribute}?'

            raise SmartHomeError(ERR_INVALID_VALUE, err)

        if not hide_warnings and rv is None and \
                str(ha_mode).lower() not in (STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
            _LOGGER.warning(
                f'Unable to get Yandex mode for "{ha_mode}" for {self.instance} instance '
                f'of {self.state.entity_id}. It may cause inconsistencies between Yandex and HA. '
                f'Check \"modes\" setting for this entity'
            )

        return rv

    def get_ha_mode_by_yandex_mode(self, yandex_mode: str) -> str:
        ha_modes = self.modes_map.get(yandex_mode, [])
        for ha_mode in ha_modes:
            for am in self.supported_ha_modes:
                if str(am).lower() == str(ha_mode).lower():
                    return am

        for ha_idx, yandex_mode_idx in self.modes_map_index_fallback.items():
            if yandex_mode_idx == yandex_mode:
                return self.supported_ha_modes[ha_idx]

        raise SmartHomeError(
            ERR_INVALID_VALUE,
            f'Unsupported mode "{yandex_mode}" for {self.instance} instance of {self.state.entity_id}. '
            f'Check \"modes\" setting for this entity'
        )

    def get_value(self) -> str | None:
        """Return the state value of this capability for this entity."""
        ha_mode = self.state.state
        if self.state_value_attribute:
            ha_mode = self.state.attributes.get(self.state_value_attribute)
        return self.get_yandex_mode_by_ha_mode(ha_mode, False)


@register_capability
class ThermostatCapability(ModeCapability):
    """Thermostat functionality"""

    instance = const.MODE_INSTANCE_THERMOSTAT
    modes_map_default = {
        const.MODE_INSTANCE_MODE_HEAT: [climate.const.HVAC_MODE_HEAT],
        const.MODE_INSTANCE_MODE_COOL: [climate.const.HVAC_MODE_COOL],
        const.MODE_INSTANCE_MODE_AUTO: [climate.const.HVAC_MODE_HEAT_COOL, climate.const.HVAC_MODE_AUTO],
        const.MODE_INSTANCE_MODE_DRY: [climate.const.HVAC_MODE_DRY],
        const.MODE_INSTANCE_MODE_FAN_ONLY: [climate.const.HVAC_MODE_FAN_ONLY],
    }

    def supported(self) -> bool:
        """Test if capability is supported."""
        if self.state.domain == climate.DOMAIN:
            return super().supported()

        return False

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return climate.ATTR_HVAC_MODES

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_HVAC_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_HVAC_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True,
            context=data.context
        )


@register_capability
class SwingCapability(ModeCapability):
    """Swing functionality"""

    instance = const.MODE_INSTANCE_SWING
    modes_map_default = {
        const.MODE_INSTANCE_MODE_VERTICAL: [climate.const.SWING_VERTICAL, 'ud'],
        const.MODE_INSTANCE_MODE_HORIZONTAL: [climate.const.SWING_HORIZONTAL, 'lr'],
        const.MODE_INSTANCE_MODE_STATIONARY: [climate.const.SWING_OFF],
        const.MODE_INSTANCE_MODE_AUTO: [climate.const.SWING_BOTH, 'all']
    }

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == climate.DOMAIN and features & climate.SUPPORT_SWING_MODE:
            return super().supported()

        return False

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return climate.ATTR_SWING_MODES

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return climate.ATTR_SWING_MODE

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_SWING_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_SWING_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True,
            context=data.context
        )


@register_capability
class ProgramCapability(ModeCapability):
    """Program functionality"""

    instance = const.MODE_INSTANCE_PROGRAM
    modes_map_default = {
        const.MODE_INSTANCE_MODE_FAN_ONLY: [const.XIAOMI_AIRPURIFIER_PRESET_FAN],
        const.MODE_INSTANCE_MODE_AUTO: [humidifier.const.MODE_AUTO],
        const.MODE_INSTANCE_MODE_QUIET: [humidifier.const.MODE_SLEEP, const.XIAOMI_AIRPURIFIER_PRESET_SILENT],
        const.MODE_INSTANCE_MODE_LOW: [const.XIAOMI_AIRPURIFIER_PRESET_LOW],
        const.MODE_INSTANCE_MODE_MIN: [humidifier.const.MODE_AWAY],
        const.MODE_INSTANCE_MODE_ECO: [humidifier.const.MODE_ECO, const.XIAOMI_AIRPURIFIER_PRESET_IDLE],
        const.MODE_INSTANCE_MODE_MEDIUM: [humidifier.const.MODE_COMFORT,
                                          const.MODE_INSTANCE_MODE_MEDIUM, const.XIAOMI_AIRPURIFIER_PRESET_MIDDLE],
        const.MODE_INSTANCE_MODE_NORMAL: [humidifier.const.MODE_NORMAL, const.XIAOMI_AIRPURIFIER_PRESET_FAVORITE],
        const.MODE_INSTANCE_MODE_MAX: [humidifier.const.MODE_HOME],
        const.MODE_INSTANCE_MODE_HIGH: [humidifier.const.MODE_BABY, const.XIAOMI_AIRPURIFIER_PRESET_HIGH],
        const.MODE_INSTANCE_MODE_TURBO: [humidifier.const.MODE_BOOST, const.XIAOMI_AIRPURIFIER_PRESET_STRONG],
    }
    modes_map_index_fallback = {
        0: const.MODE_INSTANCE_MODE_ONE,
        1: const.MODE_INSTANCE_MODE_TWO,
        2: const.MODE_INSTANCE_MODE_THREE,
        3: const.MODE_INSTANCE_MODE_FOUR,
        4: const.MODE_INSTANCE_MODE_FIVE,
        5: const.MODE_INSTANCE_MODE_SIX,
        6: const.MODE_INSTANCE_MODE_SEVEN,
        7: const.MODE_INSTANCE_MODE_EIGHT,
        8: const.MODE_INSTANCE_MODE_NINE,
        9: const.MODE_INSTANCE_MODE_TEN,
    }

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == humidifier.DOMAIN and features & humidifier.SUPPORT_MODES:
            return super().supported()

        return False

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return humidifier.ATTR_AVAILABLE_MODES

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return humidifier.ATTR_MODE

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            humidifier.DOMAIN,
            humidifier.SERVICE_SET_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                humidifier.ATTR_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True,
            context=data.context
        )


@register_capability
class InputSourceCapability(ModeCapability):
    """Input Source functionality"""

    instance = const.MODE_INSTANCE_INPUT_SOURCE
    modes_map_index_fallback = {
        0: const.MODE_INSTANCE_MODE_ONE,
        1: const.MODE_INSTANCE_MODE_TWO,
        2: const.MODE_INSTANCE_MODE_THREE,
        3: const.MODE_INSTANCE_MODE_FOUR,
        4: const.MODE_INSTANCE_MODE_FIVE,
        5: const.MODE_INSTANCE_MODE_SIX,
        6: const.MODE_INSTANCE_MODE_SEVEN,
        7: const.MODE_INSTANCE_MODE_EIGHT,
        8: const.MODE_INSTANCE_MODE_NINE,
        9: const.MODE_INSTANCE_MODE_TEN,
    }

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN and features & media_player.SUPPORT_SELECT_SOURCE:
            if len(self.supported_yandex_modes) == len(self.modes_map_index_fallback) and \
                    len(self.supported_ha_modes) > len(self.modes_map_index_fallback):
                return False

            return super().supported()

        return False

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return media_player.ATTR_INPUT_SOURCE_LIST

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return media_player.ATTR_INPUT_SOURCE

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_SELECT_SOURCE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_INPUT_SOURCE: self.get_ha_mode_by_yandex_mode(state['value']),
            },
            blocking=True,
            context=data.context
        )


class FanSpeedCapability(ModeCapability, ABC):
    """Fan speed functionality."""

    instance = const.MODE_INSTANCE_FAN_SPEED
    modes_map_default = {
        const.MODE_INSTANCE_MODE_AUTO: [climate.const.FAN_AUTO, climate.const.FAN_ON],
        const.MODE_INSTANCE_MODE_ECO: [const.XIAOMI_AIRPURIFIER_PRESET_IDLE],
        const.MODE_INSTANCE_MODE_QUIET: [fan.SPEED_OFF, climate.const.FAN_OFF, 'diffuse',
                                         const.XIAOMI_AIRPURIFIER_PRESET_SILENT, const.XIAOMI_FAN_PRESET_LEVEL_1],
        const.MODE_INSTANCE_MODE_MIN: ['1'],
        const.MODE_INSTANCE_MODE_LOW: [fan.SPEED_LOW, climate.const.FAN_LOW, 'min', '2',
                                       const.XIAOMI_FAN_PRESET_LEVEL_2],
        const.MODE_INSTANCE_MODE_MEDIUM: [fan.SPEED_MEDIUM, climate.const.FAN_MEDIUM, climate.const.FAN_MIDDLE,
                                          'mid', '3', const.XIAOMI_FAN_PRESET_LEVEL_3],
        const.MODE_INSTANCE_MODE_NORMAL: [const.XIAOMI_AIRPURIFIER_PRESET_FAVORITE],
        const.MODE_INSTANCE_MODE_HIGH: [fan.SPEED_HIGH, climate.const.FAN_HIGH, '4', const.XIAOMI_FAN_PRESET_LEVEL_4],
        const.MODE_INSTANCE_MODE_TURBO: [climate.const.FAN_FOCUS, 'max', '5',
                                         const.XIAOMI_AIRPURIFIER_PRESET_STRONG, const.XIAOMI_FAN_PRESET_LEVEL_5],
        const.MODE_INSTANCE_MODE_MAX: ['6'],
    }


@register_capability
class FanSpeedCapabilityClimate(FanSpeedCapability):
    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == climate.DOMAIN and features & climate.SUPPORT_FAN_MODE:
            return super().supported()

        return False

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return climate.ATTR_FAN_MODE

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return climate.ATTR_FAN_MODES

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_FAN_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_FAN_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True,
            context=data.context
        )


@register_capability
class FanSpeedCapabilityFan(FanSpeedCapability):
    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == fan.DOMAIN:
            if features & fan.SUPPORT_PRESET_MODE or features & fan.SUPPORT_SET_SPEED:
                return super().supported()

        return False

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        if self.state.attributes.get(fan.ATTR_PRESET_MODES):
            return fan.ATTR_PRESET_MODE
        else:
            return fan.ATTR_SPEED

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        if self.state.attributes.get(fan.ATTR_PRESET_MODES):
            return fan.ATTR_PRESET_MODES
        else:
            return fan.ATTR_SPEED_LIST

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        if self.modes_list_attribute == fan.ATTR_PRESET_MODES:
            service = fan.SERVICE_SET_PRESET_MODE
            attribute = fan.ATTR_PRESET_MODE
        else:
            service = fan.SERVICE_SET_SPEED
            attribute = fan.ATTR_SPEED
            _LOGGER.warning(
                f'Usage fan attribute "speed_list" is deprecated, use attribute "preset_modes" '
                f'instead for {self.instance} instance of {self.state.entity_id}'
            )

        await self.hass.services.async_call(
            fan.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attribute: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True,
            context=data.context
        )


@register_capability
class CleanupModeCapability(ModeCapability):
    """Vacuum cleanup mode functionality."""

    instance = const.MODE_INSTANCE_CLEANUP_MODE
    modes_map_default = {
        const.MODE_INSTANCE_MODE_AUTO: ['auto', 'automatic', '102'],
        const.MODE_INSTANCE_MODE_TURBO: ['turbo', 'high', 'performance', '104'],
        const.MODE_INSTANCE_MODE_MIN: ['min', 'mop'],
        const.MODE_INSTANCE_MODE_LOW: ['gentle'],
        const.MODE_INSTANCE_MODE_MAX: ['max', 'strong'],
        const.MODE_INSTANCE_MODE_EXPRESS: ['express', '105'],
        const.MODE_INSTANCE_MODE_NORMAL: ['normal', 'medium', 'middle', 'standard', '103'],
        const.MODE_INSTANCE_MODE_QUIET: ['quiet', 'low', 'min', 'silent', 'eco', '101'],
    }

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == vacuum.DOMAIN and features & vacuum.SUPPORT_FAN_SPEED:
            return super().supported()

        return False

    @property
    def modes_list_attribute(self) -> str | None:
        """Return HA attribute contains modes list for this entity."""
        return vacuum.ATTR_FAN_SPEED_LIST

    @property
    def state_value_attribute(self) -> str | None:
        """Return HA attribute for state of this entity."""
        return vacuum.ATTR_FAN_SPEED

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            vacuum.DOMAIN,
            vacuum.SERVICE_SET_FAN_SPEED, {
                ATTR_ENTITY_ID: self.state.entity_id,
                vacuum.ATTR_FAN_SPEED: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True,
            context=data.context
        )
