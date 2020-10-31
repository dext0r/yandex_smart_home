"""Implement the Yandex Smart Home capabilities."""
import logging

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
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_MUTE,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_OFF,
    STATE_ON,
)

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN,
    CoverEntity,
)

from homeassistant.components.water_heater import (
    STATE_ELECTRIC, SERVICE_SET_OPERATION_MODE
)
from homeassistant.core import DOMAIN as HA_DOMAIN
from homeassistant.util import color as color_util

from .const import (
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID, CONF_RELATIVE_VOLUME_ONLY,
    CONF_ENTITY_RANGE_MAX, CONF_ENTITY_RANGE_MIN, 
    CONF_ENTITY_RANGE_PRECISION, CONF_ENTITY_RANGE,
    CONF_ENTITY_MODE_MAP)
from .error import SmartHomeError

_LOGGER = logging.getLogger(__name__)

PREFIX_CAPABILITIES = 'devices.capabilities.'
CAPABILITIES_ONOFF = PREFIX_CAPABILITIES + 'on_off'
CAPABILITIES_TOGGLE = PREFIX_CAPABILITIES + 'toggle'
CAPABILITIES_RANGE = PREFIX_CAPABILITIES + 'range'
CAPABILITIES_MODE = PREFIX_CAPABILITIES + 'mode'
CAPABILITIES_COLOR_SETTING = PREFIX_CAPABILITIES + 'color_setting'

CAPABILITIES = []


def register_capability(capability):
    """Decorate a function to register a capability."""
    CAPABILITIES.append(capability)
    return capability


