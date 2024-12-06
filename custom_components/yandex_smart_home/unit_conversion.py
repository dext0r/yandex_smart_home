"""Unit conversion helpers."""

from enum import StrEnum

from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
)
from homeassistant.util.unit_conversion import (
    _IN_TO_M,
    _MERCURY_DENSITY,
    _MM_TO_M,
    _STANDARD_GRAVITY,
    BaseUnitConverter,
)

from .schema import PressureUnit, TemperatureUnit

# EFEKTA iAQ3 (#570)
UNIT_OF_MEASUREMENT_VOC_INDEX_POINT = "VOC Index points"


class TVOCConcentrationConverter(BaseUnitConverter):
    """Utility to convert TVOC concentration values."""

    UNIT_CLASS = "tvoc"
    NORMALIZED_UNIT = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    VALID_UNITS = {
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT,
        CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
        CONCENTRATION_PARTS_PER_MILLION,
        CONCENTRATION_PARTS_PER_BILLION,
        UNIT_OF_MEASUREMENT_VOC_INDEX_POINT,
    }

    # average molecular weight of tVOC = 110 g/mol
    _UNIT_CONVERSION: dict[str | None, float] = {
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER: 1,
        CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT: 1 / 35.3146667215,
        CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER: 1 / 1000,
        CONCENTRATION_PARTS_PER_MILLION: 1 / 4496.29381184,
        CONCENTRATION_PARTS_PER_BILLION: 1 / 4.49629381184,
        UNIT_OF_MEASUREMENT_VOC_INDEX_POINT: 1,
    }


class UnitOfTemperature(StrEnum):
    """Temperature units."""

    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"

    @property
    def as_property_unit(self) -> TemperatureUnit:
        """Return value as property unit."""
        match self:
            case self.CELSIUS:
                return TemperatureUnit.CELSIUS
            case self.KELVIN:
                return TemperatureUnit.KELVIN

        raise ValueError


class UnitOfPressure(StrEnum):
    """Extended pressure units."""

    ATM = "atm"
    PA = "Pa"
    HPA = "hPa"
    KPA = "kPa"
    BAR = "bar"
    CBAR = "cbar"
    MBAR = "mbar"
    MMHG = "mmHg"
    INHG = "inHg"
    PSI = "psi"

    @property
    def as_property_unit(self) -> PressureUnit:
        """Return value as property unit."""
        match self:
            case self.PA:
                return PressureUnit.PASCAL
            case self.MMHG:
                return PressureUnit.MMHG
            case self.ATM:
                return PressureUnit.ATM
            case self.BAR:
                return PressureUnit.BAR

        raise ValueError


class PressureConverter(BaseUnitConverter):
    """Utility to convert pressure values."""

    UNIT_CLASS = "pressure"
    NORMALIZED_UNIT = UnitOfPressure.PA
    _UNIT_CONVERSION: dict[str | None, float] = {
        UnitOfPressure.PA: 1,
        UnitOfPressure.HPA: 1 / 100,
        UnitOfPressure.KPA: 1 / 1000,
        UnitOfPressure.BAR: 1 / 100000,
        UnitOfPressure.CBAR: 1 / 1000,
        UnitOfPressure.MBAR: 1 / 100,
        UnitOfPressure.INHG: 1 / (_IN_TO_M * 1000 * _STANDARD_GRAVITY * _MERCURY_DENSITY),
        UnitOfPressure.PSI: 1 / 6894.757,
        UnitOfPressure.MMHG: 1 / (_MM_TO_M * 1000 * _STANDARD_GRAVITY * _MERCURY_DENSITY),
        UnitOfPressure.ATM: 1 / 101325,
    }
    VALID_UNITS = {
        UnitOfPressure.PA,
        UnitOfPressure.HPA,
        UnitOfPressure.KPA,
        UnitOfPressure.BAR,
        UnitOfPressure.CBAR,
        UnitOfPressure.MBAR,
        UnitOfPressure.INHG,
        UnitOfPressure.PSI,
        UnitOfPressure.MMHG,
    }
