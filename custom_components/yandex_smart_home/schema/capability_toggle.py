"""Schema for toggle capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle.html
"""
from enum import StrEnum

from pydantic import BaseModel


class ToggleCapabilityInstance(StrEnum):
    """Instance of a toggle capability.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html
    """

    BACKLIGHT = "backlight"
    CONTROLS_LOCKED = "controls_locked"
    IONIZATION = "ionization"
    KEEP_WARM = "keep_warm"
    MUTE = "mute"
    OSCILLATION = "oscillation"
    PAUSE = "pause"


class ToggleCapabilityParameters(BaseModel):
    """Parameters of a toggle capability."""

    instance: ToggleCapabilityInstance


class ToggleCapabilityInstanceActionState(BaseModel):
    """New value for a toggle capability."""

    instance: ToggleCapabilityInstance
    value: bool
