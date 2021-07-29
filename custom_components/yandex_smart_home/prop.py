"""Implement the Yandex Smart Home properties."""
import logging
from typing import Any

from homeassistant.components import (
    climate,
    binary_sensor,
    fan,
    humidifier,
    light,
    sensor,
    switch,
    vacuum,
    air_quality,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE,
    ATTR_UNIT_OF_MEASUREMENT,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    STATE_UNAVAILABLE,
    STATE_ON,
    STATE_OPEN,
    STATE_UNKNOWN,
)

from .error import SmartHomeError
from .const import (
    DOMAIN,
    ERR_DEVICE_NOT_FOUND,
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    STATE_NONE,
    DATA_CONFIG,
    CONF_PRESSURE_UNIT,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    PRESSURE_UNITS_TO_YANDEX_UNITS,
    PRESSURE_FROM_PASCAL,
    PRESSURE_TO_PASCAL,
    NOTIFIER_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

PREFIX_PROPERTIES = 'devices.properties.'
PROPERTY_FLOAT = PREFIX_PROPERTIES + 'float'
PROPERTY_EVENT = PREFIX_PROPERTIES + 'event'

EVENTS_VALUES = {
    'vibration': ['vibration', 'tilt', 'fall'],
    'open': ['opened', 'closed'],
    'button': ['click', 'double_click', 'long_press'],
    'motion': ['detected', 'not_detected'],
    'smoke': ['detected', 'not_detected', 'high'],
    'gas': ['detected', 'not_detected', 'high'],
    'battery_level': ['low', 'normal'],
    'water_level': ['low', 'normal'],
    'water_leak': ['leak', 'dry']
}

PROPERTIES = []


def register_property(prop):
    """Decorate a function to register a property."""
    PROPERTIES.append(prop)
    return prop


class _Property:
    """Represents a Property."""

    type = ''
    instance = ''
    values = []
    reportable = False
    retrievable = True

    def __init__(self, hass, state, entity_config):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.config = hass.data[DOMAIN][DATA_CONFIG]
        self.entity_config = entity_config
        self.reportable = hass.data[DOMAIN][NOTIFIER_ENABLED]

    @staticmethod
    def supported(domain, features, entity_config, attributes):
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
        """Return the state of this property for this entity."""
        return {
            'type': self.type,
            'state': {
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

    @staticmethod
    def bool_value(value):
        """Return the bool value according to any type of value."""
        return value in [1, STATE_ON, STATE_OPEN, 'high', True]

    def event_value(self, value):
        if self.instance in ['open']:
            return 'opened' if self.bool_value(value) else 'closed'
        elif self.instance in ['motion']:
            return 'detected' if self.bool_value(value) else 'not_detected'
        elif self.instance in ['smoke', 'gas']:
            return value if value == 'high' else 'detected' if self.bool_value(value) else 'not_detected'
        elif self.instance in ['battery_level', 'water_level']:
            return 'low' if self.bool_value(value) else 'normal'
        elif self.instance in ['water_leak']:
            return 'leak' if self.bool_value(value) else 'dry'
        elif self.instance in ['button']:
            if not value:
                if 'last_action' in self.state.attributes:
                    value = self.state.attributes.get('last_action')
                elif 'action' in self.state.attributes:
                    value = self.state.attributes.get('action')
            if value in ['single', 'click']:
                return 'click'
            elif value in ['double', 'double_click']:
                return 'double_click'
            elif value in ['long', 'long_click', 'long_click_press', 'hold']:
                return 'long_press'
        elif self.instance in ['vibration']:
            if not value:
                if 'last_action' in self.state.attributes:
                    value = self.state.attributes.get('last_action')
                elif 'action' in self.state.attributes:
                    value = self.state.attributes.get('action')
            if value in ['vibrate', 'vibration', 'actively', 'move',
                'tap_twice', 'shake_air', 'swing'] or self.bool_value(value):
                return 'vibration'
            elif value in ['tilt', 'flip90', 'flip180', 'rotate']:
                return 'tilt'
            elif value in ['free_fall', 'drop']:
                return 'fall'
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE) and self.retrievable:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Invalid {self.instance} property value: {value!r}'
            )

    def float_value(self, value: Any) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Invalid {self.instance} property value: {value!r}'
            )


class _EventProperty(_Property):
    type = PROPERTY_EVENT

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        raise NotImplementedError

    def parameters(self):
        return {
            'instance': self.instance,
            'events': [
                {'value': v}
                for v in self.values
            ]
        } if self.values else {}

    def get_value(self):
        value = False
        if self.state.domain == binary_sensor.DOMAIN:
            value = self.state.state

        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Invalid {self.instance} property value: {value!r}'
            )

        return self.event_value(value)


@register_property
class TemperatureProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'temperature'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_TEMPERATURE
        elif domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return attributes.get(climate.ATTR_CURRENT_TEMPERATURE) is not None

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.temperature.celsius'
        }

    def get_value(self):
        value = 0.0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            value = self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE)

        return self.float_value(value)


