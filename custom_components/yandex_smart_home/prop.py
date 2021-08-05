"""Implement the Yandex Smart Home properties."""
from __future__ import annotations
import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant, State
from homeassistant.components import (
    climate,
    binary_sensor,
    fan,
    humidifier,
    light,
    sensor,
    switch,
    air_quality,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_BATTERY_LEVEL,
    ATTR_VOLTAGE,
    ATTR_UNIT_OF_MEASUREMENT,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
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

from . import const
from .error import SmartHomeError
from .const import (
    DOMAIN,
    ERR_DEVICE_NOT_FOUND,
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    STATE_NONE,
    STATE_NONE_UI,
    CONFIG,
    CONF_PRESSURE_UNIT,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
    PROPERTY_TYPE_TO_UNITS,
    PROPERTY_TYPE_EVENT_VALUES,
    PRESSURE_UNITS_TO_YANDEX_UNITS,
    PRESSURE_FROM_PASCAL,
    PRESSURE_TO_PASCAL,
    NOTIFIER_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

PREFIX_PROPERTIES = 'devices.properties.'
PROPERTY_FLOAT = PREFIX_PROPERTIES + 'float'
PROPERTY_EVENT = PREFIX_PROPERTIES + 'event'
EVENTS_VALUES = PROPERTY_TYPE_EVENT_VALUES

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

    def __init__(self, hass: HomeAssistant, state: State, entity_config: dict[str, Any]):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.config = hass.data[DOMAIN][CONFIG]
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
                ERR_INVALID_VALUE,
                f'Invalid {self.instance} property value: {value!r}'
            )

    def float_value(self, value: Any) -> Optional[float]:
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )

    def convert_value(self, value: Any, from_unit: Optional[str]):
        float_value = self.float_value(value)
        if float_value is None:
            return None

        if self.instance == const.PROPERTY_TYPE_PRESSURE:
            if from_unit not in PRESSURE_TO_PASCAL:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f'Unsupported pressure unit "{from_unit}" '
                    f'for {self.instance} instance of {self.state.entity_id}'
                )

            return round(
                float_value * PRESSURE_TO_PASCAL[from_unit] *
                PRESSURE_FROM_PASCAL[self.config.settings[CONF_PRESSURE_UNIT]], 2
            )
        elif self.instance == const.PROPERTY_TYPE_TVOC:
            # average molecular weight of tVOC = 110 g/mol
            CONCENTRATION_TO_MCG_M3 = {
                CONCENTRATION_PARTS_PER_BILLION: 4.49629381184,
                CONCENTRATION_PARTS_PER_MILLION: 4496.29381184,
                CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT: 35.3146667215,
                CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER: 1000,
                CONCENTRATION_MICROGRAMS_PER_CUBIC_METER: 1
            }

            return round(float_value * CONCENTRATION_TO_MCG_M3.get(from_unit, 1), 2)

        return value


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

        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE) and self.retrievable:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )

        return self.event_value(value)


# noinspection PyAbstractClass
class _FloatProperty(_Property):
    type = PROPERTY_FLOAT

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': const.PROPERTY_TYPE_TO_UNITS[self.instance]
        }


@register_property
class TemperatureProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_TEMPERATURE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_TEMPERATURE
        elif domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return attributes.get(climate.ATTR_CURRENT_TEMPERATURE) is not None

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE))


@register_property
class HumidityProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_HUMIDITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_HUMIDITY
        elif domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return attributes.get(climate.ATTR_CURRENT_HUMIDITY) is not None

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY))


@register_property
class PressureProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_PRESSURE

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
        return self.convert_value(self.state.state, self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))


@register_property
class IlluminanceProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_ILLUMINATION

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain in (sensor.DOMAIN, light.DOMAIN, fan.DOMAIN):
            return 'illuminance' in attributes or attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_ILLUMINANCE

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (light.DOMAIN, fan.DOMAIN):
            return self.float_value(self.state.attributes.get('illuminance'))


@register_property
class WaterLevelProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_WATER_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain in (fan.DOMAIN, humidifier.DOMAIN):
            return 'water_level' in attributes

        return False

    def get_value(self):
        if self.state.domain in (fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get('water_level'))


