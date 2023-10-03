"""Schema for an user device.

https://yandex.ru/dev/dialogs/smart-home/doc/reference/get-devices.html
https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-devices-query.html
https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-action.html
"""
from enum import StrEnum
from typing import Any, Literal

from .base import APIModel
from .capability import (
    CapabilityDescription,
    CapabilityInstance,
    CapabilityInstanceAction,
    CapabilityInstanceActionResultValue,
    CapabilityInstanceState,
    CapabilityType,
)
from .property import PropertyDescription, PropertyInstanceState
from .response import ResponseCode, ResponsePayload


class DeviceType(StrEnum):
    """User device type.

    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html
    """

    LIGHT = "devices.types.light"
    SOCKET = "devices.types.socket"
    SWITCH = "devices.types.switch"
    THERMOSTAT = "devices.types.thermostat"
    THERMOSTAT_AC = "devices.types.thermostat.ac"
    MEDIA_DEVICE = "devices.types.media_device"
    MEDIA_DEVICE_TV = "devices.types.media_device.tv"
    MEDIA_DEVICE_TV_BOX = "devices.types.media_device.tv_box"
    MEDIA_DEVICE_RECIEVER = "devices.types.media_device.receiver"
    CAMERA = "devices.types.camera"
    COOKING = "devices.types.cooking"
    COFFEE_MAKER = "devices.types.cooking.coffee_maker"
    KETTLE = "devices.types.cooking.kettle"
    MULTICOOKER = "devices.types.cooking.multicooker"
    OPENABLE = "devices.types.openable"
    OPENABLE_CURTAIN = "devices.types.openable.curtain"
    HUMIDIFIER = "devices.types.humidifier"
    FAN = "devices.types.fan"
    PURIFIER = "devices.types.purifier"
    VACUUM_CLEANER = "devices.types.vacuum_cleaner"
    WASHING_MACHINE = "devices.types.washing_machine"
    DISHWASHER = "devices.types.dishwasher"
    IRON = "devices.types.iron"
    SENSOR = "devices.types.sensor"
    SENSOR_MOTION = "devices.types.sensor.motion"
    SENSOR_VIBRATION = "devices.types.sensor.vibration"
    SENSOR_ILLUMINATION = "devices.types.sensor.illumination"
    SENSOR_OPEN = "devices.types.sensor.open"
    SENSOR_CLIMATE = "devices.types.sensor.climate"
    SENSOR_WATER_LEAK = "devices.types.sensor.water_leak"
    SENSOR_BUTTON = "devices.types.sensor.button"
    SENSOR_GAS = "devices.types.sensor.gas"
    SENSOR_SMOKE = "devices.types.sensor.smoke"
    PET_DRINKING_FOUNTAIN = "devices.types.pet_drinking_fountain"
    PET_FEEDER = "devices.types.pet_feeder"
    OTHER = "devices.types.other"


class DeviceInfo(APIModel):
    """Extended device info."""

    manufacturer: str | None
    model: str | None
    hw_version: str | None
    sw_version: str | None


class DeviceDescription(APIModel):
    """Device description for a device list request."""

    id: str
    name: str
    description: str | None
    room: str | None
    type: DeviceType
    capabilities: list[CapabilityDescription]
    properties: list[PropertyDescription]
    device_info: DeviceInfo | None


class DeviceState(APIModel):
    """Device state for a state query request."""

    id: str
    capabilities: list[CapabilityInstanceState] | None
    properties: list[PropertyInstanceState] | None
    error_code: ResponseCode | None
    error_message: str | None


class DeviceList(ResponsePayload):
    """Response payload for a device list request."""

    user_id: str
    devices: list[DeviceDescription]


class DeviceStates(ResponsePayload):
    """Response payload for a state query request."""

    devices: list[DeviceState]


class StatesRequestDevice(APIModel):
    """Device for a state query request."""

    id: str
    custom_data: dict[str, Any] | None


class StatesRequest(APIModel):
    """Request body for a state query request."""

    devices: list[StatesRequestDevice]


class ActionRequestDevice(APIModel):
    """Device for a state change request."""

    id: str
    capabilities: list[CapabilityInstanceAction]


class ActionRequestPayload(APIModel):
    """Request payload for state change request."""

    devices: list[ActionRequestDevice]


class ActionRequest(APIModel):
    """Request body for a state change request."""

    payload: ActionRequestPayload


class SuccessActionResult(APIModel):
    """Success device action result."""

    status: Literal["DONE"] = "DONE"


class FailedActionResult(APIModel):
    """Failed device action result."""

    status: Literal["ERROR"] = "ERROR"
    error_code: ResponseCode


class ActionResultCapabilityState(APIModel):
    """Result of capability instance state change."""

    instance: CapabilityInstance
    value: CapabilityInstanceActionResultValue | None
    action_result: SuccessActionResult | FailedActionResult


class ActionResultCapability(APIModel):
    """Result of capability state change."""

    type: CapabilityType
    state: ActionResultCapabilityState


class ActionResultDevice(APIModel):
    """Device for a state change response."""

    id: str
    capabilities: list[ActionResultCapability] | None
    action_result: FailedActionResult | SuccessActionResult | None


class ActionResult(ResponsePayload):
    """Response for a device state change."""

    devices: list[ActionResultDevice]
