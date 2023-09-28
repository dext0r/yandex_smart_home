"""Schema for on_off capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/on_off.html
"""
from enum import StrEnum

from pydantic import BaseModel


class OnOffCapabilityInstance(StrEnum):
    """Instance of an on_off capability."""

    ON = "on"


class OnOffCapabilityParameters(BaseModel):
    """Parameters of a on_off capability."""

    split: bool


class OnOffCapabilityInstanceActionState(BaseModel):
    """New value for an on_off capability."""

    instance: OnOffCapabilityInstance
    value: bool
