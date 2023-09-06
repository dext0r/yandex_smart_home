"""Implement the Yandex Smart Home custom properties."""
from typing import Any, Protocol, Self

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, State

from .const import (
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
    ERR_DEVICE_UNREACHABLE,
)
from .error import SmartHomeError
from .helpers import Config, DictRegistry
from .property import Property
from .property_event import (
    BatteryLevelEventProperty,
    ButtonPressEventProperty,
    EventProperty,
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
    ElectricPowerProperty,
    FloatProperty,
    HumidityProperty,
    IlluminationProperty,
    PM1DensityProperty,
    PM10DensityProperty,
    PM25DensityProperty,
    PressureProperty,
    TemperatureProperty,
    TVOCConcentrationProperty,
    VoltageProperty,
    WaterLevelPercentageProperty,
)


class CustomProperty(Property, Protocol):
    """Base class for a property that user can set up using yaml configuration."""

    _property_config: dict[str, Any]
    _native_value_source: State

    def __init__(
        self,
        hass: HomeAssistant,
        config: Config,
        property_config: dict[str, Any],
        device_id: str,
        native_value_source: State,
    ):
        """Initialize a custom property."""
        self._hass = hass
        self._config = config
        self._property_config = property_config
        self._native_value_source = native_value_source

        self.device_id = device_id

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return True

    def _get_native_value(self) -> str:
        """Return the current property value without conversion."""
        value_attribute = self._property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)

        if value_attribute:
            if value_attribute not in self._native_value_source.attributes:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f"Attribute {value_attribute!r} not found in entity {self._native_value_source.entity_id} "
                    f"for {self.instance.value} instance of {self.device_id}",
                )

            value = self._native_value_source.attributes[value_attribute]
        else:
            value = self._native_value_source.state

        return str(value)

    @property
    def value_entity_id(self) -> str:
        """Return id of entity the current value is based on."""
        return self._property_config.get(CONF_ENTITY_PROPERTY_ENTITY, self._native_value_source.entity_id)

    def clone(self, native_value_source: State) -> Self:
        """Clone the property with new source of native value."""
        return self.__class__(self._hass, self._config, self._property_config, self.device_id, native_value_source)


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
        if unit := self._property_config.get(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT):
            return str(unit)

        if self._property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE):
            return None

        return self._native_value_source.attributes.get(ATTR_UNIT_OF_MEASUREMENT)


FLOAT_PROPERTIES_REGISTRY = DictRegistry[type[CustomFloatProperty]]()


@FLOAT_PROPERTIES_REGISTRY.register
class TemperatureCustomFloatProperty(TemperatureProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class HumidityCustomFloatProperty(HumidityProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class PressureCustomFloatProperty(PressureProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class IlluminationCustomFloatProperty(IlluminationProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class WaterLevelCustomFloatProperty(WaterLevelPercentageProperty, CustomFloatProperty):
    pass


@FLOAT_PROPERTIES_REGISTRY.register
class CO2LevelCustomFloatProperty(CO2LevelProperty, CustomFloatProperty):
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
    hass: HomeAssistant, config: Config, property_config: dict[str, Any], device_id: str
) -> CustomProperty:
    """Return initialized custom property based on property configuration."""
    instance = property_config[CONF_ENTITY_PROPERTY_TYPE]
    state_entity_id = property_config.get(CONF_ENTITY_PROPERTY_ENTITY, device_id)

    native_value_source = hass.states.get(state_entity_id)

    if native_value_source is None:
        raise SmartHomeError(
            ERR_DEVICE_UNREACHABLE,
            f"Entity {state_entity_id} not found for {instance} instance of {device_id}",
        )

    if native_value_source.domain == binary_sensor.DOMAIN:
        try:
            return EVENT_PROPERTIES_REGISTRY[instance](hass, config, property_config, device_id, native_value_source)
        except KeyError:
            raise SmartHomeError(
                ERR_DEVICE_UNREACHABLE,
                f"Unsupported entity {native_value_source.entity_id} for {instance} instance of {device_id}",
            )

    elif native_value_source.domain == sensor.DOMAIN:
        if instance not in FLOAT_PROPERTIES_REGISTRY and instance in EVENT_PROPERTIES_REGISTRY:
            # TODO: battery_level and water_level cannot be events for sensor domain
            return EVENT_PROPERTIES_REGISTRY[instance](hass, config, property_config, device_id, native_value_source)

    return FLOAT_PROPERTIES_REGISTRY[instance](hass, config, property_config, device_id, native_value_source)
