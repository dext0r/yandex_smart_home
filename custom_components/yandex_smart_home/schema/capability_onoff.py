"""Schema for on_off capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/on_off.html
"""
from enum import StrEnum

from .base import APIModel


class OnOffCapabilityInstance(StrEnum):
    """Instance of an on_off capability."""

    ON = "on"


class OnOffCapabilityParameters(APIModel):
    """Parameters of a on_off capability."""

    split: bool


class OnOffCapabilityInstanceActionState(APIModel):
    """New value for an on_off capability."""

    instance: OnOffCapabilityInstance
    value: bool
