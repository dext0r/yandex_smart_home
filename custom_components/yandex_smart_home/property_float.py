"""Implement the Yandex Smart Home float properties."""
from abc import ABC, abstractmethod
from typing import Protocol

from homeassistant.components import air_quality, climate, fan, humidifier, light, sensor, switch, water_heater
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.util.unit_conversion import (
    BaseUnitConverter,
    ElectricCurrentConverter,
    ElectricPotentialConverter,
    PowerConverter,
    TemperatureConverter,
)

from . import const
from .const import ERR_NOT_SUPPORTED_IN_CURRENT_MODE, STATE_EMPTY, STATE_NONE, STATE_NONE_UI
from .error import SmartHomeError
from .property import STATE_PROPERTIES_REGISTRY, Property, StateProperty
from .schema import (
    AmperageFloatPropertyParameters,
    BatteryLevelFloatPropertyParameters,
    CO2LevelFloatPropertyParameters,
    FloatPropertyDescription,
    FloatPropertyInstance,
    FloatPropertyParameters,
    HumidityFloatPropertyParameters,
    IlluminationFloatPropertyParameters,
    PM1DensityFloatPropertyParameters,
    PM10DensityFloatPropertyParameters,
    PM25DensityFloatPropertyParameters,
    PowerFloatPropertyParameters,
    PressureFloatPropertyParameters,
    PropertyType,
    TemperatureFloatPropertyParameters,
    TemperatureUnit,
    TVOCFloatPropertyParameters,
    VoltageFloatPropertyParameters,
    WaterLevelFloatPropertyParameters,
)
from .unit_conversion import PressureConverter, TVOCConcentrationConverter, UnitOfPressure


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
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f"Unsupported value {value!r} for instance {self.instance.value} of {self.device_id}",
            )

        if self._native_unit_of_measurement and self.unit_of_measurement and self._unit_converter:
            float_value = self._unit_converter.convert(
                float_value, self._native_unit_of_measurement, self.unit_of_measurement
            )

        lower_limit, upper_limit = self.parameters.range
        if lower_limit is not None and float_value < lower_limit:
            return lower_limit
        if upper_limit is not None and float_value > upper_limit:
            return upper_limit

        return round(float_value, 2)

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit the property value is expressed in."""
        return None

    @abstractmethod
    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        ...

    @property
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
        return TemperatureFloatPropertyParameters(unit=TemperatureUnit.CELSIUS)

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit the property value is expressed in."""
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
        return UnitOfPressure(self._config.pressure_unit)

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


@STATE_PROPERTIES_REGISTRY.register
class TemperatureSensor(StateProperty, TemperatureProperty):
    """Representaton of the state as a temperature sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.TEMPERATURE
            case air_quality.DOMAIN:
                return self.state.attributes.get(climate.ATTR_TEMPERATURE) is not None
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN | water_heater.DOMAIN:
                return self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE) is not None

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        match self.state.domain:
            case air_quality.DOMAIN:
                return self.state.attributes.get(climate.ATTR_TEMPERATURE)
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN | water_heater.DOMAIN:
                return self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE)

        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS)


@STATE_PROPERTIES_REGISTRY.register
class HumiditySensor(StateProperty, HumidityProperty):
    """Representaton of the state as a humidity sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.HUMIDITY
            case air_quality.DOMAIN:
                return self.state.attributes.get(climate.ATTR_HUMIDITY) is not None
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN:
                return self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY) is not None

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        match self.state.domain:
            case air_quality.DOMAIN:
                return self.state.attributes.get(climate.ATTR_HUMIDITY)
            case climate.DOMAIN | fan.DOMAIN | humidifier.DOMAIN:
                return self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY)

        return self.state.state


@STATE_PROPERTIES_REGISTRY.register
class PressureSensor(StateProperty, PressureProperty):
    """Representaton of the state as a pressure sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == sensor.DOMAIN and self.state.attributes.get(ATTR_DEVICE_CLASS) in [
            SensorDeviceClass.PRESSURE,
            SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        ]

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str | None:
        """Return the unit the native value is expressed in."""
        return self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement)


@STATE_PROPERTIES_REGISTRY.register
class IlluminationSensor(StateProperty, IlluminationProperty):
    """Representaton of the state as a illumination sensor."""

    __slots__ = ("a",)

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == sensor.DOMAIN:
            if self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.ILLUMINANCE:
                return True

        if self.state.domain in (sensor.DOMAIN, light.DOMAIN, fan.DOMAIN):
            return const.ATTR_ILLUMINANCE in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            if self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.ILLUMINANCE:
                return self.state.state

        return self.state.attributes.get(const.ATTR_ILLUMINANCE)


@STATE_PROPERTIES_REGISTRY.register
class WaterLevelPercentageSensor(StateProperty, WaterLevelPercentageProperty):
    """Representaton of the state as a water level sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain in (fan.DOMAIN, humidifier.DOMAIN):
            return const.ATTR_WATER_LEVEL in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(const.ATTR_WATER_LEVEL)


