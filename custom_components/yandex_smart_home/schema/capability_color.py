"""Schema for color_setting capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html
"""

from enum import StrEnum
from typing import Annotated, Any, Literal, Self, Union

from pydantic.v1 import Field, root_validator

from .base import APIModel


class ColorSettingCapabilityInstance(StrEnum):
    """Instance of a color_setting capability."""

    BASE = "base"
    RGB = "rgb"
    HSV = "hsv"
    TEMPERATURE_K = "temperature_k"
    SCENE = "scene"


class ColorScene(StrEnum):
    """Color scene."""

    ALARM = "alarm"
    ALICE = "alice"
    CANDLE = "candle"
    DINNER = "dinner"
    FANTASY = "fantasy"
    GARLAND = "garland"
    JUNGLE = "jungle"
    MOVIE = "movie"
    NEON = "neon"
    NIGHT = "night"
    OCEAN = "ocean"
    PARTY = "party"
    READING = "reading"
    REST = "rest"
    ROMANCE = "romance"
    SIREN = "siren"
    SUNRISE = "sunrise"
    SUNSET = "sunset"


class CapabilityParameterColorModel(StrEnum):
    """Color model."""

    RGB = "rgb"
    HSV = "hsv"


class CapabilityParameterTemperatureK(APIModel):
    """Color temperature range."""

    min: int
    max: int


class CapabilityParameterColorScene(APIModel):
    """Parameter of a scene instance."""

    scenes: list[dict[Literal["id"], ColorScene]]

    @classmethod
    def from_list(cls, scenes: list[ColorScene]) -> Self:
        return cls(scenes=[{"id": s} for s in scenes])


class ColorSettingCapabilityParameters(APIModel):
    """Parameters of a color_setting capability."""

    color_model: CapabilityParameterColorModel | None = None
    temperature_k: CapabilityParameterTemperatureK | None = None
    color_scene: CapabilityParameterColorScene | None = None

    @root_validator
    def any_of(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not any(values.values()):
            raise ValueError("one of color_model, temperature_k or color_scene must have a value")

        return values


class RGBInstanceActionState(APIModel):
    """New value for a rgb instance."""

    instance: Literal[ColorSettingCapabilityInstance.RGB] = ColorSettingCapabilityInstance.RGB
    value: int


class TemperatureKInstanceActionState(APIModel):
    """New value for a temperature_k instance."""

    instance: Literal[ColorSettingCapabilityInstance.TEMPERATURE_K] = ColorSettingCapabilityInstance.TEMPERATURE_K
    value: int


class SceneInstanceActionState(APIModel):
    """New value for a scene instance."""

    instance: Literal[ColorSettingCapabilityInstance.SCENE] = ColorSettingCapabilityInstance.SCENE
    value: ColorScene


ColorSettingCapabilityInstanceActionState = Annotated[
    Union[RGBInstanceActionState, TemperatureKInstanceActionState, SceneInstanceActionState],
    Field(discriminator="instance"),
]
"""New value for an instance of color_setting capability."""
