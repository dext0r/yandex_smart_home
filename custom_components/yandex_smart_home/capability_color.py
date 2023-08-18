"""Implement the Yandex Smart Home color_setting capability."""
from functools import cached_property
import logging
from typing import Any

from homeassistant.components import light
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.util.color import RGBColor, color_hs_to_RGB, color_xy_to_RGB

from .capability import AbstractCapability, register_capability
from .color import ColorConverter, ColorTemperatureConverter
from .const import CONF_COLOR_PROFILE, CONF_ENTITY_MODE_MAP, ERR_INTERNAL_ERROR, ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .helpers import Config
from .schema import (
    CapabilityParameterColorModel,
    CapabilityParameterColorScene,
    CapabilityParameterTemperatureK,
    CapabilityType,
    ColorScene,
    ColorSettingCapabilityInstance,
    ColorSettingCapabilityInstanceActionState,
    ColorSettingCapabilityParameters,
    RGBInstanceActionState,
    SceneInstanceActionState,
    TemperatureKInstanceActionState,
)

_LOGGER = logging.getLogger(__name__)


@register_capability
class ColorSettingCapability(AbstractCapability[ColorSettingCapabilityInstanceActionState]):
    """Root capability to discover another light device capabilities.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html
    """

    type = CapabilityType.COLOR_SETTING
    instance = ColorSettingCapabilityInstance.BASE

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a capability for a state."""
        super().__init__(hass, config, state)

        self._color = RGBColorCapability(hass, config, state)
        self._temperature = ColorTemperatureCapability(hass, config, state)
        self._color_scene = ColorSceneCapability(hass, config, state)

    @property
    def supported(self) -> bool:
        """Test if the capability is supported for its state."""
        for capability in self._capabilities:
            if capability.supported:
                return True

        return False

    @property
    def parameters(self) -> ColorSettingCapabilityParameters | None:
        """Return parameters for a devices list request."""
        return ColorSettingCapabilityParameters(
            color_model=self._color.parameters.color_model if self._color.supported else None,
            temperature_k=self._temperature.parameters.temperature_k if self._temperature.parameters else None,
            color_scene=self._color_scene.parameters.color_scene if self._color_scene.supported else None,
        )

    def get_value(self) -> None:
        """Return the current capability value."""
        return None

    async def set_instance_state(self, context: Context, state: ColorSettingCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        raise SmartHomeError(ERR_INTERNAL_ERROR, "No instance")

    @property
    def _capabilities(self) -> list[AbstractCapability]:  # type: ignore[type-arg]
        """Return all child capabilities."""
        return [self._color, self._temperature, self._color_scene]


@register_capability
class RGBColorCapability(AbstractCapability[RGBInstanceActionState]):
    """Capability to control color of a light device."""

    type = CapabilityType.COLOR_SETTING
    instance = ColorSettingCapabilityInstance.RGB

    @property
    def supported(self) -> bool:
        """Test if capability is supported."""
        if self.state.domain != light.DOMAIN:
            return False

        if self._state_features & light.SUPPORT_COLOR:  # legacy
            return True

        for color_mode in self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, []):
            if color_mode in [
                light.ColorMode.RGB,
                light.ColorMode.RGBW,
                light.ColorMode.RGBWW,
                light.ColorMode.HS,
                light.ColorMode.XY,
            ]:
                return True

        return False

    @property
    def parameters(self) -> ColorSettingCapabilityParameters:
        """Return parameters for a devices list request."""
        return ColorSettingCapabilityParameters(color_model=CapabilityParameterColorModel.RGB)

    def get_description(self) -> None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return None

    def get_value(self) -> int | None:
        """Return the current capability value."""
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

            return self._converter.get_yandex_color(RGBColor(*rgb_color))

        return None

    async def set_instance_state(self, context: Context, state: RGBInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_RGB_COLOR: tuple(self._converter.get_ha_color(state.value)),
            },
            blocking=True,
            context=context,
        )

    @cached_property
    def _converter(self) -> ColorConverter:
        """Return the color converter."""
        if color_profile_name := self._entity_config.get(CONF_COLOR_PROFILE):
            try:
                return ColorConverter(self._config.color_profiles[color_profile_name])
            except KeyError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f"Color profile {color_profile_name!r} not found for instance {self.instance} "
                    f"of {self.state.entity_id}",
                )

        return ColorConverter()


@register_capability
class ColorTemperatureCapability(AbstractCapability[TemperatureKInstanceActionState]):
    """Capability to control color temperature of a light device."""

    type = CapabilityType.COLOR_SETTING
    instance = ColorSettingCapabilityInstance.TEMPERATURE_K

    _default_white_temperature = ColorTemperatureConverter.default_white_temperature
    _cold_white_temperature = 6500
    _color_modes_temp_to_white = {light.ColorMode.RGBW, light.ColorMode.RGB, light.ColorMode.HS, light.ColorMode.XY}

    @property
    def supported(self) -> bool:
        """Test if capability is supported."""
        if self.state.domain == light.DOMAIN:
            supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])

            if self._state_features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
                return True

            if self._color_modes_temp_to_white & set(supported_color_modes):
                return True

        return False

    @property
    def parameters(self) -> ColorSettingCapabilityParameters | None:
        """Return parameters for a devices list request."""
        if not self.supported:
            return None

        supported_color_modes = set(self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, []))

        if self._state_features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
            min_temp, max_temp = self._converter.supported_range
            return ColorSettingCapabilityParameters(
                temperature_k=CapabilityParameterTemperatureK(min=min_temp, max=max_temp)
            )

        if self._color_modes_temp_to_white & supported_color_modes:
            min_temp = self._default_white_temperature
            max_temp = self._default_white_temperature
            if light.ColorMode.RGBW in supported_color_modes or light.ColorMode.WHITE in supported_color_modes:
                max_temp = self._cold_white_temperature

            return ColorSettingCapabilityParameters(
                temperature_k=CapabilityParameterTemperatureK(min=min_temp, max=max_temp)
            )

        return None  # pragma: no cover

    def get_description(self) -> None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return None

    def get_value(self) -> int | None:
        """Return the current capability value."""
        color_temperature = self.state.attributes.get(light.ATTR_COLOR_TEMP_KELVIN)
        if color_temperature is not None:
            return self._converter.get_yandex_color_temperature(color_temperature)

        supported_color_modes = self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, [])
        color_mode = self.state.attributes.get(light.ATTR_COLOR_MODE)

        if color_mode == light.ColorMode.WHITE:
            return self._default_white_temperature

        if color_mode == light.ColorMode.RGBW:
            rgbw_color = self.state.attributes.get(light.ATTR_RGBW_COLOR)
            if rgbw_color is not None:
                if rgbw_color[:3] == (0, 0, 0) and rgbw_color[3] > 0:
                    return self._default_white_temperature
                elif rgbw_color[:3] == (255, 255, 255):
                    return self._cold_white_temperature

            return None

        if color_mode in [light.ColorMode.RGB, light.ColorMode.HS, light.ColorMode.XY]:
            rgb_color = self.state.attributes.get(light.ATTR_RGB_COLOR)
            if rgb_color is not None and rgb_color == (255, 255, 255):
                if light.ColorMode.WHITE in supported_color_modes:
                    return self._cold_white_temperature

                return self._default_white_temperature

            return None

        return None

    async def set_instance_state(self, context: Context, state: TemperatureKInstanceActionState) -> None:
        """Change the capability state."""
        supported_color_modes = set(self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES, []))
        service_data: dict[str, Any] = {}

        if self._state_features & light.SUPPORT_COLOR_TEMP or light.color_temp_supported(supported_color_modes):
            service_data[light.ATTR_KELVIN] = self._converter.get_ha_color_temperature(state.value)

        elif light.ColorMode.WHITE in supported_color_modes and state.value == self._default_white_temperature:
            service_data[light.ATTR_WHITE] = self.state.attributes.get(light.ATTR_BRIGHTNESS, 255)

        elif light.ColorMode.RGBW in supported_color_modes:
            if state.value == self._default_white_temperature:
                service_data[light.ATTR_RGBW_COLOR] = (0, 0, 0, self.state.attributes.get(light.ATTR_BRIGHTNESS, 255))
            else:
                service_data[light.ATTR_RGBW_COLOR] = (255, 255, 255, 0)

        elif {light.ColorMode.RGB, light.ColorMode.HS, light.ColorMode.XY} & supported_color_modes:
            service_data[light.ATTR_RGB_COLOR] = (255, 255, 255)

        if service_data:
            service_data[ATTR_ENTITY_ID] = self.state.entity_id
            await self._hass.services.async_call(
                light.DOMAIN, light.SERVICE_TURN_ON, service_data, blocking=True, context=context
            )
        else:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f"Unsupported value {state.value!r} for instance {self.instance} of {self.state.entity_id}",
            )

    @cached_property
    def _converter(self) -> ColorTemperatureConverter:
        """Return the color temperature converter."""
        if color_profile_name := self._entity_config.get(CONF_COLOR_PROFILE):
            try:
                return ColorTemperatureConverter(self._config.color_profiles[color_profile_name], self.state)

            except KeyError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f"Color profile {color_profile_name!r} not found for instance {self.instance} "
                    f"of {self.state.entity_id}",
                )

        return ColorTemperatureConverter(None, self.state)


@register_capability
class ColorSceneCapability(AbstractCapability[SceneInstanceActionState]):
    """Capability to control effect of a light device."""

    type = CapabilityType.COLOR_SETTING
    instance = ColorSettingCapabilityInstance.SCENE

    _scenes_map_default = {
        ColorScene.ALARM: ["Тревога", "Alarm", "Shine", "Strobe Mega"],
        ColorScene.ALICE: ["Алиса", "Alice", "Meeting"],
        ColorScene.CANDLE: ["Свеча", "Огонь", "Candle", "Fire"],
        ColorScene.DINNER: ["Ужин", "Dinner"],
        ColorScene.FANTASY: ["Фантазия", "Fantasy", "Random", "Beautiful", "Sinelon Rainbow"],
        ColorScene.GARLAND: ["Гирлянда", "Garland", "Dynamic"],
        ColorScene.JUNGLE: ["Джунгли", "Jungle"],
        ColorScene.MOVIE: ["Кино", "Movie"],
        ColorScene.NEON: ["Неон", "Neon", "Breath"],
        ColorScene.NIGHT: ["Ночь", "Night", "Aurora"],
        ColorScene.OCEAN: ["Океан", "Ocean", "Pacifica"],
        ColorScene.PARTY: ["Вечеринка", "Party", "Juggle"],
        ColorScene.READING: ["Чтение", "Reading", "Read"],
        ColorScene.REST: ["Отдых", "Rest", "Soft"],
        ColorScene.ROMANCE: ["Романтика", "Romance", "Leasure", "Lake"],
        ColorScene.SIREN: ["Сирена", "Siren", "Police", "Rainbow"],
        ColorScene.SUNRISE: ["Рассвет", "Sunrise"],
        ColorScene.SUNSET: ["Закат", "Sunset"],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported for its state."""
        if self.state.domain == light.DOMAIN and self._state_features & light.LightEntityFeature.EFFECT:
            return bool(self.supported_scenes)

        return False

    @property
    def parameters(self) -> ColorSettingCapabilityParameters:
        """Return parameters for a devices list request."""
        return ColorSettingCapabilityParameters(
            color_scene=CapabilityParameterColorScene.from_list(self.supported_scenes)
        )

    def get_description(self) -> None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return None

    def get_value(self) -> ColorScene | None:
        """Return the current capability value."""
        if effect := self.state.attributes.get(light.ATTR_EFFECT):
            return self.get_scene_by_effect(effect)

        return None

    async def set_instance_state(self, context: Context, state: SceneInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_EFFECT: self.get_effect_by_scene(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def supported_scenes(self) -> list[ColorScene]:
        """Returns a list of supported Yandex scenes."""
        scenes = set()

        if effect_list := self.state.attributes.get(light.ATTR_EFFECT_LIST):
            for effect in effect_list:
                if scene := self.get_scene_by_effect(effect):
                    scenes.add(scene)

        return sorted(list(scenes))

    @cached_property
    def scenes_map(self) -> dict[ColorScene, list[str]]:
        """Return mapping between Yandex scenes and HA light effects."""
        scenes_map = self._scenes_map_default.copy()

        if CONF_ENTITY_MODE_MAP in self._entity_config:
            scenes_map.update(
                {ColorScene(k): v for k, v in self._entity_config[CONF_ENTITY_MODE_MAP].get(self.instance).items()}
            )

        for scene, effects in scenes_map.items():
            scenes_map[scene] = [e.lower() for e in effects]

        return scenes_map

    def get_scene_by_effect(self, effect: str) -> ColorScene | None:
        """Return Yandex scene for HA light effect."""
        for scene, effects in self.scenes_map.items():
            if effect.lower() in effects:
                return scene

        return None

    def get_effect_by_scene(self, scene: ColorScene) -> str | None:
        """Return HA light effect for Yandex scene."""
        for effect in self.scenes_map.get(scene, {}):
            for supported_effect in self.state.attributes.get(light.ATTR_EFFECT_LIST, []):
                if str(supported_effect).lower() == effect:
                    return str(supported_effect)

        return None
