"""Implement the Yandex Smart Home color_setting capability."""

from __future__ import annotations

from abc import abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any, cast

from homeassistant.components import light
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_WHITE,
    COLOR_MODE_COLOR_TEMP,
    ColorMode,
    LightEntityFeature,
    color_temp_supported,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.util.color import RGBColor

from .capability import STATE_CAPABILITIES_REGISTRY, Capability, StateCapability
from .color import ColorConverter, ColorTemperatureConverter, LightState
from .const import CONF_COLOR_PROFILE, CONF_ENTITY_CUSTOM_MODES, CONF_ENTITY_MODE_MAP
from .helpers import APIError
from .schema import (
    CapabilityInstance,
    CapabilityParameterColorModel,
    CapabilityParameterColorScene,
    CapabilityParameterTemperatureK,
    CapabilityType,
    ColorScene,
    ColorSettingCapabilityInstance,
    ColorSettingCapabilityInstanceActionState,
    ColorSettingCapabilityParameters,
    ResponseCode,
    RGBInstanceActionState,
    SceneInstanceActionState,
    TemperatureKInstanceActionState,
)

if TYPE_CHECKING:
    from .entry_data import ConfigEntryData


class ColorSettingCapability(StateCapability[ColorSettingCapabilityInstanceActionState]):
    """Capability to discover another color_setting capabilities.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html
    """

    type: CapabilityType = CapabilityType.COLOR_SETTING
    instance: CapabilityInstance = ColorSettingCapabilityInstance.BASE

    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData, state: State):
        """Initialize a capability for the state."""
        super().__init__(hass, entry_data, state)

        self._color = RGBColorCapability(hass, entry_data, state)
        self._temperature = ColorTemperatureCapability(hass, entry_data, state)
        self._scene = self._get_scene_capability()

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        for capability in self._capabilities:
            if capability.supported:
                return True

        return False

    @property
    def parameters(self) -> ColorSettingCapabilityParameters:
        """Return parameters for a devices list request."""
        return ColorSettingCapabilityParameters(
            color_model=self._color.parameters.color_model if self._color.supported else None,
            temperature_k=self._temperature.parameters.temperature_k if self._temperature.supported else None,
            color_scene=self._scene.parameters.color_scene if self._scene.supported else None,
        )

    def get_value(self) -> None:
        """Return the current capability value."""
        return None

    async def set_instance_state(self, context: Context, state: ColorSettingCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        raise APIError(ResponseCode.INTERNAL_ERROR, "No instance")

    def _get_scene_capability(self) -> ColorSceneCapability:
        """Return scene capability."""
        scene_instance = ColorSettingCapabilityInstance.SCENE
        if custom_scene_config := self._entity_config.get(CONF_ENTITY_CUSTOM_MODES, {}).get(scene_instance):
            from .capability_custom import get_custom_capability

            custom_capability = get_custom_capability(
                self._hass, self._entry_data, custom_scene_config, CapabilityType.MODE, scene_instance, self.device_id
            )
            return cast(ColorSceneCapability, custom_capability)

        return ColorSceneStateCapability(self._hass, self._entry_data, self.state)

    @property
    def _capabilities(self) -> list[Capability[Any]]:
        """Return all child capabilities."""
        return [self._color, self._temperature, self._scene]


class RGBColorCapability(StateCapability[RGBInstanceActionState], LightState):
    """Capability to control color of a light device."""

    type = CapabilityType.COLOR_SETTING
    instance = ColorSettingCapabilityInstance.RGB

    @property
    def supported(self) -> bool:
        """Test if capability is supported."""
        return self.state.domain == light.DOMAIN and bool(
            {
                ColorMode.RGB,
                ColorMode.RGBW,
                ColorMode.RGBWW,
                ColorMode.HS,
                ColorMode.XY,
            }
            & self._supported_color_modes
        )

    @property
    def parameters(self) -> ColorSettingCapabilityParameters:
        """Return parameters for a devices list request."""
        return ColorSettingCapabilityParameters(color_model=CapabilityParameterColorModel.RGB)

    def get_description(self) -> None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return None

    def get_value(self) -> int | None:
        """Return the current capability value."""
        if self.state.attributes.get(ATTR_COLOR_MODE) == COLOR_MODE_COLOR_TEMP:
            return None

        if self._rgb_color:
            if self._rgb_color in (RGBColor(255, 255, 255), RGBColor(0, 0, 0)):
                return None

            return self._converter.get_yandex_color(self._rgb_color)

        return None

    async def set_instance_state(self, context: Context, state: RGBInstanceActionState) -> None:
        """Change the capability state."""
        color = self._converter.get_ha_color(state.value)
        service_data: dict[str, Any] = {ATTR_ENTITY_ID: self.state.entity_id}

        if ColorMode.RGBWW in self._supported_color_modes:
            service_data[ATTR_RGBWW_COLOR] = tuple(color) + (
                self._white_brightness or 0,
                self._warm_white_brightness or 0,
            )
        elif ColorMode.RGBW in self._supported_color_modes:
            service_data[ATTR_RGBW_COLOR] = tuple(color) + (self._white_brightness or 0,)
        else:
            service_data[ATTR_RGB_COLOR] = tuple(color)

        await self._hass.services.async_call(
            light.DOMAIN, SERVICE_TURN_ON, service_data, blocking=True, context=context
        )

    @cached_property
    def _converter(self) -> ColorConverter:
        """Return the color converter."""
        if color_profile_name := self._entity_config.get(CONF_COLOR_PROFILE):
            try:
                return ColorConverter(self._entry_data.color_profiles[color_profile_name])
            except KeyError:
                raise APIError(
                    ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                    f"Color profile '{color_profile_name}' not found for {self}",
                )

        return ColorConverter()


class ColorTemperatureCapability(StateCapability[TemperatureKInstanceActionState], LightState):
    """Capability to control color temperature of a light device."""

    type = CapabilityType.COLOR_SETTING
    instance = ColorSettingCapabilityInstance.TEMPERATURE_K

    _default_white_temperature = ColorTemperatureConverter.default_white_temperature
    _cold_white_temperature = 6500
    _color_modes_temp_to_white = {ColorMode.RGBW, ColorMode.RGB, ColorMode.HS, ColorMode.XY}

    @property
    def supported(self) -> bool:
        """Test if capability is supported."""
        if self.state.domain == light.DOMAIN:
            if color_temp_supported(self._supported_color_modes):
                return True

            if self._color_modes_temp_to_white & self._supported_color_modes:
                return True

        return False

    @property
    def parameters(self) -> ColorSettingCapabilityParameters:
        """Return parameters for a devices list request."""
        if color_temp_supported(self._supported_color_modes):
            min_temp, max_temp = self._converter.supported_range
            return ColorSettingCapabilityParameters(
                temperature_k=CapabilityParameterTemperatureK(min=min_temp, max=max_temp)
            )

        min_temp = self._default_white_temperature
        max_temp = self._default_white_temperature
        if {ColorMode.RGBW, ColorMode.WHITE} & self._supported_color_modes:
            max_temp = self._cold_white_temperature

        return ColorSettingCapabilityParameters(
            temperature_k=CapabilityParameterTemperatureK(min=min_temp, max=max_temp)
        )

    def get_description(self) -> None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return None

    def get_value(self) -> int | None:
        """Return the current capability value."""
        color_temperature = self.state.attributes.get(ATTR_COLOR_TEMP_KELVIN)
        if color_temperature is not None:
            return self._converter.get_yandex_color_temperature(color_temperature)

        color_mode = self.state.attributes.get(ATTR_COLOR_MODE)
        match color_mode:
            case ColorMode.WHITE:
                return self._default_white_temperature

            case ColorMode.RGBW:
                if self._rgb_color == RGBColor(0, 0, 0) and (self._white_brightness or 0) > 0:
                    return self._default_white_temperature
                elif self._rgb_color == RGBColor(255, 255, 255):
                    return self._cold_white_temperature

            case _:
                if self._rgb_color == RGBColor(255, 255, 255):
                    if ColorMode.WHITE in self._supported_color_modes:
                        return self._cold_white_temperature

                    return self._default_white_temperature

        return None

    async def set_instance_state(self, context: Context, state: TemperatureKInstanceActionState) -> None:
        """Change the capability state."""
        service_data: dict[str, Any] = {ATTR_ENTITY_ID: self.state.entity_id}

        if color_temp_supported(self._supported_color_modes):
            service_data[ATTR_KELVIN] = self._converter.get_ha_color_temperature(state.value)

        elif ColorMode.WHITE in self._supported_color_modes and state.value == self._default_white_temperature:
            service_data[ATTR_WHITE] = self.state.attributes.get(ATTR_BRIGHTNESS, 255)

        elif ColorMode.RGBW in self._supported_color_modes:
            if state.value == self._default_white_temperature:
                service_data[ATTR_RGBW_COLOR] = (0, 0, 0, self.state.attributes.get(ATTR_BRIGHTNESS, 255))
            else:
                service_data[ATTR_RGBW_COLOR] = (255, 255, 255, 0)

        else:
            service_data[ATTR_RGB_COLOR] = (255, 255, 255)

        await self._hass.services.async_call(
            light.DOMAIN, SERVICE_TURN_ON, service_data, blocking=True, context=context
        )

    @cached_property
    def _converter(self) -> ColorTemperatureConverter:
        """Return the color temperature converter."""
        if color_profile_name := self._entity_config.get(CONF_COLOR_PROFILE):
            try:
                return ColorTemperatureConverter(self._entry_data.color_profiles[color_profile_name], self.state)

            except KeyError:
                raise APIError(
                    ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                    f"Color profile '{color_profile_name}' not found for {self}",
                )

        return ColorTemperatureConverter(None, self.state)


class ColorSceneCapability(Capability[SceneInstanceActionState]):
    """Base class for capability to control color scene."""

    type: CapabilityType = CapabilityType.COLOR_SETTING
    instance: CapabilityInstance = ColorSettingCapabilityInstance.SCENE

    _scenes_map_default: dict[ColorScene, list[str]] = {}

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return bool(self.supported_yandex_scenes)

    @property
    def parameters(self) -> ColorSettingCapabilityParameters:
        """Return parameters for a devices list request."""
        return ColorSettingCapabilityParameters(
            color_scene=CapabilityParameterColorScene.from_list(self.supported_yandex_scenes)
        )

    @property
    def supported_yandex_scenes(self) -> list[ColorScene]:
        """Returns a list of supported Yandex scenes."""
        scenes = set()
        for ha_value in self.supported_ha_scenes:
            if value := self.get_yandex_scene_by_ha_scene(ha_value):
                scenes.add(value)

        return sorted(list(scenes))

    @property
    @abstractmethod
    def supported_ha_scenes(self) -> list[str]:
        """Returns a list of supported HA scenes."""
        ...

    @cached_property
    def scenes_map(self) -> dict[ColorScene, list[str]]:
        """Return scene mapping between Yandex and HA."""
        scenes_map = self._scenes_map_default.copy()

        if CONF_ENTITY_MODE_MAP in self._entity_config:
            scenes_map.update(
                {ColorScene(k): v for k, v in self._entity_config[CONF_ENTITY_MODE_MAP].get(self.instance, {}).items()}
            )

        return scenes_map

    def get_yandex_scene_by_ha_scene(self, ha_scene: str) -> ColorScene | None:
        """Return Yandex scene for HA scene."""
        for scene, names in self.scenes_map.items():
            if ha_scene.lower() in [n.lower() for n in names]:
                return scene

        return None

    def get_ha_scene_by_yandex_scene(self, yandex_scene: ColorScene) -> str:
        """Return HA scene for Yandex scene."""
        ha_scenes = self.scenes_map.get(yandex_scene, [])
        for ha_scene in ha_scenes:
            for sc in self.supported_ha_scenes:
                if sc.lower() == ha_scene.lower():
                    return sc

        raise APIError(
            ResponseCode.INVALID_VALUE,
            f"Unsupported scene '{yandex_scene}' for {self}, see https://docs.yaha-cloud.ru/dev/config/modes/",
        )

    def get_description(self) -> None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return None

    @abstractmethod
    def get_value(self) -> ColorScene | None:
        """Return the current capability value."""
        ...

    @abstractmethod
    async def set_instance_state(self, context: Context, state: SceneInstanceActionState) -> None:
        """Change the capability state."""
        ...


class ColorSceneStateCapability(ColorSceneCapability, StateCapability[SceneInstanceActionState]):
    """Capability to control effect of a light device."""

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
        """Test if the capability is supported."""
        if self.state.domain == light.DOMAIN and self._state_features & LightEntityFeature.EFFECT:
            return super().supported

        return False

    @property
    def supported_ha_scenes(self) -> list[str]:
        """Returns a list of supported Yandex scenes."""
        return list(map(str, self.state.attributes.get(ATTR_EFFECT_LIST, []) or []))

    def get_value(self) -> ColorScene | None:
        """Return the current capability value."""
        if (effect := self.state.attributes.get(ATTR_EFFECT)) is not None:
            return self.get_yandex_scene_by_ha_scene(str(effect))

        return None

    async def set_instance_state(self, context: Context, state: SceneInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                ATTR_EFFECT: self.get_ha_scene_by_yandex_scene(state.value),
            },
            blocking=True,
            context=context,
        )


STATE_CAPABILITIES_REGISTRY.register(ColorSettingCapability)
STATE_CAPABILITIES_REGISTRY.register(RGBColorCapability)
STATE_CAPABILITIES_REGISTRY.register(ColorTemperatureCapability)
STATE_CAPABILITIES_REGISTRY.register(ColorSceneStateCapability)
