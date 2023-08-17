from pydantic import BaseModel

from custom_components.yandex_smart_home.schema import CapabilityInstanceAction


class DevicesActionRequestDevice(BaseModel):
    id: str
    capabilities: list[CapabilityInstanceAction]


class DevicesActionRequestPayload(BaseModel):
    devices: list[DevicesActionRequestDevice]


class DevicesActionRequest(BaseModel):
    """https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-action.html"""

    payload: DevicesActionRequestPayload
