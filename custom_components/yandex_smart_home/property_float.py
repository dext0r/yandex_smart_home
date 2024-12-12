"""Implement the Yandex Smart Home float properties."""

from abc import ABC, abstractmethod
from contextlib import suppress
from functools import cached_property
from typing import Protocol, Self

from homeassistant.components import air_quality, climate, fan, humidifier, light, sensor, switch, water_heater
from homeassistant.components.air_quality import ATTR_CO2, ATTR_PM_0_1, ATTR_PM_2_5, ATTR_PM_10
from homeassistant.components.climate import ATTR_CURRENT_HUMIDITY, ATTR_CURRENT_TEMPERATURE, ATTR_HUMIDITY
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolume,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.unit_conversion import (
    BaseUnitConverter,
    ElectricCurrentConverter,
    ElectricPotentialConverter,
    EnergyConverter,
    PowerConverter,
    TemperatureConverter,
    VolumeConverter,
)

from .const import (
    ATTR_CURRENT,
    ATTR_CURRENT_CONSUMPTION,
    ATTR_ILLUMINANCE,
    ATTR_LOAD_POWER,
    ATTR_POWER,
    ATTR_TVOC,
    ATTR_WATER_LEVEL,
    STATE_CHARGING,
    STATE_EMPTY,
    STATE_LOW,
    STATE_NONE,
    STATE_NONE_UI,
    XGW3DeviceClass,
)
from .helpers import APIError
from .property import STATE_PROPERTIES_REGISTRY, Property, StateProperty
from .schema import (
    AmperageFloatPropertyParameters,
    BatteryLevelFloatPropertyParameters,
    CO2LevelFloatPropertyParameters,
    ElectricityMeterFloatPropertyParameters,
    FloatPropertyDescription,
    FloatPropertyInstance,
    FloatPropertyParameters,
    FoodLevelFloatPropertyParameters,
    GasMeterFloatPropertyParameters,
    HeatMeterFloatPropertyParameters,
    HumidityFloatPropertyParameters,
    IlluminationFloatPropertyParameters,
    MeterFloatPropertyParameters,
    PM1DensityFloatPropertyParameters,
    PM10DensityFloatPropertyParameters,
    PM25DensityFloatPropertyParameters,
    PowerFloatPropertyParameters,
    PressureFloatPropertyParameters,
    PropertyType,
    ResponseCode,
    TemperatureFloatPropertyParameters,
    TVOCFloatPropertyParameters,
    VoltageFloatPropertyParameters,
    WaterLevelFloatPropertyParameters,
    WaterMeterFloatPropertyParameters,
)
from .unit_conversion import PressureConverter, TVOCConcentrationConverter, UnitOfPressure, UnitOfTemperature


