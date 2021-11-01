"""Implement the Yandex Smart Home toggles capabilities."""
from __future__ import annotations

from abc import ABC
import logging
from typing import Any

from homeassistant.components import cover, fan, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, State

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_TOGGLE = PREFIX_CAPABILITIES + 'toggle'


class ToggleCapability(AbstractCapability, ABC):
    """Base toggle functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/toggle-docpage/
    """

    type = CAPABILITIES_TOGGLE

    def parameters(self) -> dict[str, Any]:
        """Return parameters for a devices request."""
        return {
            'instance': self.instance
        }


@register_capability
class MuteCapability(ToggleCapability):
    """Mute and unmute functionality."""

    instance = const.TOGGLE_INSTANCE_MUTE

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)

        self.retrievable = media_player.ATTR_MEDIA_VOLUME_MUTED in self.state.attributes

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN:
            if features & media_player.SUPPORT_VOLUME_MUTE:
                return True

            if const.MEDIA_PLAYER_FEATURE_VOLUME_MUTE in self.entity_config.get(const.CONF_FEATURES, []):
                return True

        return False

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)

        return bool(muted)

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_VOLUME_MUTE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_MEDIA_VOLUME_MUTED: state['value']
            },
            blocking=True,
            context=data.context
        )


class PauseCapability(ToggleCapability, ABC):
    """Pause and unpause functionality."""

    instance = const.TOGGLE_INSTANCE_PAUSE


@register_capability
class PauseCapabilityMediaPlayer(PauseCapability):
    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_PAUSE and features & media_player.SUPPORT_PLAY

        return False

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        return bool(self.state.state != media_player.STATE_PLAYING)

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        if state['value']:
            service = media_player.SERVICE_MEDIA_PAUSE
        else:
            service = media_player.SERVICE_MEDIA_PLAY

        await self.hass.services.async_call(
            media_player.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class PauseCapabilityCover(PauseCapability):
    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        return self.state.domain == cover.DOMAIN and features & cover.SUPPORT_STOP

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        return False

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            cover.DOMAIN,
            cover.SERVICE_STOP_COVER, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class PauseCapabilityVacuum(PauseCapability):
    instance = const.TOGGLE_INSTANCE_PAUSE

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        return self.state.domain == vacuum.DOMAIN and features & vacuum.SUPPORT_PAUSE

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        return self.state.state == vacuum.STATE_PAUSED

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        if state['value']:
            service = vacuum.SERVICE_PAUSE
        else:
            service = vacuum.SERVICE_START

        await self.hass.services.async_call(
            vacuum.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OscillationCapability(ToggleCapability):
    """Oscillation functionality."""

    instance = const.TOGGLE_INSTANCE_OSCILLATION

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        return self.state.domain == fan.DOMAIN and features & fan.SUPPORT_OSCILLATE

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        return bool(self.state.attributes.get(fan.ATTR_OSCILLATING))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_OSCILLATE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                fan.ATTR_OSCILLATING: state['value']
            },
            blocking=True,
            context=data.context
        )
