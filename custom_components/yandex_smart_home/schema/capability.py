from enum import StrEnum
from typing import Annotated, Any, Literal, TypeVar, Union

from pydantic import BaseModel, Field

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


CapabilityParameters = (
    OnOffCapabilityParameters
    | ColorSettingCapabilityParameters
    | ModeCapabilityParameters
    | RangeCapabilityParameters
    | ToggleCapabilityParameters
    | VideoStreamCapabilityParameters
)
CapabilityInstance = (
    OnOffCapabilityInstance
    | ColorSettingCapabilityInstance
    | ModeCapabilityInstance
    | RangeCapabilityInstance
    | ToggleCapabilityInstance
    | VideoStreamCapabilityInstance
)


class CapabilityDescription(BaseModel):
    type: CapabilityType
    retrievable: bool
    reportable: bool
    parameters: CapabilityParameters | None


class CapabilityInstanceStateValue(BaseModel):
    instance: CapabilityInstance
    value: Any


class CapabilityInstanceState(BaseModel):
    """Capability state in query and callback requests."""

    type: CapabilityType
    state: CapabilityInstanceStateValue


CapabilityInstanceActionResultValue = GetStreamInstanceActionResultValue | None

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
"""New capability state in device action request."""


class OnOffCapabilityInstanceAction(BaseModel):
    type: Literal[CapabilityType.ON_OFF] = CapabilityType.ON_OFF
    state: OnOffCapabilityInstanceActionState


class ColorSettingCapabilityInstanceAction(BaseModel):
    type: Literal[CapabilityType.COLOR_SETTING] = CapabilityType.COLOR_SETTING
    state: ColorSettingCapabilityInstanceActionState


class ModeCapabilityInstanceAction(BaseModel):
    type: Literal[CapabilityType.MODE] = CapabilityType.MODE
    state: ModeCapabilityInstanceActionState


class RangeCapabilityInstanceAction(BaseModel):
    type: Literal[CapabilityType.RANGE] = CapabilityType.RANGE
    state: RangeCapabilityInstanceActionState


class ToggleCapabilityInstanceAction(BaseModel):
    type: Literal[CapabilityType.TOGGLE] = CapabilityType.TOGGLE
    state: ToggleCapabilityInstanceActionState


class VideoStreamCapabilityInstanceAction(BaseModel):
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
"""Capability state in action requests."""
