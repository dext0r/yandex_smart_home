"""Helpers for config validation using voluptuous."""

from contextlib import suppress
import logging
from typing import Any

from homeassistant.components.event import EventDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import CONF_DEVICE_CLASS, CONF_NAME, CONF_ROOM, CONF_TYPE
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entityfilter import BASE_FILTER_SCHEMA
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.color import RGBColor
import voluptuous as vol

from .color import ColorName, rgb_to_int
from .const import (
    CONF_BETA,
    CONF_CLOUD_STREAM,
    CONF_COLOR_PROFILE,
    CONF_ENTITY_CONFIG,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE,
    CONF_ENTITY_CUSTOM_MODE_SET_MODE,
    CONF_ENTITY_CUSTOM_MODES,
    CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE,
    CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE,
    CONF_ENTITY_CUSTOM_RANGE_SET_VALUE,
    CONF_ENTITY_CUSTOM_RANGES,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON,
    CONF_ENTITY_CUSTOM_TOGGLES,
    CONF_ENTITY_EVENT_MAP,
    CONF_ENTITY_MODE_MAP,
    CONF_ENTITY_PROPERTIES,
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_PROPERTY_VALUE_TEMPLATE,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
    CONF_ERROR_CODE_TEMPLATE,
    CONF_FEATURES,
    CONF_FILTER,
    CONF_NOTIFIER,
    CONF_NOTIFIER_OAUTH_TOKEN,
    CONF_NOTIFIER_SKILL_ID,
    CONF_NOTIFIER_USER_ID,
    CONF_PRESSURE_UNIT,
    CONF_SETTINGS,
    CONF_STATE_UNKNOWN,
    CONF_SUPPORT_SET_CHANNEL,
    CONF_TURN_OFF,
    CONF_TURN_ON,
    MediaPlayerFeature,
    PropertyInstanceType,
)
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
from .schema.property_event import get_supported_events_for_instance
from .unit_conversion import UnitOfPressure, UnitOfTemperature

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
                f"see valid event types at https://docs.yaha-cloud.ru/dev/devices/sensor/event/#type"
            )

    if value.startswith(f"{PropertyInstanceType.FLOAT}."):
        instance = value.split(".", 1)[1]
        try:
            FloatPropertyInstance(instance)
            return value
        except ValueError:
            raise vol.Invalid(
                f"Float property type '{instance}' is not supported, "
                f"see valid float types at https://docs.yaha-cloud.ru/dev/devices/sensor/float/#type"
            )

    for enum in [FloatPropertyInstance, EventPropertyInstance]:
        with suppress(ValueError):
            return enum(value).value

    device_class_to_float_instance = {
        SensorDeviceClass.ATMOSPHERIC_PRESSURE.value: FloatPropertyInstance.PRESSURE,
        SensorDeviceClass.CO2.value: FloatPropertyInstance.CO2_LEVEL,
        SensorDeviceClass.CURRENT.value: FloatPropertyInstance.AMPERAGE,
        SensorDeviceClass.ILLUMINANCE.value: FloatPropertyInstance.ILLUMINATION,
        SensorDeviceClass.PM1.value: FloatPropertyInstance.PM1_DENSITY,
        SensorDeviceClass.PM10.value: FloatPropertyInstance.PM10_DENSITY,
        SensorDeviceClass.PM25.value: FloatPropertyInstance.PM2_5_DENSITY,
        SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS.value: FloatPropertyInstance.TVOC,
    }
    with suppress(KeyError):
        instance = device_class_to_float_instance[value]
        return f"{PropertyInstanceType.FLOAT}.{instance}"

    raise vol.Invalid(
        f"Property type '{value}' is not supported, "
        f"see valid types at https://docs.yaha-cloud.ru/dev/devices/sensor/event/#type and "
        f"https://docs.yaha-cloud.ru/dev/devices/sensor/float/#type"
    )


def property_attributes(value: ConfigType) -> ConfigType:
    """Validate keys for property."""
    entity = value.get(CONF_ENTITY_PROPERTY_ENTITY)
    attribute = value.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)
    value_template = value.get(CONF_ENTITY_PROPERTY_VALUE_TEMPLATE)

    if value_template and (entity or attribute):
        raise vol.Invalid("entity/attribute and value_template are mutually exclusive")

    property_type_value = value.get(CONF_ENTITY_PROPERTY_TYPE)
    target_unit_of_measurement = value.get(CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT)
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
                f"at https://docs.yaha-cloud.ru/dev/devices/sensor/float/#property-target-unit-of-measurement"
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
            f"see valid modes at https://docs.yaha-cloud.ru/dev/advanced/capabilities/mode/#instance"
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
        f"https://docs.yaha-cloud.ru/dev/devices/light/#scene-list"
    )

    raise vol.Invalid(f"Mode '{value}' is not supported")


