"""Schema for device property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/properties-types.html
"""
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel

from .property_event import EventPropertyInstance, EventPropertyParameters
from .property_float import FloatPropertyInstance, FloatPropertyParameters


class PropertyType(StrEnum):
    """Property type."""

    FLOAT = "devices.properties.float"
    EVENT = "devices.properties.event"


class FloatPropertyDescription(BaseModel):
    """Description of a float property for a device list request."""

    type: Literal[PropertyType.FLOAT] = PropertyType.FLOAT
    retrievable: bool
    reportable: bool
    parameters: FloatPropertyParameters


class EventPropertyDescription(BaseModel):
    """Description of an event property for a device list request."""

    type: Literal[PropertyType.EVENT] = PropertyType.EVENT
    retrievable: bool
    reportable: bool
    parameters: EventPropertyParameters[Any]


PropertyDescription = FloatPropertyDescription | EventPropertyDescription
"""Description of a property for a device list request."""

PropertyParameters = FloatPropertyParameters | EventPropertyParameters
"""Parameters of a property for a device list request."""

PropertyInstance = FloatPropertyInstance | EventPropertyInstance
"""All property instances."""


class PropertyInstanceStateValue(BaseModel):
    """Property instance value."""

    instance: PropertyInstance
    value: Any


class PropertyInstanceState(BaseModel):
    """Property state for state query and callback requests."""

    type: PropertyType
    state: PropertyInstanceStateValue
