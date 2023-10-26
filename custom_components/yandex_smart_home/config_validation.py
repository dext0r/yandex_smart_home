"""Helpers for config validation using voluptuous."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.util.color import RGBColor
import voluptuous as vol

from . import const
from .color import ColorName, rgb_to_int
from .const import MediaPlayerFeature, PropertyInstanceType
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
from .unit_conversion import UnitOfPressure, UnitOfTemperature

if TYPE_CHECKING:
    from homeassistant.helpers import ConfigType

_LOGGER = logging.getLogger(__name__)


def property_type(value: str) -> str:
    if value.startswith(f"{PropertyInstanceType.EVENT}."):
        instance = value.split(".", 1)[1]
        try:
            EventPropertyInstance(instance)
            return value
        except ValueError:
            raise vol.Invalid(
                f"Event property type '{instance}' is not supported, "
                f"see valid event types at https://docs.yaha-cloud.ru/master/devices/sensor/event/#type"
            )

    if value.startswith(f"{PropertyInstanceType.FLOAT}."):
        instance = value.split(".", 1)[1]
        try:
            FloatPropertyInstance(instance)
            return value
        except ValueError:
            raise vol.Invalid(
                f"Float property type '{instance}' is not supported, "
                f"see valid float types at https://docs.yaha-cloud.ru/master/devices/sensor/float/#type"
            )

    for enum in [FloatPropertyInstance, EventPropertyInstance]:
        try:
            enum(value)
            return value
        except ValueError:
            pass

    raise vol.Invalid(
        f"Property type '{value}' is not supported, "
        f"see valid types at https://docs.yaha-cloud.ru/master/devices/sensor/event/#type and "
        f"https://docs.yaha-cloud.ru/master/devices/sensor/float/#type"
    )


def property_attributes(value: ConfigType) -> ConfigType:
    """Validate keys for property."""
    entity = value.get(const.CONF_ENTITY_PROPERTY_ENTITY)
    attribute = value.get(const.CONF_ENTITY_PROPERTY_ATTRIBUTE)
    value_template = value.get(const.CONF_ENTITY_PROPERTY_VALUE_TEMPLATE)

    if value_template and (entity or attribute):
        raise vol.Invalid("entity/attribute and value_template are mutually exclusive")

    property_type_value = value.get(const.CONF_ENTITY_PROPERTY_TYPE)
    target_unit_of_measurement = value.get(const.CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT)
    if target_unit_of_measurement:
        try:
            if property_type_value in [
                FloatPropertyInstance.TEMPERATURE,
                f"{PropertyInstanceType.FLOAT}.{FloatPropertyInstance.TEMPERATURE}",
            ]:
                assert UnitOfTemperature(target_unit_of_measurement).as_property_unit
            elif property_type_value in [
                FloatPropertyInstance.PRESSURE,
                f"{PropertyInstanceType.FLOAT}.{FloatPropertyInstance.PRESSURE}",
            ]:
                assert UnitOfPressure(target_unit_of_measurement).as_property_unit
            else:
                raise ValueError
        except ValueError:
            raise vol.Invalid(
                f"Target unit of measurement '{target_unit_of_measurement}' is not supported "
                f"for {property_type_value} property, see valid values "
                f"at https://docs.yaha-cloud.ru/master/devices/sensor/float/#property-target-unit-of-measurement"
            )

    return value


def mode_instance(value: str) -> str:
    if value == ColorSettingCapabilityInstance.SCENE:
        return value

    try:
        ModeCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Mode instance '{value}' is not supported, "
            f"see valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html"
        )
        raise vol.Invalid(f"Mode instance '{value}' is not supported")

    return value


def mode(value: str) -> str:
    for enum in [ModeCapabilityMode, ColorScene]:
        try:
            enum(value)
            return value
        except ValueError:
            pass

    _LOGGER.error(
        f"Mode '{value}' is not supported, "
        f"see valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html and "
        f"https://docs.yaha-cloud.ru/master/devices/light/#scene-list"
    )

    raise vol.Invalid(f"Mode '{value}' is not supported")


def toggle_instance(value: str) -> str:
    try:
        ToggleCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Toggle instance '{value}' is not supported, "
            f"see valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html"
        )
        raise vol.Invalid(f"Toggle instance '{value}' is not supported")

    return value


def range_instance(value: str) -> str:
    try:
        RangeCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Range instance '{value}' is not supported, "
            f"see valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html"
        )
        raise vol.Invalid(f"Range instance '{value}' is not supported")

    return value


def entity_features(value: list[str]) -> list[str]:
    for feature in value:
        try:
            MediaPlayerFeature(feature)
        except ValueError:
            raise vol.Invalid(f"Feature {feature} is not supported")

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
        f"Device type '{value}' is not supported, "
        f"see valid device types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html"
    )
    raise vol.Invalid(f"Device type '{value}' is not supported")


def color_name(value: str) -> str:
    try:
        ColorName(value)
    except ValueError:
        _LOGGER.error(
            f"Color name '{value}' is not supported, "
            f"see valid values at https://docs.yaha-cloud.ru/master/devices/light/#color-profile-config"
        )
        raise vol.Invalid(f"Color name '{value}' is not supported")

    return value


def color_value(value: list[Any] | int) -> int:
    if isinstance(value, (int, str)):
        return int(value)

    if isinstance(value, list) and len(value) == 3:
        return rgb_to_int(RGBColor(*[int(v) for v in value]))

    raise vol.Invalid(f"Invalid value: {value}")


def custom_capability_state(value: ConfigType) -> ConfigType:
    """Validate keys for custom capability."""
    state_entity_id = value.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
    state_attribute = value.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)
    state_template = value.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE)

    if state_template and (state_entity_id or state_attribute):
        raise vol.Invalid("state_entity_id/state_attribute and state_template are mutually exclusive")

    return value
