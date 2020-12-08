"""Implement the Yandex Smart Home properties."""
import logging

from custom_components.yandex_smart_home.const import (
    ERR_DEVICE_NOT_FOUND,
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
)
from custom_components.yandex_smart_home.error import SmartHomeError
from homeassistant.components import (
    climate,
    binary_sensor,
    sensor,
    vacuum,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
	ATTR_BATTERY_LEVEL,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN
)

from .const import (
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_ATTRIBUTE
)

_LOGGER = logging.getLogger(__name__)

PREFIX_PROPERTIES = 'devices.properties.'
PROPERTY_FLOAT = PREFIX_PROPERTIES + 'float'
PROPERTY_BOOL = PREFIX_PROPERTIES + 'bool'

PROPERTIES = []


def register_property(property):
    """Decorate a function to register a property."""
    PROPERTIES.append(property)
    return property


class _Property:
    """Represents a Property."""

    type = ''
    instance = ''
    retrievable = ''
    reportable = ''

    def __init__(self, hass, state, entity_config):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.entity_config = entity_config
        self.retrievable = True # Доступен ли для встроенного датчика устройства запрос состояния - default: True
        self.reportable = True # Оповещает ли встроенный датчик об изменении состояния платформу умного дома - default: False

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


@register_property
class TemperatureProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'temperature'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_TEMPERATURE
        elif domain == climate.DOMAIN:
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
        elif self.state.domain == climate.DOMAIN:
            value = self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE)

        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "Invalid value")

        return float(value)


@register_property
class HumidityProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'humidity'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_HUMIDITY
        elif domain == climate.DOMAIN:
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
        elif self.state.domain == climate.DOMAIN:
            value = self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY)

        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "Invalid value")

        return float(value)


@register_property
class BatteryProperty(_Property):
    type = PROPERTY_FLOAT
    instance = 'battery_level'

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == vacuum.DOMAIN:
            return vacuum.ATTR_BATTERY_LEVEL in attributes
        # elif domain == sensor.DOMAIN:
            # return attributes.get(ATTR_BATTERY_LEVEL) is not None
        # elif domain == binary_sensor.DOMAIN:
            # return attributes.get(ATTR_BATTERY_LEVEL) is not None

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
        # elif self.state.domain == sensor.DOMAIN:
            # value = self.state.attributes.get(ATTR_BATTERY_LEVEL)
        # elif self.state.domain == binary_sensor.DOMAIN:
            # value = self.state.attributes.get(ATTR_BATTERY_LEVEL)
			
        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "Invalid value")

        return float(value)

# @register_property
# class MagnetProperty(_Property):
    # type = PROPERTY_BOOL
    # instance = 'magnet'

    # @staticmethod
    # def supported(domain, features, entity_config, attributes):
        # if domain == binary_sensor.DOMAIN:
            # return attributes.get(ATTR_DEVICE_CLASS) == 'opening'

        # return False

    # def parameters(self):
        # return {
            # 'instance': self.instance
        # }

    # def get_value(self):
        # value = False
        # if self.state.domain == binary_sensor.DOMAIN:
            # value = self.state.state

        # if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            # raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "Invalid value")

        # return bool(value)

# @register_property
# class MotionProperty(_Property):
    # type = PROPERTY_BOOL
    # instance = 'motion'

    # @staticmethod
    # def supported(domain, features, entity_config, attributes):
        # if domain == binary_sensor.DOMAIN:
            # return attributes.get(ATTR_DEVICE_CLASS) == 'motion'

        # return False

    # def parameters(self):
        # return {
            # 'instance': self.instance
        # }

    # def get_value(self):
        # value = False
        # if self.state.domain == binary_sensor.DOMAIN:
            # value = self.state.state

        # if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
            # raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "Invalid value")

        # return bool(value)

class CustomEntityProperty(_Property):
    """Represents a Property."""

    instance_unit = {
        'humidity': 'unit.percent',
        'temperature': 'unit.temperature.celsius',
        'water_level': 'unit.percent',
        'co2_level': 'unit.ppm',
        'power': 'unit.watt',
        'voltage': 'unit.volt',
        'battery_level': 'unit.percent',
        'amperage': 'unit.ampere'}

    def __init__(self, hass, state, entity_config, property_config):
        super().__init__(hass, state, entity_config)

        self.hass = hass
        self.state = state
        self.entity_config = entity_config
        self.property_config = property_config
        self.type = PROPERTY_FLOAT# if self.state.domain != binary_sensor.DOMAIN else PROPERTY_BOOL
        self.instance = property_config.get(CONF_ENTITY_PROPERTY_TYPE)

    def parameters(self):
        if self.instance in self.instance_unit:
            unit = self.instance_unit[self.instance]
            return {'instance': self.instance, 'unit': unit}# if self.state.domain != binary_sensor.DOMAIN else {'instance': self.instance}

        raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "unit not found for type: {}".format(self.instance))

    def get_value(self):
        value = 0
        attribute = None

        if CONF_ENTITY_PROPERTY_ATTRIBUTE in self.property_config:
            attribute = self.property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)

        if CONF_ENTITY_PROPERTY_ENTITY in self.property_config:
            property_entity_id = self.property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
            entity = self.hass.states.get(property_entity_id)
            if entity is None:
                _LOGGER.error(f'Entity not found: {property_entity_id}')
                raise SmartHomeError(ERR_DEVICE_NOT_FOUND, "Entity not found")

            if attribute:
                value = entity.attributes.get(attribute)
            else:
                value = entity.state

            if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, None):
                _LOGGER.error(f'Invalid value: {entity}')
                raise SmartHomeError(ERR_INVALID_VALUE, "Invalid value")
            return float(value)# if self.state.domain != binary_sensor.DOMAIN else bool(value)

        if attribute:
            value = self.state.attributes.get(attribute)

        return float(value)# if self.state.domain != binary_sensor.DOMAIN else bool(value)
