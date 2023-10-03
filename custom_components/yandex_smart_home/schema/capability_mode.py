"""Schema for mode capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode.html
"""
from enum import StrEnum
from typing import Literal, Self

from .base import APIModel


class ModeCapabilityInstance(StrEnum):
    """Instance of a mode capability.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html
    """

    CLEANUP_MODE = "cleanup_mode"
    COFFEE_MODE = "coffee_mode"
    DISHWASHING = "dishwashing"
    FAN_SPEED = "fan_speed"
    HEAT = "heat"
    INPUT_SOURCE = "input_source"
    PROGRAM = "program"
    SWING = "swing"
    TEA_MODE = "tea_mode"
    THERMOSTAT = "thermostat"
    WORK_SPEED = "work_speed"


class ModeCapabilityMode(StrEnum):
    """Mode value of a mode capability.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html
    """

    AUTO = "auto"
    ECO = "eco"
    SMART = "smart"
    TURBO = "turbo"
    COOL = "cool"
    DRY = "dry"
    FAN_ONLY = "fan_only"
    HEAT = "heat"
    PREHEAT = "preheat"
    HIGH = "high"
    LOW = "low"
    MEDIUM = "medium"
    MAX = "max"
    MIN = "min"
    FAST = "fast"
    SLOW = "slow"
    EXPRESS = "express"
    NORMAL = "normal"
    QUIET = "quiet"
    HORIZONTAL = "horizontal"
    STATIONARY = "stationary"
    VERTICAL = "vertical"
    ONE = "one"
    TWO = "two"
    THREE = "three"
    FOUR = "four"
    FIVE = "five"
    SIX = "six"
    SEVEN = "seven"
    EIGHT = "eight"
    NINE = "nine"
    TEN = "ten"
    AMERICANO = "americano"
    CAPPUCCINO = "cappuccino"
    DOUBLE = "double"
    ESPRESSO = "espresso"
    DOUBLE_ESPRESSO = "double_espresso"
    LATTE = "latte"
    BLACK_TEA = "black_tea"
    FLOWER_TEA = "flower_tea"
    GREEN_TEA = "green_tea"
    HERBAL_TEA = "herbal_tea"
    OOLONG_TEA = "oolong_tea"
    PUERH_TEA = "puerh_tea"
    RED_TEA = "red_tea"
    WHITE_TEA = "white_tea"
    GLASS = "glass"
    INTENSIVE = "intensive"
    PRE_RINSE = "pre_rinse"
    ASPIC = "aspic"
    BABY_FOOD = "baby_food"
    BAKING = "baking"
    BREAD = "bread"
    BOILING = "boiling"
    CEREALS = "cereals"
    CHEESECAKE = "cheesecake"
    DEEP_FRYER = "deep_fryer"
    DESSERT = "dessert"
    FOWL = "fowl"
    FRYING = "frying"
    MACARONI = "macaroni"
    MILK_PORRIDGE = "milk_porridge"
    MULTICOOKER = "multicooker"
    PASTA = "pasta"
    PILAF = "pilaf"
    PIZZA = "pizza"
    SAUCE = "sauce"
    SLOW_COOK = "slow_cook"
    SOUP = "soup"
    STEAM = "steam"
    STEWING = "stewing"
    VACUUM = "vacuum"
    YOGURT = "yogurt"


class ModeCapabilityParameters(APIModel):
    """Parameters of a mode capability."""

    instance: ModeCapabilityInstance
    modes: list[dict[Literal["value"], ModeCapabilityMode]]

    @classmethod
    def from_list(cls, instance: ModeCapabilityInstance, modes: list[ModeCapabilityMode]) -> Self:
        return cls(instance=instance, modes=[{"value": m} for m in modes])


class ModeCapabilityInstanceActionState(APIModel):
    """New value for a mode capability."""

    instance: ModeCapabilityInstance
    value: ModeCapabilityMode
