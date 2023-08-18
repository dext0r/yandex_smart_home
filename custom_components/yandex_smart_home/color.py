"""Color manipulation helpers."""
from enum import StrEnum
from math import sqrt
from typing import Self

from homeassistant.components import light
from homeassistant.core import State
from homeassistant.util.color import RGBColor


class ColorName(StrEnum):
    RED = "red"
    CORAL = "coral"
    ORANGE = "orange"
    YELLOW = "yellow"
    LIME = "lime"
    GREEN = "green"
    EMERALD = "emerald"
    TURQUOISE = "turquoise"
    CYAN = "cyan"
    BLUE = "blue"
    MOONLIGHT = "moonlight"
    LAVENDER = "lavender"
    VIOLET = "violet"
    PURPLE = "purple"
    ORCHID = "orchid"
    MAUVE = "mauve"
    RASPBERRY = "raspberry"

    FIERY_WHITE = "fiery_white"
    SOFT_WHITE = "soft_white"
    WARM_WHITE = "warm_white"
    WHITE = "white"
    DAYLIGHT = "daylight"
    COLD_WHITE = "cold_white"
    MISTY_WHITE = "misty_white"
    HEAVENLY_WHITE = "heavenly_white"


def rgb_to_int(color: RGBColor) -> int:
    """Convert a rgb color to int value."""
    return (color.r << 16) + (color.g << 8) + color.b


def int_to_rgb(i: int) -> RGBColor:
    """Convert int value to a rgb color."""
    return RGBColor(r=(i >> 16) & 0xFF, g=(i >> 8) & 0xFF, b=i & 0xFF)


ColorProfile = dict[ColorName, int]
"""Hold int value for color/temperature name."""


class ColorProfiles(dict[str, ColorProfile]):
    _default_profiles = {
        "natural": {
            ColorName.RED: 16711680,
            ColorName.YELLOW: 16760576,
            ColorName.GREEN: 65280,
            ColorName.EMERALD: 2424612,
            ColorName.TURQUOISE: 65471,
            ColorName.CYAN: 65535,
            ColorName.BLUE: 255,
            ColorName.MOONLIGHT: 16763025,
            ColorName.LAVENDER: 4129023,
            ColorName.VIOLET: 8323327,
            ColorName.PURPLE: 12517631,
            ColorName.ORCHID: 16711765,
            ColorName.RASPBERRY: 16713260,
        }
    }

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, int]]) -> Self:
        """Intialize the color profiles from a dict."""
        profiles = cls._default_profiles.copy()
        for profile_name, mapping in data.items():
            profiles.setdefault(profile_name, {})
            profiles[profile_name].update({ColorName(name): v for name, v in mapping.items()})

        return cls(profiles)


class ColorConverter:
    """Utility to convert Yandex color to HA and vise-versa."""

    _palette = {
        ColorName.RED: 16714250,
        ColorName.CORAL: 16729907,
        ColorName.ORANGE: 16727040,
        ColorName.YELLOW: 16740362,
        ColorName.LIME: 13303562,
        ColorName.GREEN: 720711,
        ColorName.EMERALD: 720813,
        ColorName.TURQUOISE: 720883,
        ColorName.CYAN: 710399,
        ColorName.BLUE: 673791,
        ColorName.MOONLIGHT: 15067647,
        ColorName.LAVENDER: 8719103,
        ColorName.VIOLET: 11340543,
        ColorName.PURPLE: 16714471,
        ColorName.ORCHID: 16714393,
        ColorName.MAUVE: 16722742,
        ColorName.RASPBERRY: 16711765,
    }

    def __init__(self, profile: ColorProfile | None = None):
        """Initialize the color converter from color profile."""
        profile = profile or {}

        self._yandex_mapping: dict[int, int] = {}
        self._ha_mapping: dict[int, int] = {}

        for color_name, yandex_value in self._palette.items():
            ha_value = profile.get(color_name, yandex_value)

            self._yandex_mapping[yandex_value] = ha_value
            self._ha_mapping[ha_value] = yandex_value

    def get_ha_color(self, yandex_color: int) -> RGBColor:
        """Return HA color for Yandex color."""
        return int_to_rgb(self._yandex_mapping.get(yandex_color, yandex_color))

    def get_yandex_color(self, ha_color: RGBColor) -> int:
        """Return Yandex color for HA color."""
        for from_ha_value, to_yandex_value in self._ha_mapping.items():
            if self._distance(ha_color, int_to_rgb(from_ha_value)) <= 2:
                return to_yandex_value

        return rgb_to_int(ha_color)

    @staticmethod
    def _distance(a: RGBColor, b: RGBColor) -> float:
        """Return a distance between two colors."""
        return abs(sqrt((a.r - b.r) ** 2 + (a.g - b.g) ** 2 + (a.b - b.b) ** 2))


