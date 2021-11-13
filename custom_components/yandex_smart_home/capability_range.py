"""Implement the Yandex Smart Home ranges capabilities."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any

from homeassistant.components import climate, cover, fan, humidifier, light, media_player, water_heater
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_MODEL,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import (
    ATTR_TARGET_HUMIDITY,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
    DOMAIN_XIAOMI_AIRPURIFIER,
    ERR_DEVICE_OFF,
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    MODEL_PREFIX_XIAOMI_AIRPURIFIER,
    SERVICE_FAN_SET_TARGET_HUMIDITY,
    STATE_NONE,
)
from .error import SmartHomeError
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_RANGE = PREFIX_CAPABILITIES + 'range'


class RangeCapability(AbstractCapability, ABC):
    """Base class of capabilities with range functionality like volume or
    brightness.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/range-docpage/
    """

    type = CAPABILITIES_RANGE
    default_range = (0, 100, 1)

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)
        self.retrievable = self.support_random_access

    @property
    @abstractmethod
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        pass

    @property
    def range(self) -> (float, float, float):
        """Return support range (min, max, precision)."""
        return (
            self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, self.default_range[0]),
            self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, self.default_range[1]),
            self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, self.default_range[2])
        )

    def parameters(self) -> dict[str, Any]:
        """Return parameters for a devices request."""
        if self.support_random_access:
            range_min, range_max, range_precision = self.range
            rv = {
                'instance': self.instance,
                'random_access': True,
                'range': {
                    'min': range_min,
                    'max': range_max,
                    'precision': range_precision
                }
            }

            if self.instance in const.RANGE_INSTANCE_TO_UNITS:
                rv['unit'] = const.RANGE_INSTANCE_TO_UNITS[self.instance]

            return rv

        return {
            'instance': self.instance,
            'random_access': False,
        }

    def float_value(self, value: Any, strict: bool = True) -> float | None:
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            if strict:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
                )

    def get_absolute_value(self, relative_value: float) -> float:
        """Return absolute value for relative value."""
        value = self.get_value()
        if value is None:
            if self.state.state == STATE_OFF:
                raise SmartHomeError(
                    ERR_DEVICE_OFF,
                    f'Device {self.state.entity_id} probably turned off'
                )

            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unable to get current value or {self.instance} instance of {self.state.entity_id}'
            )

        return max(min(value + relative_value, self.range[1]), self.range[0])


@register_capability
class CoverLevelCapability(RangeCapability):
    """Set cover level"""

    instance = const.RANGE_INSTANCE_OPEN

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        return self.state.domain == cover.DOMAIN and features & cover.SUPPORT_SET_POSITION

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        return self.float_value(self.state.attributes.get(cover.ATTR_CURRENT_POSITION))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value'] if not state.get('relative') else self.get_absolute_value(state['value'])

        await self.hass.services.async_call(
            cover.DOMAIN,
            cover.SERVICE_SET_COVER_POSITION, {
                ATTR_ENTITY_ID: self.state.entity_id,
                cover.ATTR_POSITION: value
            },
            blocking=True,
            context=data.context
        )


class TemperatureCapability(RangeCapability, ABC):
    """Set temperature functionality."""

    instance = const.RANGE_INSTANCE_TEMPERATURE
    default_range = (0, 100, 0.5)

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True


@register_capability
class TemperatureCapabilityWaterHeater(TemperatureCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)

        self.default_range = (
            self.state.attributes.get(water_heater.ATTR_MIN_TEMP),
            self.state.attributes.get(water_heater.ATTR_MAX_TEMP),
            0.5
        )

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        return self.state.domain == water_heater.DOMAIN and features & water_heater.SUPPORT_TARGET_TEMPERATURE

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        return self.float_value(self.state.attributes.get(water_heater.ATTR_TEMPERATURE))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value'] if not state.get('relative') else self.get_absolute_value(state['value'])

        await self.hass.services.async_call(
            water_heater.DOMAIN,
            water_heater.SERVICE_SET_TEMPERATURE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                water_heater.ATTR_TEMPERATURE: value
            },
            blocking=True,
            context=data.context
        )


@register_capability
class TemperatureCapabilityClimate(TemperatureCapability):
    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)

        self.default_range = (
            self.state.attributes.get(climate.ATTR_MIN_TEMP),
            self.state.attributes.get(climate.ATTR_MAX_TEMP),
            self.state.attributes.get(climate.ATTR_TARGET_TEMP_STEP, 0.5),
        )

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        return self.state.domain == climate.DOMAIN and features & climate.SUPPORT_TARGET_TEMPERATURE

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        return self.float_value(self.state.attributes.get(climate.ATTR_TEMPERATURE))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value'] if not state.get('relative') else self.get_absolute_value(state['value'])

        await self.hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_TEMPERATURE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_TEMPERATURE: value
            },
            blocking=True,
            context=data.context
        )


class HumidityCapability(RangeCapability, ABC):
    """Set humidity functionality."""

    instance = const.RANGE_INSTANCE_HUMIDITY

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True


@register_capability
class HumidityCapabilityHumidifier(HumidityCapability):
    instance = const.RANGE_INSTANCE_HUMIDITY

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        super().__init__(hass, config, state)

        self.default_range = (
            self.state.attributes.get(humidifier.ATTR_MIN_HUMIDITY),
            self.state.attributes.get(humidifier.ATTR_MAX_HUMIDITY),
            1
        )

    def supported(self) -> bool:
        """Test if capability is supported."""
        return self.state.domain == humidifier.DOMAIN

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        return self.float_value(self.state.attributes.get(humidifier.ATTR_HUMIDITY))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value'] if not state.get('relative') else self.get_absolute_value(state['value'])

        await self.hass.services.async_call(
            humidifier.DOMAIN,
            humidifier.SERVICE_SET_HUMIDITY, {
                ATTR_ENTITY_ID: self.state.entity_id,
                humidifier.ATTR_HUMIDITY: value
            },
            blocking=True,
            context=data.context
        )


@register_capability
class HumidityCapabilityHumidiferXiaomi(HumidityCapability):
    """Set humidity functionality."""

    def supported(self) -> bool:
        """Test if capability is supported."""
        if self.state.domain == fan.DOMAIN:
            if self.state.attributes.get(ATTR_MODEL, '').startswith(MODEL_PREFIX_XIAOMI_AIRPURIFIER):
                if ATTR_TARGET_HUMIDITY in self.state.attributes:
                    return True

        return False

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        return self.float_value(self.state.attributes.get(ATTR_TARGET_HUMIDITY))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value'] if not state.get('relative') else self.get_absolute_value(state['value'])

        await self.hass.services.async_call(
            DOMAIN_XIAOMI_AIRPURIFIER,
            SERVICE_FAN_SET_TARGET_HUMIDITY, {
                ATTR_ENTITY_ID: self.state.entity_id,
                humidifier.ATTR_HUMIDITY: value
            },
            blocking=True,
            context=data.context
        )


@register_capability
class BrightnessCapability(RangeCapability):
    """Set brightness functionality."""

    instance = const.RANGE_INSTANCE_BRIGHTNESS
    default_range = (1, 100, 1)

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == light.DOMAIN:
            if features & light.SUPPORT_BRIGHTNESS:
                return True

            if light.brightness_supported(self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES)):
                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        return True

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        brightness = self.state.attributes.get(light.ATTR_BRIGHTNESS)
        if brightness is not None:
            return int(100 * (self.float_value(brightness) / 255))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        if state.get('relative'):
            attribute = light.ATTR_BRIGHTNESS_STEP_PCT
        else:
            attribute = light.ATTR_BRIGHTNESS_PCT

        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id,
                attribute: state['value']
            },
            blocking=True,
            context=data.context
        )


@register_capability
class VolumeCapability(RangeCapability):
    """Set volume functionality."""

    instance = const.RANGE_INSTANCE_VOLUME

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN:
            if features & media_player.SUPPORT_VOLUME_STEP:
                return True

            if features & media_player.SUPPORT_VOLUME_SET:
                return True

            if const.MEDIA_PLAYER_FEATURE_VOLUME_SET in self.entity_config.get(const.CONF_FEATURES, []):
                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if const.MEDIA_PLAYER_FEATURE_VOLUME_SET in self.entity_config.get(const.CONF_FEATURES, []):
            return True

        return not (features & media_player.SUPPORT_VOLUME_STEP and not features & media_player.SUPPORT_VOLUME_SET)

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        level = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_LEVEL)

        if level is not None:
            return int(self.float_value(level) * 100)

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        if not self.support_random_access:
            if not state.get('relative'):
                raise SmartHomeError(ERR_INVALID_VALUE, f'Failed to set absolute volume for {self.state.entity_id}')

            if state['value'] > 0:
                service = media_player.SERVICE_VOLUME_UP
            else:
                service = media_player.SERVICE_VOLUME_DOWN

            volume_step = int(self.entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_PRECISION, 1))
            if abs(state['value']) != 1:
                volume_step = abs(state['value'])

            for _ in range(volume_step):
                await self.hass.services.async_call(
                    media_player.DOMAIN,
                    service, {
                        ATTR_ENTITY_ID: self.state.entity_id
                    }, blocking=True, context=data.context
                )

            return

        value = (state['value'] if not state.get('relative') else self.get_absolute_value(state['value'])) / 100

        await self.hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_VOLUME_SET, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_MEDIA_VOLUME_LEVEL: value
            },
            blocking=True,
            context=data.context
        )


@register_capability
class ChannelCapability(RangeCapability):
    """Set channel functionality."""

    instance = const.RANGE_INSTANCE_CHANNEL
    default_range = (0, 999, 1)

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN:
            if features & media_player.SUPPORT_PREVIOUS_TRACK and features & media_player.SUPPORT_NEXT_TRACK:
                return True

            if const.MEDIA_PLAYER_FEATURE_NEXT_PREVIOUS_TRACK in self.entity_config.get(const.CONF_FEATURES, []):
                return True

            if features & media_player.SUPPORT_PLAY_MEDIA:
                if self.entity_config.get(const.CONF_SUPPORT_SET_CHANNEL) is False:
                    return False

                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if capability supports random access."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        device_class = self.state.attributes.get(ATTR_DEVICE_CLASS)

        if self.entity_config.get(const.CONF_SUPPORT_SET_CHANNEL) is False:
            return False

        return bool(features & media_player.SUPPORT_PLAY_MEDIA and device_class == media_player.DEVICE_CLASS_TV)

    def get_value(self) -> float | None:
        """Return the state value of this capability for this entity."""
        media_content_type = self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_TYPE)

        if media_content_type == media_player.const.MEDIA_TYPE_CHANNEL:
            return self.float_value(self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_ID), strict=False)

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        value = state['value']
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if state.get('relative'):
            if features & media_player.SUPPORT_PREVIOUS_TRACK and features & media_player.SUPPORT_NEXT_TRACK:
                if state['value'] >= 0:
                    service = media_player.SERVICE_MEDIA_NEXT_TRACK
                else:
                    service = media_player.SERVICE_MEDIA_PREVIOUS_TRACK

                await self.hass.services.async_call(
                    media_player.DOMAIN,
                    service, {
                        ATTR_ENTITY_ID: self.state.entity_id
                    },
                    blocking=True,
                    context=data.context
                )
                return

            if self.get_value() is None:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f'Failed to set relative value for {self.instance} instance of {self.state.entity_id}.'
                )
            else:
                value = self.get_absolute_value(state['value'])

        try:
            await self.hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_PLAY_MEDIA, {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.ATTR_MEDIA_CONTENT_ID: int(value),
                    media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL
                },
                blocking=False,  # some tv's do it too slow
                context=data.context
            )
        except ValueError as e:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Failed to set channel for {self.state.entity_id}. '
                f'Please change setting "support_set_channel" to "false" in entity_config '
                f'if the device does not support channel selection. Error: {e!r}'
            )
