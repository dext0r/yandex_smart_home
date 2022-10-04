"""Implement the Yandex Smart Home color capabilities."""
from __future__ import annotations

from abc import ABC
import logging
from math import sqrt
from typing import Any

from homeassistant.components import light
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, State
from homeassistant.util.color import RGBColor, color_hs_to_RGB, color_temperature_mired_to_kelvin, color_xy_to_RGB

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import CONF_ENTITY_MODE_MAP, ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_COLOR_SETTING = PREFIX_CAPABILITIES + 'color_setting'
COLOR_MODES_TEMP_TO_WHITE = (
    light.ColorMode.RGBW,
    light.ColorMode.RGB,
    light.ColorMode.HS,
    light.ColorMode.XY
)
COLOR_PROFILES: dict[str, dict[str]: tuple[int, int, int]] = {
    'natural': {
        const.COLOR_NAME_RED: 16711680,
        const.COLOR_NAME_YELLOW: 16760576,
        const.COLOR_NAME_GREEN: 65280,
        const.COLOR_NAME_EMERALD: 2424612,
        const.COLOR_NAME_TURQUOISE: 65471,
        const.COLOR_NAME_CYAN: 65535,
        const.COLOR_NAME_BLUE: 255,
        const.COLOR_NAME_MOONLIGHT: 16763025,
        const.COLOR_NAME_LAVENDER: 4129023,
        const.COLOR_NAME_VIOLET: 8323327,
        const.COLOR_NAME_PURPLE: 12517631,
        const.COLOR_NAME_ORCHID: 16711765,
        const.COLOR_NAME_RASPBERRY: 16713260
    }
}
DEFAULT_WHITE_TEMPERATURE_K = 4500


