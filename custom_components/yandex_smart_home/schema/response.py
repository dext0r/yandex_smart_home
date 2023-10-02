"""Schema for an API response.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/response-codes.html
"""
from enum import StrEnum

from pydantic import BaseModel


class ResponseCode(StrEnum):
    """Response code."""

    DOOR_OPEN = "DOOR_OPEN"
    LID_OPEN = "LID_OPEN"
    REMOTE_CONTROL_DISABLED = "REMOTE_CONTROL_DISABLED"
    NOT_ENOUGH_WATER = "NOT_ENOUGH_WATER"
    LOW_CHARGE_LEVEL = "LOW_CHARGE_LEVEL"
    CONTAINER_FULL = "CONTAINER_FULL"
    CONTAINER_EMPTY = "CONTAINER_EMPTY"
    DRIP_TRAY_FULL = "DRIP_TRAY_FULL"
    DEVICE_STUCK = "DEVICE_STUCK"
    DEVICE_OFF = "DEVICE_OFF"
    FIRMWARE_OUT_OF_DATE = "FIRMWARE_OUT_OF_DATE"
    NOT_ENOUGH_DETERGENT = "NOT_ENOUGH_DETERGENT"
    HUMAN_INVOLVEMENT_NEEDED = "HUMAN_INVOLVEMENT_NEEDED"
    DEVICE_UNREACHABLE = "DEVICE_UNREACHABLE"
    DEVICE_BUSY = "DEVICE_BUSY"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_ACTION = "INVALID_ACTION"
    INVALID_VALUE = "INVALID_VALUE"
    NOT_SUPPORTED_IN_CURRENT_MODE = "NOT_SUPPORTED_IN_CURRENT_MODE"
    ACCOUNT_LINKING_ERROR = "ACCOUNT_LINKING_ERROR"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"


class ResponsePayload(BaseModel):
    """Base class for an API response payload."""


class Error(ResponsePayload):
    """Error payload."""

    error_code: ResponseCode
    error_message: str | None


class Response(BaseModel):
    """Base API response."""

    request_id: str | None
    payload: ResponsePayload | None