class ColorTemperatureConverter:
    """Utility to convert Yandex color temperature to HA and vise-versa."""

    default_white_temperature = 4500

    _palette = {
        ColorName.FIERY_WHITE: 1500,
        ColorName.SOFT_WHITE: 2700,
        ColorName.WARM_WHITE: 3400,
        ColorName.WHITE: 4500,
        ColorName.DAYLIGHT: 5600,
        ColorName.COLD_WHITE: 6500,
        ColorName.MISTY_WHITE: 7500,
        ColorName.HEAVENLY_WHITE: 9000,
    }
    _temperature_steps = sorted(_palette.values())

    def __init__(self, profile: ColorProfile | None, state: State):
        """Initialize the color temperature converter from color profile."""

        self._yandex_mapping: dict[int, int] = {}
        self._ha_mapping: dict[int, int] = {}

        profile = profile or {}
        range_extend_threshold = 200
        min_color_temp = self._round_color_temperature(
            int(state.attributes.get(light.ATTR_MIN_COLOR_TEMP_KELVIN, 2000))
        )
        max_color_temp = self._round_color_temperature(
            int(state.attributes.get(light.ATTR_MAX_COLOR_TEMP_KELVIN, 6500))
        )

        for color_name, yandex_value in self._palette.items():
            ha_value = self._round_color_temperature(profile.get(color_name, yandex_value))
            if ha_value < min_color_temp or ha_value > max_color_temp:
                continue

            self._map_values(yandex_value, ha_value)

        if self._ha_mapping and self._yandex_mapping:
            if min_color_temp + range_extend_threshold < min(self._ha_mapping):
                if yandex_color_temp := self._first_available_temperature_step:
                    self._map_values(yandex_color_temp, min_color_temp)

            if max_color_temp - range_extend_threshold > max(self._ha_mapping):
                if yandex_color_temp := self._last_available_temperature_step:
                    self._map_values(yandex_color_temp, max_color_temp)
        else:
            self._ha_mapping[min_color_temp] = self.default_white_temperature
            self._yandex_mapping[self.default_white_temperature] = min_color_temp

    def get_ha_color_temperature(self, yandex_color_temperature: int) -> int:
        """Return HA color temperature for Yandex color temperature."""
        return self._yandex_mapping.get(yandex_color_temperature, yandex_color_temperature)

    def get_yandex_color_temperature(self, ha_color_temperature: int) -> int:
        """Return Yandex color temperature for HA color temperature."""
        color_temperature = self._round_color_temperature(ha_color_temperature)
        return self._ha_mapping.get(color_temperature, color_temperature)

    @property
    def supported_range(self) -> tuple[int, int]:
        """Return temperature range supported for the state."""
        return min(self._yandex_mapping), max(self._yandex_mapping)

    @staticmethod
    def _round_color_temperature(color_temperature: int) -> int:
        """Return kelvin temperature with decreased precision."""
        return round(color_temperature, -2)

    @property
    def _first_available_temperature_step(self) -> int | None:
        """Return additional minimal temperature that outside mapped temperature range."""
        min_color_temp = min(self._yandex_mapping)
        idx = self._temperature_steps.index(min_color_temp)
        if idx != 0:
            return self._temperature_steps[idx - 1]

        return None

    @property
    def _last_available_temperature_step(self) -> int | None:
        """Return additional maximal temperature that outside mapped temperature range."""
        max_color_temp = max(self._yandex_mapping)
        idx = self._temperature_steps.index(max_color_temp)
        try:
            return self._temperature_steps[idx + 1]
        except IndexError:
            pass

        return None

    def _map_values(self, yandex_value: int, ha_value: int) -> None:
        """Add mapping between yandex values and HA."""
        self._yandex_mapping[yandex_value] = ha_value
        self._ha_mapping[ha_value] = yandex_value
        return None
