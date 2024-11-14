"""Implement the Yandex Smart Home range capabilities."""

from abc import ABC, abstractmethod
from functools import cached_property
import logging
import math
from typing import Any, Protocol

from homeassistant.components import climate, cover, fan, humidifier, light, media_player, valve, water_heater
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.light import ColorMode
from homeassistant.components.media_player import MediaPlayerDeviceClass, MediaPlayerEntityFeature, MediaType
from homeassistant.components.valve import ValveEntityFeature
from homeassistant.components.water_heater import WaterHeaterEntityFeature
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_MODEL,
    ATTR_TEMPERATURE,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_VALVE_POSITION,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context
from homeassistant.util.color import RGBColor

from .capability import STATE_CAPABILITIES_REGISTRY, Capability, StateCapability
from .capability_color import LightState
from .const import (
    ATTR_TARGET_HUMIDITY,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
    CONF_FEATURES,
    CONF_SUPPORT_SET_CHANNEL,
    DOMAIN_XIAOMI_AIRPURIFIER,
    MODEL_PREFIX_XIAOMI_AIRPURIFIER,
    SERVICE_FAN_SET_TARGET_HUMIDITY,
    STATE_NONE,
    MediaPlayerFeature,
)
from .helpers import APIError
from .schema import (
    CapabilityType,
    RangeCapabilityInstance,
    RangeCapabilityInstanceActionState,
    RangeCapabilityParameters,
    RangeCapabilityRange,
    ResponseCode,
)

_LOGGER = logging.getLogger(__name__)


class RangeCapability(Capability[RangeCapabilityInstanceActionState], Protocol):
    """Base class for capabilities with range functionality like volume or brightness.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/range-docpage/
    """

    type: CapabilityType = CapabilityType.RANGE
    instance: RangeCapabilityInstance

    @property
    @abstractmethod
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        ...

    @abstractmethod
    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        ...

    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        return self.support_random_access

    @property
    def parameters(self) -> RangeCapabilityParameters:
        """Return parameters for a devices list request."""
        if self.support_random_access:
            return RangeCapabilityParameters(instance=self.instance, random_access=True, range=self._range)

        if self.instance in [
            RangeCapabilityInstance.BRIGHTNESS,
            RangeCapabilityInstance.HUMIDITY,
            RangeCapabilityInstance.OPEN,
            RangeCapabilityInstance.TEMPERATURE,
        ]:
            return RangeCapabilityParameters(
                instance=self.instance, random_access=self.support_random_access, range=self._range
            )

        return RangeCapabilityParameters(instance=self.instance, random_access=False)

    def get_value(self) -> float | None:
        """Return the current capability value."""
        value = self._get_value()

        if self.support_random_access and value is not None:
            if not (self._range.min <= value <= self._range.max):
                _LOGGER.debug(
                    f"Value {value} is not in range {self._range} for instance {self.instance.value} "
                    f"of {self.device_id}"
                )
                return None

        return value

    @abstractmethod
    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        ...

    @abstractmethod
    def _get_absolute_value(self, relative_value: float) -> float:
        """Return the absolute value for a relative value."""
        ...

    def _get_service_call_value(self, state: RangeCapabilityInstanceActionState) -> float:
        """Return the absolute value for a service call."""
        if state.relative:
            return self._get_absolute_value(state.value)

        return state.value

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(min=0, max=100, precision=1)

    def _convert_to_float(self, value: Any, strict: bool = True) -> float | None:
        """Return float of a value, ignore some states, catch errors."""
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            if strict:
                raise APIError(ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, f"Unsupported value '{value}' for {self}")

        return None


class StateRangeCapability(RangeCapability, StateCapability[RangeCapabilityInstanceActionState], Protocol):
    """Base class for a range capability based on the state."""

    def _get_absolute_value(self, relative_value: float) -> float:
        """Return the absolute value for a relative value."""
        value = self._get_value()

        if value is None:
            if self.state.state == STATE_OFF:
                raise APIError(ResponseCode.DEVICE_OFF, f"Device {self.state.entity_id} probably turned off")

            raise APIError(ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, f"Missing current value for {self}")

        return max(min(value + relative_value, self._range.max), self._range.min)


