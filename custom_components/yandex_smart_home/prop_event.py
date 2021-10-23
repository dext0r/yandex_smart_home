"""Implement the Yandex Smart Home event properties."""
from __future__ import annotations

from abc import ABC
from functools import wraps
import logging
from typing import Any

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON, STATE_OPEN, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State

from . import const
from .const import ERR_NOT_SUPPORTED_IN_CURRENT_MODE, STATE_EMPTY, STATE_NONE, STATE_NONE_UI
from .error import SmartHomeError
from .helpers import Config
from .prop import PREFIX_PROPERTIES, AbstractProperty, register_property

_LOGGER = logging.getLogger(__name__)

PROPERTY_EVENT = PREFIX_PROPERTIES + 'event'
PROPERTY_EVENT_VALUES = {
    const.EVENT_INSTANCE_VIBRATION: [
        const.EVENT_VIBRATION_VIBRATION,
        const.EVENT_VIBRATION_TILT,
        const.EVENT_VIBRATION_FALL,
    ],
    const.EVENT_INSTANCE_OPEN: [
        const.EVENT_OPEN_OPENED,
        const.EVENT_OPEN_CLOSED,
    ],
    const.EVENT_INSTANCE_BUTTON: [
        const.EVENT_BUTTON_CLICK,
        const.EVENT_BUTTON_DOUBLE_CLICK,
        const.EVENT_BUTTON_LONG_PRESS,
    ],
    const.EVENT_INSTANCE_MOTION: [
        const.EVENT_MOTION_DETECTED,
        const.EVENT_MOTION_NOT_DETECTED,
    ],
    const.EVENT_INSTANCE_SMOKE: [
        const.EVENT_SMOKE_DETECTED,
        const.EVENT_SMOKE_NOT_DETECTED,
        const.EVENT_SMOKE_HIGH,
    ],
    const.EVENT_INSTANCE_GAS: [
        const.EVENT_GAS_DETECTED,
        const.EVENT_GAS_NOT_DETECTED,
        const.EVENT_GAS_HIGH,
    ],
    const.EVENT_INSTANCE_BATTERY_LEVEL: [
        const.EVENT_BATTERY_LEVEL_LOW,
        const.EVENT_BATTERY_LEVEL_NORMAL,
    ],
    const.EVENT_INSTANCE_WATER_LEVEL: [
        const.EVENT_WATER_LEVEL_LOW,
        const.EVENT_WATER_LEVEL_NORMAL,
    ],
    const.EVENT_INSTANCE_WATER_LEAK: [
        const.EVENT_WATER_LEAK_LEAK,
        const.EVENT_WATER_LEAK_DRY,
    ],
}


def require_beta(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.config.beta:
            return method(self, *args, **kwargs)

        return False

    return wrapper


class EventProperty(AbstractProperty, ABC):
    type = PROPERTY_EVENT

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)
        self.values = PROPERTY_EVENT_VALUES.get(self.instance)

    def parameters(self) -> dict[str, Any]:
        return {
            'instance': self.instance,
            'events': [
                {'value': v}
                for v in self.values
            ]
        } if self.values else {}

    @staticmethod
    def bool_value(value) -> bool:
        """Return the bool value according to any type of value."""
        return value in [1, STATE_ON, STATE_OPEN, 'high', True]

    def event_value(self, value) -> str | None:
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

        if self.instance == const.EVENT_INSTANCE_OPEN:
            return const.EVENT_OPEN_OPENED if self.bool_value(value) else const.EVENT_OPEN_CLOSED

        elif self.instance == const.EVENT_INSTANCE_MOTION:
            return const.EVENT_MOTION_DETECTED if self.bool_value(value) else const.EVENT_MOTION_NOT_DETECTED

        elif self.instance == const.EVENT_INSTANCE_SMOKE:
            if value == 'high':
                return const.EVENT_SMOKE_HIGH

            return const.EVENT_SMOKE_DETECTED if self.bool_value(value) else const.EVENT_SMOKE_NOT_DETECTED

        elif self.instance == const.EVENT_INSTANCE_GAS:
            if value == 'high':
                return const.EVENT_GAS_HIGH

            return const.EVENT_GAS_DETECTED if self.bool_value(value) else const.EVENT_GAS_NOT_DETECTED

        elif self.instance in const.EVENT_INSTANCE_BATTERY_LEVEL:
            return const.EVENT_BATTERY_LEVEL_LOW if self.bool_value(value) else const.EVENT_BATTERY_LEVEL_NORMAL

        elif self.instance in const.EVENT_INSTANCE_WATER_LEVEL:
            return const.EVENT_WATER_LEVEL_LOW if self.bool_value(value) else const.EVENT_WATER_LEVEL_NORMAL

        elif self.instance == const.EVENT_INSTANCE_WATER_LEAK:
            return const.EVENT_WATER_LEAK_LEAK if self.bool_value(value) else const.EVENT_WATER_LEAK_DRY

        elif self.instance in const.EVENT_INSTANCE_BUTTON:
            if value in ['single', 'click']:
                return const.EVENT_BUTTON_CLICK
            elif value in ['double', 'double_click']:
                return const.EVENT_BUTTON_DOUBLE_CLICK
            elif value in ['long', 'long_click', 'long_click_press', 'hold']:
                return const.EVENT_BUTTON_LONG_PRESS

        elif self.instance in const.EVENT_INSTANCE_VIBRATION:
            if value in ['vibrate', 'vibration', 'actively', 'move', 'tap_twice', 'shake_air', 'swing']:
                return const.EVENT_VIBRATION_VIBRATION
            elif self.bool_value(value):
                return const.EVENT_VIBRATION_VIBRATION
            elif value in ['tilt', 'flip90', 'flip180', 'rotate']:
                return const.EVENT_VIBRATION_TILT
            elif value in ['free_fall', 'drop']:
                return const.EVENT_VIBRATION_FALL

    def get_value(self) -> str | None:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.event_value(self.state.state)

        raise SmartHomeError(
            ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
            f'Failed to get value for instance {self.instance} of {self.state.entity_id}'
        )


