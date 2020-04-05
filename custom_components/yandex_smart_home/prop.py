"""Implement the Yandex Smart Home properties."""
import logging

from custom_components.yandex_smart_home.const import ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from custom_components.yandex_smart_home.error import SmartHomeError
from homeassistant.components import (
    climate,
    sensor,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

PREFIX_PROPERTIES = 'devices.properties.'
PROPERTY_FLOAT = PREFIX_PROPERTIES + 'float'

PROPERTIES = []


def register_property(property):
    """Decorate a function to register a property."""
    PROPERTIES.append(property)
    return property


class _Property:
    """Represents a Property."""

    type = ''
    instance = ''

    def __init__(self, hass, state, entity_config):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.entity_config = entity_config

    def description(self):
        """Return description for a devices request."""
        response = {
            'type': self.type,
            'retrievable': True,
        }
        parameters = self.parameters()
        if parameters is not None:
            response['parameters'] = parameters

        return response

    def get_state(self):
        """Return the state of this property for this entity."""
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
