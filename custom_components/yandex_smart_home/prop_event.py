"""Implement the Yandex Smart Home event properties."""
from __future__ import annotations

from abc import ABC
import logging

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON, STATE_OPEN, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State

from . import const
from .const import ERR_NOT_SUPPORTED_IN_CURRENT_MODE, PROPERTY_TYPE_EVENT_VALUES, STATE_EMPTY, STATE_NONE, STATE_NONE_UI
from .error import SmartHomeError
from .helpers import Config
from .prop import PREFIX_PROPERTIES, AbstractProperty, register_property

_LOGGER = logging.getLogger(__name__)

PROPERTY_EVENT = PREFIX_PROPERTIES + 'event'
EVENTS_VALUES = PROPERTY_TYPE_EVENT_VALUES


class EventProperty(AbstractProperty, ABC):
    type = PROPERTY_EVENT

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)
        self.values = EVENTS_VALUES.get(self.instance)

    def parameters(self):
        return {
            'instance': self.instance,
            'events': [
                {'value': v}
                for v in self.values
            ]
        } if self.values else {}

    @staticmethod
    def bool_value(value):
        """Return the bool value according to any type of value."""
        return value in [1, STATE_ON, STATE_OPEN, 'high', True]

    def event_value(self, value):
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

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
            if value in ['single', 'click']:
                return 'click'
            elif value in ['double', 'double_click']:
                return 'double_click'
            elif value in ['long', 'long_click', 'long_click_press', 'hold']:
                return 'long_press'
        elif self.instance in ['vibration']:
            if value in ['vibrate', 'vibration', 'actively', 'move',
                         'tap_twice', 'shake_air', 'swing'] or self.bool_value(value):
                return 'vibration'
            elif value in ['tilt', 'flip90', 'flip180', 'rotate']:
                return 'tilt'
            elif value in ['free_fall', 'drop']:
                return 'fall'

    def get_value(self):
        if self.state.domain == binary_sensor.DOMAIN:
            return self.event_value(self.state.state)

        raise SmartHomeError(
            ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
            f'Failed to get value for instance {self.instance} of {self.state.entity_id}'
        )


@register_property
class ContactProperty(EventProperty):
    instance = const.PROPERTY_TYPE_OPEN

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
class MotionProperty(EventProperty):
    instance = const.PROPERTY_TYPE_MOTION

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
class GasProperty(EventProperty):
    instance = const.PROPERTY_TYPE_GAS

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_GAS

        return False


@register_property
class SmokeProperty(EventProperty):
    instance = const.PROPERTY_TYPE_SMOKE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_SMOKE

        return False


@register_property
class BatteryLevelLowProperty(EventProperty):
    instance = const.PROPERTY_TYPE_BATTERY_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_BATTERY

        return False


@register_property
class WaterLevelLowProperty(EventProperty):
    instance = const.PROPERTY_TYPE_WATER_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == 'water_level'

        return False


@register_property
class WaterLeakProperty(EventProperty):
    instance = const.PROPERTY_TYPE_WATER_LEAK

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_MOISTURE

        return False


@register_property
class ButtonProperty(EventProperty):
    instance = const.PROPERTY_TYPE_BUTTON
    retrievable = False

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

    def get_value(self):
        if self.state.domain == binary_sensor.DOMAIN:
            return self.event_value(self.state.attributes.get('last_action'))
        elif self.state.domain == sensor.DOMAIN:
            return self.event_value(self.state.attributes.get('action'))


@register_property
class VibrationProperty(EventProperty):
    instance = const.PROPERTY_TYPE_VIBRATION
    retrievable = False

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

    def get_value(self):
        if self.state.domain == binary_sensor.DOMAIN:
            if self.state.attributes.get('last_action'):
                return self.event_value(self.state.attributes.get('last_action'))
            else:
                return self.event_value(self.state.state)
        elif self.state.domain == sensor.DOMAIN:
            return self.event_value(self.state.attributes.get('action'))
