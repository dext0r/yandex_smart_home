"""Schema for event property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event.html
"""
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import validator

from .base import GenericAPIModel


class EventPropertyInstance(StrEnum):
    """Instance of an event property.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html
    """

    VIBRATION = "vibration"
    OPEN = "open"
    BUTTON = "button"
    MOTION = "motion"
    SMOKE = "smoke"
    GAS = "gas"
    BATTERY_LEVEL = "battery_level"
    FOOD_LEVEL = "food_level"
    WATER_LEVEL = "water_level"
    WATER_LEAK = "water_leak"


class VibrationInstanceEvent(StrEnum):
    """Event of a vibration instance."""

    TILT = "tilt"
    FALL = "fall"
    VIBRATION = "vibration"


class OpenInstanceEvent(StrEnum):
    """Event of a open instance."""

    OPENED = "opened"
    CLOSED = "closed"


class ButtonInstanceEvent(StrEnum):
    """Event of a button instance."""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    LONG_PRESS = "long_press"


class MotionInstanceEvent(StrEnum):
    """Event of a motion instance."""

    DETECTED = "detected"
    NOT_DETECTED = "not_detected"


class SmokeInstanceEvent(StrEnum):
    """Event of a smoke instance."""

    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    HIGH = "high"


class GasInstanceEvent(StrEnum):
    """Event of a gas instance."""

    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    HIGH = "high"


class BatteryLevelInstanceEvent(StrEnum):
    """Event of a battery_level instance."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class FoodLevelInstanceEvent(StrEnum):
    """Event of a food_level instance."""

    EMPTY = "empty"
    LOW = "low"
    NORMAL = "normal"


class WaterLevelInstanceEvent(StrEnum):
    """Event of a water_level instance."""

    EMPTY = "empty"
    LOW = "low"
    NORMAL = "normal"


class WaterLeakInstanceEvent(StrEnum):
    """Event of a water_leak instance."""

    DRY = "dry"
    LEAK = "leak"


EventInstanceEvent = TypeVar(
    "EventInstanceEvent",
    VibrationInstanceEvent,
    OpenInstanceEvent,
    ButtonInstanceEvent,
    MotionInstanceEvent,
    SmokeInstanceEvent,
    GasInstanceEvent,
    BatteryLevelInstanceEvent,
    FoodLevelInstanceEvent,
    WaterLevelInstanceEvent,
    WaterLeakInstanceEvent,
)
"""All events of event instances."""


class EventPropertyParameters(GenericAPIModel, Generic[EventInstanceEvent]):
    """Parameters of an event property."""

    instance: EventPropertyInstance
    events: list[dict[Literal["value"], EventInstanceEvent]] = []

    @validator("events", pre=True, always=True)
    def set_events(cls, v: Any) -> Any:
        """Update events list value."""
        if not v:
            instance_event: type[EventInstanceEvent] = cls.__fields__["events"].type_.__args__[1]
            return [{"value": m} for m in instance_event.__members__.values()]

        return v  # pragma: nocover


class VibrationEventPropertyParameters(EventPropertyParameters[VibrationInstanceEvent]):
    instance: Literal[EventPropertyInstance.VIBRATION] = EventPropertyInstance.VIBRATION


class OpenEventPropertyParameters(EventPropertyParameters[OpenInstanceEvent]):
    instance: Literal[EventPropertyInstance.OPEN] = EventPropertyInstance.OPEN


class ButtonEventPropertyParameters(EventPropertyParameters[ButtonInstanceEvent]):
    instance: Literal[EventPropertyInstance.BUTTON] = EventPropertyInstance.BUTTON


class MotionEventPropertyParameters(EventPropertyParameters[MotionInstanceEvent]):
    instance: Literal[EventPropertyInstance.MOTION] = EventPropertyInstance.MOTION


class SmokeEventPropertyParameters(EventPropertyParameters[SmokeInstanceEvent]):
    instance: Literal[EventPropertyInstance.SMOKE] = EventPropertyInstance.SMOKE


class GasEventPropertyParameters(EventPropertyParameters[GasInstanceEvent]):
    instance: Literal[EventPropertyInstance.GAS] = EventPropertyInstance.GAS


class BatteryLevelEventPropertyParameters(EventPropertyParameters[BatteryLevelInstanceEvent]):
    instance: Literal[EventPropertyInstance.BATTERY_LEVEL] = EventPropertyInstance.BATTERY_LEVEL


class FoodLevelEventPropertyParameters(EventPropertyParameters[FoodLevelInstanceEvent]):
    instance: Literal[EventPropertyInstance.FOOD_LEVEL] = EventPropertyInstance.FOOD_LEVEL


class WaterLevelEventPropertyParameters(EventPropertyParameters[WaterLevelInstanceEvent]):
    instance: Literal[EventPropertyInstance.WATER_LEVEL] = EventPropertyInstance.WATER_LEVEL


class WaterLeakEventPropertyParameters(EventPropertyParameters[WaterLeakInstanceEvent]):
    instance: Literal[EventPropertyInstance.WATER_LEAK] = EventPropertyInstance.WATER_LEAK