class FloatProperty(Property, Protocol):
    """Base class for float properties (sensors)."""

    type: PropertyType = PropertyType.FLOAT
    instance: FloatPropertyInstance

    @property
    @abstractmethod
    def parameters(self) -> FloatPropertyParameters:
        """Return parameters for a devices list request."""
        ...

    def get_description(self) -> FloatPropertyDescription:
        """Return a description for a device list request."""
        return FloatPropertyDescription(
            retrievable=self.retrievable, reportable=self.reportable, parameters=self.parameters
        )

    def get_value(self) -> float | None:
        """Return the current property value."""
        value = self._get_native_value()

        if value is None:
            return None

        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise APIError(ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, f"Unsupported value '{value}' for {self}")

        if self._native_unit_of_measurement and self.unit_of_measurement and self._unit_converter:
            try:
                float_value = self._unit_converter.convert(
                    float_value, self._native_unit_of_measurement, self.unit_of_measurement
                )
            except HomeAssistantError as e:
                raise APIError(
                    ResponseCode.INVALID_VALUE,
                    f"Failed to convert value from '{self._native_unit_of_measurement}' to "
                    f"'{self.unit_of_measurement}' for {self}: {e}",
                )

        lower_limit, upper_limit = self.parameters.range
        if lower_limit is not None and float_value < lower_limit:
            return lower_limit
        if upper_limit is not None and float_value > upper_limit:
            return upper_limit

        return round(float_value, 2)

    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        if other is None:
            return True

        value, other_value = self.get_value(), other.get_value()
        if value is None:
            return False

        if other_value is None or value != other_value:
            return True

        return False

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit the property value is expressed in."""
        return None

    @abstractmethod
    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        ...

    @cached_property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        return None

    @property
    def _unit_converter(self) -> BaseUnitConverter | None:
        """Return the unit converter."""
        return None  # pragma: nocover


class TemperatureProperty(FloatProperty, ABC):
    """Base class for temperature properties."""

    instance = FloatPropertyInstance.TEMPERATURE

    @property
    def parameters(self) -> TemperatureFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return TemperatureFloatPropertyParameters(unit=self.unit_of_measurement.as_property_unit)

    @property
    def unit_of_measurement(self) -> UnitOfTemperature:
        """Return the unit the property value is expressed in."""
        if self._native_unit_of_measurement:
            with suppress(ValueError):
                unit = UnitOfTemperature(self._native_unit_of_measurement)
                if unit.as_property_unit:
                    return unit

        return UnitOfTemperature.CELSIUS

    @property
    def _unit_converter(self) -> TemperatureConverter:
        """Return the unit converter."""
        return TemperatureConverter()


class HumidityProperty(FloatProperty, ABC):
    """Base class for humidity properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.HUMIDITY

    @property
    def parameters(self) -> HumidityFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return HumidityFloatPropertyParameters()


class PressureProperty(FloatProperty, ABC):
    """Base class for pressure properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.PRESSURE

    @property
    def parameters(self) -> PressureFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PressureFloatPropertyParameters(unit=self.unit_of_measurement.as_property_unit)

    @property
    def unit_of_measurement(self) -> UnitOfPressure:
        """Return the unit the property value is expressed in."""
        if self._native_unit_of_measurement:
            with suppress(ValueError):
                unit = UnitOfPressure(self._native_unit_of_measurement)
                if unit.as_property_unit:
                    return unit

        return UnitOfPressure.MMHG

    @property
    def _unit_converter(self) -> PressureConverter:
        """Return the unit converter."""
        return PressureConverter()


class IlluminationProperty(FloatProperty, ABC):
    """Base class for illumination properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.ILLUMINATION

    @property
    def parameters(self) -> IlluminationFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return IlluminationFloatPropertyParameters()


class FoodLevelPercentageProperty(FloatProperty, Protocol):
    """Base class for food level (%) properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.FOOD_LEVEL

    @property
    def parameters(self) -> FoodLevelFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return FoodLevelFloatPropertyParameters()


class WaterLevelPercentageProperty(FloatProperty, Protocol):
    """Base class for water level (%) properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.WATER_LEVEL

    @property
    def parameters(self) -> WaterLevelFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return WaterLevelFloatPropertyParameters()


class CO2LevelProperty(FloatProperty, Protocol):
    """Base class for CO2 level properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.CO2_LEVEL

    @property
    def parameters(self) -> CO2LevelFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return CO2LevelFloatPropertyParameters()


class MeterProperty(FloatProperty, Protocol):
    """Base class for meter properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.METER

    @property
    def parameters(self) -> MeterFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return MeterFloatPropertyParameters()


class ElectricityMeterProperty(FloatProperty, Protocol):
    """Base class for electricity meter properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.ELECTRICITY_METER

    @property
    def parameters(self) -> ElectricityMeterFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return ElectricityMeterFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> UnitOfEnergy:
        """Return the unit the property value is expressed in."""
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def _unit_converter(self) -> EnergyConverter:
        """Return the unit converter."""
        return EnergyConverter()


class GasMeterProperty(FloatProperty, Protocol):
    """Base class for gas meter properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.GAS_METER

    @property
    def parameters(self) -> GasMeterFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return GasMeterFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> UnitOfVolume:
        """Return the unit the property value is expressed in."""
        return UnitOfVolume.CUBIC_METERS

    @property
    def _unit_converter(self) -> VolumeConverter:
        """Return the unit converter."""
        return VolumeConverter()