class ColorSettingCapability(AbstractCapability, ABC):
    """Base color setting functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/color_setting-docpage/
    """

    type = CAPABILITIES_COLOR_SETTING
    scenes_map_default = {
        const.COLOR_SCENE_ALARM: ['Тревога', 'Alarm', 'Shine', 'Strobe Mega'],
        const.COLOR_SCENE_ALICE: ['Алиса', 'Alice', 'Meeting'],
        const.COLOR_SCENE_CANDLE: ['Свеча', 'Огонь', 'Candle', 'Fire'],
        const.COLOR_SCENE_DINNER: ['Ужин', 'Dinner'],
        const.COLOR_SCENE_FANTASY: ['Фантазия', 'Fantasy', 'Random', 'Beautiful', 'Sinelon Rainbow'],
        const.COLOR_SCENE_GARLAND: ['Гирлянда', 'Garland', 'Dynamic'],
        const.COLOR_SCENE_JUNGLE: ['Джунгли', 'Jungle'],
        const.COLOR_SCENE_MOVIE: ['Кино', 'Movie'],
        const.COLOR_SCENE_NEON: ['Неон', 'Neon', 'Breath'],
        const.COLOR_SCENE_NIGHT: ['Ночь', 'Night', 'Aurora'],
        const.COLOR_SCENE_OCEAN: ['Океан', 'Ocean', 'Pacifica'],
        const.COLOR_SCENE_PARTY: ['Вечеринка', 'Party', 'Juggle'],
        const.COLOR_SCENE_READING: ['Чтение', 'Reading', 'Read'],
        const.COLOR_SCENE_REST: ['Отдых', 'Rest', 'Soft'],
        const.COLOR_SCENE_ROMANCE: ['Романтика', 'Romance', 'Leasure', 'Lake'],
        const.COLOR_SCENE_SIREN: ['Сирена', 'Siren', 'Police', 'Rainbow'],
        const.COLOR_SCENE_SUNRISE: ['Рассвет', 'Sunrise'],
        const.COLOR_SCENE_SUNSET: ['Закат', 'Sunset']
    }
    default_white_temperature_k = DEFAULT_WHITE_TEMPERATURE_K
    cold_white_temperature_k = 6500

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)

        if self.state.domain == light.DOMAIN:
            self._color_profiles = COLOR_PROFILES.copy()
            self._color_profiles.update(config.color_profiles)

    def parameters(self) -> dict[str, Any]:
        """Return parameters for a devices request."""
        result = {}

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if self.support_color:
            result['color_model'] = 'rgb'

        if features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
            min_temp, max_temp = self._temperature_converter.supported_temperature_range
            result['temperature_k'] = {
                'min': min_temp,
                'max': max_temp
            }
        else:
            min_temp = self.default_white_temperature_k
            max_temp = self.default_white_temperature_k
            if light.ColorMode.RGBW in supported_color_modes or light.ColorMode.WHITE in supported_color_modes:
                max_temp = self.cold_white_temperature_k

            for color_mode in COLOR_MODES_TEMP_TO_WHITE:
                if color_mode in supported_color_modes:
                    result['temperature_k'] = {
                        'min': min_temp,
                        'max': max_temp
                    }
                    break

        if features & light.LightEntityFeature.EFFECT:
            supported_scenes = self.get_supported_scenes(
                self.get_scenes_map_from_config(self.entity_config),
                self.state.attributes.get(light.ATTR_EFFECT_LIST) or []
            )
            if supported_scenes:
                result['color_scene'] = {
                    'scenes': [
                        {'id': s}
                        for s in supported_scenes
                    ]
                }

        return result

    @property
    def support_color(self) -> bool:
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if self.state.domain != light.DOMAIN:
            return False

        if features & light.SUPPORT_COLOR:  # legacy
            return True

        for color_mode in supported_color_modes:
            if color_mode in [light.ColorMode.RGB, light.ColorMode.RGBW, light.ColorMode.RGBWW,
                              light.ColorMode.HS, light.ColorMode.XY]:
                return True

        return False

    @staticmethod
    def get_supported_scenes(scenes_map: dict[str, list[str]],
                             entity_effect_list: list[str]) -> list[str]:
        yandex_scenes = set()
        for effect in entity_effect_list:
            for yandex_scene, ha_effects in scenes_map.items():
                if effect in ha_effects:
                    yandex_scenes.add(yandex_scene)

        return sorted(list(yandex_scenes))

    @staticmethod
    def get_scenes_map_from_config(entity_config: dict[str, Any]) -> dict[str, list[str]]:
        scenes_map = ColorSettingCapability.scenes_map_default.copy()
        instance = const.COLOR_SETTING_SCENE

        if CONF_ENTITY_MODE_MAP in entity_config:
            modes = entity_config.get(CONF_ENTITY_MODE_MAP)
            if instance in modes:
                config_scenes = modes.get(instance)
                for yandex_scene in scenes_map.keys():
                    if yandex_scene in config_scenes.keys():
                        scenes_map[yandex_scene] = config_scenes[yandex_scene]

        return scenes_map

    def get_yandex_scene_by_ha_effect(self, ha_effect: str) -> str | None:
        scenes_map = self.get_scenes_map_from_config(self.entity_config)

        for yandex_scene, ha_effects in scenes_map.items():
            if str(ha_effect) in ha_effects:
                return yandex_scene

        return None

    def get_ha_effect_by_yandex_scene(self, yandex_scene: str) -> str | None:
        scenes_map = self.get_scenes_map_from_config(self.entity_config)

        ha_effects = scenes_map.get(yandex_scene)
        if not ha_effects:
            return None

        for ha_effect in ha_effects:
            for am in self.state.attributes.get(light.ATTR_EFFECT_LIST, []):
                if str(am) == ha_effect:
                    return ha_effect

    @property
    def _temperature_converter(self) -> TemperatureConverter:
        color_profile = None
        color_profile_name = self.entity_config.get(const.CONF_COLOR_PROFILE)
        if color_profile_name:
            try:
                color_profile = self._color_profiles[color_profile_name]
            except KeyError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f'Color profile {color_profile_name!r} not found for instance {self.instance} '
                    f'of {self.state.entity_id}'
                )

        return TemperatureConverter(color_profile, self.state)


