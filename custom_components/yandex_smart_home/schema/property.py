"""Schema for device property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/properties-types.html
"""

from enum import StrEnum
from typing import Any, Literal

from .base import APIModel
from .property_event import EventPropertyInstance, EventPropertyParameters
from .property_float import FloatPropertyInstance, FloatPropertyParameters


class PropertyType(StrEnum):
    """Property type."""

    FLOAT = "devices.properties.float"
    EVENT = "devices.properties.event"

    @property
    def short(self) -> str:
        """Return short version of the property type."""
        return str(self).replace("devices.properties.", "")


class FloatPropertyDescription(APIModel):
    """Description of a float property for a device list request."""

    type: Literal[PropertyType.FLOAT] = PropertyType.FLOAT
    retrievable: bool
    reportable: bool
    parameters: FloatPropertyParameters


class EventPropertyDescription(APIModel):
    """Description of an event property for a device list request."""

    type: Literal[PropertyType.EVENT] = PropertyType.EVENT
    retrievable: bool
    reportable: bool
    parameters: EventPropertyParameters[Any]


PropertyDescription = FloatPropertyDescription | EventPropertyDescription
"""Description of a property for a device list request."""

PropertyParameters = FloatPropertyParameters | EventPropertyParameters[Any]
"""Parameters of a property for a device list request."""

PropertyInstance = FloatPropertyInstance | EventPropertyInstance
"""All property instances."""


class PropertyInstanceStateValue(APIModel):
    """Property instance value."""

    instance: PropertyInstance
    value: Any


class PropertyInstanceState(APIModel):
    """Property state for state query and callback requests."""

    type: PropertyType
    state: PropertyInstanceStateValue
