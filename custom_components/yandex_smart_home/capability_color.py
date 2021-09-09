"""Implement the Yandex Smart Home color capabilities."""
from __future__ import annotations

from abc import ABC
import logging
from typing import Any

from homeassistant.components import light
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.util import color as color_util

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import CONF_ENTITY_MODE_MAP, ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .helpers import RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_COLOR_SETTING = PREFIX_CAPABILITIES + 'color_setting'


class ColorSettingCapability(AbstractCapability, ABC):
    """Base color setting functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/color_setting-docpage/
    """

    type = CAPABILITIES_COLOR_SETTING
    scenes_map_default = {
        const.COLOR_SCENE_ALARM: ['Тревога', 'Alarm', 'Shine'],
        const.COLOR_SCENE_ALICE: ['Алиса', 'Alice', 'Meeting'],
        const.COLOR_SCENE_CANDLE: ['Свеча', 'Огонь', 'Candle', 'Fire'],
        const.COLOR_SCENE_DINNER: ['Ужин', 'Dinner'],
        const.COLOR_SCENE_FANTASY: ['Фантазия', 'Fantasy', 'Random', 'Beautiful'],
        const.COLOR_SCENE_GARLAND: ['Гирлянда', 'Garland'],
        const.COLOR_SCENE_JUNGLE: ['Джунгли', 'Jungle'],
        const.COLOR_SCENE_MOVIE: ['Кино', 'Movie'],
        const.COLOR_SCENE_NEON: ['Неон', 'Neon'],
        const.COLOR_SCENE_NIGHT: ['Ночь', 'Night'],
        const.COLOR_SCENE_OCEAN: ['Океан', 'Ocean'],
        const.COLOR_SCENE_PARTY: ['Вечеринка', 'Party'],
        const.COLOR_SCENE_READING: ['Чтение', 'Reading', 'Read'],
        const.COLOR_SCENE_REST: ['Отдых', 'Rest', 'Soft'],
        const.COLOR_SCENE_ROMANCE: ['Романтика', 'Romance', 'Leasure'],
        const.COLOR_SCENE_SIREN: ['Сирена', 'Siren', 'Rainbow'],
        const.COLOR_SCENE_SUNRISE: ['Рассвет', 'Sunrise'],
        const.COLOR_SCENE_SUNSET: ['Закат', 'Sunset']
    }
    default_white_temperature_k = 4500
    cold_white_temperature_k = 6500

    def parameters(self) -> dict[str, Any]:
        """Return parameters for a devices request."""
        result = {}

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if self.support_color:
            result['color_model'] = 'rgb'

        if features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
            min_temp = self.state.attributes.get(light.ATTR_MAX_MIREDS, 153)
            max_temp = self.state.attributes.get(light.ATTR_MIN_MIREDS, 500)
            result['temperature_k'] = {
                'min': color_util.color_temperature_mired_to_kelvin(min_temp),
                'max': color_util.color_temperature_mired_to_kelvin(max_temp)
            }
        elif light.COLOR_MODE_RGBW in supported_color_modes:
            result['temperature_k'] = {
                'min': self.default_white_temperature_k,
                'max': self.cold_white_temperature_k
            }
        elif light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
            result['temperature_k'] = {
                'min': self.default_white_temperature_k,
                'max': self.default_white_temperature_k
            }

        if features & light.SUPPORT_EFFECT:
            supported_scenes = self.get_supported_scenes(
                self.get_scenes_map_from_config(self.entity_config),
                self.state.attributes.get(light.ATTR_EFFECT_LIST, [])
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
            if color_mode in [light.COLOR_MODE_RGB, light.COLOR_MODE_RGBW, light.COLOR_MODE_RGBWW, light.COLOR_MODE_HS]:
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


@register_capability
class RgbCapability(ColorSettingCapability):
    """RGB color functionality."""

    instance = const.COLOR_SETTING_RGB

    def supported(self) -> bool:
        """Test if capability is supported."""
        return self.support_color

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
        if rgb_color is None:
            hs_color = self.state.attributes.get(light.ATTR_HS_COLOR)
            if hs_color is not None:
                rgb_color = color_util.color_hs_to_RGB(*hs_color)

        if rgb_color is not None:
            if rgb_color == (255, 255, 255):
                return None

            value = rgb_color[0]
            value = (value << 8) + rgb_color[1]
            value = (value << 8) + rgb_color[2]

            return value

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        red = (state['value'] >> 16) & 0xFF
        green = (state['value'] >> 8) & 0xFF
        blue = state['value'] & 0xFF

        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_RGB_COLOR: (red, green, blue)
            },
            blocking=True,
            context=data.context
        )


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
            elif light.COLOR_MODE_RGBW in supported_color_modes:
                return True
            elif light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
                return True

        return False

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        temperature_mired = self.state.attributes.get(light.ATTR_COLOR_TEMP)
        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

        if temperature_mired is not None:
            return color_util.color_temperature_mired_to_kelvin(temperature_mired)

        if light.COLOR_MODE_RGBW in supported_color_modes:
            rgbw_color = self.state.attributes.get(light.ATTR_RGBW_COLOR)
            if rgbw_color is not None:
                if rgbw_color[:3] == (0, 0, 0) and rgbw_color[3] > 0:
                    return self.default_white_temperature_k
                elif rgbw_color[:3] == (255, 255, 255):
                    return self.cold_white_temperature_k

            return None

        if light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
            rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
            if rgb_color is not None and rgb_color == (255, 255, 255):
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
            service_data[light.ATTR_KELVIN] = value

        elif light.COLOR_MODE_RGBW in supported_color_modes:
            if value == self.default_white_temperature_k:
                service_data[light.ATTR_RGBW_COLOR] = (0, 0, 0, self.state.attributes.get(light.ATTR_BRIGHTNESS, 255))
            else:
                service_data[light.ATTR_RGBW_COLOR] = (255, 255, 255, 0)

        elif light.COLOR_MODE_RGB in supported_color_modes or light.COLOR_MODE_HS in supported_color_modes:
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

        if self.state.domain == light.DOMAIN and features & light.SUPPORT_EFFECT:
            return bool(
                ColorSceneCapability.get_supported_scenes(
                    ColorSceneCapability.get_scenes_map_from_config(self.entity_config),
                    self.state.attributes.get(light.ATTR_EFFECT_LIST, [])
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
