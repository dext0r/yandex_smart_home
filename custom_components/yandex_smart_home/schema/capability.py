"""Schema for device capabilities."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field

from .base import APIModel
from .capability_color import (
    ColorSettingCapabilityInstance,
    ColorSettingCapabilityInstanceActionState,
    ColorSettingCapabilityParameters,
    RGBInstanceActionState,
    SceneInstanceActionState,
    TemperatureKInstanceActionState,
)
from .capability_mode import ModeCapabilityInstance, ModeCapabilityInstanceActionState, ModeCapabilityParameters
from .capability_onoff import OnOffCapabilityInstance, OnOffCapabilityInstanceActionState, OnOffCapabilityParameters
from .capability_range import RangeCapabilityInstance, RangeCapabilityInstanceActionState, RangeCapabilityParameters
from .capability_toggle import ToggleCapabilityInstance, ToggleCapabilityInstanceActionState, ToggleCapabilityParameters
from .capability_video import (
    GetStreamInstanceActionResultValue,
    GetStreamInstanceActionState,
    VideoStreamCapabilityInstance,
    VideoStreamCapabilityParameters,
)


class CapabilityType(StrEnum):
    ON_OFF = "devices.capabilities.on_off"
    COLOR_SETTING = "devices.capabilities.color_setting"
    MODE = "devices.capabilities.mode"
    RANGE = "devices.capabilities.range"
    TOGGLE = "devices.capabilities.toggle"
    VIDEO_STREAM = "devices.capabilities.video_stream"

    @property
    def short(self) -> str:
        return str(self).replace("devices.capabilities.", "")


CapabilityParameters = Union[
    OnOffCapabilityParameters,
    ColorSettingCapabilityParameters,
    ModeCapabilityParameters,
    RangeCapabilityParameters,
    ToggleCapabilityParameters,
    VideoStreamCapabilityParameters,
]


CapabilityInstance = Union[
    OnOffCapabilityInstance,
    ColorSettingCapabilityInstance,
    ModeCapabilityInstance,
    RangeCapabilityInstance,
    ToggleCapabilityInstance,
    VideoStreamCapabilityInstance,
]


class CapabilityDescription(APIModel):
    type: CapabilityType
    retrievable: bool
    reportable: bool
    parameters: CapabilityParameters | None = None


class CapabilityInstanceStateValue(APIModel):
    instance: CapabilityInstance
    value: Any


class CapabilityInstanceState(APIModel):
    type: CapabilityType
    state: CapabilityInstanceStateValue


class OnOffCapabilityInstanceAction(APIModel):
    type: Literal[CapabilityType.ON_OFF] = CapabilityType.ON_OFF
    state: OnOffCapabilityInstanceActionState


class ColorSettingCapabilityInstanceAction(APIModel):
    type: Literal[CapabilityType.COLOR_SETTING] = CapabilityType.COLOR_SETTING
    state: ColorSettingCapabilityInstanceActionState


class ModeCapabilityInstanceAction(APIModel):
    type: Literal[CapabilityType.MODE] = CapabilityType.MODE
    state: ModeCapabilityInstanceActionState


class RangeCapabilityInstanceAction(APIModel):
    type: Literal[CapabilityType.RANGE] = CapabilityType.RANGE
    state: RangeCapabilityInstanceActionState


class ToggleCapabilityInstanceAction(APIModel):
    type: Literal[CapabilityType.TOGGLE] = CapabilityType.TOGGLE
    state: ToggleCapabilityInstanceActionState


class VideoStreamCapabilityInstanceAction(APIModel):
    type: Literal[CapabilityType.VIDEO_STREAM] = CapabilityType.VIDEO_STREAM
    state: GetStreamInstanceActionState


CapabilityInstanceAction = Annotated[
    Union[
        OnOffCapabilityInstanceAction,
        ColorSettingCapabilityInstanceAction,
        ModeCapabilityInstanceAction,
        RangeCapabilityInstanceAction,
        ToggleCapabilityInstanceAction,
        VideoStreamCapabilityInstanceAction,
    ],
    Field(discriminator="type"),
]


CapabilityInstanceActionState = TypeVar(
    "CapabilityInstanceActionState",
    OnOffCapabilityInstanceActionState,
    ColorSettingCapabilityInstanceActionState,
    RGBInstanceActionState,
    TemperatureKInstanceActionState,
    SceneInstanceActionState,
    ModeCapabilityInstanceActionState,
    RangeCapabilityInstanceActionState,
    ToggleCapabilityInstanceActionState,
    GetStreamInstanceActionState,
    contravariant=True,
)


CapabilityInstanceActionResultValue = GetStreamInstanceActionResultValue | None