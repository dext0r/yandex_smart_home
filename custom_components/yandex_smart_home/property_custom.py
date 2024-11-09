"""Implement the Yandex Smart Home custom properties."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Self, cast

from homeassistant.components import binary_sensor
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_PROPERTY_VALUE_TEMPLATE,
    PropertyInstanceType,
)
from .helpers import APIError, DictRegistry
from .property import Property
from .property_event import (
    BatteryLevelEventProperty,
    ButtonPressEventProperty,
    EventProperty,
    FoodLevelEventProperty,
    GasEventProperty,
    MotionEventProperty,
    OpenEventProperty,
    SmokeEventProperty,
    VibrationEventProperty,
    WaterLeakEventProperty,
    WaterLevelEventProperty,
)
from .property_float import (
    BatteryLevelPercentageProperty,
    CO2LevelProperty,
    ElectricCurrentProperty,
    ElectricityMeterProperty,
    ElectricPowerProperty,
    FloatProperty,
    FoodLevelPercentageProperty,
    GasMeterProperty,
    HeatMeterProperty,
    HumidityProperty,
    IlluminationProperty,
    MeterProperty,
    PM1DensityProperty,
    PM10DensityProperty,
    PM25DensityProperty,
    PressureProperty,
    TemperatureProperty,
    TVOCConcentrationProperty,
    VoltageProperty,
    WaterLevelPercentageProperty,
    WaterMeterProperty,
)
from .schema import PropertyType, ResponseCode
from .unit_conversion import UnitOfPressure, UnitOfTemperature

if TYPE_CHECKING:
    from .entry_data import ConfigEntryData


class CustomProperty(Property, Protocol):
    """Base class for a property that user can set up using yaml configuration."""

    _config: ConfigType
    _value_template: Template

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: ConfigEntryData,
        config: ConfigType,
        device_id: str,
        value_template: Template,
    ):
        """Initialize a custom property."""
        self._hass = hass
        self._entry_data = entry_data
        self._config = config
        self._value_template = value_template
        self._value_template.hass = hass

        self.device_id = device_id

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return True

    def _get_native_value(self) -> str:
        """Return the current property value without conversion."""
        try:
            return str(self._value_template.async_render()).strip()
        except TemplateError as exc:
            raise APIError(ResponseCode.INVALID_VALUE, f"Failed to get current value for {self}: {exc!r}")

    def new_with_value_template(self, value_template: Template) -> Self:
        """Return copy of the property with new value template."""
        return self.__class__(self._hass, self._entry_data, self._config, self.device_id, value_template)

    def __repr__(self) -> str:
        """Return the representation."""
        return (
            f"<{self.__class__.__name__}"
            f" device_id={self.device_id }"
            f" instance={self.instance}"
            f" value_template={self._value_template}"
            f">"
        )


class CustomEventProperty(CustomProperty, EventProperty[Any], Protocol):
    """Base class for a event property that user can set up using yaml configuration."""

    def _get_native_value(self) -> str:
        """Return the current property value without conversion."""
        return super()._get_native_value()


EVENT_PROPERTIES_REGISTRY = DictRegistry[type[CustomEventProperty]]()


@EVENT_PROPERTIES_REGISTRY.register
class OpenCustomEventProperty(OpenEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class MotionCustomEventProperty(MotionEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class GasCustomEventProperty(GasEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class SmokeCustomEventProperty(SmokeEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class BatteryLevelCustomEventProperty(BatteryLevelEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class FoodLevelCustomEventProperty(FoodLevelEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class WaterLevelCustomEventProperty(WaterLevelEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class WaterLeakCustomEventProperty(WaterLeakEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class ButtonPressCustomEventProperty(ButtonPressEventProperty, CustomEventProperty):
    pass


@EVENT_PROPERTIES_REGISTRY.register
class VibrationCustomEventProperty(VibrationEventProperty, CustomEventProperty):
    pass


class CustomFloatProperty(CustomProperty, FloatProperty, Protocol):
    """Base class for a float property that user can set up using yaml configuration."""

    def _get_native_value(self) -> str:
        """Return the current property value without conversion."""
        return super()._get_native_value()

    @property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        if unit := self._config.get(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT):
            return str(unit)

        for s in ("state_attr(", ".attributes"):
            if s in self._value_template.template:
                return None

        info = self._value_template.async_render_to_info()
        if len(info.entities) == 1:
            entity_id = next(iter(info.entities))
            state = self._hass.states.get(entity_id)
            if state:
                return state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        return None


FLOAT_PROPERTIES_REGISTRY = DictRegistry[type[CustomFloatProperty]]()


@FLOAT_PROPERTIES_REGISTRY.register
class TemperatureCustomFloatProperty(TemperatureProperty, CustomFloatProperty):
    @property
    def unit_of_measurement(self) -> UnitOfTemperature:
        """Return the unit the property value is expressed in."""
        if unit := self._config.get(CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT):
            return UnitOfTemperature(unit)

        return super().unit_of_measurement


@FLOAT_PROPERTIES_REGISTRY.register
class HumidityCustomFloatProperty(HumidityProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class PressureCustomFloatProperty(PressureProperty, CustomFloatProperty):
    @property
    def unit_of_measurement(self) -> UnitOfPressure:
        """Return the unit the property value is expressed in."""
        if unit := self._config.get(CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT):
            return UnitOfPressure(unit)

        return super().unit_of_measurement


@FLOAT_PROPERTIES_REGISTRY.register
class IlluminationCustomFloatProperty(IlluminationProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class FoodLevelCustomFloatProperty(FoodLevelPercentageProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class WaterLevelCustomFloatProperty(WaterLevelPercentageProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class CO2LevelCustomFloatProperty(CO2LevelProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class MeterCustomFloatProperty(MeterProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class ElectricityMeterCustomFloatProperty(ElectricityMeterProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class GasMeterCustomFloatProperty(GasMeterProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class HeatMeterCustomFloatProperty(HeatMeterProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class WaterMeterCustomFloatProperty(WaterMeterProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class PM1DensityCustomFloatProperty(PM1DensityProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class PM25DensityCustomFloatProperty(PM25DensityProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class PM10DensityCustomFloatProperty(PM10DensityProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class TVOCConcentrationCustomFloatProperty(TVOCConcentrationProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class VoltageCustomFloatProperty(VoltageProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class ElectricCurrentCustomFloatProperty(ElectricCurrentProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class ElectricPowerCustomFloatProperty(ElectricPowerProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class BatteryLevelCustomFloatProperty(BatteryLevelPercentageProperty, CustomFloatProperty):
    pass


def get_custom_property(
    hass: HomeAssistant, entry_data: ConfigEntryData, config: ConfigType, device_id: str
) -> CustomProperty:
    """Return initialized custom property based on property configuration."""
    cls: type[CustomEventProperty] | type[CustomFloatProperty]
    property_type: str = config[CONF_ENTITY_PROPERTY_TYPE]
    value_template = get_value_template(hass, device_id, config)
    value_template.hass = hass

    if property_type.startswith(f"{PropertyInstanceType.EVENT}."):
        cls = EVENT_PROPERTIES_REGISTRY[property_type.split(".", 1)[1]]
    elif property_type.startswith(f"{PropertyInstanceType.FLOAT}."):
        cls = FLOAT_PROPERTIES_REGISTRY[property_type.split(".", 1)[1]]
    else:
        instance = property_type
        if instance not in FLOAT_PROPERTIES_REGISTRY and instance in EVENT_PROPERTIES_REGISTRY:
            property_type = PropertyType.EVENT
        else:
            property_type = PropertyType.FLOAT

        info = value_template.async_render_to_info()
        if len(info.entities) == 1:
            entity_id = next(iter(info.entities))
            domain, _ = split_entity_id(entity_id)

            if domain == binary_sensor.DOMAIN:
                if instance not in EVENT_PROPERTIES_REGISTRY:
                    raise APIError(
                        ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                        f"Unsupported entity {entity_id} for {instance} property of {device_id}",
                    )

                property_type = PropertyType.EVENT

        if property_type == PropertyType.EVENT:
            cls = EVENT_PROPERTIES_REGISTRY[instance]
        else:
            cls = FLOAT_PROPERTIES_REGISTRY[instance]

    return cls(hass, entry_data, config, device_id, value_template)


def get_value_template(hass: HomeAssistant, device_id: str, property_config: ConfigType) -> Template:
    """Return property value template from property configuration."""
    if template := property_config.get(CONF_ENTITY_PROPERTY_VALUE_TEMPLATE):
        return cast(Template, template)

    entity_id = property_config.get(CONF_ENTITY_PROPERTY_ENTITY, device_id)
    attribute = property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)

    if attribute:
        return Template("{{ state_attr('%s', '%s') }}" % (entity_id, attribute), hass)

    return Template("{{ states('%s') }}" % entity_id, hass)
