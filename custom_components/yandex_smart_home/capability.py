"""Implement the Yandex Smart Home capabilities."""
from __future__ import annotations

import logging
import itertools
from typing import Any, Optional, Type

from homeassistant.core import HomeAssistant, State
from homeassistant.components import (
    climate,
    cover,
    group,
    fan,
    humidifier,
    input_boolean,
    media_player,
    light,
    scene,
    script,
    switch,
    vacuum,
    water_heater,
    lock,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_MODEL,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_MUTE,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.components.water_heater import (
    STATE_ELECTRIC, SERVICE_SET_OPERATION_MODE
)
from homeassistant.core import DOMAIN as HA_DOMAIN
from homeassistant.util import color as color_util
from homeassistant.helpers.service import async_call_from_config

from . import const
from .helpers import Config
from .const import (
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    ERR_DEVICE_NOT_FOUND,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID,
    CONF_ENTITY_RANGE_MAX, CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION, CONF_ENTITY_RANGE,
    CONF_ENTITY_MODE_MAP,
    DOMAIN_XIAOMI_AIRPURIFIER, ATTR_TARGET_HUMIDITY, SERVICE_FAN_SET_TARGET_HUMIDITY,
    MODEL_PREFIX_XIAOMI_AIRPURIFIER, STATE_NONE
)
from .error import SmartHomeError

_LOGGER = logging.getLogger(__name__)

PREFIX_CAPABILITIES = 'devices.capabilities.'
CAPABILITIES_ONOFF = PREFIX_CAPABILITIES + 'on_off'
CAPABILITIES_TOGGLE = PREFIX_CAPABILITIES + 'toggle'
CAPABILITIES_RANGE = PREFIX_CAPABILITIES + 'range'
CAPABILITIES_MODE = PREFIX_CAPABILITIES + 'mode'
CAPABILITIES_COLOR_SETTING = PREFIX_CAPABILITIES + 'color_setting'

CAPABILITIES: list[Type[_Capability]] = []


def register_capability(capability):
    """Decorate a function to register a capability."""
    CAPABILITIES.append(capability)
    return capability


class _Capability:
    """Represents a Capability."""

    type = ''
    instance = ''

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state

        self.entity_config = config.get_entity_config(state.entity_id)
        self.retrievable = True
        self.reportable = config.is_reporting_state

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        raise NotImplementedError

    def description(self):
        """Return description for a devices request."""
        response = {
            'type': self.type,
            'retrievable': self.retrievable,
            'reportable': self.reportable,
        }
        parameters = self.parameters()
        if parameters is not None:
            response['parameters'] = parameters

        return response

    def get_state(self):
        """Return the state of this capability for this entity."""
        value = self.get_value()
        return {
            'type': self.type,
            'state':  {
                'instance': self.instance,
                'value': value
            }
        } if value is not None else None

    def parameters(self):
        """Return parameters for a devices request."""
        raise NotImplementedError

    def get_value(self):
        """Return the state value of this capability for this entity."""
        raise NotImplementedError

    async def set_state(self, data, state):
        """Set device state."""
        raise NotImplementedError


@register_capability
class OnOffCapability(_Capability):
    """On_off to offer basic on and off functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/on_off-docpage/
    """

    type = CAPABILITIES_ONOFF
    instance = 'on'
    water_heater_operations = {
        STATE_ON: [STATE_ON, 'On', 'ON', STATE_ELECTRIC],
        STATE_OFF: [STATE_OFF, 'Off', 'OFF'],
    }

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)
        self.retrievable = state.domain != scene.DOMAIN and state.domain != \
            script.DOMAIN

        if self.state.domain == cover.DOMAIN:
            if not self.state.attributes.get(ATTR_SUPPORTED_FEATURES) & cover.SUPPORT_SET_POSITION:
                self.retrievable = False

    def get_water_heater_operation(self, required_mode, operations_list):
        for operation in self.water_heater_operations[required_mode]:
            if operation in operations_list:
                return operation

        return None

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_TURN_ON and features & media_player.SUPPORT_TURN_OFF

        if domain == vacuum.DOMAIN:
            return (features & vacuum.SUPPORT_START and (
                        features & vacuum.SUPPORT_RETURN_HOME or features & vacuum.SUPPORT_STOP)) or (
                               features & vacuum.SUPPORT_TURN_ON and features & vacuum.SUPPORT_TURN_OFF)

        if domain == water_heater.DOMAIN and features & water_heater.SUPPORT_OPERATION_MODE:
            operation_list = attributes.get(water_heater.ATTR_OPERATION_LIST)
            if self.get_water_heater_operation(STATE_ON, operation_list) is None:
                return False
            if self.get_water_heater_operation(STATE_OFF, operation_list) is None:
                return False
            return True

        if const.CONF_TURN_ON in entity_config:
            return True

        return domain in (
            cover.DOMAIN,
            group.DOMAIN,
            input_boolean.DOMAIN,
            switch.DOMAIN,
            fan.DOMAIN,
            light.DOMAIN,
            climate.DOMAIN,
            scene.DOMAIN,
            script.DOMAIN,
            lock.DOMAIN,
            humidifier.DOMAIN,
        )

    def parameters(self):
        """Return parameters for a devices request."""
        if self.state.domain == cover.DOMAIN:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES)
            if not features & cover.SUPPORT_SET_POSITION:
                return {'split': True}

        return None

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == cover.DOMAIN:
            return self.state.state == cover.STATE_OPEN
        elif self.state.domain == vacuum.DOMAIN:
            return self.state.state == STATE_ON or self.state.state == \
                   vacuum.STATE_CLEANING
        elif self.state.domain == climate.DOMAIN:
            return self.state.state != climate.HVAC_MODE_OFF
        elif self.state.domain == lock.DOMAIN:
            return self.state.state == lock.STATE_UNLOCKED
        elif self.state.domain == water_heater.DOMAIN:
            operation_mode = self.state.attributes.get(water_heater.ATTR_OPERATION_MODE)
            operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)
            return operation_mode != self.get_water_heater_operation(STATE_OFF, operation_list)
        else:
            return self.state.state != STATE_OFF

    async def set_state(self, data, state):
        """Set device state."""
        for key, call in ((const.CONF_TURN_ON, state['value']), (const.CONF_TURN_OFF, not state['value'])):
            if key in self.entity_config and call:
                return await async_call_from_config(
                    self.hass,
                    self.entity_config[key],
                    blocking=True,
                    context=data.context,
                )

        domain = service_domain = self.state.domain
        service_data = {
            ATTR_ENTITY_ID: self.state.entity_id
        }
        if domain == group.DOMAIN:
            service_domain = HA_DOMAIN
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF
        elif domain == cover.DOMAIN:
            service = SERVICE_OPEN_COVER if state['value'] else \
                SERVICE_CLOSE_COVER
        elif domain == vacuum.DOMAIN:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES)
            if state['value']:
                if features & vacuum.SUPPORT_START:
                    service = vacuum.SERVICE_START
                else:
                    service = SERVICE_TURN_ON
            else:
                if features & vacuum.SUPPORT_RETURN_HOME:
                    service = vacuum.SERVICE_RETURN_TO_BASE
                elif features & vacuum.SUPPORT_STOP:
                    service = vacuum.SERVICE_STOP
                else:
                    service = SERVICE_TURN_OFF
        elif self.state.domain in (scene.DOMAIN, script.DOMAIN):
            service = SERVICE_TURN_ON
        elif self.state.domain == lock.DOMAIN:
            service = SERVICE_UNLOCK if state['value'] else \
                SERVICE_LOCK
        elif self.state.domain == water_heater.DOMAIN:
            operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)
            service = SERVICE_SET_OPERATION_MODE
            if state['value']:
                service_data[water_heater.ATTR_OPERATION_MODE] = \
                    self.get_water_heater_operation(STATE_ON, operation_list)
            else:
                service_data[water_heater.ATTR_OPERATION_MODE] = \
                    self.get_water_heater_operation(STATE_OFF, operation_list)
        else:
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF

        if self.state.domain == climate.DOMAIN and state['value']:
            hvac_modes = self.state.attributes.get(climate.ATTR_HVAC_MODES)
            for mode in (climate.const.HVAC_MODE_HEAT_COOL,
                         climate.const.HVAC_MODE_AUTO):
                if mode not in hvac_modes:
                    continue

                service_data[climate.ATTR_HVAC_MODE] = mode
                service = climate.SERVICE_SET_HVAC_MODE
                break

        await self.hass.services.async_call(service_domain, service, service_data,
                                            blocking=self.state.domain != script.DOMAIN, context=data.context)


