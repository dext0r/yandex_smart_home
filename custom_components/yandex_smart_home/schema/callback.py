"""Schema for event notification service.

https://yandex.ru/dev/dialogs/smart-home/doc/reference-alerts/resources-alerts.html
"""

from enum import StrEnum
import time

from pydantic import Field

from .base import APIModel
from .device import DeviceState


class CallbackStatesRequestPayload(APIModel):
    """Payload of request body for notification about device state change."""

    user_id: str
    devices: list[DeviceState]


class CallbackStatesRequest(APIModel):
    """Request body for notification about device state change."""

    ts: float = Field(default_factory=lambda: time.time())
    payload: CallbackStatesRequestPayload


class CallbackDiscoveryRequestPayload(APIModel):
    """Payload of request body for notification about change of devices' parameters."""

    user_id: str


class CallbackDiscoveryRequest(APIModel):
    """Request body for notification about change of devices' parameters."""

    ts: float = Field(default_factory=lambda: time.time())
    payload: CallbackDiscoveryRequestPayload


class CallbackResponseStatus(StrEnum):
    """Status of a callback request."""

    OK = "ok"
    ERROR = "error"


class CallbackResponse(APIModel):
    """Response on a callback request."""

    status: CallbackResponseStatus
    error_code: str | None
    error_message: str | None


CallbackRequest = CallbackDiscoveryRequest | CallbackStatesRequest