class HeatMeterProperty(FloatProperty, Protocol):
    """Base class for heat meter properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.HEAT_METER

    @property
    def parameters(self) -> HeatMeterFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return HeatMeterFloatPropertyParameters()


class WaterMeterProperty(FloatProperty, Protocol):
    """Base class for water meter properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.WATER_METER

    @property
    def parameters(self) -> WaterMeterFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return WaterMeterFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> UnitOfVolume:
        """Return the unit the property value is expressed in."""
        return UnitOfVolume.CUBIC_METERS

    @property
    def _unit_converter(self) -> VolumeConverter:
        """Return the unit converter."""
        return VolumeConverter()


class PM1DensityProperty(FloatProperty, Protocol):
    """Base class for PM1 density properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.PM1_DENSITY

    @property
    def parameters(self) -> PM1DensityFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PM1DensityFloatPropertyParameters()


class PM25DensityProperty(FloatProperty, Protocol):
    """Base class for PM2.5 density properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.PM2_5_DENSITY

    @property
    def parameters(self) -> PM25DensityFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PM25DensityFloatPropertyParameters()


class PM10DensityProperty(FloatProperty, Protocol):
    """Base class for PM10 density properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.PM10_DENSITY

    @property
    def parameters(self) -> PM10DensityFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PM10DensityFloatPropertyParameters()


class TVOCConcentrationProperty(FloatProperty, Protocol):
    """Base class for TVOC concentration properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.TVOC

    @property
    def parameters(self) -> TVOCFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return TVOCFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit the property value is expressed in."""
        return CONCENTRATION_MICROGRAMS_PER_CUBIC_METER

    @property
    def _unit_converter(self) -> TVOCConcentrationConverter:
        """Return the unit converter."""
        return TVOCConcentrationConverter()


class VoltageProperty(FloatProperty, Protocol):
    """Base class for voltage properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.VOLTAGE

    @property
    def parameters(self) -> VoltageFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return VoltageFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit the property value is expressed in."""
        return UnitOfElectricPotential.VOLT

    @property
    def _unit_converter(self) -> ElectricPotentialConverter:
        """Return the unit converter."""
        return ElectricPotentialConverter()


class ElectricCurrentProperty(FloatProperty, Protocol):
    """Base class for electric current properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.AMPERAGE

    @property
    def parameters(self) -> AmperageFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return AmperageFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit the property value is expressed in."""
        return UnitOfElectricCurrent.AMPERE

    @property
    def _unit_converter(self) -> ElectricCurrentConverter:
        """Return the unit converter."""
        return ElectricCurrentConverter()


class ElectricPowerProperty(FloatProperty, Protocol):
    """Base class for electric power properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.POWER

    @property
    def parameters(self) -> PowerFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PowerFloatPropertyParameters()

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit the property value is expressed in."""
        return UnitOfPower.WATT

    @property
    def _unit_converter(self) -> PowerConverter:
        """Return the unit converter."""
        return PowerConverter()


class BatteryLevelPercentageProperty(FloatProperty, Protocol):
    """Base class for battery level (%) properties."""

    instance: FloatPropertyInstance = FloatPropertyInstance.BATTERY_LEVEL

    @property
    def parameters(self) -> BatteryLevelFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return BatteryLevelFloatPropertyParameters()


class StateFloatProperty(StateProperty, FloatProperty):
    """Base class for a float property based on the state."""


class TemperatureSensor(StateFloatProperty, TemperatureProperty):
    """Representaton of the state as a temperature sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                if self._state_device_class == SensorDeviceClass.TEMPERATURE:
                    return True
                if self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) in UnitOfTemperature.__members__.values():
                    return True
            case air_quality.DOMAIN:
                return self.state.attributes.get(ATTR_TEMPERATURE) is not None
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN | water_heater.DOMAIN:
                return self.state.attributes.get(ATTR_CURRENT_TEMPERATURE) is not None

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        match self.state.domain:
            case air_quality.DOMAIN:
                return self.state.attributes.get(ATTR_TEMPERATURE)
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN | water_heater.DOMAIN:
                return self.state.attributes.get(ATTR_CURRENT_TEMPERATURE)

        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS))