# noinspection PyAbstractClass
class _ToggleCapability(_Capability):
    """Base toggle functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/toggle-docpage/
    """

    type = CAPABILITIES_TOGGLE

    def parameters(self):
        """Return parameters for a devices request."""
        return {
            'instance': self.instance
        }


@register_capability
class MuteCapability(_ToggleCapability):
    """Mute and unmute functionality."""

    instance = const.TOGGLE_INSTANCE_MUTE

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == media_player.DOMAIN and features & media_player.SUPPORT_VOLUME_MUTE

    def get_value(self):
        """Return the state value of this capability for this entity."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)

        return bool(muted)

    async def set_state(self, data, state):
        """Set device state."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        if muted is None:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Device {self.state.entity_id} probably turned off'
            )

        await self.hass.services.async_call(
            self.state.domain,
            SERVICE_VOLUME_MUTE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_MEDIA_VOLUME_MUTED: state['value']
            }, blocking=True, context=data.context)


@register_capability
class PauseCapability(_ToggleCapability):
    """Pause and unpause functionality."""

    instance = const.TOGGLE_INSTANCE_PAUSE

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_PAUSE and features & media_player.SUPPORT_PLAY
        elif domain == vacuum.DOMAIN:
            return features & vacuum.SUPPORT_PAUSE
        elif domain == cover.DOMAIN:
            return features & cover.SUPPORT_STOP

        return False

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == media_player.DOMAIN:
            return bool(self.state.state != media_player.STATE_PLAYING)
        elif self.state.domain == vacuum.DOMAIN:
            return self.state.state == vacuum.STATE_PAUSED
        elif self.state.domain == cover.DOMAIN:
            return False

        return None

    async def set_state(self, data, state):
        """Set device state."""
        if self.state.domain == media_player.DOMAIN:
            if state['value']:
                service = media_player.SERVICE_MEDIA_PAUSE
            else:
                service = media_player.SERVICE_MEDIA_PLAY
        elif self.state.domain == vacuum.DOMAIN:
            if state['value']:
                service = vacuum.SERVICE_PAUSE
            else:
                service = vacuum.SERVICE_START
        elif self.state.domain == cover.DOMAIN:
            service = cover.SERVICE_STOP_COVER
        else:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unsupported domain for {self.instance} instance of {self.state.entity_id}'
            )

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            }, blocking=True, context=data.context)


