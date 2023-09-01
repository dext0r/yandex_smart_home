"""Schema for float property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float.html
"""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class FloatPropertyInstance(StrEnum):
    """https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html"""

    AMPERAGE = "amperage"
    BATTERY_LEVEL = "battery_level"
    CO2_LEVEL = "co2_level"
    HUMIDITY = "humidity"
    # TODO: FOOD_LEVEL = "food_level"
    ILLUMINATION = "illumination"
    PM10_DENSITY = "pm10_density"
    PM1_DENSITY = "pm1_density"
    PM2_5_DENSITY = "pm2.5_density"
    POWER = "power"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    TVOC = "tvoc"
    VOLTAGE = "voltage"
    WATER_LEVEL = "water_level"


class FloatUnit(StrEnum):
    AMPERE = "unit.ampere"
    LUX = "unit.illumination.lux"
    PERCENT = "unit.percent"
    PPM = "unit.ppm"
    MCG_M3 = "unit.density.mcg_m3"
    WATT = "unit.watt"
    VOLT = "unit.volt"


class PressureUnit(StrEnum):
    PASCAL = "unit.pressure.pascal"
    MMHG = "unit.pressure.mmhg"
    ATM = "unit.pressure.atm"
    BAR = "unit.pressure.bar"


class TemperatureUnit(StrEnum):
    CELSIUS = "unit.temperature.celsius"
    KELVIN = "unit.temperature.kelvin"


class FloatPropertyParameters(BaseModel):
    instance: FloatPropertyInstance
    unit: FloatUnit | PressureUnit | TemperatureUnit

    @property
    def range(self) -> tuple[int | None, int | None]:
        """Return value range."""
        return None, None


class FloatPropertyAboveZeroMixin:
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


# TODO
# class FoodLevelFloatPropertyParameters(PercentFloatPropertyParameters):
#     instance: Literal[FloatPropertyInstance.FOOD_LEVEL] = FloatPropertyInstance.FOOD_LEVEL


class HumidityFloatPropertyParameters(PercentFloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.HUMIDITY] = FloatPropertyInstance.HUMIDITY


class IlluminationFloatPropertyParameters(FloatPropertyAboveZeroMixin, FloatPropertyParameters):
    instance: Literal[FloatPropertyInstance.ILLUMINATION] = FloatPropertyInstance.ILLUMINATION
    unit: Literal[FloatUnit.LUX] = FloatUnit.LUX


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