class CoverPositionCapability(StateRangeCapability):
    """Capability to control position of a cover."""

    instance = RangeCapabilityInstance.OPEN

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == cover.DOMAIN and bool(self._state_features & CoverEntityFeature.SET_POSITION)

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            cover.DOMAIN,
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: self.state.entity_id, cover.ATTR_POSITION: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(cover.ATTR_CURRENT_POSITION))


class TemperatureCapability(StateRangeCapability, ABC):
    """Capability to control a device target temperature."""

    instance = RangeCapabilityInstance.TEMPERATURE

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True


class TemperatureCapabilityWaterHeater(TemperatureCapability):
    """Capability to control a water heater target temperature."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == water_heater.DOMAIN and bool(
            self._state_features & WaterHeaterEntityFeature.TARGET_TEMPERATURE
        )

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            water_heater.DOMAIN,
            water_heater.SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: self.state.entity_id, ATTR_TEMPERATURE: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(ATTR_TEMPERATURE))

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(
            min=self.state.attributes.get(water_heater.ATTR_MIN_TEMP, 0),
            max=self.state.attributes.get(water_heater.ATTR_MAX_TEMP, 100),
            precision=0.5,
        )


class TemperatureCapabilityClimate(TemperatureCapability):
    """Capability to control a climate device target temperature."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == climate.DOMAIN and bool(
            self._state_features & ClimateEntityFeature.TARGET_TEMPERATURE
        )

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: self.state.entity_id, ATTR_TEMPERATURE: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(ATTR_TEMPERATURE))

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(
            min=self.state.attributes.get(climate.ATTR_MIN_TEMP, 0),
            max=self.state.attributes.get(climate.ATTR_MAX_TEMP, 100),
            precision=self.state.attributes.get(climate.ATTR_TARGET_TEMP_STEP, 0.5),
        )


class HumidityCapability(StateRangeCapability, ABC):
    """Capability to control a device target humidity."""

    instance = RangeCapabilityInstance.HUMIDITY

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True


class HumidityCapabilityHumidifier(HumidityCapability):
    """Capability to control a humidifier target humidity."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == humidifier.DOMAIN

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            humidifier.DOMAIN,
            humidifier.SERVICE_SET_HUMIDITY,
            {ATTR_ENTITY_ID: self.state.entity_id, humidifier.ATTR_HUMIDITY: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(humidifier.ATTR_HUMIDITY))

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(
            min=self.state.attributes.get(humidifier.ATTR_MIN_HUMIDITY, 0),
            max=self.state.attributes.get(humidifier.ATTR_MAX_HUMIDITY, 100),
            precision=1,
        )


class HumidityCapabilityXiaomiFan(HumidityCapability):
    """Capability to control a Xiaomi fan target humidity."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == fan.DOMAIN:
            if self.state.attributes.get(ATTR_MODEL, "").startswith(MODEL_PREFIX_XIAOMI_AIRPURIFIER):
                if ATTR_TARGET_HUMIDITY in self.state.attributes:
                    return True

        return False

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            DOMAIN_XIAOMI_AIRPURIFIER,
            SERVICE_FAN_SET_TARGET_HUMIDITY,
            {ATTR_ENTITY_ID: self.state.entity_id, humidifier.ATTR_HUMIDITY: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(ATTR_TARGET_HUMIDITY))


class BrightnessCapability(StateRangeCapability):
    """Capability to control brightness of a device."""

    instance = RangeCapabilityInstance.BRIGHTNESS

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == light.DOMAIN and light.brightness_supported(
            self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES)
        )

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if state.relative:
            attribute = light.ATTR_BRIGHTNESS_STEP_PCT
        else:
            attribute = light.ATTR_BRIGHTNESS_PCT

        await self._hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.state.entity_id, attribute: state.value},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if (brightness := self._convert_to_float(self.state.attributes.get(light.ATTR_BRIGHTNESS))) is not None:
            return int(100 * (brightness / 255))

        return None

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(min=1, max=100, precision=1)