@register_capability
class RgbCapability(ColorSettingCapability):
    """RGB color functionality."""

    instance = const.COLOR_SETTING_RGB

    def supported(self) -> bool:
        """Test if capability is supported."""
        return self.support_color

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        if self.state.attributes.get(light.ATTR_COLOR_MODE) == light.COLOR_MODE_COLOR_TEMP:
            return None

        rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
        if rgb_color is None:
            hs_color = self.state.attributes.get(light.ATTR_HS_COLOR)
            if hs_color is not None:
                rgb_color = color_hs_to_RGB(*hs_color)

            xy_color = self.state.attributes.get(light.ATTR_XY_COLOR)
            if xy_color is not None:
                rgb_color = color_xy_to_RGB(*xy_color)

        if rgb_color is not None:
            if rgb_color == (255, 255, 255):
                return None

            return self._color_converter.get_yandex_color(RGBColor(*rgb_color))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_RGB_COLOR: self._color_converter.get_ha_rgb_color(int(state['value']))
            },
            blocking=True,
            context=data.context
        )

    @property
    def _color_converter(self) -> ColorConverter:
        color_profile_name = self.entity_config.get(const.CONF_COLOR_PROFILE)
        if color_profile_name:
            try:
                return ColorConverter(self._color_profiles[color_profile_name])
            except KeyError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f'Color profile {color_profile_name!r} not found for instance {self.instance} '
                    f'of {self.state.entity_id}'
                )

        return ColorConverter()


@register_capability
class TemperatureKCapability(ColorSettingCapability):
    """Color temperature functionality."""

    instance = const.COLOR_SETTING_TEMPERATURE_K

    def supported(self) -> bool:
        """Test if capability is supported."""
        if self.state.domain == light.DOMAIN:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
            supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

            if features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
                return True

            for color_mode in COLOR_MODES_TEMP_TO_WHITE:
                if color_mode in supported_color_modes:
                    return True

        return False

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        temperature_mired = self.state.attributes.get(light.ATTR_COLOR_TEMP)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])
        color_mode = self.state.attributes.get(light.ATTR_COLOR_MODE)

        if temperature_mired is not None:
            return self._temperature_converter.get_yandex_temperature(temperature_mired)

        if color_mode == light.ColorMode.WHITE:
            return self.default_white_temperature_k

        if color_mode == light.ColorMode.RGBW:
            rgbw_color = self.state.attributes.get(light.ATTR_RGBW_COLOR)
            if rgbw_color is not None:
                if rgbw_color[:3] == (0, 0, 0) and rgbw_color[3] > 0:
                    return self.default_white_temperature_k
                elif rgbw_color[:3] == (255, 255, 255):
                    return self.cold_white_temperature_k

            return None

        if color_mode in [light.ColorMode.RGB, light.ColorMode.HS, light.ColorMode.XY]:
            rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
            if rgb_color is not None and rgb_color == (255, 255, 255):
                if light.ColorMode.WHITE in supported_color_modes:
                    return self.cold_white_temperature_k

                return self.default_white_temperature_k

            return None

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])
        value = state['value']
        service_data = {}

        if features & light.SUPPORT_COLOR_TEMP or \
                light.color_temp_supported(self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])):
            service_data[light.ATTR_KELVIN] = self._temperature_converter.get_ha_temperature(value)

        elif light.ColorMode.WHITE in supported_color_modes and value == self.default_white_temperature_k:
            service_data[light.ATTR_WHITE] = self.state.attributes.get(light.ATTR_BRIGHTNESS, 255)

        elif light.ColorMode.RGBW in supported_color_modes:
            if value == self.default_white_temperature_k:
                service_data[light.ATTR_RGBW_COLOR] = (0, 0, 0, self.state.attributes.get(light.ATTR_BRIGHTNESS, 255))
            else:
                service_data[light.ATTR_RGBW_COLOR] = (255, 255, 255, 0)

        elif light.ColorMode.RGB in supported_color_modes or \
                light.ColorMode.HS in supported_color_modes or \
                light.ColorMode.XY in supported_color_modes:
            service_data[light.ATTR_RGB_COLOR] = (255, 255, 255)

        if service_data:
            service_data[ATTR_ENTITY_ID] = self.state.entity_id
            await self.hass.services.async_call(
                light.DOMAIN,
                light.SERVICE_TURN_ON,
                service_data,
                blocking=True,
                context=data.context
            )
        else:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )


