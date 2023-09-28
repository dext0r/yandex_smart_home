"""Implement the Yandex Smart Home base device capability."""
from abc import abstractmethod
from functools import cached_property
from typing import Any, Protocol

from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import Context, HomeAssistant, State

from .helpers import CacheStore, Config, ListRegistry
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


class Capability(Protocol[CapabilityInstanceActionState]):
    """Base class for a device capability."""

    device_id: str
    type: CapabilityType
    instance: CapabilityInstance

    _hass: HomeAssistant
    _config: Config

    @property
    @abstractmethod
    def supported(self) -> bool:
        """Test if the capability is supported."""
        ...

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
        ...

    def get_description(self) -> CapabilityDescription | None:
        """Return a description for a device list request. Capability with an empty description isn't discoverable."""
        return CapabilityDescription(
            type=self.type, retrievable=self.retrievable, reportable=self.reportable, parameters=self.parameters
        )

    @abstractmethod
    def get_value(self) -> Any:
        """Return the current capability value."""
        ...

    def get_instance_state(self) -> CapabilityInstanceState | None:
        """Return a state for a state query request."""
        if (value := self.get_value()) is not None:
            return CapabilityInstanceState(
                type=self.type, state=CapabilityInstanceStateValue(instance=self.instance, value=value)
            )

        return None

    @abstractmethod
    async def set_instance_state(
        self, context: Context, state: CapabilityInstanceActionState
    ) -> CapabilityInstanceActionResultValue:
        """Change the capability state."""
        ...

    @cached_property
    def _entity_config(self) -> dict[str, Any]:
        """Return additional configuration for the device."""
        return self._config.get_entity_config(self.device_id)


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

    # noinspection PyMethodMayBeStatic
    def get_value(self) -> None:
        """Return the state value of this capability for this entity."""
        return None


class StateCapability(Capability[CapabilityInstanceActionState], Protocol):
    """Base class for a device capability based on the state."""

    state: State

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a capability for the state."""
        self._hass = hass
        self._config = config

        self.device_id = state.entity_id
        self.state = state

    @property
    def _state_features(self) -> int:
        """Return supported features for the state."""
        return int(self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0))

    @property
    def _cache(self) -> CacheStore:
        """Return cache storage."""
        return self._config.cache


STATE_CAPABILITIES_REGISTRY = ListRegistry[type[StateCapability[Any]]]()
