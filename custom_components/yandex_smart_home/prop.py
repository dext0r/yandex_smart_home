"""Implement the Yandex Smart Home properties."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Type

from homeassistant.core import HomeAssistant, State

from .helpers import Config

_LOGGER = logging.getLogger(__name__)

PREFIX_PROPERTIES = 'devices.properties.'
PROPERTIES: list[Type[AbstractProperty]] = []


def register_property(prop):
    """Decorate a function to register a property."""
    PROPERTIES.append(prop)
    return prop


class AbstractProperty(ABC):
    """Represents a Property."""

    type = ''
    instance = ''
    values = []
    retrievable = True

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        self.hass = hass
        self.config = config
        self.state = state

        self.reportable = config.is_reporting_state

    @abstractmethod
    def supported(self) -> bool:
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
        """Return the state of this property for this entity."""
        value = self.get_value()
        return {
            'type': self.type,
            'state': {
                'instance': self.instance,
                'value': value
            }
        } if value is not None else None

    @abstractmethod
    def parameters(self) -> dict[str, Any] | None:
        """Return parameters for a devices request."""
        pass

    @abstractmethod
    def get_value(self) -> str | float | None:
        """Return the state value of this capability for this entity."""
        pass
