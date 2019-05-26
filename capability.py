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
    STATE_OFF,
)
from homeassistant.core import DOMAIN as HA_DOMAIN

from .const import (
    ERR_INVALID_VALUE
)
from .error import SmartHomeError

_LOGGER = logging.getLogger(__name__)

PREFIX_CAPABILITIES = 'devices.capabilities.'
CAPABILITIES_ONOFF = PREFIX_CAPABILITIES + 'on_off'

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
            'type': 'devices.capabilities.on_off',
            'retrievable': True
        }

    def get_state(self):
        """Return the attributes of this capability for this entity."""
        return {
            'type': 'devices.capabilities.on_off',
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