@register_property
class CO2Property(_FloatProperty):
    instance = const.PROPERTY_TYPE_CO2_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CO2
        elif domain in (air_quality.DOMAIN, fan.DOMAIN):
            return air_quality.ATTR_CO2 in attributes

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (air_quality.DOMAIN, fan.DOMAIN):
            return self.float_value(self.state.attributes.get(air_quality.ATTR_CO2))


@register_property
class PM1Property(_FloatProperty):
    instance = const.PROPERTY_TYPE_PM1_DENSITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_0_1 in attributes

        return False

    def get_value(self):
        if self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_0_1))


@register_property
class PM25Property(_FloatProperty):
    instance = const.PROPERTY_TYPE_PM2_5_DENSITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_2_5 in attributes

        return False

    def get_value(self):
        value = 0
        if self.state.domain == air_quality.DOMAIN:
            value = self.state.attributes.get(air_quality.ATTR_PM_2_5)

        return self.float_value(value)


@register_property
class PM10Property(_FloatProperty):
    instance = const.PROPERTY_TYPE_PM10_DENSITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_10 in attributes

        return False

    def get_value(self):
        if self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_10))


@register_property
class TVOCProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_TVOC

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return 'total_volatile_organic_compounds' in attributes

        return False

    def get_value(self):
        if self.state.domain == air_quality.DOMAIN:
            return self.convert_value(
                self.state.attributes.get('total_volatile_organic_compounds'),
                self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            )


@register_property
class VoltageProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_VOLTAGE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_VOLTAGE
        elif domain in (switch.DOMAIN, light.DOMAIN):
            return ATTR_VOLTAGE in attributes

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            return self.float_value(self.state.attributes.get(ATTR_VOLTAGE))


@register_property
class CurrentProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_AMPERAGE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CURRENT
        elif domain in (switch.DOMAIN, light.DOMAIN):
            return 'current' in attributes

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            return self.float_value(self.state.attributes.get('current'))


@register_property
class PowerProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_POWER

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_POWER
        elif domain == switch.DOMAIN:
            return 'power' in attributes or 'load_power' in attributes

        return False

    def get_value(self):
        value = None
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain == switch.DOMAIN:
            if 'power' in self.state.attributes:
                value = self.state.attributes.get('power')
            elif 'load_power' in self.state.attributes:
                value = self.state.attributes.get('load_power')

        return self.float_value(value)


@register_property
class BatteryLevelProperty(_FloatProperty):
    instance = const.PROPERTY_TYPE_BATTERY_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        return ATTR_BATTERY_LEVEL in attributes or attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY

    def get_value(self):
        value = None
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY:
            value = self.state.state
        elif ATTR_BATTERY_LEVEL in self.state.attributes:
            value = self.state.attributes.get(ATTR_BATTERY_LEVEL)

        if value in [const.STATE_LOW, const.STATE_CHARGING]:
            return 0

        return self.float_value(value)


@register_property
class ContactProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_OPEN
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
    instance = const.PROPERTY_TYPE_MOTION
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
    instance = const.PROPERTY_TYPE_GAS
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_GAS

        return False


@register_property
class SmokeProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_SMOKE
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_SMOKE

        return False


@register_property
class BatteryLevelLowProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_BATTERY_LEVEL
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_BATTERY

        return False


@register_property
class WaterLevelLowProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_WATER_LEVEL
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == 'water_level'

        return False


@register_property
class WaterLeakProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_WATER_LEAK
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_MOISTURE

        return False


@register_property
class ButtonProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_BUTTON
    retrievable = False
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:  # XiaomiAqara
            return ('last_action' in attributes and
                    attributes.get('last_action') in [
                        'single', 'click', 'double', 'double_click',
                        'long', 'long_click', 'long_click_press',
                        'long_click_release', 'hold', 'release',
                        'triple', 'quadruple', 'many'])
        elif domain == sensor.DOMAIN:  # XiaomiGateway3 and others
            return ('action' in attributes and
                    attributes.get('action') in [
                        'single', 'click', 'double', 'double_click',
                        'long', 'long_click', 'long_click_press',
                        'long_click_release', 'hold', 'release',
                        'triple', 'quadruple', 'many'])

        return False


