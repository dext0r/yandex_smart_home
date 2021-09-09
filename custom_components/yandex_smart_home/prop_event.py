"""Implement the Yandex Smart Home event properties."""
from __future__ import annotations

import logging

from abc import ABC
from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_DEVICE_CLASS

from . import const
from .const import ERR_NOT_SUPPORTED_IN_CURRENT_MODE, PROPERTY_TYPE_EVENT_VALUES
from .error import SmartHomeError
from .prop import PREFIX_PROPERTIES, AbstractProperty, register_property

_LOGGER = logging.getLogger(__name__)

PROPERTY_EVENT = PREFIX_PROPERTIES + 'event'
EVENTS_VALUES = PROPERTY_TYPE_EVENT_VALUES


class EventProperty(AbstractProperty, ABC):
    type = PROPERTY_EVENT

    def parameters(self):
        return {
            'instance': self.instance,
            'events': [
                {'value': v}
                for v in self.values
            ]
        } if self.values else {}

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
class MotionProperty(EventProperty):
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
class GasProperty(EventProperty):
    instance = const.PROPERTY_TYPE_GAS
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_GAS

        return False


@register_property
class SmokeProperty(EventProperty):
    instance = const.PROPERTY_TYPE_SMOKE
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_SMOKE

        return False


@register_property
class BatteryLevelLowProperty(EventProperty):
    instance = const.PROPERTY_TYPE_BATTERY_LEVEL
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_BATTERY

        return False


@register_property
class WaterLevelLowProperty(EventProperty):
    instance = const.PROPERTY_TYPE_WATER_LEVEL
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == 'water_level'

        return False


@register_property
class WaterLeakProperty(EventProperty):
    instance = const.PROPERTY_TYPE_WATER_LEAK
    values = EVENTS_VALUES.get(instance)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == binary_sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_MOISTURE

        return False


@register_property
class ButtonProperty(EventProperty):
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

    def get_value(self):
        if self.state.domain == binary_sensor.DOMAIN:
            return self.event_value(self.state.attributes.get('last_action'))
        elif self.state.domain == sensor.DOMAIN:
            return self.event_value(self.state.attributes.get('action'))


@register_property
class VibrationProperty(EventProperty):
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

    def get_value(self):
        if self.state.domain == binary_sensor.DOMAIN:
            if self.state.attributes.get('last_action'):
                return self.event_value(self.state.attributes.get('last_action'))
            else:
                return self.event_value(self.state.state)
        elif self.state.domain == sensor.DOMAIN:
            return self.event_value(self.state.attributes.get('action'))