@register_capability
class ColorSceneCapability(ColorSettingCapability):
    """Color temperature functionality."""

    instance = const.COLOR_SETTING_SCENE

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == light.DOMAIN and features & light.LightEntityFeature.EFFECT:
            return bool(
                self.get_supported_scenes(
                    self.get_scenes_map_from_config(self.entity_config),
                    self.state.attributes.get(light.ATTR_EFFECT_LIST) or []
                )
            )

    def get_value(self) -> str | None:
        """Return the state value of this capability for this entity."""
        return self.get_yandex_scene_by_ha_effect(self.state.attributes.get(light.ATTR_EFFECT))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_EFFECT: self.get_ha_effect_by_yandex_scene(state['value']),
            },
            blocking=True,
            context=data.context
        )


class ColorConverter:
    _palette = {
        const.COLOR_NAME_RED: 16714250,
        const.COLOR_NAME_CORAL: 16729907,
        const.COLOR_NAME_ORANGE: 16727040,
        const.COLOR_NAME_YELLOW: 16740362,
        const.COLOR_NAME_LIME: 13303562,
        const.COLOR_NAME_GREEN: 720711,
        const.COLOR_NAME_EMERALD: 720813,
        const.COLOR_NAME_TURQUOISE: 720883,
        const.COLOR_NAME_CYAN: 710399,
        const.COLOR_NAME_BLUE: 673791,
        const.COLOR_NAME_MOONLIGHT: 15067647,
        const.COLOR_NAME_LAVENDER: 8719103,
        const.COLOR_NAME_VIOLET: 11340543,
        const.COLOR_NAME_PURPLE: 16714471,
        const.COLOR_NAME_ORCHID: 16714393,
        const.COLOR_NAME_MAUVE: 16722742,
        const.COLOR_NAME_RASPBERRY: 16711765,
    }

    def __init__(self, profile: dict[str, int] | None = None):
        profile = profile or {}

        self._yandex_value_to_ha: dict[int, int] = {}
        self._ha_value_to_yandex: dict[int, int] = {}

        for name, yandex_value in self._palette.items():
            ha_value = profile.get(name, yandex_value)

            self._yandex_value_to_ha[yandex_value] = ha_value
            self._ha_value_to_yandex[ha_value] = yandex_value

    def get_ha_rgb_color(self, yandex_color: int) -> tuple[int, int, int]:
        return self._int_to_rgb(
            self._yandex_value_to_ha.get(yandex_color, yandex_color)
        )

    def get_yandex_color(self, ha_color: RGBColor) -> int:
        for ha_color_value, yandex_color_value in self._ha_value_to_yandex.items():
            if self._distance(ha_color, RGBColor(*self._int_to_rgb(ha_color_value))) <= 2:
                return yandex_color_value

        return self.rgb_to_int(*ha_color)

    @staticmethod
    def rgb_to_int(r: int, g: int, b: int) -> int:
        rv = r
        rv = (rv << 8) + g
        rv = (rv << 8) + b

        return rv

    @staticmethod
    def _int_to_rgb(i: int) -> tuple[int, int, int]:
        return (
            (i >> 16) & 0xFF,
            (i >> 8) & 0xFF,
            i & 0xFF
        )

    @staticmethod
    def _distance(a: RGBColor, b: RGBColor) -> float:
        return abs(sqrt(
            (a.r - b.r) ** 2 +
            (a.g - b.g) ** 2 +
            (a.b - b.b) ** 2
        ))


