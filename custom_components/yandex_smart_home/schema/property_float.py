"""Schema for float property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float.html
"""
from enum import StrEnum
from typing import Literal

from .base import APIModel


class FloatPropertyInstance(StrEnum):
    """Instance of an event property.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html
    """

    AMPERAGE = "amperage"
    BATTERY_LEVEL = "battery_level"
    CO2_LEVEL = "co2_level"
    ELECTRICITY_METER = "electricity_meter"
    FOOD_LEVEL = "food_level"
    GAS_METER = "gas_meter"
    HEAT_METER = "heat_meter"
    HUMIDITY = "humidity"
    ILLUMINATION = "illumination"
    METER = "meter"
    PM10_DENSITY = "pm10_density"
    PM1_DENSITY = "pm1_density"
    PM2_5_DENSITY = "pm2.5_density"
    POWER = "power"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    TVOC = "tvoc"
    VOLTAGE = "voltage"
    WATER_LEVEL = "water_level"
    WATER_METER = "water_meter"


class FloatUnit(StrEnum):
    """Unit used in a float property."""

    AMPERE = "unit.ampere"
    CUBIC_METER = "unit.cubic_meter"
    GIGACALORIE = "unit.gigacalorie"
    KILOWATT_HOUR = "unit.kilowatt_hour"
    LUX = "unit.illumination.lux"
    MCG_M3 = "unit.density.mcg_m3"
    PERCENT = "unit.percent"
    PPM = "unit.ppm"
    VOLT = "unit.volt"
    WATT = "unit.watt"


class PressureUnit(StrEnum):
    """Pressure unit."""

    PASCAL = "unit.pressure.pascal"
    MMHG = "unit.pressure.mmhg"
    ATM = "unit.pressure.atm"
    BAR = "unit.pressure.bar"


class TemperatureUnit(StrEnum):
    """Temperature unit."""

    CELSIUS = "unit.temperature.celsius"
    KELVIN = "unit.temperature.kelvin"


class FloatPropertyParameters(APIModel):
    """Parameters of a float property."""

    instance: FloatPropertyInstance
    unit: FloatUnit | PressureUnit | TemperatureUnit | None

    @property
    def range(self) -> tuple[int | None, int | None]:
        """Return value range."""
        return None, None


class FloatPropertyAboveZeroMixin:
    """Mixin for a property that has value only above zero."""

    @property
    def range(self) -> tuple[int | None, int | None]:
        """Return value range."""
        return 0, None


class PercentFloatPropertyParameters(FloatPropertyParameters):
    unit: Literal[FloatUnit.PERCENT] = FloatUnit.PERCENT

    @property
    def range(self) -> tuple[int | None, int | None]:
        """Return value range."""
        return 0, 100


class DensityFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    unit: Literal[FloatUnit.MCG_M3] = FloatUnit.MCG_M3


class AmperageFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.AMPERAGE] = FloatPropertyInstance.AMPERAGE
    unit: Literal[FloatUnit.AMPERE] = FloatUnit.AMPERE


class BatteryLevelFloatPropertyParameters(PercentFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.BATTERY_LEVEL] = FloatPropertyInstance.BATTERY_LEVEL


class CO2LevelFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.CO2_LEVEL] = FloatPropertyInstance.CO2_LEVEL
    unit: Literal[FloatUnit.PPM] = FloatUnit.PPM


class ElectricityMeterFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.ELECTRICITY_METER] = FloatPropertyInstance.ELECTRICITY_METER
    unit: Literal[FloatUnit.KILOWATT_HOUR] = FloatUnit.KILOWATT_HOUR


class FoodLevelFloatPropertyParameters(PercentFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.FOOD_LEVEL] = FloatPropertyInstance.FOOD_LEVEL


class GasMeterFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.GAS_METER] = FloatPropertyInstance.GAS_METER
    unit: Literal[FloatUnit.CUBIC_METER] = FloatUnit.CUBIC_METER


class HeatMeterFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.HEAT_METER] = FloatPropertyInstance.HEAT_METER
    unit: Literal[FloatUnit.GIGACALORIE] = FloatUnit.GIGACALORIE


class HumidityFloatPropertyParameters(PercentFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.HUMIDITY] = FloatPropertyInstance.HUMIDITY


class IlluminationFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.ILLUMINATION] = FloatPropertyInstance.ILLUMINATION
    unit: Literal[FloatUnit.LUX] = FloatUnit.LUX


class MeterFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.METER] = FloatPropertyInstance.METER
    unit: None = None


class PM1DensityFloatPropertyParameters(DensityFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.PM1_DENSITY] = FloatPropertyInstance.PM1_DENSITY


class PM25DensityFloatPropertyParameters(DensityFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.PM2_5_DENSITY] = FloatPropertyInstance.PM2_5_DENSITY


class PM10DensityFloatPropertyParameters(DensityFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.PM10_DENSITY] = FloatPropertyInstance.PM10_DENSITY


class PowerFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.POWER] = FloatPropertyInstance.POWER
    unit: Literal[FloatUnit.WATT] = FloatUnit.WATT


class PressureFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.PRESSURE] = FloatPropertyInstance.PRESSURE
    unit: PressureUnit


class TemperatureFloatPropertyParameters(FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.TEMPERATURE] = FloatPropertyInstance.TEMPERATURE
    unit: TemperatureUnit


class TVOCFloatPropertyParameters(DensityFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.TVOC] = FloatPropertyInstance.TVOC


class VoltageFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.VOLTAGE] = FloatPropertyInstance.VOLTAGE
    unit: Literal[FloatUnit.VOLT] = FloatUnit.VOLT


class WaterLevelFloatPropertyParameters(PercentFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.WATER_LEVEL] = FloatPropertyInstance.WATER_LEVEL


class WaterMeterFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.WATER_METER] = FloatPropertyInstance.WATER_METER
    unit: Literal[FloatUnit.CUBIC_METER] = FloatUnit.CUBIC_METER