@register_property
class HumidityProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'humidity'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_HUMIDITY
        elif domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return attributes.get(climate.ATTR_CURRENT_HUMIDITY) is not None

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.percent'
        }

    def get_value(self):
        value = 0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            value = self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY)

        return self.float_value(value)


@register_property
class PressureProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'pressure'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_PRESSURE

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]],
        }

    def get_value(self):
        value = 0.0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state

        # Get a conversion multiplier to pascal
        unit = self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if unit not in PRESSURE_TO_PASCAL:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported pressure unit: {unit}'
            )

        # Convert the value to pascal and then to the chosen Yandex unit
        val = self.float_value(value) * PRESSURE_TO_PASCAL[unit] * \
            PRESSURE_FROM_PASCAL[self.config.settings[CONF_PRESSURE_UNIT]]
        return round(val, 2)


@register_property
class IlluminanceProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'illumination'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain in (sensor.DOMAIN, light.DOMAIN, fan.DOMAIN):
            return 'illuminance' in attributes or attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_ILLUMINANCE

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.illumination.lux'
        }

    def get_value(self):
        value = 0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain in (light.DOMAIN, fan.DOMAIN):
            value = self.state.attributes.get('illuminance')

        return self.float_value(value)


@register_property
class WaterLevelProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'water_level'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain in (fan.DOMAIN, humidifier.DOMAIN):
            return 'water_level' in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.percent'
        }

    def get_value(self):
        value = 0
        if self.state.domain in (fan.DOMAIN, humidifier.DOMAIN):
            value = self.state.attributes.get('water_level')

        return self.float_value(value)


@register_property
class CO2Property(_Property):
    type = PROPERTY_FLOAT
    instance = 'co2_level'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CO2
        elif domain in (air_quality.DOMAIN, fan.DOMAIN):
            return air_quality.ATTR_CO2 in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.ppm'
        }

    def get_value(self):
        value = 0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain in (air_quality.DOMAIN, fan.DOMAIN):
            value = self.state.attributes.get(air_quality.ATTR_CO2)

        return self.float_value(value)


@register_property
class PM1Property(_Property):
    type = PROPERTY_FLOAT
    instance = 'pm1_density'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_0_1 in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.density.mcg_m3'
        }

    def get_value(self):
        value = 0
        if self.state.domain == air_quality.DOMAIN:
            value = self.state.attributes.get(air_quality.ATTR_PM_0_1)

        return self.float_value(value)


@register_property
class PM25Property(_Property):
    type = PROPERTY_FLOAT
    instance = 'pm2.5_density'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_2_5 in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.density.mcg_m3'
        }

    def get_value(self):
        value = 0
        if self.state.domain == air_quality.DOMAIN:
            value = self.state.attributes.get(air_quality.ATTR_PM_2_5)

        return self.float_value(value)


@register_property
class PM10Property(_Property):
    type = PROPERTY_FLOAT
    instance = 'pm10_density'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_10 in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.density.mcg_m3'
        }

    def get_value(self):
        value = 0
        if self.state.domain == air_quality.DOMAIN:
            value = self.state.attributes.get(air_quality.ATTR_PM_10)

        return self.float_value(value)


@register_property
class TVOCProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'tvoc'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return 'total_volatile_organic_compounds' in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.density.mcg_m3'
        }

    def get_value(self):
        value = 0
        if self.state.domain == air_quality.DOMAIN:
            value = self.state.attributes.get('total_volatile_organic_compounds')

        return self.float_value(value)


@register_property
class VoltageProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'voltage'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_VOLTAGE
        elif domain in (switch.DOMAIN, light.DOMAIN):
            return ATTR_VOLTAGE in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.volt'
        }

    def get_value(self):
        value = 0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            value = self.state.attributes.get(ATTR_VOLTAGE)

        return self.float_value(value)


@register_property
class CurrentProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'amperage'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CURRENT
        elif domain in (switch.DOMAIN, light.DOMAIN):
            return 'current' in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.ampere'
        }

    def get_value(self):
        value = 0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            value = self.state.attributes.get('current')

        return self.float_value(value)


@register_property
class PowerProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'power'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_POWER
        elif domain == switch.DOMAIN:
            return 'power' in attributes or 'load_power' in attributes

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.watt'
        }

    def get_value(self):
        value = 0
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain == switch.DOMAIN:
            if 'power' in self.state.attributes:
                value = self.state.attributes.get('power')
            elif 'load_power' in self.state.attributes:
                value = self.state.attributes.get('load_power')

        return self.float_value(value)


