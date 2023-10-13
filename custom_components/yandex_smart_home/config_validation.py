"""Helpers for config validation using voluptuous."""
import logging
from typing import Any

from homeassistant.util.color import RGBColor
import voluptuous as vol

from .color import ColorName, rgb_to_int
from .const import MediaPlayerFeature
from .schema import (
    ColorScene,
    ColorSettingCapabilityInstance,
    DeviceType,
    EventPropertyInstance,
    FloatPropertyInstance,
    ModeCapabilityInstance,
    ModeCapabilityMode,
    RangeCapabilityInstance,
    ToggleCapabilityInstance,
)
from .unit_conversion import UnitOfPressure

_LOGGER = logging.getLogger(__name__)


def property_type(value: str) -> str:
    if value == EventPropertyInstance.BUTTON:
        _LOGGER.warning(
            f"Property type {value!r} is not supported. See documentation "
            f"at https://docs.yaha-cloud.ru/master/devices/button/"
        )
        return value

    for enum in [FloatPropertyInstance, EventPropertyInstance]:
        try:
            enum(value)
            return value
        except ValueError:
            pass

    raise vol.Invalid(
        f"Property type {value!r} is not supported. "
        f"See valid types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html and "
        f"https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html"
    )


def mode_instance(value: str) -> str:
    if value == ColorSettingCapabilityInstance.SCENE:
        return value

    try:
        ModeCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Mode instance {value!r} is not supported. "
            f"See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html"
        )
        raise vol.Invalid(f"Mode instance {value!r} is not supported")

    return value


def mode(value: str) -> str:
    for enum in [ModeCapabilityMode, ColorScene]:
        try:
            enum(value)
            return value
        except ValueError:
            pass

    _LOGGER.error(
        f"Mode {value!r} is not supported. "
        f"See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html and "
        f"https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html#discovery__discovery-"
        f"parameters-color-setting-table__entry__75"
    )

    raise vol.Invalid(f"Mode {value!r} is not supported.")


def toggle_instance(value: str) -> str:
    try:
        ToggleCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Toggle instance {value!r} is not supported. "
            f"See valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html"
        )
        raise vol.Invalid(f"Toggle instance {value!r} is not supported.")

    return value


def range_instance(value: str) -> str:
    try:
        RangeCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Range instance {value!r} is not supported. "
            f"See valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html"
        )
        raise vol.Invalid(f"Range instance {value!r} is not supported.")

    return value


def entity_features(value: list[str]) -> list[str]:
    for feature in value:
        try:
            MediaPlayerFeature(feature)
        except ValueError:
            raise vol.Invalid(f"Feature {feature!r} is not supported")

    return value


def device_type(value: str) -> str:
    try:
        return str(DeviceType(value))
    except ValueError:
        try:
            return DeviceType(f"devices.types.{value}")
        except ValueError:
            pass

    _LOGGER.error(
        f"Device type {value!r} is not supported. "
        f"See valid device types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html"
    )
    raise vol.Invalid(f"Device type {value!r} is not supported.")


def pressure_unit(value: str) -> str:
    try:
        UnitOfPressure(value)
    except ValueError:
        raise vol.Invalid(f"Pressure unit {value!r} is not supported")

    return value


def color_name(value: str) -> str:
    try:
        ColorName(value)
    except ValueError:
        _LOGGER.error(
            f"Color name {value!r} is not supported. "
            f"See valid values at https://docs.yaha-cloud.ru/v0.6.x/devices/light/#color-profile-config"
        )
        raise vol.Invalid(f"Color name {value!r} is not supported")

    return value


def color_value(value: list[Any] | int) -> int:
    if isinstance(value, (int, str)):
        return int(value)

    if isinstance(value, list) and len(value) == 3:
        return rgb_to_int(RGBColor(*[int(v) for v in value]))

    raise vol.Invalid(f"Invalid value: {value!r}")