@register_capability
class OscillationCapability(_ToggleCapability):
    """Oscillation functionality."""

    instance = const.TOGGLE_INSTANCE_OSCILLATION

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == fan.DOMAIN and features & fan.SUPPORT_OSCILLATE

    def get_value(self):
        """Return the state value of this capability for this entity."""
        return bool(self.state.attributes.get(fan.ATTR_OSCILLATING))

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            self.state.domain,
            fan.SERVICE_OSCILLATE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                fan.ATTR_OSCILLATING: state['value']
            }, blocking=True, context=data.context)


# noinspection PyAbstractClass
class _ModeCapability(_Capability):
    """Base class of capabilities with mode functionality like thermostat mode
    or fan speed.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/mode-docpage/
    """

    type = CAPABILITIES_MODE
    modes_map_default: dict[str, list[str]] = {}
    modes_map_index_fallback: dict[int, str] = {}

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return bool(self.supported_yandex_modes)

    def parameters(self) -> dict[str, Any]:
        """Return parameters for a devices request."""

        return {
            'instance': self.instance,
            'modes': [{'value': v} for v in self.supported_yandex_modes],
        }

    @property
    def supported_yandex_modes(self):
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
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        raise NotImplementedError

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        return None

    def get_yandex_mode_by_ha_mode(self, ha_mode: str, hide_warnings=False) -> Optional[str]:
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
            err = f'Unsupported HA mode "{rv}" for {self.instance} instance of {self.state.entity_id}.'
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

    def get_ha_mode_by_yandex_mode(self, yandex_mode: str, available_modes: Optional[list[str]] = None) -> str:
        if available_modes is None:
            available_modes = self.supported_ha_modes

        ha_modes = self.modes_map.get(yandex_mode, [])
        for ha_mode in ha_modes:
            for am in available_modes:
                if str(am).lower() == str(ha_mode).lower():
                    return am

        for ha_idx, yandex_mode_idx in self.modes_map_index_fallback.items():
            if yandex_mode_idx == yandex_mode:
                return available_modes[ha_idx]

        raise SmartHomeError(
            ERR_INVALID_VALUE,
            f'Unsupported mode "{yandex_mode}" for {self.instance} instance of {self.state.entity_id}. '
            f'Check \"modes\" setting for this entity'
        )

    def get_value(self):
        """Return the state value of this capability for this entity."""
        ha_mode = self.state.state
        if self.state_value_attribute:
            ha_mode = self.state.attributes.get(self.state_value_attribute)

        return self.get_yandex_mode_by_ha_mode(ha_mode)


@register_capability
class ThermostatCapability(_ModeCapability):
    """Thermostat functionality"""

    instance = const.MODE_INSTANCE_THERMOSTAT
    modes_map_default = {
        const.MODE_INSTANCE_MODE_HEAT: [climate.const.HVAC_MODE_HEAT],
        const.MODE_INSTANCE_MODE_COOL: [climate.const.HVAC_MODE_COOL],
        const.MODE_INSTANCE_MODE_AUTO: [climate.const.HVAC_MODE_HEAT_COOL, climate.const.HVAC_MODE_AUTO],
        const.MODE_INSTANCE_MODE_DRY: [climate.const.HVAC_MODE_DRY],
        const.MODE_INSTANCE_MODE_FAN_ONLY: [climate.const.HVAC_MODE_FAN_ONLY],
    }

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == climate.DOMAIN:
            return super().supported(domain, features, entity_config, attributes)

        return False

    @property
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        if self.state.domain == climate.DOMAIN:
            return climate.ATTR_HVAC_MODES

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_HVAC_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_HVAC_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            }, blocking=True, context=data.context)


@register_capability
class SwingCapability(_ModeCapability):
    """Swing functionality"""

    instance = const.MODE_INSTANCE_SWING
    modes_map_default = {
        const.MODE_INSTANCE_MODE_VERTICAL: [climate.const.SWING_VERTICAL, 'ud'],
        const.MODE_INSTANCE_MODE_HORIZONTAL: [climate.const.SWING_HORIZONTAL, 'lr'],
        const.MODE_INSTANCE_MODE_STATIONARY: [climate.const.SWING_OFF],
        const.MODE_INSTANCE_MODE_AUTO: [climate.const.SWING_BOTH, 'all']
    }

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == climate.DOMAIN and features & climate.SUPPORT_SWING_MODE:
            return super().supported(domain, features, entity_config, attributes)

        return False

    @property
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        if self.state.domain == climate.DOMAIN:
            return climate.ATTR_SWING_MODES

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        if self.state.domain == climate.DOMAIN:
            return climate.ATTR_SWING_MODE

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_SWING_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_SWING_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            }, blocking=True, context=data.context)


