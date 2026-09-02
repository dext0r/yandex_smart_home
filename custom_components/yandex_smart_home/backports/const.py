"""Constants introduced in Home Assistant 2026.7 and newer.

Copies of constants that are missing in the minimal supported Home Assistant version (2025.12).
Drop them in favour of the direct import as soon as the minimal supported version is raised.
"""

from enum import StrEnum


class UnitOfDensity(StrEnum):
    """Density units.

    Ratio of a substance's mass to its volume.
    """

    GRAMS_PER_CUBIC_METER = "g/m³"
    MILLIGRAMS_PER_CUBIC_METER = "mg/m³"
    MICROGRAMS_PER_CUBIC_METER = "μg/m³"
    MICROGRAMS_PER_CUBIC_FOOT = "μg/ft³"


class UnitOfRatio(StrEnum):
    """Ratio units."""

    PARTS_PER_MILLION = "ppm"
    PARTS_PER_BILLION = "ppb"
    PERCENTAGE = "%"
