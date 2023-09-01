"""Schema for device property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/properties-types.html
"""
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel

from .property_event import EventPropertyInstance, EventPropertyParameters
from .property_float import FloatPropertyInstance, FloatPropertyParameters


class PropertyType(StrEnum):
    FLOAT = "devices.properties.float"
    EVENT = "devices.properties.event"


class FloatPropertyDescription(BaseModel):
    type: Literal[PropertyType.FLOAT] = PropertyType.FLOAT
    retrievable: bool
    reportable: bool
    parameters: FloatPropertyParameters


class EventPropertyDescription(BaseModel):
    type: Literal[PropertyType.EVENT] = PropertyType.EVENT
    retrievable: bool
    reportable: bool
    parameters: EventPropertyParameters  # type: ignore[type-arg]


PropertyDescription = FloatPropertyDescription | EventPropertyDescription
PropertyParameters = FloatPropertyParameters | EventPropertyParameters
PropertyInstance = FloatPropertyInstance | EventPropertyInstance


class PropertyInstanceStateValue(BaseModel):
    instance: PropertyInstance
    value: Any


class PropertyInstanceState(BaseModel):
    """Property state in query and callback requests."""

    type: PropertyType
    state: PropertyInstanceStateValue