@register_capability
class ProgramCapability(_ModeCapability):
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

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == humidifier.DOMAIN and features & humidifier.SUPPORT_MODES:
            return super().supported(domain, features, entity_config, attributes)

        return False

    @property
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        if self.state.domain == humidifier.DOMAIN:
            return humidifier.ATTR_AVAILABLE_MODES

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        if self.state.domain == humidifier.DOMAIN:
            return humidifier.ATTR_MODE

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            humidifier.DOMAIN,
            humidifier.SERVICE_SET_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                humidifier.ATTR_MODE: self.get_ha_mode_by_yandex_mode(state['value'])
            },
            blocking=True, context=data.context,
        )


@register_capability
class InputSourceCapability(_ModeCapability):
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

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == media_player.DOMAIN and features & media_player.SUPPORT_SELECT_SOURCE:
            if len(self.supported_yandex_modes) == len(self.modes_map_index_fallback) and \
                    len(self.supported_ha_modes) > len(self.modes_map_index_fallback):
                return False

            return super().supported(domain, features, entity_config, attributes)

        return False

    @property
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        if self.state.domain == media_player.DOMAIN:
            return media_player.ATTR_INPUT_SOURCE_LIST

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        if self.state.domain == media_player.DOMAIN:
            return media_player.ATTR_INPUT_SOURCE

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_SELECT_SOURCE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.const.ATTR_INPUT_SOURCE: self.get_ha_mode_by_yandex_mode(state['value']),
            }, blocking=True, context=data.context)


@register_capability
class FanSpeedCapability(_ModeCapability):
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

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == climate.DOMAIN and features & climate.SUPPORT_FAN_MODE:
            return super().supported(domain, features, entity_config, attributes)
        elif domain == fan.DOMAIN:
            if features & fan.SUPPORT_PRESET_MODE or features & fan.SUPPORT_SET_SPEED:
                return super().supported(domain, features, entity_config, attributes)

        return False

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        if self.state.domain == climate.DOMAIN:
            return climate.ATTR_FAN_MODE
        elif self.state.domain == fan.DOMAIN:
            if self.state.attributes.get(fan.ATTR_PRESET_MODES):
                return fan.ATTR_PRESET_MODE
            else:
                return fan.ATTR_SPEED

    @property
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        if self.state.domain == climate.DOMAIN:
            return climate.ATTR_FAN_MODES
        elif self.state.domain == fan.DOMAIN:
            if self.state.attributes.get(fan.ATTR_PRESET_MODES):
                return fan.ATTR_PRESET_MODES
            else:
                return fan.ATTR_SPEED_LIST

    async def set_state(self, data, state):
        """Set device state."""
        value = self.get_ha_mode_by_yandex_mode(state['value'])

        if self.state.domain == climate.DOMAIN:
            service = climate.SERVICE_SET_FAN_MODE
            attr = climate.ATTR_FAN_MODE
        elif self.state.domain == fan.DOMAIN:
            if self.modes_list_attribute == fan.ATTR_PRESET_MODES:
                service = fan.SERVICE_SET_PRESET_MODE
                attr = fan.ATTR_PRESET_MODE
            else:
                service = fan.SERVICE_SET_SPEED
                attr = fan.ATTR_SPEED
                _LOGGER.warning(
                    f'Usage fan attribute "speed_list" is deprecated, use attribute "preset_modes" '
                    f'instead for {self.instance} instance of {self.state.entity_id}'
                )
        else:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unsupported domain for {self.instance} instance of {self.state.entity_id}'
            )

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: value
            }, blocking=True, context=data.context)


# noinspection PyAbstractClass
class _RangeCapability(_Capability):
    """Base class of capabilities with range functionality like volume or
    brightness.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/range-docpage/
    """

    type = CAPABILITIES_RANGE
    default_range = (0, 100, 1)

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)
        self.retrievable = self.support_random_access

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        raise NotImplementedError

    @property
    def range(self) -> (float, float, float):
        """Return support range (min, max, precision)."""
        return (
            self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, self.default_range[0]),
            self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, self.default_range[1]),
            self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, self.default_range[2])
        )

    def parameters(self):
        """Return parameters for a devices request."""
        if self.support_random_access:
            range_min, range_max, range_precision = self.range
            rv = {
                'instance': self.instance,
                'random_access': True,
                'range': {
                    'min': range_min,
                    'max': range_max,
                    'precision': range_precision
                }
            }

            if self.instance in const.RANGE_INSTANCE_TO_UNITS:
                rv['unit'] = const.RANGE_INSTANCE_TO_UNITS[self.instance]

            return rv

        return {
            'instance': self.instance,
            'random_access': False,
        }

    def float_value(self, value: Any) -> Optional[float]:
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )


@register_capability
class CoverLevelCapability(_RangeCapability):
    """Set cover level"""

    instance = const.RANGE_INSTANCE_OPEN

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == cover.DOMAIN:
            return features & cover.SUPPORT_SET_POSITION

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == cover.DOMAIN:
            return self.float_value(self.state.attributes.get(cover.ATTR_CURRENT_POSITION))

    async def set_state(self, data, state):
        """Set device state."""
        value = state['value']
        if value < 0:
            value = min(self.get_value() + value, 0)

        await self.hass.services.async_call(
            self.state.domain,
            cover.SERVICE_SET_COVER_POSITION, {
                ATTR_ENTITY_ID: self.state.entity_id,
                cover.ATTR_POSITION: value
            }, blocking=True, context=data.context)


