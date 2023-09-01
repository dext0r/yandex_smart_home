"""Implement the Yandex Smart Home base capability."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Generic, TypeVar

from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import Context, HomeAssistant, State

from .helpers import Config
from .schema import (
    CapabilityDescription,
    CapabilityInstance,
    CapabilityInstanceActionResultValue,
    CapabilityInstanceActionState,
    CapabilityInstanceState,
    CapabilityInstanceStateValue,
    CapabilityParameters,
    CapabilityType,
)

_LOGGER = logging.getLogger(__name__)
_CapabilityT = TypeVar("_CapabilityT", bound="AbstractCapability")  # type: ignore[type-arg]

CAPABILITIES: list[type[AbstractCapability]] = []  # type: ignore[type-arg]


def register_capability(capability: type[_CapabilityT]) -> type[_CapabilityT]:
    """Decorate a function to register a capability."""
    CAPABILITIES.append(capability)
    return capability


class AbstractCapability(Generic[CapabilityInstanceActionState], ABC):
    """Represents a device base capability."""

    type: CapabilityType
    instance: CapabilityInstance

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a capability for a state."""
        self._hass = hass
        self._config = config
        self._entity_config = config.get_entity_config(state.entity_id)
        self._cache = config.cache

        self.state = state

    @property
    @abstractmethod
    def supported(self) -> bool:
        """Test if the capability is supported for its state."""
        pass

    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        return True

    @property
    def reportable(self) -> bool:
        """Test if the capability can report changes."""
        return self._config.is_reporting_state

    @property
    @abstractmethod
    def parameters(self) -> CapabilityParameters | None:
        """Return parameters for a devices list request."""
        return None

    def get_description(self) -> CapabilityDescription | None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return CapabilityDescription(
            type=self.type, retrievable=self.retrievable, reportable=self.reportable, parameters=self.parameters
        )

    @abstractmethod
    def get_value(self) -> Any:
        """Return the current capability value."""
        pass

    def get_instance_state(self) -> CapabilityInstanceState | None:
        """Return a state for a device query request."""
        if (value := self.get_value()) is not None and self.instance:
            return CapabilityInstanceState(
                type=self.type, state=CapabilityInstanceStateValue(instance=self.instance, value=value)
            )

        return None

    @abstractmethod
    async def set_instance_state(
        self, context: Context, state: CapabilityInstanceActionState
    ) -> CapabilityInstanceActionResultValue:
        """Change the capability state."""
        pass

    @property
    def _state_features(self) -> int:
        """Return features attribute for the state."""
        return int(self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0))


class ActionOnlyCapabilityMixin:
    """Represents a capability that only execute action."""

    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        return False

    @property
    def reportable(self) -> bool:
        """Test if the capability can report changes."""
        return False

    def get_value(self) -> None:
        """Return the state value of this capability for this entity."""
        return None