class _Capability:
    """Represents a Capability."""

    type = ''
    instance = ''
    retrievable = True

    def __init__(self, hass, state, entity_config):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.entity_config = entity_config

    def description(self):
        """Return description for a devices request."""
        response = {
            'type': self.type,
            'retrievable': self.retrievable,
        }
        parameters = self.parameters()
        if parameters is not None:
            response['parameters'] = parameters

        return response

    def get_state(self):
        """Return the state of this capability for this entity."""
        return {
            'type': self.type,
            'state':  {
                'instance': self.instance,
                'value': self.get_value()
            }
        }

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

    @staticmethod
    def get_water_heater_operation(required_mode, operations_list):
        for operation in OnOffCapability.water_heater_operations[required_mode]:
            if operation in operations_list:
                return operation
        return None

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_TURN_ON and features & media_player.SUPPORT_TURN_OFF

        if domain == vacuum.DOMAIN:
            return (features & vacuum.SUPPORT_START and (
                        features & vacuum.SUPPORT_RETURN_HOME or features & vacuum.SUPPORT_STOP)) or (
                               features & vacuum.SUPPORT_TURN_ON and features & vacuum.SUPPORT_TURN_OFF)

        if domain == water_heater.DOMAIN and features & water_heater.SUPPORT_OPERATION_MODE:
            operation_list = attributes.get(water_heater.ATTR_OPERATION_LIST)
            if OnOffCapability.get_water_heater_operation(STATE_ON, operation_list) is None:
                return False
            if OnOffCapability.get_water_heater_operation(STATE_OFF, operation_list) is None:
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
            return operation_mode != OnOffCapability.get_water_heater_operation(STATE_OFF, operation_list)
        else:
            return self.state.state != STATE_OFF

    async def set_state(self, data, state):
        """Set device state."""
        domain = self.state.domain

        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, "Value is not boolean")

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
        elif self.state.domain == scene.DOMAIN or self.state.domain == \
                script.DOMAIN:
            service = SERVICE_TURN_ON
        elif self.state.domain == lock.DOMAIN:
            service = SERVICE_UNLOCK if state['value'] else \
                SERVICE_LOCK
        elif self.state.domain == water_heater.DOMAIN:
            operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)
            service = SERVICE_SET_OPERATION_MODE
            if state['value']:
                service_data[water_heater.ATTR_OPERATION_MODE] = \
                    OnOffCapability.get_water_heater_operation(STATE_ON, operation_list)
            else:
                service_data[water_heater.ATTR_OPERATION_MODE] = \
                    OnOffCapability.get_water_heater_operation(STATE_OFF, operation_list)
        else:
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF

        await self.hass.services.async_call(service_domain, service, service_data,
                                            blocking=self.state.domain != script.DOMAIN, context=data.context)


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

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == media_player.DOMAIN and features & \
            media_player.SUPPORT_VOLUME_MUTE

    def get_value(self):
        """Return the state value of this capability for this entity."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)

        return bool(muted)

    async def set_state(self, data, state):
        """Set device state."""
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, "Value is not boolean")

        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        if muted is None:
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                                 "Device probably turned off")

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

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_PAUSE and features & media_player.SUPPORT_PLAY
        elif domain == vacuum.DOMAIN:
            return features & vacuum.SUPPORT_PAUSE
        return False

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == media_player.DOMAIN:
            return bool(self.state.state != media_player.STATE_PLAYING)
        elif self.state.domain == vacuum.DOMAIN:
            return self.state.state == vacuum.STATE_PAUSED
        return None

    async def set_state(self, data, state):
        """Set device state."""
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, "Value is not boolean")

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
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            }, blocking=True, context=data.context)


@register_capability
class OscillationCapability(_ToggleCapability):
    """Oscillation functionality."""

    instance = 'oscillation'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == fan.DOMAIN and features & fan.SUPPORT_OSCILLATE

    def get_value(self):
        """Return the state value of this capability for this entity."""
        return bool(self.state.attributes.get(fan.ATTR_OSCILLATING))

    async def set_state(self, data, state):
        """Set device state."""
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, "Value is not boolean")

        await self.hass.services.async_call(
            self.state.domain,
            fan.SERVICE_OSCILLATE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                fan.ATTR_OSCILLATING: state['value']
            }, blocking=True, context=data.context)


class _ModeCapability(_Capability):
    """Base class of capabilities with mode functionality like thermostat mode
    or fan speed.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/mode-docpage/
    """

    type = CAPABILITIES_MODE
    modes_map = {}

    def get_modes_map_from_config(self):
        if CONF_ENTITY_MODE_MAP in self.entity_config:
            modes = self.entity_config.get(CONF_ENTITY_MODE_MAP)
            if self.instance in modes:
                return modes.get(self.instance)
        return None

    def get_yandex_mode_by_ha_mode(self, ha_mode):
        modes = self.get_modes_map_from_config()
        if modes is None:
            modes = self.modes_map

        for yandex_mode, names in modes.items():
            if str(ha_mode).lower() in names:
                return yandex_mode
        return None

    def get_ha_mode_by_yandex_mode(self, yandex_mode, available_modes):
        modes = self.get_modes_map_from_config()
        if modes is None:
            modes = self.modes_map

        ha_modes = modes[yandex_mode]
        for ha_mode in ha_modes:
            for am in available_modes:
                if str(am).lower() == ha_mode:
                    return ha_mode
        return None


@register_capability
class ThermostatCapability(_ModeCapability):
    """Thermostat functionality"""

    instance = 'thermostat'

    climate_map = {
        climate.const.HVAC_MODE_HEAT: 'heat',
        climate.const.HVAC_MODE_COOL: 'cool',
        climate.const.HVAC_MODE_AUTO: 'auto',
        climate.const.HVAC_MODE_DRY: 'dry',
        climate.const.HVAC_MODE_FAN_ONLY: 'fan_only'
    }

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == climate.DOMAIN:
            operation_list = attributes.get(climate.ATTR_HVAC_MODES)
            for operation in operation_list:
                if operation in ThermostatCapability.climate_map:
                    return True
        return False

    def parameters(self):
        """Return parameters for a devices request."""
        operation_list = self.state.attributes.get(climate.ATTR_HVAC_MODES)
        modes = []
        for operation in operation_list:
            if operation in self.climate_map:
                modes.append({'value': self.climate_map[operation]})

        return {
            'instance': self.instance,
            'modes': modes,
            'ordered': False
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        operation = self.state.attributes.get(climate.ATTR_HVAC_MODE)

        if operation is not None and operation in self.climate_map:
            return self.climate_map[operation]
        
        # Try to take current mode from device state
        operation = self.state.state
        if operation is not None and operation in self.climate_map:
            return self.climate_map[operation]

        # Return first value if current one is not acceptable
        for operation in self.state.attributes.get(climate.ATTR_HVAC_MODES):
            if operation in self.climate_map:
                return self.climate_map[operation]

        return 'auto'

    async def set_state(self, data, state):
        """Set device state."""
        value = None
        for climate_value, yandex_value in self.climate_map.items():
            if yandex_value == state['value']:
                value = climate_value
                break

        if value is None:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unacceptable value")

        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_HVAC_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_HVAC_MODE: value
            }, blocking=True, context=data.context)


@register_capability
class ProgramCapability(_ModeCapability):
    """Program functionality"""

    instance = "program"

    # Because there is no 1 to 1 compatibility between default humidifier modes and yandex modes,
    # we just chose what is closest or at least not too confusing
    modes_map = {
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

    # For custom modes we fallback to its number
    fallback_program_map = {
        0: "one",
        1: "two",
        2: "three",
        3: "four",
        4: "five",
        5: "six",
        6: "seven",
        7: "eight",
        8: "nine",
        9: "ten",
    }

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == humidifier.DOMAIN:
            return features & humidifier.SUPPORT_MODES
        return False

    def parameters(self):
        """Return parameters for a devices request."""
        if self.state.domain == humidifier.DOMAIN:
            mode_list = self.state.attributes.get(humidifier.ATTR_AVAILABLE_MODES)
            modes = []
            for mode in mode_list:
                value = self.get_yandex_mode_by_ha_mode(mode)
                if value is not None:
                    modes.append({"value": value})
                # If mapping not found in configuration or default map,
                # enumerate the mode by its position in the mode list
                else:
                    mode_index = mode_list.index(mode)
                    if mode_index <= 10:
                        modes.append({"value": self.fallback_program_map[mode_index]})
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        return {"instance": self.instance, "modes": modes, "ordered": False}

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == humidifier.DOMAIN:
            mode = self.state.attributes.get(humidifier.ATTR_MODE)
            if mode is not None:
                ya_mode = self.get_yandex_mode_by_ha_mode(mode)
                if ya_mode is not None:
                    return ya_mode

                # Fallback into numeric mode
                mode_list = self.state.attributes.get(humidifier.ATTR_AVAILABLE_MODES)
                mode_index = mode_list.index(mode)
                if mode_index <= 10:
                    return self.fallback_program_map[mode_index]
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        return "auto"

    async def set_state(self, data, state):
        """Set device state."""
        value = None
        if self.state.domain == humidifier.DOMAIN:
            service = humidifier.SERVICE_SET_MODE
            attr = humidifier.ATTR_MODE

            mode_list = self.state.attributes.get(humidifier.ATTR_AVAILABLE_MODES)
            try:
                value = self.get_ha_mode_by_yandex_mode(state["value"], mode_list)
            except KeyError:
                pass

            if value is None:
                for humidifier_value, yandex_value in self.fallback_program_map.items():
                    if yandex_value == state["value"]:
                        value = mode_list[humidifier_value]
                        break
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        if value is None or value not in mode_list:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unacceptable value")

        await self.hass.services.async_call(
            self.state.domain,
            service,
            {ATTR_ENTITY_ID: self.state.entity_id, attr: value},
            blocking=True,
            context=data.context,
        )


@register_capability
class InputSourceCapability(_ModeCapability):
    """Input Source functionality"""

    instance = 'input_source'

    media_player_source_map = {
        1: 'one',
        2: 'two',
        3: 'three',
        4: 'four',
        5: 'five',
        6: 'six',
        7: 'seven',
        8: 'eight',
        9: 'nine',
        10: 'ten'
    }

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == media_player.DOMAIN \
            and features & media_player.SUPPORT_SELECT_SOURCE \
            and attributes.get(media_player.ATTR_INPUT_SOURCE_LIST) is not None

    def parameters(self):
        """Return parameters for a devices request."""
        source_list = self.state.attributes.get(media_player.ATTR_INPUT_SOURCE_LIST)
        modes = []
        if source_list is not None:
            for i in range(0, min(len(source_list), 10)):
                modes.append({'value': self.media_player_source_map[i + 1]})

        return {
            'instance': self.instance,
            'modes': modes,
            'ordered': True
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        source = self.state.attributes.get(media_player.ATTR_INPUT_SOURCE)
        source_list = self.state.attributes.get(media_player.ATTR_INPUT_SOURCE_LIST)
        if source_list is not None and source in source_list:
            return self.media_player_source_map[min(source_list.index(source) + 1, 10)]
        return self.media_player_source_map[1]

    async def set_state(self, data, state):
        """Set device state."""
        value = None
        source_list = self.state.attributes.get(media_player.ATTR_INPUT_SOURCE_LIST)
        for index, yandex_value in self.media_player_source_map.items():
            if yandex_value == state['value']:
                if index <= len(source_list):
                    value = source_list[index - 1]
                break

        if value is None:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unacceptable value")

        await self.hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_SELECT_SOURCE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.const.ATTR_INPUT_SOURCE: value,
            }, blocking=True, context=data.context)


@register_capability
class FanSpeedCapability(_ModeCapability):
    """Fan speed functionality."""

    instance = 'fan_speed'

    modes_map = {
        'auto': ['auto'],
        'low': ['low', 'min', 'silent', 'level 2'],
        'medium': ['medium', 'middle', 'level 3'],
        'high': ['high', 'max', 'strong', 'favorite', 'level 4'],
    }

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == climate.DOMAIN:
            return features & climate.SUPPORT_FAN_MODE
        elif domain == fan.DOMAIN:
            return features & fan.SUPPORT_SET_SPEED
        return False

    def parameters(self):
        """Return parameters for a devices request."""
        if self.state.domain == climate.DOMAIN:
            speed_list = self.state.attributes.get(climate.ATTR_FAN_MODES)
        elif self.state.domain == fan.DOMAIN:
            speed_list = self.state.attributes.get(fan.ATTR_SPEED_LIST)
        else:
            speed_list = []

        speeds = []
        added = []
        for ha_value in speed_list:
            value = self.get_yandex_mode_by_ha_mode(ha_value)
            if value is not None and value not in added:
                speeds.append({'value': value})
                added.append(value)

        return {
            'instance': self.instance,
            'modes': speeds,
            'ordered': True
        }

    def get_ha_by_yandex_value(self, yandex_value):
        if self.state.domain == climate.DOMAIN:
            speed_list = self.state.attributes.get(climate.ATTR_FAN_MODES)
        elif self.state.domain == fan.DOMAIN:
            speed_list = self.state.attributes.get(fan.ATTR_SPEED_LIST)
        else:
            return None

        return self.get_ha_mode_by_yandex_mode(yandex_value, speed_list)

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == climate.DOMAIN:
            ha_value = self.state.attributes.get(climate.ATTR_FAN_MODE)
        elif self.state.domain == fan.DOMAIN:
            ha_value = self.state.attributes.get(fan.ATTR_SPEED)
        else:
            ha_value = None

        if ha_value is not None:
            yandex_value = self.get_yandex_mode_by_ha_mode(ha_value)
            if yandex_value is not None:
                return yandex_value

        modes = self.parameters()['modes']

        return modes[0]['value'] if len(modes) > 0 else 'auto'

    async def set_state(self, data, state):
        """Set device state."""
        value = self.get_ha_by_yandex_value(state['value'])

        if value is None:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported value")

        if self.state.domain == climate.DOMAIN:
            service = climate.SERVICE_SET_FAN_MODE
            attr = climate.ATTR_FAN_MODE
        elif self.state.domain == fan.DOMAIN:
            service = fan.SERVICE_SET_SPEED
            attr = fan.ATTR_SPEED
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: value
            }, blocking=True, context=data.context)


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

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == cover.DOMAIN:
            return features & cover.SUPPORT_SET_POSITION
        return False

    def parameters(self):
        """Return parameters for a devices request."""
        return {
				"instance": self.instance,
				"range": {
					"max": 100,
					"min": 0,
					"precision": 1
				},
				"unit": "unit.percent"
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
             raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")
             
        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: state['value']
            }, blocking=True, context=data.context)

@register_capability
class TemperatureCapability(_RangeCapability):
    """Set temperature functionality."""

    instance = 'temperature'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
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
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: state['value']
            }, blocking=True, context=data.context)


@register_capability
class HumidityCapability(_RangeCapability):
    """Set humidity functionality."""

    instance = "humidity"

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == humidifier.DOMAIN:
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
            "instance": self.instance,
            "unit": "unit.percent",
            "range": {"min": min_humidity, "max": max_humidity, "precision": precision},
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        humidity = None
        if self.state.domain == humidifier.DOMAIN:
            humidity = self.state.attributes.get(humidifier.ATTR_HUMIDITY)

        if humidity is None:
            return 0
        else:
            return float(humidity)

    async def set_state(self, data, state):
        """Set device state."""

        if self.state.domain == humidifier.DOMAIN:
            service = humidifier.SERVICE_SET_HUMIDITY
            attr = humidifier.ATTR_HUMIDITY
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        await self.hass.services.async_call(
            self.state.domain,
            service,
            {ATTR_ENTITY_ID: self.state.entity_id, attr: state["value"]},
            blocking=True,
            context=data.context,
        )


@register_capability
class BrightnessCapability(_RangeCapability):
    """Set brightness functionality."""

    instance = 'brightness'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == light.DOMAIN and features & light.SUPPORT_BRIGHTNESS

    def parameters(self):
        """Return parameters for a devices request."""
        return {
            'instance': self.instance,
            'unit': 'unit.percent',
            'range': {
                'min': 0,
                'max': 100,
                'precision': 1
            }
        }

    def get_value(self):
        """Return the state value of this capability for this entity."""
        brightness = self.state.attributes.get(light.ATTR_BRIGHTNESS)
        if brightness is None:
            return 0
        else:
            return int(100 * (brightness / 255))

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_BRIGHTNESS_PCT: state['value']
            }, blocking=True, context=data.context)


@register_capability
class VolumeCapability(_RangeCapability):
    """Set volume functionality."""

    instance = 'volume'
    retrievable = False

    def __init__(self, hass, state, config):
        super().__init__(hass, state, config)
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        self.retrievable = features & media_player.SUPPORT_VOLUME_SET != 0

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == media_player.DOMAIN and features & \
            media_player.SUPPORT_VOLUME_STEP

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
        _LOGGER.debug("CONF_RELATIVE_VOLUME_ONLY: %r" % self.entity_config.get(
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
                _LOGGER.error("Invalid element of range object: %r" % range_entity)
                _LOGGER.error('Undefined unit: {}'.format(e.args[0]))
                # raise ValueError('Undefined unit: {}'.format(e.args[0])) 
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
        if 'relative' in state and state['relative']:
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
            await self.hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_VOLUME_SET, {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.const.ATTR_MEDIA_VOLUME_LEVEL:
                        state['value'] / 100,
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

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
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
        if self.retrievable or self.state.attributes.get(
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


class _ColorSettingCapability(_Capability):
    """Base color setting functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/color_setting-docpage/
    """

    type = CAPABILITIES_COLOR_SETTING

    def parameters(self):
        """Return parameters for a devices request."""
        result = {}

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if features & light.SUPPORT_COLOR:
            result['color_model'] = 'rgb'

        if features & light.SUPPORT_COLOR_TEMP:
            max_temp = self.state.attributes[light.ATTR_MIN_MIREDS]
            min_temp = self.state.attributes[light.ATTR_MAX_MIREDS]
            result['temperature_k'] = {
                'min': color_util.color_temperature_mired_to_kelvin(min_temp),
                'max': color_util.color_temperature_mired_to_kelvin(max_temp)
            }

        return result


@register_capability
class RgbCapability(_ColorSettingCapability):
    """RGB color functionality."""

    instance = 'rgb'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == light.DOMAIN and features & light.SUPPORT_COLOR

    def get_value(self):
        """Return the state value of this capability for this entity."""
        color = self.state.attributes.get(light.ATTR_RGB_COLOR)
        if color is None:
            return 0

        rgb = color[0]
        rgb = (rgb << 8) + color[1]
        rgb = (rgb << 8) + color[2]

        return rgb

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

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        return domain == light.DOMAIN and features & light.SUPPORT_COLOR_TEMP

    def get_value(self):
        """Return the state value of this capability for this entity."""
        kelvin = self.state.attributes.get(light.ATTR_COLOR_TEMP)
        if kelvin is None:
            return 0

        return color_util.color_temperature_mired_to_kelvin(kelvin)

    async def set_state(self, data, state):
        """Set device state."""
        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_KELVIN: state['value']
            }, blocking=True, context=data.context)


@register_capability
class CleanupModeCapability(_ModeCapability):
    """Vacuum cleanup mode functionality."""

    instance = 'cleanup_mode'

    # 101-105 xiaomi miio fan speeds
    modes_map = {
        'auto': {'auto', '102'},
        'turbo': {'turbo', 'high', '104'},
        'min': {'min', 'mop'},
        'max': {'max', 'strong'},
        'express': {'express', '105'},
        'normal': {'normal', 'medium', 'middle', '103'},
        'quiet': {'quiet', 'low', 'min', 'silent', '101'},
    }

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        """Test if state is supported."""
        if domain == vacuum.DOMAIN:
            return features & vacuum.SUPPORT_FAN_SPEED
        return False

    def parameters(self):
        """Return parameters for a devices request."""
        if self.state.domain == vacuum.DOMAIN:
            speed_list = self.state.attributes.get(vacuum.ATTR_FAN_SPEED_LIST)
        else:
            speed_list = []

        speeds = []
        added = set()
        for ha_value in speed_list:
            value = self.get_yandex_mode_by_ha_mode(ha_value)
            if value is not None and value not in added:
                speeds.append({'value': value})
                added.add(value)

        return {
            'instance': self.instance,
            'modes': speeds
        }

    def get_ha_by_yandex_value(self, yandex_value):
        if self.state.domain == vacuum.DOMAIN:
            instance_speeds = self.state.attributes.get(vacuum.ATTR_FAN_SPEED_LIST)
        else:
            return None

        return self.get_ha_mode_by_yandex_mode(yandex_value, instance_speeds)

    def get_value(self):
        """Return the state value of this capability for this entity."""
        if self.state.domain == vacuum.DOMAIN:
            ha_value = self.state.attributes.get(vacuum.ATTR_FAN_SPEED)
        else:
            ha_value = None

        if ha_value is not None:
            yandex_value = self.get_yandex_mode_by_ha_mode(ha_value)
            if yandex_value is not None:
                return yandex_value

        modes = self.parameters()['modes']

        return modes[0]['value'] if len(modes) > 0 else 'auto'

    async def set_state(self, data, state):
        """Set device state."""
        value = self.get_ha_by_yandex_value(state['value'])

        if value is None:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported value")

        if self.state.domain == vacuum.DOMAIN:
            service = vacuum.SERVICE_SET_FAN_SPEED
            attr = vacuum.ATTR_FAN_SPEED
        else:
            raise SmartHomeError(ERR_INVALID_VALUE, "Unsupported domain")

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attr: value
            }, blocking=True, context=data.context)
