"""Implement the Yandex Smart Home toggles capabilities."""
from __future__ import annotations

from abc import ABC
import logging
from typing import Any

from homeassistant.components import cover, fan, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, SERVICE_VOLUME_MUTE

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import ERR_INVALID_VALUE, ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .helpers import RequestData

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

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN:
            if features & media_player.SUPPORT_VOLUME_MUTE:
                return True

        return False

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)

        return bool(muted)

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        if muted is None:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Device {self.state.entity_id} probably turned off'
            )

        await self.hass.services.async_call(
            self.state.domain,
            SERVICE_VOLUME_MUTE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_MEDIA_VOLUME_MUTED: state['value']
            },
            blocking=True,
            context=data.context
        )


@register_capability
class PauseCapability(ToggleCapability):
    """Pause and unpause functionality."""

    instance = const.TOGGLE_INSTANCE_PAUSE

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if self.state.domain == media_player.DOMAIN:
            if features & media_player.SUPPORT_PAUSE and features & media_player.SUPPORT_PLAY:
                return True

        elif self.state.domain == vacuum.DOMAIN:
            if features & vacuum.SUPPORT_PAUSE:
                return True

        elif self.state.domain == cover.DOMAIN:
            if features & cover.SUPPORT_STOP:
                return True

        return False

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        if self.state.domain == media_player.DOMAIN:
            return bool(self.state.state != media_player.STATE_PLAYING)
        elif self.state.domain == vacuum.DOMAIN:
            return self.state.state == vacuum.STATE_PAUSED
        elif self.state.domain == cover.DOMAIN:
            return False

        return False

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        if self.state.domain == media_player.DOMAIN:
            if state['value']:
                service = media_player.SERVICE_MEDIA_PAUSE
            else:
                service = media_player.SERVICE_MEDIA_PLAY
        elif self.state.domain == vacuum.DOMAIN:
            if state['value']:
                service = vacuum.SERVICE_PAUSE
            else:
                service = vacuum.SERVICE_START
        elif self.state.domain == cover.DOMAIN:
            service = cover.SERVICE_STOP_COVER
        else:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Unsupported domain for {self.instance} instance of {self.state.entity_id}'
            )

        await self.hass.services.async_call(
            self.state.domain,
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

        if self.state.domain == fan.DOMAIN:
            if features & fan.SUPPORT_OSCILLATE:
                return True

        return False

    def get_value(self) -> bool:
        """Return the state value of this capability for this entity."""
        return bool(self.state.attributes.get(fan.ATTR_OSCILLATING))

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        await self.hass.services.async_call(
            self.state.domain,
            fan.SERVICE_OSCILLATE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                fan.ATTR_OSCILLATING: state['value']
            },
            blocking=True,
            context=data.context
        )
