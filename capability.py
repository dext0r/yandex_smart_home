"""Implement the Google Smart Home traits."""
import logging

from homeassistant.components import (
    group,
    fan,
    input_boolean,
    media_player,
    light,
    switch,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_MUTE,
    STATE_OFF,
)
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_VOLUME_MUTED
)
from homeassistant.core import DOMAIN as HA_DOMAIN

from .const import (
    ERR_INVALID_VALUE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE
)
from .error import SmartHomeError

_LOGGER = logging.getLogger(__name__)

PREFIX_CAPABILITIES = 'devices.capabilities.'
CAPABILITIES_ONOFF = PREFIX_CAPABILITIES + 'on_off'
CAPABILITIES_TOGGLE = PREFIX_CAPABILITIES + 'toggle'

CAPABILITIES = []

def register_capability (capability):
    """Decorate a function to register a capability."""
    CAPABILITIES.append(capability)
    return capability

class _Capability:
    """Represents a Capability."""

    def __init__(self, hass, state, config):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state
        self.config = config

    def description(self):
        """Return description for a devices request."""
        raise NotImplementedError

    def get_state(self):
        """Return the state of this trait for this entity."""
        raise NotImplementedError

    async def set_state(self, data, params):
        """Execute a command."""
        raise NotImplementedError

@register_capability
class OnOffCapability(_Capability):
    """On_off to offer basic on and off functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/on_off-docpage/
    """

    type = CAPABILITIES_ONOFF

    @staticmethod
    def supported(domain, features, device_class):
        """Test if state is supported."""
        return domain in (
            group.DOMAIN,
            input_boolean.DOMAIN,
            switch.DOMAIN,
            fan.DOMAIN,
            light.DOMAIN,
            media_player.DOMAIN,
        )

    def description(self):
        """Return description for a devices request."""
        return {
            'type': CAPABILITIES_ONOFF,
            'retrievable': True
        }

    def get_state(self):
        """Return the attributes of this capability for this entity."""
        return {
            'type': CAPABILITIES_ONOFF,
            'state': {
                "instance": "on",
                "value": self.state.state != STATE_OFF
            }
        }

    async def set_state(self, data, state):
        """Set state."""
        domain = self.state.domain

        if type(state['value']) is not bool:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                'Value is not boolean')

        if domain == group.DOMAIN:
            service_domain = HA_DOMAIN
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF

        else:
            service_domain = domain
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF

        await self.hass.services.async_call(service_domain, service, {
            ATTR_ENTITY_ID: self.state.entity_id
        }, blocking=True, context=data.context)

@register_capability
class ToggleCapability(_Capability):
    """Toggle to offer mute and unmute functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/toggle-docpage/
    """

    type = CAPABILITIES_TOGGLE

    @staticmethod
    def supported(domain, features, device_class):
        """Test if state is supported."""
        return domain in (
            media_player.DOMAIN,
        )

    def description(self):
        """Return description for a devices request."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        return {
            'type': CAPABILITIES_TOGGLE,
            'retrievable': True,
            'parameters': {
                'instance': 'mute'
            }
        }

    def get_state(self):
        """Return the attributes of this capability for this entity."""
        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        return {
            'type': CAPABILITIES_TOGGLE,
            'state': {
                "instance": "mute",
                "value": bool(muted)
            }
        }

    async def set_state(self, data, state):
        """Set state."""
        if type(state['value']) is not bool:
            raise SmartHomeError(ERR_INVALID_VALUE, 'Value is not boolean')

        muted = self.state.attributes.get(media_player.ATTR_MEDIA_VOLUME_MUTED)
        if muted is None:
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                                 "Device probably turned off")

        await self.hass.services.async_call(
            self.state.domain,
            SERVICE_VOLUME_MUTE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                ATTR_MEDIA_VOLUME_MUTED: state['value']
            }, blocking=True, context=data.context)