@register_capability
class TemperatureCapability(_RangeCapability):
    """Set temperature functionality."""

    instance = const.RANGE_INSTANCE_TEMPERATURE
    default_range = (0, 100, 0.5)

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        super().__init__(hass, config, state)

        if self.state.domain == water_heater.DOMAIN:
            self.default_range = (
                self.state.attributes.get(water_heater.ATTR_MIN_TEMP),
                self.state.attributes.get(water_heater.ATTR_MAX_TEMP),
                0.5
            )
        elif self.state.domain == climate.DOMAIN:
            self.default_range = (
                self.state.attributes.get(climate.ATTR_MIN_TEMP),
                self.state.attributes.get(climate.ATTR_MAX_TEMP),
                self.state.attributes.get(climate.ATTR_TARGET_TEMP_STEP, 0.5),
            )

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == water_heater.DOMAIN:
            return features & water_heater.SUPPORT_TARGET_TEMPERATURE
        elif domain == climate.DOMAIN:
            return features & climate.const.SUPPORT_TARGET_TEMPERATURE

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == water_heater.DOMAIN:
            return self.float_value(self.state.attributes.get(water_heater.ATTR_TEMPERATURE))
        elif self.state.domain == climate.DOMAIN:
            return self.float_value(self.state.attributes.get(climate.ATTR_TEMPERATURE))

    async def set_state(self, data, state):
        """Set device state."""
        if self.state.domain == water_heater.DOMAIN:
            service = water_heater.SERVICE_SET_TEMPERATURE
            attr = water_heater.ATTR_TEMPERATURE
        elif self.state.domain == climate.DOMAIN:
            service = climate.SERVICE_SET_TEMPERATURE
            attr = climate.ATTR_TEMPERATURE
        else:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unsupported domain for {self.instance} instance of {self.state.entity_id}'
            )

        new_value = state['value']
        if 'relative' in state and state['relative'] and self.state.domain == climate.DOMAIN:
            new_value = self.state.attributes.get(climate.ATTR_TEMPERATURE) + state['value']

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: new_value
            }, blocking=True, context=data.context)


@register_capability
class HumidityCapability(_RangeCapability):
    """Set humidity functionality."""

    instance = const.RANGE_INSTANCE_HUMIDITY

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        super().__init__(hass, config, state)

        if self.state.domain == humidifier.DOMAIN:
            self.default_range = (
                self.state.attributes.get(humidifier.ATTR_MIN_HUMIDITY),
                self.state.attributes.get(humidifier.ATTR_MAX_HUMIDITY),
                1
            )

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == humidifier.DOMAIN:
            return True
        elif domain == fan.DOMAIN and \
                attributes.get(ATTR_TARGET_HUMIDITY) and \
                attributes.get(ATTR_MODEL, '').startswith(MODEL_PREFIX_XIAOMI_AIRPURIFIER):
            return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == humidifier.DOMAIN:
            return self.float_value(self.state.attributes.get(humidifier.ATTR_HUMIDITY))
        elif self.state.domain == fan.DOMAIN:
            return self.float_value(self.state.attributes.get(ATTR_TARGET_HUMIDITY))

    async def set_state(self, data, state):
        """Set device state."""
        domain = self.state.domain

        if self.state.domain == humidifier.DOMAIN:
            service = humidifier.SERVICE_SET_HUMIDITY
            attr = humidifier.ATTR_HUMIDITY
        elif self.state.domain == fan.DOMAIN and \
                self.state.attributes.get(ATTR_MODEL, '').startswith(MODEL_PREFIX_XIAOMI_AIRPURIFIER):
            domain = DOMAIN_XIAOMI_AIRPURIFIER
            service = SERVICE_FAN_SET_TARGET_HUMIDITY
            attr = humidifier.ATTR_HUMIDITY
        else:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unsupported domain for {self.instance} instance of {self.state.entity_id}'
            )

        await self.hass.services.async_call(
            domain,
            service,
            {ATTR_ENTITY_ID: self.state.entity_id, attr: state['value']},
            blocking=True,
            context=data.context,
        )


@register_capability
class BrightnessCapability(_RangeCapability):
    """Set brightness functionality."""

    instance = const.RANGE_INSTANCE_BRIGHTNESS
    default_range = (1, 100, 1)

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == light.DOMAIN and (
            features & light.SUPPORT_BRIGHTNESS or
            light.brightness_supported(attributes.get(light.ATTR_SUPPORTED_COLOR_MODES))
        )

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True

    def get_value(self):
        """Return the state value of this capability for this entity."""
        brightness = self.state.attributes.get(light.ATTR_BRIGHTNESS)
        if brightness is not None:
            return int(100 * (self.float_value(brightness) / 255))

    async def set_state(self, data, state):
        """Set device state."""
        if 'relative' in state and state['relative']:
            attr_name = light.ATTR_BRIGHTNESS_STEP_PCT
        else:
            attr_name = light.ATTR_BRIGHTNESS_PCT

        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr_name: state['value']
            }, blocking=True, context=data.context)