@register_property
class BatteryProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'battery_level'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == vacuum.DOMAIN:
            return vacuum.ATTR_BATTERY_LEVEL in attributes
        elif domain == sensor.DOMAIN:
            return attributes.get(ATTR_BATTERY_LEVEL) is not None or \
                attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY
        elif domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_BATTERY_LEVEL) is not None

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': 'unit.percent'
        }

    def get_value(self):
        value = 0
        if self.state.domain == vacuum.DOMAIN:
            value = self.state.attributes.get(vacuum.ATTR_BATTERY_LEVEL)
        elif self.state.domain == sensor.DOMAIN:
            if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY:
                value = self.state.state
            elif self.state.attributes.get(ATTR_BATTERY_LEVEL) is not None:
                value = self.state.attributes.get(ATTR_BATTERY_LEVEL)
        elif self.state.domain == binary_sensor.DOMAIN:
            if self.state.attributes.get(ATTR_BATTERY_LEVEL) is not None:
                value = self.state.attributes.get(ATTR_BATTERY_LEVEL)

        return self.float_value(value)


@register_property
class ContactProperty(_EventProperty):
    instance = 'open'
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) in (
                binary_sensor.DEVICE_CLASS_DOOR,
                binary_sensor.DEVICE_CLASS_GARAGE_DOOR,
                binary_sensor.DEVICE_CLASS_WINDOW,
                binary_sensor.DEVICE_CLASS_OPENING
            )

        return False


@register_property
class MotionProperty(_EventProperty):
    instance = 'motion'
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) in (
                binary_sensor.DEVICE_CLASS_MOTION,
                binary_sensor.DEVICE_CLASS_OCCUPANCY,
                binary_sensor.DEVICE_CLASS_PRESENCE
            )

        return False


@register_property
class GasProperty(_EventProperty):
    instance = 'gas'
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_GAS

        return False


@register_property
class SmokeProperty(_EventProperty):
    instance = 'smoke'
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_SMOKE

        return False


@register_property
class WaterLevelLowProperty(_EventProperty):
    instance = 'water_level'
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == 'water_level'

        return False


@register_property
class WaterLeakProperty(_EventProperty):
    instance = 'water_leak'
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_MOISTURE

        return False


class CustomEntityProperty(_Property):
    """Represents a Property."""

    def __init__(self, hass, state, entity_config, property_config):
        super().__init__(hass, state, entity_config)

        self.instance_unit = {
            'humidity': 'unit.percent',
            'temperature': 'unit.temperature.celsius',
            'pressure': PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]],
            'water_level': 'unit.percent',
            'co2_level': 'unit.ppm',
            'power': 'unit.watt',
            'voltage': 'unit.volt',
            'battery_level': 'unit.percent',
            'amperage': 'unit.ampere',
            'illumination': 'unit.illumination.lux',
            'tvoc': 'unit.density.mcg_m3',
            'pm1_density': 'unit.density.mcg_m3',
            'pm2.5_density': 'unit.density.mcg_m3',
            'pm10_density': 'unit.density.mcg_m3'
        }

        self.property_config = property_config
        self.type = PROPERTY_FLOAT
        self.instance = property_config.get(CONF_ENTITY_PROPERTY_TYPE)

        if CONF_ENTITY_PROPERTY_ENTITY in self.property_config:
            property_entity_id = self.property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
            entity = self.hass.states.get(property_entity_id)
            if entity is None:
                raise SmartHomeError(ERR_DEVICE_NOT_FOUND, f'Entity {property_entity_id} not found')

            if entity.domain == binary_sensor.DOMAIN and self.instance in EVENTS_VALUES.keys():
                self.type = PROPERTY_EVENT
                self.values = EVENTS_VALUES.get(self.instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        return True

    def parameters(self):
        if self.instance in self.instance_unit:
            unit = self.instance_unit[self.instance]
            return {'instance': self.instance, 'unit': unit}
        elif self.type == PROPERTY_EVENT:
            return {
                'instance': self.instance,
                'events': [
                    {'value': v}
                    for v in self.values
                ]
            } if self.values else {}

        raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, f'Unit not found for type: {self.instance}')

    def get_value(self):
        value = 0
        attribute = None

        if CONF_ENTITY_PROPERTY_ATTRIBUTE in self.property_config:
            attribute = self.property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)

        if attribute:
            value = self.state.attributes.get(attribute)

        if CONF_ENTITY_PROPERTY_ENTITY in self.property_config:
            property_entity_id = self.property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
            entity = self.hass.states.get(property_entity_id)
            if entity is None:
                raise SmartHomeError(ERR_DEVICE_NOT_FOUND, f'Entity {property_entity_id} not found')

            if attribute:
                value = entity.attributes.get(attribute)
            else:
                value = entity.state

            if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE) and self.retrievable:
                raise SmartHomeError(ERR_INVALID_VALUE, f'Invalid entity {property_entity_id} value: {value!r}')

            if self.instance == 'pressure':
                # Get a conversion multiplier to pascal
                unit = entity.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
                if unit not in PRESSURE_TO_PASCAL:
                    raise SmartHomeError(
                        ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                        f'Unsupported pressure unit: {unit}'
                    )

                # Convert the value to pascal and then to the chosen Yandex unit
                value = round(self.float_value(value) * PRESSURE_TO_PASCAL[unit] *
                              PRESSURE_FROM_PASCAL[self.config.settings[CONF_PRESSURE_UNIT]], 2)

        return self.float_value(value) if self.type != PROPERTY_EVENT else self.event_value(value)