@register_property
class ContactProperty(EventProperty):
    instance = const.EVENT_INSTANCE_OPEN

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) in (
                binary_sensor.DEVICE_CLASS_DOOR,
                binary_sensor.DEVICE_CLASS_GARAGE_DOOR,
                binary_sensor.DEVICE_CLASS_WINDOW,
                binary_sensor.DEVICE_CLASS_OPENING
            )

        return False


@register_property
class MotionProperty(EventProperty):
    instance = const.EVENT_INSTANCE_MOTION

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) in (
                binary_sensor.DEVICE_CLASS_MOTION,
                binary_sensor.DEVICE_CLASS_OCCUPANCY,
                binary_sensor.DEVICE_CLASS_PRESENCE
            )

        return False


@register_property
class GasProperty(EventProperty):
    instance = const.EVENT_INSTANCE_GAS

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_GAS

        return False


@register_property
class SmokeProperty(EventProperty):
    instance = const.EVENT_INSTANCE_SMOKE

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_SMOKE

        return False


@register_property
class BatteryLevelLowProperty(EventProperty):
    instance = const.EVENT_INSTANCE_BATTERY_LEVEL

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_BATTERY

        return False


@register_property
class WaterLevelLowProperty(EventProperty):
    instance = const.EVENT_INSTANCE_WATER_LEVEL

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == 'water_level'

        return False


@register_property
class WaterLeakProperty(EventProperty):
    instance = const.EVENT_INSTANCE_WATER_LEAK

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_MOISTURE

        return False


@register_property
class ButtonBinarySensorProperty(EventProperty):
    instance = const.EVENT_INSTANCE_BUTTON
    retrievable = False

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get('last_action') in [
                'single', 'click', 'double', 'double_click',
                'long', 'long_click', 'long_click_press',
                'long_click_release', 'hold', 'release',
                'triple', 'quadruple', 'many'
            ]

        return False

    def get_value(self) -> str | None:
        return self.event_value(self.state.attributes.get('last_action'))


@register_property
class ButtonSensorProperty(EventProperty):
    instance = const.EVENT_INSTANCE_BUTTON
    retrievable = False

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get('action') in [
                'single', 'click', 'double', 'double_click',
                'long', 'long_click', 'long_click_press',
                'long_click_release', 'hold', 'release',
                'triple', 'quadruple', 'many'
            ]

        return False

    def get_value(self) -> str | None:
        return self.event_value(self.state.attributes.get('action'))


@register_property
class VibrationBinarySensorProperty(EventProperty):
    instance = const.EVENT_INSTANCE_VIBRATION
    retrievable = False

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == binary_sensor.DOMAIN:
            if self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_VIBRATION:
                return True

            return self.state.attributes.get('last_action') in [
                'vibrate', 'tilt', 'free_fall', 'actively',
                'move', 'tap_twice', 'shake_air', 'swing',
                'flip90', 'flip180', 'rotate', 'drop'
            ]

        return False

    def get_value(self) -> str | None:
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.DEVICE_CLASS_VIBRATION:
            return self.event_value(self.state.state)

        return self.event_value(self.state.attributes.get('last_action'))


@register_property
class VibrationSensorProperty(EventProperty):
    instance = const.EVENT_INSTANCE_VIBRATION
    retrievable = False

    @require_beta
    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get('action') in [
                'vibrate', 'tilt', 'free_fall', 'actively',
                'move', 'tap_twice', 'shake_air', 'swing',
                'flip90', 'flip180', 'rotate', 'drop'
            ]

        return False

    def get_value(self) -> str | None:
        return self.event_value(self.state.attributes.get('action'))
