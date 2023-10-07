"""Implement the Yandex Smart Home range capabilities."""
from abc import ABC, abstractmethod
import logging
from typing import Any, Protocol

from homeassistant.backports.functools import cached_property
from homeassistant.components import climate, cover, fan, humidifier, light, media_player, water_heater
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_MODEL,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context

from .capability import STATE_CAPABILITIES_REGISTRY, Capability, StateCapability
from .const import (
    ATTR_TARGET_HUMIDITY,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
    CONF_FEATURES,
    CONF_SUPPORT_SET_CHANNEL,
    DOMAIN_XIAOMI_AIRPURIFIER,
    MEDIA_PLAYER_FEATURE_NEXT_PREVIOUS_TRACK,
    MEDIA_PLAYER_FEATURE_PLAY_MEDIA,
    MEDIA_PLAYER_FEATURE_VOLUME_SET,
    MODEL_PREFIX_XIAOMI_AIRPURIFIER,
    SERVICE_FAN_SET_TARGET_HUMIDITY,
    STATE_NONE,
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
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(min=0, max=100, precision=1)

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
        """Return supporting range."""
        return RangeCapabilityRange(
            min=self._entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, self._default_range.min),
            max=self._entity_config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, self._default_range.max),
            precision=self._entity_config.get(CONF_ENTITY_RANGE, {}).get(
                CONF_ENTITY_RANGE_PRECISION, self._default_range.precision
            ),
        )

    def _convert_to_float(self, value: Any, strict: bool = True) -> float | None:
        """Return float of a value, ignore some states, catch errors."""
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            if strict:
                raise APIError(
                    ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                    f"Unsupported value {value!r} for instance {self.instance} of {self.device_id}",
                )

        return None


class StateRangeCapability(RangeCapability, StateCapability[RangeCapabilityInstanceActionState], Protocol):
    """Base class for a range capability based on the state."""

    def _get_absolute_value(self, relative_value: float) -> float:
        """Return the absolute value for a relative value."""
        value = self._get_value()

        if value is None:
            if self.state.state == STATE_OFF:
                raise APIError(ResponseCode.DEVICE_OFF, f"Device {self.state.entity_id} probably turned off")

            raise APIError(
                ResponseCode.INVALID_VALUE,
                f"Unable to get current value or {self.instance.value} instance of {self.device_id}",
            )

        return max(min(value + relative_value, self._range.max), self._range.min)


@STATE_CAPABILITIES_REGISTRY.register
class CoverPositionCapability(StateRangeCapability):
    """Capability to control position of a cover."""

    instance = RangeCapabilityInstance.OPEN

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == cover.DOMAIN and bool(self._state_features & cover.CoverEntityFeature.SET_POSITION)

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        return True

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            cover.DOMAIN,
            cover.SERVICE_SET_COVER_POSITION,
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


@STATE_CAPABILITIES_REGISTRY.register
class TemperatureCapabilityWaterHeater(TemperatureCapability):
    """Capability to control a water heater target temperature."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == water_heater.DOMAIN and bool(
            self._state_features & water_heater.WaterHeaterEntityFeature.TARGET_TEMPERATURE
        )

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            water_heater.DOMAIN,
            water_heater.SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: self.state.entity_id, water_heater.ATTR_TEMPERATURE: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(water_heater.ATTR_TEMPERATURE))

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(
            min=self.state.attributes.get(water_heater.ATTR_MIN_TEMP, 0),
            max=self.state.attributes.get(water_heater.ATTR_MAX_TEMP, 100),
            precision=0.5,
        )


@STATE_CAPABILITIES_REGISTRY.register
class TemperatureCapabilityClimate(TemperatureCapability):
    """Capability to control a climate device target temperature."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == climate.DOMAIN and bool(
            self._state_features & climate.ClimateEntityFeature.TARGET_TEMPERATURE
        )

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: self.state.entity_id, climate.ATTR_TEMPERATURE: self._get_service_call_value(state)},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        return self._convert_to_float(self.state.attributes.get(climate.ATTR_TEMPERATURE))

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
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


@STATE_CAPABILITIES_REGISTRY.register
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

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(
            min=self.state.attributes.get(humidifier.ATTR_MIN_HUMIDITY, 0),
            max=self.state.attributes.get(humidifier.ATTR_MAX_HUMIDITY, 100),
            precision=1,
        )


@STATE_CAPABILITIES_REGISTRY.register
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