@STATE_PROPERTIES_REGISTRY.register
class CO2LevelSensor(StateProperty, CO2LevelProperty):
    """Representaton of the state as a CO2 level sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.CO2
            case air_quality.DOMAIN | fan.DOMAIN:
                return air_quality.ATTR_CO2 in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(air_quality.ATTR_CO2)


@STATE_PROPERTIES_REGISTRY.register
class PM1DensitySensor(StateProperty, PM1DensityProperty):
    """Representaton of the state as a PM1 density sensor."""

    instance = FloatPropertyInstance.PM1_DENSITY

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_0_1 in self.state.attributes

        return False

    @property
    def parameters(self) -> PM1DensityFloatPropertyParameters:
        """Return parameters for a devices list request."""
        return PM1DensityFloatPropertyParameters()

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(air_quality.ATTR_PM_0_1)


@STATE_PROPERTIES_REGISTRY.register
class PM25DensitySensor(StateProperty, PM25DensityProperty):
    """Representaton of the state as a PM2.5 density sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_2_5 in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(air_quality.ATTR_PM_2_5)


@STATE_PROPERTIES_REGISTRY.register
class PM10DensitySensor(StateProperty, PM10DensityProperty):
    """Representaton of the state as a PM10 density sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_10 in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(air_quality.ATTR_PM_10)


@STATE_PROPERTIES_REGISTRY.register
class TVOCConcentrationSensor(StateProperty, TVOCConcentrationProperty):
    """Representaton of the state as a TVOC concentration sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == air_quality.DOMAIN:
            return const.ATTR_TVOC in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(const.ATTR_TVOC)

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        return self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER)


@STATE_PROPERTIES_REGISTRY.register
class VoltageSensor(StateProperty, VoltageProperty):
    """Representaton of the state as a voltage sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.VOLTAGE
            case switch.DOMAIN | light.DOMAIN:
                return ATTR_VOLTAGE in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(ATTR_VOLTAGE)

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement)

        return self.unit_of_measurement


@STATE_PROPERTIES_REGISTRY.register
class ElectricCurrentSensor(StateProperty, ElectricCurrentProperty):
    """Representaton of the state as a electric current sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        match self.state.domain:
            case sensor.DOMAIN:
                return self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.CURRENT
            case switch.DOMAIN | light.DOMAIN:
                return const.ATTR_CURRENT in self.state.attributes

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.state

        return self.state.attributes.get(const.ATTR_CURRENT)

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement)

        return self.unit_of_measurement


@STATE_PROPERTIES_REGISTRY.register
class ElectricPowerSensor(StateProperty, ElectricPowerProperty):
    """Representaton of the state as a electric power sensor."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.POWER

        if self.state.domain == switch.DOMAIN:
            for attribute in [const.ATTR_POWER, const.ATTR_LOAD_POWER, const.ATTR_CURRENT_CONSUMPTION]:
                if attribute in self.state.attributes:
                    return True

        return False

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        if self.state.domain == switch.DOMAIN:
            for attribute in [const.ATTR_POWER, const.ATTR_LOAD_POWER, const.ATTR_CURRENT_CONSUMPTION]:
                if attribute in self.state.attributes:
                    return self.state.attributes.get(attribute)

        return self.state.state

    @property
    def _native_unit_of_measurement(self) -> str:
        """Return the unit the native value is expressed in."""
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, self.unit_of_measurement)

        return self.unit_of_measurement


@STATE_PROPERTIES_REGISTRY.register
class BatteryLevelPercentageSensor(StateProperty, BatteryLevelPercentageProperty):
    """Representaton of the state as battery level sensor."""

    __slots__ = ()

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if (
            self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.BATTERY
            and self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE
        ):
            return True

        return ATTR_BATTERY_LEVEL in self.state.attributes

    def _get_native_value(self) -> float | str | None:
        """Return the current property value without conversion."""
        value = None
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.BATTERY:
            value = self.state.state
        elif ATTR_BATTERY_LEVEL in self.state.attributes:
            value = self.state.attributes.get(ATTR_BATTERY_LEVEL)

        if value in [const.STATE_LOW, const.STATE_CHARGING]:
            return 0

        return value