def event_instance(value: str) -> str:
    try:
        EventPropertyInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Event instance '{value}' is not supported, "
            f"see valid event types at https://docs.yaha-cloud.ru/dev/devices/sensor/event/#event-types"
        )
        raise vol.Invalid(f"Event instance '{value}' is not supported")

    return value


def event_map(value: dict[str, dict[str, list[str]]]) -> dict[str, dict[str, list[str]]]:
    for instance, mapped_events in value.items():
        supported_events = get_supported_events_for_instance(EventPropertyInstance(instance))
        for event in mapped_events:
            if event not in supported_events:
                _LOGGER.error(
                    f"Event '{event}' is not supported for '{instance}' event instance, "
                    f"see valid event types at https://docs.yaha-cloud.ru/dev/devices/sensor/event/#event-types"
                )
                raise vol.Invalid(f"Event '{event}' is not supported for '{instance}' event instance")

    return value


def toggle_instance(value: str) -> str:
    try:
        ToggleCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Toggle instance '{value}' is not supported, "
            f"see valid values at https://docs.yaha-cloud.ru/dev/advanced/capabilities/toggle/#instance"
        )
        raise vol.Invalid(f"Toggle instance '{value}' is not supported")

    return value


def range_instance(value: str) -> str:
    try:
        RangeCapabilityInstance(value)
    except ValueError:
        _LOGGER.error(
            f"Range instance '{value}' is not supported, "
            f"see valid values at https://docs.yaha-cloud.ru/dev/advanced/capabilities/range/#instance"
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
    if value in ("devices.types.fan", "fan"):
        _LOGGER.warning(
            f"Device type '{value}' is deprecated, use 'devices.types.ventilation.fan' or 'ventilation.fan' instead"
        )
        value = "devices.types.ventilation.fan"

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
            f"see valid values at https://docs.yaha-cloud.ru/dev/devices/light/#color-profile-config"
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
    state_entity_id = value.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
    state_attribute = value.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)
    state_template = value.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE)

    if state_template and (state_entity_id or state_attribute):
        raise vol.Invalid("state_entity_id/state_attribute and state_template are mutually exclusive")

    return value


ENTITY_PROPERTY_SCHEMA = vol.All(
    cv.has_at_least_one_key(
        CONF_ENTITY_PROPERTY_ENTITY,
        CONF_ENTITY_PROPERTY_ATTRIBUTE,
        CONF_ENTITY_PROPERTY_VALUE_TEMPLATE,
    ),
    vol.All(
        {
            vol.Required(CONF_ENTITY_PROPERTY_TYPE): vol.Schema(vol.All(str, property_type)),
            vol.Optional(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(CONF_ENTITY_PROPERTY_ENTITY): cv.entity_id,
            vol.Optional(CONF_ENTITY_PROPERTY_ATTRIBUTE): cv.string,
            vol.Optional(CONF_ENTITY_PROPERTY_VALUE_TEMPLATE): cv.template,
        },
        property_attributes,
    ),
)


ENTITY_MODE_MAP_SCHEMA = vol.Schema(
    {vol.All(cv.string, mode_instance): vol.Schema({vol.All(cv.string, mode): vol.All(cv.ensure_list, [cv.string])})}
)

ENTITY_EVENT_MAP_SCHEMA = vol.Schema(
    {vol.All(cv.string, event_instance): vol.Schema({cv.string: vol.All(cv.ensure_list, [cv.string])})}
)


ENTITY_RANGE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTITY_RANGE_MAX): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
        vol.Optional(CONF_ENTITY_RANGE_MIN): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
        vol.Optional(CONF_ENTITY_RANGE_PRECISION): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    },
)

ENTITY_CUSTOM_MODE_SCHEMA = vol.Schema(
    {
        vol.All(cv.string, mode_instance): vol.Any(
            vol.All(
                {
                    vol.Optional(CONF_ENTITY_CUSTOM_MODE_SET_MODE): cv.SERVICE_SCHEMA,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE): cv.template,
                },
                custom_capability_state,
            ),
            cv.boolean,
        )
    }
)