@register_capability
class VolumeCapability(_RangeCapability):
    """Set volume functionality."""

    instance = const.RANGE_INSTANCE_VOLUME

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_VOLUME_STEP or features & media_player.SUPPORT_VOLUME_SET

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        return not (features & media_player.SUPPORT_VOLUME_STEP and not features & media_player.SUPPORT_VOLUME_SET)

    def get_value(self):
        """Return the state value of this capability for this entity."""
        level = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_LEVEL)

        if level is not None:
            return int(self.float_value(level) * 100)

    async def set_state(self, data, state):
        """Set device state."""
        if not self.support_random_access and state.get('relative'):
            if state['value'] > 0:
                service = media_player.SERVICE_VOLUME_UP
            else:
                service = media_player.SERVICE_VOLUME_DOWN

            volume_step = int(self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, 1))
            if abs(state['value']) != 1:
                volume_step = abs(state['value'])

            for _ in range(volume_step):
                await self.hass.services.async_call(
                    media_player.DOMAIN,
                    service, {
                        ATTR_ENTITY_ID: self.state.entity_id
                    }, blocking=True, context=data.context
                )

            return

        target_volume_level = state['value'] / 100
        if state.get('relative'):
            target_volume_level = (self.get_value() + state['value']) / 100

        await self.hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_VOLUME_SET, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.const.ATTR_MEDIA_VOLUME_LEVEL: target_volume_level,
            }, blocking=True, context=data.context
        )


@register_capability
class ChannelCapability(_RangeCapability):
    """Set channel functionality."""

    instance = const.RANGE_INSTANCE_CHANNEL
    default_range = (0, 999, 1)

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == media_player.DOMAIN:
            if features & media_player.SUPPORT_PLAY_MEDIA and entity_config.get(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID):
                return True

            if features & media_player.SUPPORT_PREVIOUS_TRACK and features & media_player.SUPPORT_NEXT_TRACK:
                return True

            if self.state.entity_id == const.YANDEX_STATION_INTENTS_MEDIA_PLAYER:
                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        if features & media_player.SUPPORT_PLAY_MEDIA and self.entity_config.get(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID):
            return True

        if self.state.entity_id == const.YANDEX_STATION_INTENTS_MEDIA_PLAYER:
            return True

        return False

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.support_random_access and self.state.entity_id != const.YANDEX_STATION_INTENTS_MEDIA_PLAYER:
            return self.float_value(self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_ID))

    async def set_state(self, data, state):
        """Set device state."""
        if 'relative' in state and state['relative']:
            if state['value'] > 0:
                service = media_player.SERVICE_MEDIA_NEXT_TRACK
            else:
                service = media_player.SERVICE_MEDIA_PREVIOUS_TRACK
            await self.hass.services.async_call(
                media_player.DOMAIN,
                service, {
                    ATTR_ENTITY_ID: self.state.entity_id
                }, blocking=True, context=data.context)
        else:
            await self.hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_PLAY_MEDIA, {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.const.ATTR_MEDIA_CONTENT_ID: state['value'],
                    media_player.const.ATTR_MEDIA_CONTENT_TYPE:
                        media_player.const.MEDIA_TYPE_CHANNEL,
                }, blocking=True, context=data.context)