@register_property
class VibrationProperty(_EventProperty):
    instance = const.PROPERTY_TYPE_VIBRATION
    retrievable = False
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:  # XiaomiAqara
            return (('last_action' in attributes and
                    attributes.get('last_action') in [
                        'vibrate', 'tilt', 'free_fall', 'actively',
                        'move', 'tap_twice', 'shake_air', 'swing',
                        'flip90', 'flip180', 'rotate', 'drop']) or
                    attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_VIBRATION)
        elif domain == sensor.DOMAIN:  # XiaomiGateway3 and others
            return ('action' in attributes and
                    attributes.get('action') in [
                        'vibrate', 'tilt', 'free_fall', 'actively',
                        'move', 'tap_twice', 'shake_air', 'swing',
                        'flip90', 'flip180', 'rotate', 'drop'])

        return False


class CustomEntityProperty(_Property):
    """Represents a Property."""

    def __init__(self, hass: HomeAssistant, state: State,
                 entity_config: dict[str, Any], property_config: dict[str, str]):
        super().__init__(hass, state, entity_config)

        self.type = PROPERTY_FLOAT
        self.property_config = property_config
        self.instance = property_config[CONF_ENTITY_PROPERTY_TYPE]
        self.instance_unit: Optional[str] = None
        self.property_state = state

        property_entity_id = self.property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
        if property_entity_id:
            self.property_state = self.hass.states.get(property_entity_id)
            if self.property_state is None:
                raise SmartHomeError(
                    ERR_DEVICE_NOT_FOUND,
                    f'Entity {property_entity_id} not found for {self.instance} instance of {self.state.entity_id}'
                )

        if self.property_state.domain == binary_sensor.DOMAIN:
            if self.instance not in PROPERTY_TYPE_EVENT_VALUES:
                raise SmartHomeError(
                    ERR_DEVICE_NOT_FOUND,
                    f'Unsupported entity {self.property_state.entity_id} for {self.instance} instance '
                    f'of {self.state.entity_id}'
                )

            self.type = PROPERTY_EVENT
            self.values = PROPERTY_TYPE_EVENT_VALUES.get(self.instance)
        elif self.property_state.domain == sensor.DOMAIN:
            if self.instance not in PROPERTY_TYPE_TO_UNITS and self.instance in PROPERTY_TYPE_EVENT_VALUES:
                # TODO: battery_level and water_level cannot be events for sensor domain
                self.type = PROPERTY_EVENT
                self.values = PROPERTY_TYPE_EVENT_VALUES.get(self.instance)

        if self.instance in [const.PROPERTY_TYPE_BUTTON, const.PROPERTY_TYPE_VIBRATION]:
            self.retrievable = False

        if self.type == PROPERTY_FLOAT:
            self.instance_unit = PROPERTY_TYPE_TO_UNITS[self.instance]

            if self.instance == const.PROPERTY_TYPE_PRESSURE:
                self.instance_unit = PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]]

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        return True

    def parameters(self):
        if self.type == PROPERTY_FLOAT:
            return {
                'instance': self.instance,
                'unit': self.instance_unit
            }
        elif self.type == PROPERTY_EVENT:
            if not self.values:
                raise SmartHomeError(
                    ERR_DEVICE_NOT_FOUND,
                    f'No values for {self.instance} instance of {self.state.entity_id}'
                )

            return {
                'instance': self.instance,
                'events': [
                    {'value': v}
                    for v in self.values
                ]
            }

    def get_value(self):
        if not self.retrievable:
            return None

        value_attribute = self.property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)

        if value_attribute:
            if value_attribute not in self.property_state.attributes:
                raise SmartHomeError(
                    ERR_DEVICE_NOT_FOUND,
                    f'Attribute {value_attribute} not found in entity {self.property_state.entity_id} '
                    f'for {self.instance} instance of {self.state.entity_id}'
                )

            value = self.property_state.attributes[value_attribute]
        else:
            value = self.property_state.state

        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI):
            if self.type == PROPERTY_FLOAT:
                return None

            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for {self.instance} instance of {self.state.entity_id}'
            )

        if self.instance in [const.PROPERTY_TYPE_PRESSURE, const.PROPERTY_TYPE_TVOC]:
            value_unit = self.property_config.get(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
                                                  self.property_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))
            return self.convert_value(value, value_unit)

        return self.float_value(value) if self.type != PROPERTY_EVENT else self.event_value(value)
