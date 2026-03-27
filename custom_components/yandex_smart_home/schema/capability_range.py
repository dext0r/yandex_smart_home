"""Schema for range capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range.html
"""

from enum import StrEnum
from typing import Any, Self

from pydantic import field_validator, model_validator

from .base import APIModel


class RangeCapabilityUnit(StrEnum):
    """Unit used in a range capability."""

    PERCENT = "unit.percent"
    TEMPERATURE_CELSIUS = "unit.temperature.celsius"


class RangeCapabilityInstance(StrEnum):
    """Instance of a range capability.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html
    """

    BRIGHTNESS = "brightness"
    CHANNEL = "channel"
    HUMIDITY = "humidity"
    OPEN = "open"
    TEMPERATURE = "temperature"
    VOLUME = "volume"


class RangeCapabilityRange(APIModel):
    """Value range of a range capability."""

    min: float
    max: float
    precision: float

    def __str__(self) -> str:
        return f"[{self.min}, {self.max}]"


class RangeCapabilityParameters(APIModel):
    """Parameters of a range capability."""

    instance: RangeCapabilityInstance
    unit: RangeCapabilityUnit | None = None
    random_access: bool
    range: RangeCapabilityRange | None = None

    @model_validator(mode="after")
    def compute_unit(self) -> Self:
        """Return value unit for a capability instance."""
        match self.instance:
            case RangeCapabilityInstance.BRIGHTNESS:
                self.unit = RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.HUMIDITY:
                self.unit = RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.OPEN:
                self.unit = RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.TEMPERATURE:
                self.unit = RangeCapabilityUnit.TEMPERATURE_CELSIUS

        return self

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        """Force range boundaries for a capability instance."""

        if self.range:
            match self.instance:
                case RangeCapabilityInstance.HUMIDITY | RangeCapabilityInstance.OPEN:
                    self.range.min, self.range.max = max([0.0, self.range.min]), min([100.0, self.range.max])
                case RangeCapabilityInstance.BRIGHTNESS:
                    self.range.min = max(min(self.range.min, 1.0), 0.0)
                    self.range.max = 100.0
                    self.range.precision = 1.0
        elif self.instance in (
            RangeCapabilityInstance.BRIGHTNESS,
            RangeCapabilityInstance.HUMIDITY,
            RangeCapabilityInstance.OPEN,
            RangeCapabilityInstance.TEMPERATURE,
        ):
            raise ValueError(f"range field required for {self.instance}")

        return self


class RangeCapabilityInstanceActionState(APIModel):
    """New value for a range capability."""

    instance: RangeCapabilityInstance
    value: float
    relative: bool = False

    @field_validator("relative", mode="before")
    def set_relative(cls, v: Any) -> Any:  # noqa: N805
        """Update relative value."""
        if v is None:  # VK
            return False

        return v
