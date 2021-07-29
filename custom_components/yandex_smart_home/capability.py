"""Implement the Yandex Smart Home capabilities."""
from __future__ import annotations

import logging
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
    STATE_OFF,
    STATE_ON,
)
from homeassistant.components.water_heater import (
    STATE_ELECTRIC, SERVICE_SET_OPERATION_MODE
)
from homeassistant.core import DOMAIN as HA_DOMAIN
from homeassistant.util import color as color_util

from .const import (
    DOMAIN,
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID, CONF_RELATIVE_VOLUME_ONLY,
    CONF_ENTITY_RANGE_MAX, CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION, CONF_ENTITY_RANGE,
    CONF_ENTITY_MODE_MAP, NOTIFIER_ENABLED,
    DOMAIN_XIAOMI_AIRPURIFIER, ATTR_TARGET_HUMIDITY, SERVICE_FAN_SET_TARGET_HUMIDITY,
    MODEL_PREFIX_XIAOMI_AIRPURIFIER
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
    reportable = False

    def __init__(self, hass: HomeAssistant, state: State, entity_config: dict[str, Any]):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.entity_config = entity_config
        self.retrievable = True
        self.reportable = hass.data[DOMAIN][NOTIFIER_ENABLED]

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

    def __init__(self, hass, state, config):
        super().__init__(hass, state, config)
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
        domain = self.state.domain

        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Value is not boolean')

        service_domain = domain
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
                         climate.const.HVAC_MODE_AUTO,
                         climate.const.HVAC_MODE_HEAT,
                         climate.const.HVAC_MODE_COOL):
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

    instance = 'mute'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == media_player.DOMAIN and features & media_player.SUPPORT_VOLUME_MUTE

    def get_value(self):
        """Return the state value of this capability for this entity."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)

        return bool(muted)

    async def set_state(self, data, state):
        """Set device state."""
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Value is not boolean')

        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        if muted is None:
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                                 'Device probably turned off')

        await self.hass.services.async_call(
            self.state.domain,
            SERVICE_VOLUME_MUTE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_MEDIA_VOLUME_MUTED: state['value']
            }, blocking=True, context=data.context)


@register_capability
class PauseCapability(_ToggleCapability):
    """Pause and unpause functionality."""

    instance = 'pause'

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
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Value is not boolean')

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
            raise SmartHomeError(ERR_INVALID_VALUE, 'Unsupported domain')

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            }, blocking=True, context=data.context)


@register_capability
class OscillationCapability(_ToggleCapability):
    """Oscillation functionality."""

    instance = 'oscillation'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == fan.DOMAIN and features & fan.SUPPORT_OSCILLATE

    def get_value(self):
        """Return the state value of this capability for this entity."""
        return bool(self.state.attributes.get(fan.ATTR_OSCILLATING))

    async def set_state(self, data, state):
        """Set device state."""
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Value is not boolean')

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

        for ha_value in self.state.attributes.get(self.modes_list_attribute, []):
            value = self.get_yandex_mode_by_ha_mode(ha_value)
            if value is not None and value not in modes:
                modes.append(value)

        return modes

    @property
    def modes_map(self) -> dict[str, list[str]]:
        """Return modes mapping between Yandex and HA."""
        if CONF_ENTITY_MODE_MAP in self.entity_config:
            modes = self.entity_config.get(CONF_ENTITY_MODE_MAP)
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

    def get_yandex_mode_by_ha_mode(self, ha_mode: str) -> Optional[str]:
        for yandex_mode, names in self.modes_map.items():
            lower_names = [str(n).lower() for n in names]
            if str(ha_mode).lower() in lower_names:
                return yandex_mode

        if self.modes_map_index_fallback:
            available_modes = self.state.attributes.get(self.modes_list_attribute, [])
            try:
                return self.modes_map_index_fallback[available_modes.index(ha_mode)]
            except (IndexError, ValueError, KeyError):
                pass

        return None

    def get_ha_mode_by_yandex_mode(self, yandex_mode: str, available_modes: Optional[list[str]] = None) -> str:
        if available_modes is None:
            available_modes = self.state.attributes.get(self.modes_list_attribute, [])

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
            f'Unknown mode "{yandex_mode}" for {self.state.entity_id} ({self.instance})'
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

    instance = 'thermostat'
    modes_map_default = {
        'heat': [climate.const.HVAC_MODE_HEAT],
        'cool': [climate.const.HVAC_MODE_COOL],
        'auto': [climate.const.HVAC_MODE_HEAT_COOL],
        'dry': [climate.const.HVAC_MODE_DRY],
        'fan_only': [climate.const.HVAC_MODE_FAN_ONLY],
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

    instance = 'swing'
    modes_map_default = {
        'vertical': [climate.const.SWING_VERTICAL],
        'horizontal': [climate.const.SWING_HORIZONTAL],
        'stationary': [climate.const.SWING_OFF],
        'auto': [climate.const.SWING_BOTH]
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

    instance = 'program'
    modes_map_default = {
        'normal': [humidifier.const.MODE_NORMAL],
        'eco': [humidifier.const.MODE_ECO],
        'min': [humidifier.const.MODE_AWAY],
        'turbo': [humidifier.const.MODE_BOOST],
        'medium': [humidifier.const.MODE_COMFORT],
        'max': [humidifier.const.MODE_HOME],
        'quiet': [humidifier.const.MODE_SLEEP],
        'auto': [humidifier.const.MODE_AUTO],
        'high': [humidifier.const.MODE_BABY],
    }
    modes_map_index_fallback = {
        0: 'one',
        1: 'two',
        2: 'three',
        3: 'four',
        4: 'five',
        5: 'six',
        6: 'seven',
        7: 'eight',
        8: 'nine',
        9: 'ten',
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

    instance = 'input_source'
    modes_map_index_fallback = {
        0: 'one',
        1: 'two',
        2: 'three',
        3: 'four',
        4: 'five',
        5: 'six',
        6: 'seven',
        7: 'eight',
        8: 'nine',
        9: 'ten'
    }

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == media_player.DOMAIN and features & media_player.SUPPORT_SELECT_SOURCE:
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

    instance = 'fan_speed'
    modes_map_default = {
        'auto': [climate.const.FAN_AUTO, climate.const.FAN_ON],
        'quiet': [fan.SPEED_OFF, climate.const.FAN_OFF, 'silent', 'level 1'],
        'low': [fan.SPEED_LOW, climate.const.FAN_LOW, 'min', 'level 2'],
        'medium': [fan.SPEED_MEDIUM, climate.const.FAN_MEDIUM, climate.const.FAN_MIDDLE, 'mid', 'level 3'],
        'high': [fan.SPEED_HIGH, climate.const.FAN_HIGH, 'strong', 'favorite', 'level 4'],
        'turbo': [climate.const.FAN_FOCUS, 'max', 'level 5'],
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
                _LOGGER.warning('Usage fan attribute "speed_list" is deprecated, use attribute "preset_modes" instead')
        else:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unsupported domain for {self.state.entity_id} ({self.instance})'
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


@register_capability
class CoverLevelCapability(_RangeCapability):
    """Set cover level"""

    instance = 'open'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == cover.DOMAIN:
            return features & cover.SUPPORT_SET_POSITION

        return False

    def parameters(self):
        """Return parameters for a devices request."""
        return {
            'instance': self.instance,
            'range': {
                'max': 100,
                'min': 0,
                'precision': 1
            },
            'unit': 'unit.percent'
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        position = None
        if self.state.domain == cover.DOMAIN:
            position = self.state.attributes.get(cover.ATTR_CURRENT_POSITION)

        if position is None:
            return 0
        else:
            return float(position)

    async def set_state(self, data, state):
        """Set device state."""
        if self.state.domain == cover.DOMAIN:
            service = cover.SERVICE_SET_COVER_POSITION
            attr = cover.ATTR_POSITION
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Unsupported domain')

        value = state['value']
        if value < 0:
            value = min(self.get_value() + value, 0)

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: value
            }, blocking=True, context=data.context)


@register_capability
class TemperatureCapability(_RangeCapability):
    """Set temperature functionality."""

    instance = 'temperature'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == water_heater.DOMAIN:
            return features & water_heater.SUPPORT_TARGET_TEMPERATURE
        elif domain == climate.DOMAIN:
            return features & climate.const.SUPPORT_TARGET_TEMPERATURE

        return False

    def parameters(self):
        """Return parameters for a devices request."""
        if self.state.domain == water_heater.DOMAIN:
            min_temp = self.state.attributes.get(water_heater.ATTR_MIN_TEMP)
            max_temp = self.state.attributes.get(water_heater.ATTR_MAX_TEMP)
            precision = 0.5
        elif self.state.domain == climate.DOMAIN:
            min_temp = self.state.attributes.get(climate.ATTR_MIN_TEMP)
            max_temp = self.state.attributes.get(climate.ATTR_MAX_TEMP)
            precision = self.state.attributes.get(climate.ATTR_TARGET_TEMP_STEP, 0.5)
        else:
            min_temp = 0
            max_temp = 100
            precision = 0.5
        return {
            'instance': self.instance,
            'unit': 'unit.temperature.celsius',
            'range': {
                'min': min_temp,
                'max': max_temp,
                'precision': precision
            }
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        temperature = None
        if self.state.domain == water_heater.DOMAIN:
            temperature = self.state.attributes.get(water_heater.ATTR_TEMPERATURE)
        elif self.state.domain == climate.DOMAIN:
            temperature = self.state.attributes.get(climate.ATTR_TEMPERATURE)

        if temperature is None:
            return 0
        else:
            return float(temperature)

    async def set_state(self, data, state):
        """Set device state."""
        if self.state.domain == water_heater.DOMAIN:
            service = water_heater.SERVICE_SET_TEMPERATURE
            attr = water_heater.ATTR_TEMPERATURE
        elif self.state.domain == climate.DOMAIN:
            service = climate.SERVICE_SET_TEMPERATURE
            attr = climate.ATTR_TEMPERATURE
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Unsupported domain')

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

    instance = 'humidity'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == humidifier.DOMAIN:
            return True
        elif domain == fan.DOMAIN and \
                attributes.get(ATTR_TARGET_HUMIDITY) and \
                attributes.get(ATTR_MODEL, '').startswith(MODEL_PREFIX_XIAOMI_AIRPURIFIER):
            return True

        return False

    def parameters(self):
        """Return parameters for a devices request."""
        if self.state.domain == humidifier.DOMAIN:
            min_humidity = self.state.attributes.get(humidifier.ATTR_MIN_HUMIDITY)
            max_humidity = self.state.attributes.get(humidifier.ATTR_MAX_HUMIDITY)
            precision = 1
        else:
            min_humidity = 0
            max_humidity = 100
            precision = 1
        return {
            'instance': self.instance,
            'unit': 'unit.percent',
            'range': {'min': min_humidity, 'max': max_humidity, 'precision': precision},
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        humidity = None
        if self.state.domain == humidifier.DOMAIN:
            humidity = self.state.attributes.get(humidifier.ATTR_HUMIDITY)
        elif self.state.domain == fan.DOMAIN and self.state.attributes.get(ATTR_TARGET_HUMIDITY):
            humidity = self.state.attributes.get(ATTR_TARGET_HUMIDITY)

        if humidity is None:
            return 0
        else:
            return float(humidity)

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
            raise SmartHomeError(ERR_INVALID_VALUE, 'Unsupported domain')

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

    instance = 'brightness'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == light.DOMAIN and (
            features & light.SUPPORT_BRIGHTNESS or
            light.brightness_supported(attributes.get(light.ATTR_SUPPORTED_COLOR_MODES))
        )

    def parameters(self):
        """Return parameters for a devices request."""
        return {
            'instance': self.instance,
            'unit': 'unit.percent',
            'range': {
                'min': 1,
                'max': 100,
                'precision': 1
            }
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        brightness = self.state.attributes.get(light.ATTR_BRIGHTNESS)
        if brightness is not None:
            return int(100 * (brightness / 255))

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

    instance = 'volume'

    def __init__(self, hass, state, config):
        super().__init__(hass, state, config)
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        self.retrievable = features & media_player.SUPPORT_VOLUME_SET != 0

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == media_player.DOMAIN and (
                    features & media_player.SUPPORT_VOLUME_STEP or features & media_player.SUPPORT_VOLUME_SET)

    def parameters(self):
        """Return parameters for a devices request."""
        if self.is_relative_volume_only():
            return {
                'instance': self.instance
            }
        else:
            default_values = {
                CONF_ENTITY_RANGE_MAX: 100,
                CONF_ENTITY_RANGE_MIN: 0,
                CONF_ENTITY_RANGE_PRECISION: 1
            }
            vol_max = self.get_entity_range_value(CONF_ENTITY_RANGE_MAX, default_values)
            vol_min = self.get_entity_range_value(CONF_ENTITY_RANGE_MIN, default_values)
            vol_step = self.get_entity_range_value(CONF_ENTITY_RANGE_PRECISION, default_values)
            return {
                'instance': self.instance,
                'random_access': True,
                'range': {
                    'max': vol_max,
                    'min': vol_min,
                    'precision': vol_step
                }
            }

    def is_relative_volume_only(self):
        _LOGGER.debug('CONF_RELATIVE_VOLUME_ONLY: %r' % self.entity_config.get(
            CONF_RELATIVE_VOLUME_ONLY))
        return not self.retrievable or self.entity_config.get(
            CONF_RELATIVE_VOLUME_ONLY)

    def get_entity_range_value(self, range_entity, default_values):
        if CONF_ENTITY_RANGE in self.entity_config and range_entity in self.entity_config.get(CONF_ENTITY_RANGE):
            return int(self.entity_config.get(CONF_ENTITY_RANGE).get(range_entity))
        else:
            try:
                return int(default_values[range_entity])
            except KeyError as e:
                _LOGGER.error('Invalid element of range object: %r' % range_entity)
                _LOGGER.error('Undefined unit: {}'.format(e.args[0]))
                return 0

    def get_value(self):
        """Return the state value of this capability for this entity."""
        level = self.state.attributes.get(
            media_player.ATTR_MEDIA_VOLUME_LEVEL)

        if level is None:
            return 0
        else:
            return int(level * 100)

    async def set_state(self, data, state):
        """Set device state."""
        set_volume_level = None
        if 'relative' in state and state['relative']:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES)
            if features & media_player.SUPPORT_VOLUME_STEP:
                if state['value'] > 0:
                    service = media_player.SERVICE_VOLUME_UP
                else:
                    service = media_player.SERVICE_VOLUME_DOWN
                for i in range(abs(state['value'])):
                    await self.hass.services.async_call(
                        media_player.DOMAIN,
                        service, {
                            ATTR_ENTITY_ID: self.state.entity_id
                        }, blocking=True, context=data.context)
            else:
                set_volume_level = (self.get_value() + state['value']) / 100
        else:
            set_volume_level = state['value'] / 100

        if set_volume_level is not None:
            await self.hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_VOLUME_SET, {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.const.ATTR_MEDIA_VOLUME_LEVEL: set_volume_level,
                }, blocking=True, context=data.context)


@register_capability
class ChannelCapability(_RangeCapability):
    """Set channel functionality."""

    instance = 'channel'

    def __init__(self, hass, state, config):
        super().__init__(hass, state, config)
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        self.retrievable = features & media_player.SUPPORT_PLAY_MEDIA != 0 and \
            self.entity_config.get(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID)

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        return domain == media_player.DOMAIN and (
                (features & media_player.SUPPORT_PLAY_MEDIA and
                    entity_config.get(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID)) or (
                    features & media_player.SUPPORT_PREVIOUS_TRACK
                    and features & media_player.SUPPORT_NEXT_TRACK)
        )

    def parameters(self):
        """Return parameters for a devices request."""
        if self.retrievable:
            return {
                'instance': self.instance,
                'random_access': True,
                'range': {
                    'max': 999,
                    'min': 0,
                    'precision': 1
                }
            }
        else:
            return {
                'instance': self.instance,
                'random_access': False
            }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if not self.retrievable or self.state.attributes.get(
                media_player.ATTR_MEDIA_CONTENT_TYPE) \
                != media_player.const.MEDIA_TYPE_CHANNEL:
            return 0
        try:
            return int(self.state.attributes.get(
                media_player.ATTR_MEDIA_CONTENT_ID))
        except ValueError:
            return 0
        except TypeError:
            return 0

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
        'alarm': ['Тревога', 'Alarm'],
        'alice': ['Алиса', 'Alice'],
        'candle': ['Свеча', 'Огонь', 'Candle', 'Fire'],
        'dinner': ['Ужин', 'Dinner'],
        'fantasy': ['Фантазия', 'Fantasy'],
        'garland': ['Гирлянда', 'Garland'],
        'jungle': ['Джунгли', 'Jungle'],
        'movie': ['Кино', 'Movie'],
        'neon': ['Неон', 'Neon'],
        'night': ['Ночь', 'Night'],
        'ocean': ['Океан', 'Ocean'],
        'party': ['Вечеринка', 'Party'],
        'reading': ['Чтение', 'Reading'],
        'rest': ['Отдых', 'Rest'],
        'romance': ['Романтика', 'Romance'],
        'siren': ['Сирена', 'Siren'],
        'sunrise': ['Рассвет', 'Sunrise'],
        'sunset': ['Закат', 'Sunset']
    }

    def parameters(self):
        """Return parameters for a devices request."""
        result = {}

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if features & light.SUPPORT_COLOR or \
                light.COLOR_MODE_RGB in supported_color_modes or \
                light.COLOR_MODE_HS in supported_color_modes:
            result['color_model'] = 'rgb'

        if features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
            max_temp = self.state.attributes[light.ATTR_MIN_MIREDS]
            min_temp = self.state.attributes[light.ATTR_MAX_MIREDS]
            result['temperature_k'] = {
                'min': color_util.color_temperature_mired_to_kelvin(min_temp),
                'max': color_util.color_temperature_mired_to_kelvin(max_temp)
            }

        if features & light.SUPPORT_EFFECT:
            supported_scenes = self.get_supported_scenes(
                self.get_scenes_map_from_config(self.entity_config),
                self.state.attributes[light.ATTR_EFFECT_LIST]
            )
            if supported_scenes:
                result['color_scene'] = {
                    'scenes': [
                        {'id': s}
                        for s in supported_scenes
                    ]
                }

        return result

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
            _LOGGER.warning(f'Missing mapping for scene {yandex_scene}')
            return None

        for ha_effect in ha_effects:
            for am in self.state.attributes[light.ATTR_EFFECT_LIST]:
                if str(am) == ha_effect:
                    return ha_effect

        return None


@register_capability
class RgbCapability(_ColorSettingCapability):
    """RGB color functionality."""

    instance = 'rgb'

    def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
        """Test if capability is supported."""
        if domain == light.DOMAIN:
            supported_color_modes = attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

            return features & light.SUPPORT_COLOR or \
                light.COLOR_MODE_RGB in supported_color_modes or \
                light.COLOR_MODE_HS in supported_color_modes

        return False

    def get_value(self):
        """Return the state value of this capability for this entity."""
        rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
        if rgb_color is None:
            hs_color = self.state.attributes.get(light.ATTR_HS_COLOR)
            if hs_color is not None:
                rgb_color = color_util.color_hs_to_RGB(*hs_color)

        if rgb_color is not None:
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
        return domain == light.DOMAIN and (
            features & light.SUPPORT_COLOR_TEMP or
            light.color_temp_supported(attributes.get(light.ATTR_SUPPORTED_COLOR_MODES))
        )

    def get_value(self):
        """Return the state value of this capability for this entity."""
        temperature_mired = self.state.attributes.get(light.ATTR_COLOR_TEMP)

        if temperature_mired is not None:
            return color_util.color_temperature_mired_to_kelvin(temperature_mired)

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_KELVIN: state['value']
            }, blocking=True, context=data.context)


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
                    attributes[light.ATTR_EFFECT_LIST] or []
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

    instance = 'cleanup_mode'
    modes_map_default = {
        'auto': ['auto', 'automatic', '102'],
        'turbo': ['turbo', 'high', 'performance', '104'],
        'min': ['min', 'mop'],
        'max': ['max', 'strong'],
        'express': ['express', '105'],
        'normal': ['normal', 'medium', 'middle', 'standard', '103'],
        'quiet': ['quiet', 'low', 'min', 'silent', 'eco', '101'],
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
