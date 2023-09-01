"""Schema for event property.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event.html
"""
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import validator
from pydantic.generics import GenericModel


class EventPropertyInstance(StrEnum):
    """# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html"""

    VIBRATION = "vibration"
    OPEN = "open"
    BUTTON = "button"
    MOTION = "motion"
    SMOKE = "smoke"
    GAS = "gas"
    BATTERY_LEVEL = "battery_level"
    # TODO: FOOD_LEVEL = "food_level"
    WATER_LEVEL = "water_level"
    WATER_LEAK = "water_leak"


class VibrationInstanceEvent(StrEnum):
    TILT = "tilt"
    FALL = "fall"
    VIBRATION = "vibration"


class OpenInstanceEvent(StrEnum):
    OPENED = "opened"
    CLOSED = "closed"


class ButtonInstanceEvent(StrEnum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    LONG_PRESS = "long_press"


class MotionInstanceEvent(StrEnum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"


class SmokeInstanceEvent(StrEnum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    HIGH = "high"


class GasInstanceEvent(StrEnum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    HIGH = "high"


class BatteryLevelInstanceEvent(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class FoodLevelInstanceEvent(StrEnum):
    EMPTY = "empty"
    LOW = "low"
    NORMAL = "normal"


class WaterLevelInstanceEvent(StrEnum):
    EMPTY = "empty"
    LOW = "low"
    NORMAL = "normal"


class WaterLeakInstanceEvent(StrEnum):
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


class EventPropertyParameters(GenericModel, Generic[EventInstanceEvent]):
    instance: EventPropertyInstance
    events: list[dict[Literal["value"], EventInstanceEvent]] = []

    @validator("events", pre=True, always=True)
    def set_events(cls, v: Any) -> Any:
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


# TODO
# class FoodLevelEventPropertyParameters(EventPropertyParameters[FoodLevelInstanceEvent]):
#     instance: Literal[EventPropertyInstance.FOOD_LEVEL] = EventPropertyInstance.FOOD_LEVEL


class WaterLevelEventPropertyParameters(EventPropertyParameters[WaterLevelInstanceEvent]):
    instance: Literal[EventPropertyInstance.WATER_LEVEL] = EventPropertyInstance.WATER_LEVEL


class WaterLeakEventPropertyParameters(EventPropertyParameters[WaterLeakInstanceEvent]):
    instance: Literal[EventPropertyInstance.WATER_LEAK] = EventPropertyInstance.WATER_LEAK
