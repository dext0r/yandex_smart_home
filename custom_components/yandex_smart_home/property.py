"""Implement the Yandex Smart Home base device property."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, Self, runtime_checkable

from homeassistant.core import HomeAssistant, State
from homeassistant.const import ATTR_DEVICE_CLASS

from .helpers import ListRegistry
from .schema import (
    PropertyDescription,
    PropertyInstance,
    PropertyInstanceState,
    PropertyInstanceStateValue,
    PropertyParameters,
    PropertyType,
)

if TYPE_CHECKING:
    from .entry_data import ConfigEntryData


@runtime_checkable
class Property(Protocol):
    """Base class for a device property."""

    device_id: str
    type: PropertyType
    instance: PropertyInstance

    _hass: HomeAssistant
    _entry_data: ConfigEntryData

    @property
    @abstractmethod
    def supported(self) -> bool:
        """Test if the property is supported."""
        ...

    @property
    def retrievable(self) -> bool:
        """Test if the property can return the current value."""
        return True

    @property
    def reportable(self) -> bool:
        """Test if the property can report value changes."""
        return self._entry_data.is_reporting_states

    @property
    def report_on_startup(self) -> bool:
        """Test if property value should be reported on startup."""
        return True

    @property
    def time_sensitive(self) -> bool:
        """Test if value changes should be reported immediately."""
        return False

    @property
    @abstractmethod
    def parameters(self) -> PropertyParameters:
        """Return parameters for a devices list request."""
        ...

    @abstractmethod
    def get_description(self) -> PropertyDescription:
        """Return a description for a device list request."""
        ...

    @abstractmethod
    def get_value(self) -> Any:
        """Return the current property value."""
        ...

    def get_instance_state(self) -> PropertyInstanceState | None:
        """Return a state for a state query request."""
        if (value := self.get_value()) is not None:
            return PropertyInstanceState(
                type=self.type, state=PropertyInstanceStateValue(instance=self.instance, value=value)
            )

        return None

    @abstractmethod
    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        ...

    def __str__(self) -> str:
        """Return string representation."""
        return f"instance {self.instance} of {self.type.short} property of {self.device_id}"

    def __repr__(self) -> str:
        """Return the representation."""
        return (
            f"<{self.__class__.__name__}"
            f" device_id={self.device_id }"
            f" type={self.type}"
            f" instance={self.instance}"
            f">"
        )

    def __eq__(self, other: Any) -> bool:
        """Compare properties."""
        return bool(
            isinstance(other, Property)
            and self.type == other.type
            and self.instance == other.instance
            and self.device_id == other.device_id
        )


@runtime_checkable
class StateProperty(Property, Protocol):
    """Base class for a device property based on the state."""

    state: State

    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData, state: State):
        """Initialize a property for the state."""
        self._hass = hass
        self._entry_data = entry_data

        self.state = state
        self.device_id = state.entity_id

    @property
    def _state_device_class(self) -> str | None:
        """Return state device class."""
        return self.state.attributes.get(ATTR_DEVICE_CLASS)


STATE_PROPERTIES_REGISTRY = ListRegistry[type[StateProperty]]()