@STATE_CAPABILITIES_REGISTRY.register
class BrightnessCapability(StateRangeCapability):
    """Capability to control brightness of a device."""

    instance = RangeCapabilityInstance.BRIGHTNESS

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == light.DOMAIN:
            if self._state_features & light.SUPPORT_BRIGHTNESS:
                return True

            if light.brightness_supported(self.state.attributes.get(light.ATTR_SUPPORTED_COLOR_MODES)):
                return True

        return False

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
            light.SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.state.entity_id, attribute: state.value},
            blocking=True,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if (brightness := self._convert_to_float(self.state.attributes.get(light.ATTR_BRIGHTNESS))) is not None:
            return int(100 * (brightness / 255))

        return None

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(
            min=1,
            max=100,
            precision=1,
        )


@STATE_CAPABILITIES_REGISTRY.register
class VolumeCapability(StateRangeCapability):
    """Capability to control volume of a device."""

    instance = RangeCapabilityInstance.VOLUME

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if self._state_features & media_player.MediaPlayerEntityFeature.VOLUME_STEP:
                return True

            if self._state_features & media_player.MediaPlayerEntityFeature.VOLUME_SET:
                return True

            if MEDIA_PLAYER_FEATURE_VOLUME_SET in self._entity_config.get(CONF_FEATURES, []):
                return True

        return False

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        if MEDIA_PLAYER_FEATURE_VOLUME_SET in self._entity_config.get(CONF_FEATURES, []):
            return True

        return not (
            self._state_features & media_player.MediaPlayerEntityFeature.VOLUME_STEP
            and not self._state_features & media_player.MediaPlayerEntityFeature.VOLUME_SET
        )

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if self.support_random_access:
            await self._hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_VOLUME_SET,
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
            raise APIError(ResponseCode.INVALID_VALUE, f"Failed to set absolute volume for {self.state.entity_id}")

        if state.value > 0:
            service = media_player.SERVICE_VOLUME_UP
        else:
            service = media_player.SERVICE_VOLUME_DOWN

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


@STATE_CAPABILITIES_REGISTRY.register
class ChannelCapability(StateRangeCapability):
    """Capability to control media playback state."""

    instance = RangeCapabilityInstance.CHANNEL

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if (
                self._state_features & media_player.MediaPlayerEntityFeature.PREVIOUS_TRACK
                and self._state_features & media_player.MediaPlayerEntityFeature.NEXT_TRACK
            ):
                return True

            if MEDIA_PLAYER_FEATURE_NEXT_PREVIOUS_TRACK in self._entity_config.get(CONF_FEATURES, []):
                return True

            if (
                self._state_features & media_player.MediaPlayerEntityFeature.PLAY_MEDIA
                or MEDIA_PLAYER_FEATURE_PLAY_MEDIA in self._entity_config.get(CONF_FEATURES, [])
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

        if device_class == media_player.MediaPlayerDeviceClass.TV:
            if (
                self._state_features & media_player.MediaPlayerEntityFeature.PLAY_MEDIA
                or MEDIA_PLAYER_FEATURE_PLAY_MEDIA in self._entity_config.get(CONF_FEATURES, [])
            ):
                return True

        return False

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        value = state.value

        if state.relative:
            if (
                self._state_features & media_player.MediaPlayerEntityFeature.PREVIOUS_TRACK
                and self._state_features & media_player.MediaPlayerEntityFeature.NEXT_TRACK
            ):
                if state.value >= 0:
                    service = media_player.SERVICE_MEDIA_NEXT_TRACK
                else:
                    service = media_player.SERVICE_MEDIA_PREVIOUS_TRACK

                await self._hass.services.async_call(
                    media_player.DOMAIN,
                    service,
                    {ATTR_ENTITY_ID: self.state.entity_id},
                    blocking=True,
                    context=context,
                )
                return

            if self.get_value() is None:
                raise APIError(
                    ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                    f"Failed to set relative value for {self.instance.value} instance of {self.state.entity_id}.",
                )
            else:
                value = self._get_absolute_value(state.value)

        try:
            await self._hass.services.async_call(
                media_player.DOMAIN,
                media_player.SERVICE_PLAY_MEDIA,
                {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    media_player.ATTR_MEDIA_CONTENT_ID: int(value),
                    media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
                },
                blocking=False,  # some tv's do it too slow
                context=context,
            )
        except ValueError as e:
            raise APIError(
                ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                f"Failed to set channel for {self.state.entity_id}. "
                f'Please change setting "support_set_channel" to "false" in entity_config '
                f"if the device does not support channel selection. Error: {e!r}",
            )

        return None

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        media_content_type = self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_TYPE)

        if media_content_type == media_player.const.MEDIA_TYPE_CHANNEL:
            return self._convert_to_float(self.state.attributes.get(media_player.ATTR_MEDIA_CONTENT_ID), strict=False)

        return None

    @property
    def _default_range(self) -> RangeCapabilityRange:
        """Return a default supporting range. Can be overrided by user."""
        return RangeCapabilityRange(
            min=0,
            max=999,
            precision=1,
        )