class WhiteLightBrightnessCapability(StateRangeCapability, LightState):
    """Capability to control white brightness and cold white brightness of a RGBW/RGBWW light device."""

    instance = RangeCapabilityInstance.VOLUME
    volume_default_relative_step = 3
    brightness_relative_step = 20

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == light.DOMAIN and bool(
            {ColorMode.RGBW, ColorMode.RGBWW} & self._supported_color_modes
        )

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        service_data: dict[str, Any] = {ATTR_ENTITY_ID: self.state.entity_id}
        color = self._rgb_color or RGBColor(0, 0, 0)
        brightness_pct = state.value

        if state.relative:
            if abs(state.value) == self.volume_default_relative_step:
                brightness_pct = self._get_absolute_value(self.brightness_relative_step * math.copysign(1, state.value))
            else:
                brightness_pct = self._get_absolute_value(state.value)

        brightness = round(255 * brightness_pct / 100)

        if ColorMode.RGBWW in self._supported_color_modes:
            service_data[light.ATTR_RGBWW_COLOR] = color + (brightness, self._warm_white_brightness or 0)
        else:
            service_data[light.ATTR_RGBW_COLOR] = color + (brightness,)

        await self._hass.services.async_call(
            light.DOMAIN, SERVICE_TURN_ON, service_data, blocking=True, context=context
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if (value := self._white_brightness) is not None:
            return int(100 * (value / 255))

        return None

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(min=0, max=100, precision=1)


class WarmWhiteLightBrightnessCapability(StateRangeCapability, LightState):
    """Capability to control warm white brightness of a RGBWW light device."""

    instance = RangeCapabilityInstance.OPEN

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == light.DOMAIN and ColorMode.RGBWW in self._supported_color_modes

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        color = self._rgb_color or RGBColor(0, 0, 0)
        brightness_pct = self._get_service_call_value(state)

        await self._hass.services.async_call(
            light.DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                light.ATTR_RGBWW_COLOR: color + (self._white_brightness or 0, round(255 * brightness_pct / 100)),
            },
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if (value := self._warm_white_brightness) is not None:
            return int(100 * (value / 255))

        return None

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(min=0, max=100, precision=1)


class VolumeCapability(StateRangeCapability):
    """Capability to control volume of a device."""

    instance = RangeCapabilityInstance.VOLUME

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if self._state_features & MediaPlayerEntityFeature.VOLUME_STEP:
                return True

            if self._state_features & MediaPlayerEntityFeature.VOLUME_SET:
                return True

            if MediaPlayerFeature.VOLUME_SET in self._entity_config.get(CONF_FEATURES, []):
                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        if MediaPlayerFeature.VOLUME_SET in self._entity_config.get(CONF_FEATURES, []):
            return True

        return not (
            self._state_features & MediaPlayerEntityFeature.VOLUME_STEP
            and not self._state_features & MediaPlayerEntityFeature.VOLUME_SET
        )

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if self.support_random_access:
            await self._hass.services.async_call(
                media_player.DOMAIN,
                SERVICE_VOLUME_SET,
                {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.ATTR_MEDIA_VOLUME_LEVEL: self._get_service_call_value(state) / 100,
                },
                blocking=True,
                context=context,
            )
            return

        # absolute volume
        if not state.relative:
            raise APIError(ResponseCode.INVALID_VALUE, f"Absolute volume is not supported for {self}")

        if state.value > 0:
            service = SERVICE_VOLUME_UP
        else:
            service = SERVICE_VOLUME_DOWN

        volume_step = int(self._entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, 1))
        if abs(state.value) != 1:
            volume_step = int(abs(state.value))

        for _ in range(volume_step):
            await self._hass.services.async_call(
                media_player.DOMAIN,
                service,
                {ATTR_ENTITY_ID: self.state.entity_id},
                blocking=True,
                context=context,
            )

        return None

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if (
            level := self._convert_to_float(self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_LEVEL))
        ) is not None:
            return int(level * 100)

        return None

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(
            min=self._entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, 0),
            max=self._entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, 100),
            precision=self._entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, 1),
        )