class HumiditySensor(StateFloatProperty, HumidityProperty):
    """Representaton of the state as a humidity sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class in (SensorDeviceClass.HUMIDITY, SensorDeviceClass.MOISTURE)
            case air_quality.DOMAIN:
                return self.state.attributes.get(ATTR_HUMIDITY) is not None
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN:
                return self.state.attributes.get(ATTR_CURRENT_HUMIDITY) is not None

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        match self.state.domain:
            case air_quality.DOMAIN:
                return self.state.attributes.get(ATTR_HUMIDITY)
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN:
                return self.state.attributes.get(ATTR_CURRENT_HUMIDITY)

        return self.state.state


class PressureSensor(StateFloatProperty, PressureProperty):
    """Representaton of the state as a pressure sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == sensor.DOMAIN and self._state_device_class in (
            SensorDeviceClass.PRESSURE,
            SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        )

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfPressure.MMHG))


class IlluminationSensor(StateFloatProperty, IlluminationProperty):
    """Representaton of the state as a illumination sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == sensor.DOMAIN and self._state_device_class == SensorDeviceClass.ILLUMINANCE:
            return True

        if self.state.domain in (sensor.DOMAIN, light.DOMAIN, fan.DOMAIN):
            return ATTR_ILLUMINANCE in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN and self._state_device_class == SensorDeviceClass.ILLUMINANCE:
            return self.state.state

        return self.state.attributes.get(ATTR_ILLUMINANCE)


class WaterLevelPercentageSensor(StateFloatProperty, WaterLevelPercentageProperty):
    """Representaton of the state as a water level sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain in (fan.DOMAIN, humidifier.DOMAIN):
            return ATTR_WATER_LEVEL in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(ATTR_WATER_LEVEL)


class CO2LevelSensor(StateFloatProperty, CO2LevelProperty):
    """Representaton of the state as a CO2 level sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class == SensorDeviceClass.CO2
            case air_quality.DOMAIN | fan.DOMAIN:
                return ATTR_CO2 in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_CO2)


class ElectricityMeterSensor(StateFloatProperty, ElectricityMeterProperty):
    """Representaton of the state as a electricity meter sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == sensor.DOMAIN and self._state_device_class == SensorDeviceClass.ENERGY

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfEnergy.KILO_WATT_HOUR))


class GasMeterSensor(StateFloatProperty, GasMeterProperty):
    """Representaton of the state as a gas meter sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == sensor.DOMAIN and self._state_device_class == SensorDeviceClass.GAS

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfVolume.CUBIC_METERS))


class WaterMeterSensor(StateFloatProperty, WaterMeterProperty):
    """Representaton of the state as a water meter sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == sensor.DOMAIN and self._state_device_class == SensorDeviceClass.WATER

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfVolume.CUBIC_METERS))


class PM1DensitySensor(StateFloatProperty, PM1DensityProperty):
    """Representaton of the state as a PM1 density sensor."""

    instance = FloatPropertyInstance.PM1_DENSITY

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class == SensorDeviceClass.PM1
            case air_quality.DOMAIN:
                return ATTR_PM_0_1 in self.state.attributes

        return False

    @property
    def parameters(self) -> PM1DensityFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PM1DensityFloatPropertyParameters()

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_PM_0_1)


class PM25DensitySensor(StateFloatProperty, PM25DensityProperty):
    """Representaton of the state as a PM2.5 density sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class == SensorDeviceClass.PM25
            case air_quality.DOMAIN:
                return ATTR_PM_2_5 in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_PM_2_5)


class PM10DensitySensor(StateFloatProperty, PM10DensityProperty):
    """Representaton of the state as a PM10 density sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class == SensorDeviceClass.PM10
            case air_quality.DOMAIN:
                return ATTR_PM_10 in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_PM_10)


