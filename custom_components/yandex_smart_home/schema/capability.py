"""Schema for device capabilities."""
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeVar, Union

from pydantic import Field

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
    """Capability type."""

    ON_OFF = "devices.capabilities.on_off"
    COLOR_SETTING = "devices.capabilities.color_setting"
    MODE = "devices.capabilities.mode"
    RANGE = "devices.capabilities.range"
    TOGGLE = "devices.capabilities.toggle"
    VIDEO_STREAM = "devices.capabilities.video_stream"

    @property
    def short(self) -> str:
        """Return short version of the capability type."""
        return str(self).replace("devices.capabilities.", "")


CapabilityParameters = (
    OnOffCapabilityParameters
    | ColorSettingCapabilityParameters
    | ModeCapabilityParameters
    | RangeCapabilityParameters
    | ToggleCapabilityParameters
    | VideoStreamCapabilityParameters
)
"""Parameters of a capability for a device list request."""

CapabilityInstance = (
    OnOffCapabilityInstance
    | ColorSettingCapabilityInstance
    | ModeCapabilityInstance
    | RangeCapabilityInstance
    | ToggleCapabilityInstance
    | VideoStreamCapabilityInstance
)
"""All capability instances."""


class CapabilityDescription(APIModel):
    """Description of a capability for a device list request."""

    type: CapabilityType
    retrievable: bool
    reportable: bool
    parameters: CapabilityParameters | None


class CapabilityInstanceStateValue(APIModel):
    """Capability instance value."""

    instance: CapabilityInstance
    value: Any


class CapabilityInstanceState(APIModel):
    """Capability state for state query and callback requests."""

    type: CapabilityType
    state: CapabilityInstanceStateValue


class OnOffCapabilityInstanceAction(APIModel):
    """New capability state for a state change request of on_off capability."""

    type: Literal[CapabilityType.ON_OFF] = CapabilityType.ON_OFF
    state: OnOffCapabilityInstanceActionState


class ColorSettingCapabilityInstanceAction(APIModel):
    """New capability state for a state change request of color_setting capability."""

    type: Literal[CapabilityType.COLOR_SETTING] = CapabilityType.COLOR_SETTING
    state: ColorSettingCapabilityInstanceActionState


class ModeCapabilityInstanceAction(APIModel):
    """New capability state for a state change request of mode capability."""

    type: Literal[CapabilityType.MODE] = CapabilityType.MODE
    state: ModeCapabilityInstanceActionState


class RangeCapabilityInstanceAction(APIModel):
    """New capability state for a state change request of range capability."""

    type: Literal[CapabilityType.RANGE] = CapabilityType.RANGE
    state: RangeCapabilityInstanceActionState


class ToggleCapabilityInstanceAction(APIModel):
    """New capability state for a state change request of toggle capability."""

    type: Literal[CapabilityType.TOGGLE] = CapabilityType.TOGGLE
    state: ToggleCapabilityInstanceActionState


class VideoStreamCapabilityInstanceAction(APIModel):
    """New capability state for a state change request of video_stream capability."""

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
"""New capability state including type for a state change request."""

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
"""New capability state for a state change request."""

CapabilityInstanceActionResultValue = GetStreamInstanceActionResultValue | None
"""Result of a capability state change."""