class TemperatureConverter:
    _palette = {
        const.COLOR_TEMPERATURE_NAME_FIERY_WHITE: 1500,
        const.COLOR_TEMPERATURE_NAME_SOFT_WHITE: 2700,
        const.COLOR_TEMPERATURE_NAME_WARM_WHITE: 3400,
        const.COLOR_TEMPERATURE_NAME_WHITE: 4500,
        const.COLOR_TEMPERATURE_NAME_DAYLIGHT: 5600,
        const.COLOR_TEMPERATURE_NAME_COLD_WHITE: 6500,
        const.COLOR_TEMPERATURE_NAME_MISTY_WHITE: 7500,
        const.COLOR_TEMPERATURE_NAME_HEAVENLY_WHITE: 9000
    }
    _temperature_steps = sorted(_palette.values())

    def __init__(self, profile: dict[str, int] | None = None, state: State | None = None):
        self._yandex_value_to_ha: dict[int, int] = {}
        self._ha_value_to_yandex: dict[int, int] = {}

        profile = profile or {}
        range_extend_threshold = 200
        min_temp = self._color_temperature_mired_to_kelvin(state.attributes.get(light.ATTR_MAX_MIREDS, 500))
        max_temp = self._color_temperature_mired_to_kelvin(state.attributes.get(light.ATTR_MIN_MIREDS, 153))

        for name, yandex_temperature in self._palette.items():
            ha_temperature = self._round_kelvin_temperature(profile.get(name, yandex_temperature))
            if ha_temperature < min_temp or ha_temperature > max_temp:
                continue

            self._map_values(yandex_temperature, ha_temperature)

        if self._ha_value_to_yandex and self._yandex_value_to_ha:
            if min_temp + range_extend_threshold < min(self._ha_value_to_yandex):
                if yandex_temperature := self._first_available_temperature_step:
                    self._map_values(yandex_temperature, min_temp)

            if max_temp - range_extend_threshold > max(self._ha_value_to_yandex):
                if yandex_temperature := self._last_available_temperature_step:
                    self._map_values(yandex_temperature, max_temp)
        else:
            self._ha_value_to_yandex[min_temp] = DEFAULT_WHITE_TEMPERATURE_K
            self._yandex_value_to_ha[DEFAULT_WHITE_TEMPERATURE_K] = min_temp

    def get_ha_temperature(self, yandex_temperature: int) -> int:
        return self._yandex_value_to_ha.get(yandex_temperature, yandex_temperature)

    def get_yandex_temperature(self, ha_temperature_mired: int) -> int:
        ha_temperature_k = self._color_temperature_mired_to_kelvin(ha_temperature_mired)
        return self._ha_value_to_yandex.get(ha_temperature_k, ha_temperature_k)

    @property
    def supported_temperature_range(self) -> (int, int):
        return min(self._yandex_value_to_ha), max(self._yandex_value_to_ha)

    @staticmethod
    def _round_kelvin_temperature(kelvin_temperature: int) -> int:
        return round(kelvin_temperature, -2)

    def _color_temperature_mired_to_kelvin(self, mired_temperature: float) -> int:
        return self._round_kelvin_temperature(color_temperature_mired_to_kelvin(mired_temperature))

    @property
    def _first_available_temperature_step(self) -> int | None:
        min_temp = min(self._yandex_value_to_ha)
        idx = self._temperature_steps.index(min_temp)
        if idx != 0:
            return self._temperature_steps[idx - 1]

    @property
    def _last_available_temperature_step(self) -> int | None:
        max_temp = max(self._yandex_value_to_ha)
        idx = self._temperature_steps.index(max_temp)
        try:
            return self._temperature_steps[idx + 1]
        except IndexError:
            return None

    def _map_values(self, yandex_value: int, ha_value: int):
        self._yandex_value_to_ha[yandex_value] = ha_value
        self._ha_value_to_yandex[ha_value] = yandex_value