ENTITY_CUSTOM_RANGE_SCHEMA = vol.Schema(
    {
        vol.All(cv.string, range_instance): vol.Any(
            vol.All(
                {
                    vol.Optional(CONF_ENTITY_CUSTOM_RANGE_SET_VALUE): vol.Any(cv.SERVICE_SCHEMA),
                    vol.Optional(CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE): vol.Any(cv.SERVICE_SCHEMA),
                    vol.Optional(CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE): vol.Any(cv.SERVICE_SCHEMA),
                    vol.Optional(CONF_ENTITY_RANGE): ENTITY_RANGE_SCHEMA,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE): cv.template,
                },
                custom_capability_state,
            ),
            cv.boolean,
        )
    }
)


ENTITY_CUSTOM_TOGGLE_SCHEMA = vol.Schema(
    {
        vol.All(cv.string, toggle_instance): vol.Any(
            vol.All(
                {
                    vol.Optional(CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON): cv.SERVICE_SCHEMA,
                    vol.Optional(CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF): cv.SERVICE_SCHEMA,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
                    vol.Optional(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE): cv.template,
                },
                custom_capability_state,
            ),
            cv.boolean,
        )
    }
)


ENTITY_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_ROOM): cv.string,
            vol.Optional(CONF_TYPE): vol.All(cv.string, device_type),
            vol.Optional(CONF_TURN_ON): vol.Any(cv.SERVICE_SCHEMA, cv.boolean),
            vol.Optional(CONF_TURN_OFF): vol.Any(cv.SERVICE_SCHEMA, cv.boolean),
            vol.Optional(CONF_DEVICE_CLASS): vol.In(EventDeviceClass.BUTTON),
            vol.Optional(CONF_FEATURES): vol.All(cv.ensure_list, entity_features),
            vol.Optional(CONF_ENTITY_PROPERTIES): [ENTITY_PROPERTY_SCHEMA],
            vol.Optional(CONF_SUPPORT_SET_CHANNEL): cv.boolean,
            vol.Optional(CONF_STATE_UNKNOWN): cv.boolean,
            vol.Optional(CONF_COLOR_PROFILE): cv.string,
            vol.Optional(CONF_ERROR_CODE_TEMPLATE): cv.template,
            vol.Optional(CONF_ENTITY_RANGE): ENTITY_RANGE_SCHEMA,
            vol.Optional(CONF_ENTITY_MODE_MAP): ENTITY_MODE_MAP_SCHEMA,
            vol.Optional(CONF_ENTITY_EVENT_MAP): vol.All(ENTITY_EVENT_MAP_SCHEMA, event_map),
            vol.Optional(CONF_ENTITY_CUSTOM_MODES): ENTITY_CUSTOM_MODE_SCHEMA,
            vol.Optional(CONF_ENTITY_CUSTOM_TOGGLES): ENTITY_CUSTOM_TOGGLE_SCHEMA,
            vol.Optional(CONF_ENTITY_CUSTOM_RANGES): ENTITY_CUSTOM_RANGE_SCHEMA,
        }
    )
)

NOTIFIER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NOTIFIER_OAUTH_TOKEN): cv.string,
        vol.Required(CONF_NOTIFIER_SKILL_ID): cv.string,
        vol.Required(CONF_NOTIFIER_USER_ID): cv.string,
    },
)


SETTINGS_SCHEMA = vol.All(
    cv.deprecated(CONF_PRESSURE_UNIT),
    {
        vol.Optional(CONF_PRESSURE_UNIT): cv.string,
        vol.Optional(CONF_BETA): cv.boolean,
        vol.Optional(CONF_CLOUD_STREAM): cv.boolean,
    },
)


YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(CONF_NOTIFIER): vol.All(cv.ensure_list, [NOTIFIER_SCHEMA]),
            vol.Optional(CONF_SETTINGS): vol.All(lambda value: value or {}, SETTINGS_SCHEMA),
            vol.Optional(CONF_FILTER): BASE_FILTER_SCHEMA,
            vol.Optional(CONF_ENTITY_CONFIG): vol.All(lambda value: value or {}, {cv.entity_id: ENTITY_SCHEMA}),
            vol.Optional(CONF_COLOR_PROFILE): vol.Schema({cv.string: {vol.All(color_name): vol.All(color_value)}}),
        },
    )
)
