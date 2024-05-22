from __future__ import annotations

import logging

import voluptuous as vol

from . import const
from .capability_color import ColorConverter
from .prop_float import PRESSURE_UNITS_TO_YANDEX_UNITS

_LOGGER = logging.getLogger(__name__)


def property_type(value: str) -> str:
    if value not in const.FLOAT_INSTANCES and value not in const.EVENT_INSTANCES:
        raise vol.Invalid(
            f'Property type {value!r} is not supported. '
            f'See valid types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html and '
            f'https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html'
        )

    if value == const.EVENT_INSTANCE_BUTTON:
        _LOGGER.warning('Property type "button" is not supported. See documentation '
                        'at https://docs.yaha-cloud.ru/v0.6.x/devices/button/')

    return value


def mode_instance(value: str) -> str:
    if value not in const.MODE_INSTANCES and value not in const.COLOR_SETTING_SCENE:
        _LOGGER.error(
            f'Mode instance {value!r} is not supported. '
            f'See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html'
        )

        raise vol.Invalid(f'Mode instance {value!r} is not supported.')

    return value


def mode(value: str) -> str:
    if value not in const.MODE_INSTANCE_MODES and value not in const.COLOR_SCENES:
        _LOGGER.error(
            f'Mode {value!r} is not supported. '
            f'See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html and '
            f'https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html#discovery__discovery-'
            f'parameters-color-setting-table__entry__75'
        )

        raise vol.Invalid(f'Mode {value!r} is not supported.')

    return value


def toggle_instance(value: str) -> str:
    if value not in const.TOGGLE_INSTANCES:
        _LOGGER.error(
            f'Toggle instance {value!r} is not supported. '
            f'See valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html'
        )

        raise vol.Invalid(f'Toggle instance {value!r} is not supported.')

    return value


def range_instance(value: str) -> str:
    if value not in const.RANGE_INSTANCES:
        _LOGGER.error(
            f'Range instance {value!r} is not supported. '
            f'See valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html'
        )

        raise vol.Invalid(f'Range instance {value!r} is not supported.')

    return value


def entity_features(value: list[str]):
    for feature in value:
        if feature not in const.MEDIA_PLAYER_FEATURES:
            raise vol.Invalid(f'Feature {feature!r} is not supported')

    return value


def device_type(value: str) -> str:
    if value == 'devices.types.fan':
        _LOGGER.warning(f"Device type '{value}' is deprecated, use 'devices.types.ventilation.fan' instead")
        value = 'devices.types.ventilation.fan'

    if value not in const.TYPES:
        _LOGGER.error(
            f'Device type {value!r} is not supported. '
            f'See valid device types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html'
        )

        raise vol.Invalid(f'Device type {value!r} is not supported.')

    return value


def pressure_unit(value):
    if value not in PRESSURE_UNITS_TO_YANDEX_UNITS:
        raise vol.Invalid(f'Pressure unit {value!r} is not supported')

    return value


def color_value(value: list | int) -> int:
    if isinstance(value, (int, str)):
        return int(value)

    if isinstance(value, list) and len(value) == 3:
        return ColorConverter.rgb_to_int(*[int(v) for v in value])

    raise vol.Invalid(f'Invalid value: {value!r}')