# noinspection PyAbstractClass
class _ColorSettingCapability(_Capability):
    """Base color setting functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/color_setting-docpage/
    """

    type = CAPABILITIES_COLOR_SETTING
    scenes_map_default = {
        const.COLOR_SCENE_ALARM: ['Тревога', 'Alarm', 'Shine'],
        const.COLOR_SCENE_ALICE: ['Алиса', 'Alice', 'Meeting'],
        const.COLOR_SCENE_CANDLE: ['Свеча', 'Огонь', 'Candle', 'Fire'],
        const.COLOR_SCENE_DINNER: ['Ужин', 'Dinner'],
        const.COLOR_SCENE_FANTASY: ['Фантазия', 'Fantasy', 'Random', 'Beautiful'],
        const.COLOR_SCENE_GARLAND: ['Гирлянда', 'Garland'],
        const.COLOR_SCENE_JUNGLE: ['Джунгли', 'Jungle'],
        const.COLOR_SCENE_MOVIE: ['Кино', 'Movie'],
        const.COLOR_SCENE_NEON: ['Неон', 'Neon'],
        const.COLOR_SCENE_NIGHT: ['Ночь', 'Night'],
        const.COLOR_SCENE_OCEAN: ['Океан', 'Ocean'],
        const.COLOR_SCENE_PARTY: ['Вечеринка', 'Party'],
        const.COLOR_SCENE_READING: ['Чтение', 'Reading', 'Read'],
        const.COLOR_SCENE_REST: ['Отдых', 'Rest', 'Soft'],
        const.COLOR_SCENE_ROMANCE: ['Романтика', 'Romance', 'Leasure'],
        const.COLOR_SCENE_SIREN: ['Сирена', 'Siren', 'Rainbow'],
        const.COLOR_SCENE_SUNRISE: ['Рассвет', 'Sunrise'],
        const.COLOR_SCENE_SUNSET: ['Закат', 'Sunset']
    }
    default_white_temperature_k = 4500
    cold_white_temperature_k = 6500

    def parameters(self):
        """Return parameters for a devices request."""
        result = {}

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if self.support_color:
            result['color_model'] = 'rgb'

        if features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
            min_temp = self.state.attributes.get(light.ATTR_MAX_MIREDS, 153)
            max_temp = self.state.attributes.get(light.ATTR_MIN_MIREDS, 500)
            result['temperature_k'] = {
                'min': color_util.color_temperature_mired_to_kelvin(min_temp),
                'max': color_util.color_temperature_mired_to_kelvin(max_temp)
            }
        elif light.COLOR_MODE_RGBW in supported_color_modes:
            result['temperature_k'] = {
                'min': self.default_white_temperature_k,
                'max': self.cold_white_temperature_k
            }
        elif light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
            result['temperature_k'] = {
                'min': self.default_white_temperature_k,
                'max': self.default_white_temperature_k
            }

        if features & light.SUPPORT_EFFECT:
            supported_scenes = self.get_supported_scenes(
                self.get_scenes_map_from_config(self.entity_config),
                self.state.attributes.get(light.ATTR_EFFECT_LIST, [])
            )
            if supported_scenes:
                result['color_scene'] = {
                    'scenes': [
                        {'id': s}
                        for s in supported_scenes
                    ]
                }

        return result

    @property
    def support_color(self) -> bool:
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if self.state.domain != light.DOMAIN:
            return False

        if features & light.SUPPORT_COLOR:  # legacy
            return True

        for color_mode in supported_color_modes:
            if color_mode in [light.COLOR_MODE_RGB, light.COLOR_MODE_RGBW, light.COLOR_MODE_RGBWW, light.COLOR_MODE_HS]:
                return True

        return False

    @staticmethod
    def get_supported_scenes(scenes_map: dict[str, list[str]],
                             entity_effect_list: list[str]) -> set[str]:
        yandex_scenes = set()
        for effect in entity_effect_list:
            for yandex_scene, ha_effects in scenes_map.items():
                if effect in ha_effects:
                    yandex_scenes.add(yandex_scene)

        return yandex_scenes

    @staticmethod
    def get_scenes_map_from_config(entity_config: dict[str, Any]) -> dict[str, list[str]]:
        scenes_map = _ColorSettingCapability.scenes_map_default.copy()
        instance = 'scene'

        if CONF_ENTITY_MODE_MAP in entity_config:
            modes = entity_config.get(CONF_ENTITY_MODE_MAP)
            if instance in modes:
                config_scenes = modes.get(instance)
                for yandex_scene in scenes_map.keys():
                    if yandex_scene in config_scenes.keys():
                        scenes_map[yandex_scene] = config_scenes[yandex_scene]

        return scenes_map

    def get_yandex_scene_by_ha_effect(self, ha_effect: str) -> Optional[str]:
        scenes_map = self.get_scenes_map_from_config(self.entity_config)

        for yandex_scene, ha_effects in scenes_map.items():
            if str(ha_effect) in ha_effects:
                return yandex_scene

        return None

    def get_ha_effect_by_yandex_scene(self, yandex_scene: str) -> Optional[str]:
        scenes_map = self.get_scenes_map_from_config(self.entity_config)

        ha_effects = scenes_map.get(yandex_scene)
        if not ha_effects:
            return None

        for ha_effect in ha_effects:
            for am in self.state.attributes.get(light.ATTR_EFFECT_LIST, []):
                if str(am) == ha_effect:
                    return ha_effect

        return None


@register_capability
class RgbCapability(_ColorSettingCapability):
    """RGB color functionality."""

    instance = 'rgb'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return self.support_color

    def get_value(self):
        """Return the state value of this capability for this entity."""
        rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
        if rgb_color is None:
            hs_color = self.state.attributes.get(light.ATTR_HS_COLOR)
            if hs_color is not None:
                rgb_color = color_util.color_hs_to_RGB(*hs_color)

        if rgb_color is not None:
            if rgb_color == (255, 255, 255):
                return None

            value = rgb_color[0]
            value = (value << 8) + rgb_color[1]
            value = (value << 8) + rgb_color[2]

            return value

    async def set_state(self, data, state):
        """Set device state."""
        red = (state['value'] >> 16) & 0xFF
        green = (state['value'] >> 8) & 0xFF
        blue = state['value'] & 0xFF

        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_RGB_COLOR: (red, green, blue)
            }, blocking=True, context=data.context)