class TVOCConcentrationSensor(StateFloatProperty, TVOCConcentrationProperty):
    """Representaton of the state as a TVOC concentration sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class in (
                    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
                    XGW3DeviceClass.TVOC,
                )
            case air_quality.DOMAIN:
                return ATTR_TVOC in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_TVOC)

    @property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER))

        return None


class VOCConcentrationSensor(StateFloatProperty, TVOCConcentrationProperty):
    """Representaton of the state as a VOC concentration sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return (
            self.state.domain == sensor.DOMAIN
            and self._state_device_class == SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
        )

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.state


class VoltageSensor(StateFloatProperty, VoltageProperty):
    """Representaton of the state as a voltage sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class == SensorDeviceClass.VOLTAGE
            case switch.DOMAIN | light.DOMAIN:
                return ATTR_VOLTAGE in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_VOLTAGE)

    @property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement))

        return None


class ElectricCurrentSensor(StateFloatProperty, ElectricCurrentProperty):
    """Representaton of the state as a electric current sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self._state_device_class == SensorDeviceClass.CURRENT
            case switch.DOMAIN | light.DOMAIN:
                return ATTR_CURRENT in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_CURRENT)

    @property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement))

        return None


class ElectricPowerSensor(StateFloatProperty, ElectricPowerProperty):
    """Representaton of the state as a electric power sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == sensor.DOMAIN:
            return self._state_device_class == SensorDeviceClass.POWER

        if self.state.domain == switch.DOMAIN:
            for attribute in (ATTR_POWER, ATTR_LOAD_POWER, ATTR_CURRENT_CONSUMPTION):
                if attribute in self.state.attributes:
                    return True

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == switch.DOMAIN:
            for attribute in (ATTR_POWER, ATTR_LOAD_POWER, ATTR_CURRENT_CONSUMPTION):
                if attribute in self.state.attributes:
                    return self.state.attributes.get(attribute)

        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return str(self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement))

        return None


class BatteryLevelPercentageSensor(StateFloatProperty, BatteryLevelPercentageProperty):
    """Representaton of the state as battery level sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if (
            self._state_device_class == SensorDeviceClass.BATTERY
            and self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE
        ):
            return True

        return ATTR_BATTERY_LEVEL in self.state.attributes

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        value = None
        if self._state_device_class == SensorDeviceClass.BATTERY:
            value = self.state.state
        elif ATTR_BATTERY_LEVEL in self.state.attributes:
            value = self.state.attributes.get(ATTR_BATTERY_LEVEL)

        if value in [STATE_LOW, STATE_CHARGING]:
            return 0

        return value


STATE_PROPERTIES_REGISTRY.register(TemperatureSensor)
STATE_PROPERTIES_REGISTRY.register(HumiditySensor)
STATE_PROPERTIES_REGISTRY.register(PressureSensor)
STATE_PROPERTIES_REGISTRY.register(IlluminationSensor)
STATE_PROPERTIES_REGISTRY.register(WaterLevelPercentageSensor)
STATE_PROPERTIES_REGISTRY.register(CO2LevelSensor)
STATE_PROPERTIES_REGISTRY.register(ElectricityMeterSensor)
STATE_PROPERTIES_REGISTRY.register(GasMeterSensor)
STATE_PROPERTIES_REGISTRY.register(WaterMeterSensor)
STATE_PROPERTIES_REGISTRY.register(PM1DensitySensor)
STATE_PROPERTIES_REGISTRY.register(PM25DensitySensor)
STATE_PROPERTIES_REGISTRY.register(PM10DensitySensor)
STATE_PROPERTIES_REGISTRY.register(TVOCConcentrationSensor)
STATE_PROPERTIES_REGISTRY.register(VOCConcentrationSensor)
STATE_PROPERTIES_REGISTRY.register(VoltageSensor)
STATE_PROPERTIES_REGISTRY.register(ElectricCurrentSensor)
STATE_PROPERTIES_REGISTRY.register(ElectricPowerSensor)
STATE_PROPERTIES_REGISTRY.register(BatteryLevelPercentageSensor)
