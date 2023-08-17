"""Schema for on_off capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/on_off.html
"""
from enum import StrEnum

from pydantic import BaseModel


class OnOffCapabilityInstance(StrEnum):
    ON = "on"


class OnOffCapabilityParameters(BaseModel):
    split: bool


class OnOffCapabilityInstanceActionState(BaseModel):
    instance: OnOffCapabilityInstance
    value: bool
