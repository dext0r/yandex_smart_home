"""Implement the Yandex Smart Home capabilities."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Type

from homeassistant.core import HomeAssistant, State

from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

PREFIX_CAPABILITIES = 'devices.capabilities.'

CAPABILITIES: list[Type[AbstractCapability]] = []


def register_capability(capability):
    """Decorate a function to register a capability."""
    CAPABILITIES.append(capability)
    return capability


class AbstractCapability(ABC):
    """Represents a Capability."""

    type = ''
    instance = ''
    retrievable = True

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        self.hass = hass
        self.state = state

        self.entity_config = config.get_entity_config(state.entity_id)
        self.reportable = config.is_reporting_state

        self._cache = config.cache

    @abstractmethod
    def supported(self) -> bool:
        """Test if capability is supported."""
        pass

    def description(self) -> dict[str, Any]:
        """Return description for a devices request."""
        response = {
            'type': self.type,
            'retrievable': self.retrievable,
            'reportable': self.reportable,
        }
        parameters = self.parameters()
        if parameters is not None:
            response['parameters'] = parameters

        return response

    def get_state(self) -> dict[str, Any]:
        """Return the state of this capability for this entity."""
        value = self.get_value()
        return {
            'type': self.type,
            'state':  {
                'instance': self.instance,
                'value': value
            }
        } if value is not None else None

    @abstractmethod
    def parameters(self) -> dict[str, Any] | None:
        """Return parameters for a devices request."""
        pass

    @abstractmethod
    def get_value(self) -> float | str | bool | None:
        """Return the state value of this capability for this entity."""
        pass

    @abstractmethod
    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        pass
