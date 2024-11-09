"""Implement the Yandex Smart Home toggle capabilities."""

from typing import Protocol

from homeassistant.components import cover, fan, media_player, vacuum
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.fan import FanEntityFeature
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.components.vacuum import VacuumEntityFeature
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_STOP_COVER,
    SERVICE_VOLUME_MUTE,
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.core import Context

from .capability import STATE_CAPABILITIES_REGISTRY, ActionOnlyCapabilityMixin, Capability, StateCapability
from .const import CONF_FEATURES, MediaPlayerFeature
from .schema import (
    CapabilityType,
    ToggleCapabilityInstance,
    ToggleCapabilityInstanceActionState,
    ToggleCapabilityParameters,
)


class ToggleCapability(Capability[ToggleCapabilityInstanceActionState], Protocol):
    """Base class for capabilities with toggle functions like mute or pause.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/toggle-docpage/
    """

    type: CapabilityType = CapabilityType.TOGGLE
    instance: ToggleCapabilityInstance

    @property
    def parameters(self) -> ToggleCapabilityParameters:
        """Return parameters for a devices list request."""
        return ToggleCapabilityParameters(instance=self.instance)


class StateToggleCapability(ToggleCapability, StateCapability[ToggleCapabilityInstanceActionState], Protocol):
    """Base class for a toggle capability based on the state."""

    pass


class MuteCapability(StateToggleCapability):
    """Capability to mute and unmute device."""

    instance = ToggleCapabilityInstance.MUTE

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if self._state_features & MediaPlayerEntityFeature.VOLUME_MUTE:
                return True

            if MediaPlayerFeature.VOLUME_MUTE in self._entity_config.get(CONF_FEATURES, []):
                return True

        return False

    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        return media_player.ATTR_MEDIA_VOLUME_MUTED in self.state.attributes

    def get_value(self) -> bool:
        """Return the current capability value."""
        return bool(self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED))

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            media_player.DOMAIN,
            SERVICE_VOLUME_MUTE,
            {ATTR_ENTITY_ID: self.state.entity_id, media_player.ATTR_MEDIA_VOLUME_MUTED: state.value},
            blocking=True,
            context=context,
        )


class PauseCapabilityMediaPlayer(StateToggleCapability):
    """Capability to pause and resume media player playback."""

    instance = ToggleCapabilityInstance.PAUSE

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if MediaPlayerFeature.PLAY_PAUSE in self._entity_config.get(CONF_FEATURES, []):
                return True

            if (
                self._state_features & MediaPlayerEntityFeature.PAUSE
                and self._state_features & MediaPlayerEntityFeature.PLAY
            ):
                return True

        return False

    def get_value(self) -> bool:
        """Return the current capability value."""
        return bool(self.state.state != STATE_PLAYING)

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if state.value:
            service = SERVICE_MEDIA_PAUSE
        else:
            service = SERVICE_MEDIA_PLAY

        await self._hass.services.async_call(
            media_player.DOMAIN, service, {ATTR_ENTITY_ID: self.state.entity_id}, blocking=True, context=context
        )


class PauseCapabilityCover(ActionOnlyCapabilityMixin, StateToggleCapability):
    """Capability to stop a cover."""

    instance = ToggleCapabilityInstance.PAUSE

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == cover.DOMAIN and bool(self._state_features & CoverEntityFeature.STOP)

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            cover.DOMAIN,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: self.state.entity_id},
            blocking=True,
            context=context,
        )


class PauseCapabilityVacuum(StateToggleCapability):
    """Capability to stop a vacuum."""

    instance = ToggleCapabilityInstance.PAUSE

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == vacuum.DOMAIN and bool(self._state_features & VacuumEntityFeature.PAUSE)

    def get_value(self) -> bool:
        """Return the current capability value."""
        return self.state.state == STATE_PAUSED

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if state.value:
            service = vacuum.SERVICE_PAUSE
        else:
            service = vacuum.SERVICE_START

        await self._hass.services.async_call(
            vacuum.DOMAIN, service, {ATTR_ENTITY_ID: self.state.entity_id}, blocking=True, context=context
        )


class OscillationCapability(StateToggleCapability):
    """Capability to control fan oscillation."""

    instance = ToggleCapabilityInstance.OSCILLATION

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == fan.DOMAIN and bool(self._state_features & FanEntityFeature.OSCILLATE)

    def get_value(self) -> bool:
        """Return the current capability value."""
        return bool(self.state.attributes.get(fan.ATTR_OSCILLATING))

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_OSCILLATE,
            {ATTR_ENTITY_ID: self.state.entity_id, fan.ATTR_OSCILLATING: state.value},
            blocking=True,
            context=context,
        )


STATE_CAPABILITIES_REGISTRY.register(MuteCapability)
STATE_CAPABILITIES_REGISTRY.register(PauseCapabilityMediaPlayer)
STATE_CAPABILITIES_REGISTRY.register(PauseCapabilityCover)
STATE_CAPABILITIES_REGISTRY.register(PauseCapabilityVacuum)
STATE_CAPABILITIES_REGISTRY.register(OscillationCapability)