class ChannelCapability(StateRangeCapability):
    """Capability to control media playback state."""

    instance = RangeCapabilityInstance.CHANNEL

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if (
                self._state_features & MediaPlayerEntityFeature.PREVIOUS_TRACK
                and self._state_features & MediaPlayerEntityFeature.NEXT_TRACK
            ):
                return True

            if MediaPlayerFeature.NEXT_PREVIOUS_TRACK in self._entity_config.get(CONF_FEATURES, []):
                return True

            if (
                self._state_features & MediaPlayerEntityFeature.PLAY_MEDIA
                or MediaPlayerFeature.PLAY_MEDIA in self._entity_config.get(CONF_FEATURES, [])
            ):
                if self._entity_config.get(CONF_SUPPORT_SET_CHANNEL) is False:
                    return False

                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        device_class = self.state.attributes.get(ATTR_DEVICE_CLASS)

        if self._entity_config.get(CONF_SUPPORT_SET_CHANNEL) is False:
            return False

        if device_class == MediaPlayerDeviceClass.TV:
            if (
                self._state_features & MediaPlayerEntityFeature.PLAY_MEDIA
                or MediaPlayerFeature.PLAY_MEDIA in self._entity_config.get(CONF_FEATURES, [])
            ):
                return True

        return False

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        value = state.value

        if state.relative:
            if (
                self._state_features & MediaPlayerEntityFeature.PREVIOUS_TRACK
                and self._state_features & MediaPlayerEntityFeature.NEXT_TRACK
            ):
                if state.value > 0:
                    service = SERVICE_MEDIA_NEXT_TRACK
                else:
                    service = SERVICE_MEDIA_PREVIOUS_TRACK

                await self._hass.services.async_call(
                    media_player.DOMAIN,
                    service,
                    {ATTR_ENTITY_ID: self.state.entity_id},
                    blocking=True,
                    context=context,
                )
                return

            if self.get_value() is None:
                raise APIError(ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, f"Missing current value for {self}")
            else:
                value = self._get_absolute_value(state.value)

        try:
            await self._hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_PLAY_MEDIA,
                {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.ATTR_MEDIA_CONTENT_ID: int(value),
                    media_player.ATTR_MEDIA_CONTENT_TYPE: MediaType.CHANNEL,
                },
                blocking=False,  # some tv's do it too slow
                context=context,
            )
        except ValueError as e:
            raise APIError(
                ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                f"Failed to set channel for {self.device_id}. "
                f'Please change setting "support_set_channel" to "false" in entity_config '
                f"if the device does not support channel selection. Error: {e!r}",
            )

        return None

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        media_content_type = self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_TYPE)

        if media_content_type == MediaType.CHANNEL:
            return self._convert_to_float(self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_ID), strict=False)

        return None

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(
            min=0,
            max=999,
            precision=1,
        )


class ValvePositionCapability(StateRangeCapability):
    """Capability to control position of a device."""

    instance = RangeCapabilityInstance.OPEN

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == valve.DOMAIN and bool(self._state_features & ValveEntityFeature.SET_POSITION)

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            valve.DOMAIN,
            SERVICE_SET_VALVE_POSITION,
            {ATTR_ENTITY_ID: self.state.entity_id, valve.ATTR_POSITION: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(valve.ATTR_CURRENT_POSITION))


STATE_CAPABILITIES_REGISTRY.register(CoverPositionCapability)
STATE_CAPABILITIES_REGISTRY.register(TemperatureCapabilityWaterHeater)
STATE_CAPABILITIES_REGISTRY.register(TemperatureCapabilityClimate)
STATE_CAPABILITIES_REGISTRY.register(HumidityCapabilityHumidifier)
STATE_CAPABILITIES_REGISTRY.register(HumidityCapabilityXiaomiFan)
STATE_CAPABILITIES_REGISTRY.register(BrightnessCapability)
STATE_CAPABILITIES_REGISTRY.register(WhiteLightBrightnessCapability)
STATE_CAPABILITIES_REGISTRY.register(WarmWhiteLightBrightnessCapability)
STATE_CAPABILITIES_REGISTRY.register(VolumeCapability)
STATE_CAPABILITIES_REGISTRY.register(ChannelCapability)
STATE_CAPABILITIES_REGISTRY.register(ValvePositionCapability)
