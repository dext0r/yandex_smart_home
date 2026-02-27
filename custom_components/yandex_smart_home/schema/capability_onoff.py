"""Schema for on_off capability.
https://yandex.ru/dev/dialogs/smart-home/doc/concepts/on_off.html
"""

from __future__ import annotations
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel
from .base import APIModel
from .response import SuccessActionResult


class OnOffCapabilityInstance(StrEnum):
    """Instance of an on_off capability."""
    ON = "on"


class OnOffCapabilityParameters(APIModel):
    """Parameters of a on_off capability."""
    split: bool = False


class OnOffCapabilityInstanceActionState(APIModel):
    """New value for an on_off capability."""
    instance: Literal[OnOffCapabilityInstance.ON] = OnOffCapabilityInstance.ON
    value: bool


class OnOffCapabilityInstanceActionResultValue(BaseModel):
    """ActionResult value for on_off capability."""
    on: bool