@register_capability
class TemperatureKCapability(_ColorSettingCapability):
    """Color temperature functionality."""

    instance = 'temperature_k'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == light.DOMAIN:
            supported_color_modes = attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

            if features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
                return True
            elif light.COLOR_MODE_RGBW in supported_color_modes:
                return True
            elif light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
                return True

        return False

    def get_value(self):
        """Return the state value of this capability for this entity."""
        temperature_mired = self.state.attributes.get(light.ATTR_COLOR_TEMP)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if temperature_mired is not None:
            return color_util.color_temperature_mired_to_kelvin(temperature_mired)

        if light.COLOR_MODE_RGBW in supported_color_modes:
            rgbw_color = self.state.attributes.get(light.ATTR_RGBW_COLOR)
            if rgbw_color is not None:
                if rgbw_color[:3] == (0, 0, 0) and rgbw_color[3] > 0:
                    return self.default_white_temperature_k
                elif rgbw_color[:3] == (255, 255, 255):
                    return self.cold_white_temperature_k

            return None

        if light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
            rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
            if rgb_color is not None and rgb_color == (255, 255, 255):
                return self.default_white_temperature_k

            return None

    async def set_state(self, data, state):
        """Set device state."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])
        value = state['value']
        service_data = {}

        if features & light.SUPPORT_COLOR_TEMP or \
                light.color_temp_supported(self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])):
            service_data[light.ATTR_KELVIN] = value

        elif light.COLOR_MODE_RGBW in supported_color_modes:
            if value == self.default_white_temperature_k:
                service_data[light.ATTR_RGBW_COLOR] = (0, 0, 0, self.state.attributes.get(light.ATTR_BRIGHTNESS, 255))
            else:
                service_data[light.ATTR_RGBW_COLOR] = (255, 255, 255, 0)

        elif light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
            service_data[light.ATTR_RGB_COLOR] = (255, 255, 255)

        if service_data:
            service_data[ATTR_ENTITY_ID] = self.state.entity_id
            await self.hass.services.async_call(
                light.DOMAIN, light.SERVICE_TURN_ON, service_data, blocking=True, context=data.context
            )
        else:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )


@register_capability
class ColorSceneCapability(_ColorSettingCapability):
    """Color temperature functionality."""

    instance = 'scene'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == light.DOMAIN and features & light.SUPPORT_EFFECT:
            return bool(
                ColorSceneCapability.get_supported_scenes(
                    ColorSceneCapability.get_scenes_map_from_config(entity_config),
                    attributes.get(light.ATTR_EFFECT_LIST, [])
                )
            )

    def get_value(self):
        """Return the state value of this capability for this entity."""
        return self.get_yandex_scene_by_ha_effect(self.state.attributes.get(light.ATTR_EFFECT))

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_EFFECT: self.get_ha_effect_by_yandex_scene(state['value']),
            }, blocking=True, context=data.context)


@register_capability
class CleanupModeCapability(_ModeCapability):
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

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == vacuum.DOMAIN and features & vacuum.SUPPORT_FAN_SPEED:
            return super().supported(domain, features, entity_config, attributes)

        return False

    @property
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        if self.state.domain == vacuum.DOMAIN:
            return vacuum.ATTR_FAN_SPEED_LIST

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        if self.state.domain == vacuum.DOMAIN:
            return vacuum.ATTR_FAN_SPEED

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            self.state.domain,
            vacuum.SERVICE_SET_FAN_SPEED, {
                ATTR_ENTITY_ID: self.state.entity_id,
                vacuum.ATTR_FAN_SPEED: self.get_ha_mode_by_yandex_mode(state['value'])
            }, blocking=True, context=data.context)


# noinspection PyAbstractClass
class _CustomCapability(_Capability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        super().__init__(hass, config, state)
        self.instance = instance
        self.capability_config = capability_config
        self.state_entity_id = self.capability_config.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
        self.retrievable = bool(self.state_entity_id or self.state_value_attribute)

    @property
    def state_value_attribute(self) -> Optional[str]:
        """Return HA attribute for state of this entity."""
        return self.capability_config.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)

    def get_value(self):
        """Return the state value of this capability for this entity."""
        entity_state = self.state

        if self.state_entity_id:
            entity_state = self.hass.states.get(self.state_entity_id)
            if not entity_state:
                raise SmartHomeError(
                    ERR_DEVICE_NOT_FOUND,
                    f'Entity {self.state_entity_id} not found for {self.instance} instance of {self.state.entity_id}'
                )

        if self.state_value_attribute:
            value = entity_state.attributes.get(self.state_value_attribute)
        else:
            value = entity_state.state

        return value


class CustomModeCapability(_CustomCapability, _ModeCapability):
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
    def modes_list_attribute(self) -> Optional[str]:
        """Return HA attribute contains modes list for this entity."""
        raise None

    def get_value(self):
        """Return the state value of this capability for this entity."""
        return self.get_yandex_mode_by_ha_mode(super().get_value())

    async def set_state(self, data, state):
        """Set device state."""
        await async_call_from_config(
            self.hass,
            self.set_mode_config,
            validate_config=False,
            variables={'mode': self.get_ha_mode_by_yandex_mode(state['value'])},
            blocking=True,
            context=data.context,
        )


class CustomToggleCapability(_CustomCapability, _ToggleCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        super().__init__(hass, config, state, instance, capability_config)

        self.turn_on_config = self.capability_config[const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON]
        self.turn_off_config = self.capability_config[const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF]

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return True

    def get_value(self):
        """Return the state value of this capability for this entity."""
        return super().get_value() in [STATE_ON, True]

    async def set_state(self, data, state):
        """Set device state."""
        await async_call_from_config(
            self.hass,
            self.turn_on_config if state['value'] else self.turn_off_config,
            validate_config=False,
            blocking=True,
            context=data.context,
        )


class CustomRangeCapability(_CustomCapability, _RangeCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 instance: str, capability_config: dict[str, Any]):
        super().__init__(hass, config, state, instance, capability_config)

        self.set_value = self.capability_config[const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE]
        self.default_range = (
            self.capability_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, self.default_range[0]),
            self.capability_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, self.default_range[1]),
            self.capability_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, self.default_range[2])
        )

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return True

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        for key in [CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_MAX]:
            if key not in self.capability_config.get(CONF_ENTITY_RANGE, {}):
                return False

        return True

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if not self.support_random_access:
            return None

        return self.float_value(super().get_value())

    async def set_state(self, data, state):
        """Set device state."""
        value = state['value']
        if 'relative' in state and self.support_random_access:
            value = self.get_value() + state['value']

        await async_call_from_config(
            self.hass,
            self.set_value,
            validate_config=False,
            variables={'value': value},
            blocking=True,
            context=data.context,
        )
