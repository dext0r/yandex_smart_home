"""Yandex Smart Home request handlers — упрощённая версия без строгой Pydantic-валидации."""

import logging
from typing import Any, Callable, Coroutine

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.util.decorator import Registry

from .const import ATTR_CAPABILITY, ATTR_ERROR_CODE, EVENT_DEVICE_ACTION
from .device import Device, async_get_device_description, async_get_device_states, async_get_devices
from .helpers import ActionNotAllowed, APIError, RequestData
from .schema import (
    ActionRequest,
    DeviceDescription,
    DeviceList,
    DeviceStates,
    Response,
    ResponseCode,
    StatesRequest,
)

_LOGGER = logging.getLogger(__name__)

HANDLERS: Registry[
    str,
    Callable[
        [HomeAssistant, RequestData, str],
        Coroutine[Any, Any, dict | None],
    ],
] = Registry()


async def async_handle_request(
    hass: HomeAssistant, data: RequestData, action: str, payload: str
) -> Response:
    handler = HANDLERS.get(action)
    if handler is None:
        _LOGGER.error(f"Unexpected action '{action}'")
        return Response(request_id=data.request_id)

    try:
        result = await handler(hass, data, payload)
        _LOGGER.debug("Handler result: %s", result)

        # Конвертируем Pydantic-модели в обычные словари
        if hasattr(result, "model_dump"):
            result = result.model_dump(exclude_none=True)

        return Response(request_id=data.request_id, payload=result)
    except Exception:
        _LOGGER.exception("Unexpected exception in handler")
        return Response(request_id=data.request_id)


@HANDLERS.register("/user/devices")
async def async_device_list(
    hass: HomeAssistant, data: RequestData, _payload: str
) -> DeviceList:
    assert data.request_user_id
    devices: list[DeviceDescription] = []
    for device in await async_get_devices(hass, data.entry_data):
        if (description := await async_get_device_description(hass, device)) is not None:
            devices.append(description)
    data.entry_data.link_platform(data.platform)
    return DeviceList(user_id=data.request_user_id, devices=devices)


@HANDLERS.register("/user/devices/query")
async def async_devices_query(
    hass: HomeAssistant, data: RequestData, payload: str
) -> DeviceStates:
    request = StatesRequest.model_validate_json(payload)
    states = await async_get_device_states(hass, data.entry_data, [rd.id for rd in request.devices])
    return DeviceStates(devices=states)


@HANDLERS.register("/user/devices/action")
async def async_devices_action(
    hass: HomeAssistant, data: RequestData, payload: str
) -> dict:
    try:
        request = ActionRequest.model_validate_json(payload)
        _LOGGER.debug("Action request: %s", request.model_dump(exclude_none=True))
    except Exception as e:
        _LOGGER.error(f"Failed to parse action request: {e}")
        return {"devices": []}

    devices_list = []

    for device_req in request.payload.devices:
        dev_id = device_req.id
        caps = device_req.capabilities

        ha_state = hass.states.get(dev_id)
        if not ha_state:
            devices_list.append({
                "id": dev_id,
                "action_result": {"status": "ERROR", "error_code": "DEVICE_NOT_FOUND"}
            })
            continue

        dev = Device(hass, data.entry_data, dev_id, ha_state)

        if not dev.should_expose:
            data.entry_data.mark_entity_unexposed(ha_state.entity_id)

        if dev.unavailable:
            hass.bus.async_fire(
                EVENT_DEVICE_ACTION,
                {ATTR_ENTITY_ID: dev_id, ATTR_ERROR_CODE: ResponseCode.DEVICE_UNREACHABLE.value},
                context=data.context,
            )
            devices_list.append({
                "id": dev_id,
                "action_result": {"status": "ERROR", "error_code": "DEVICE_UNREACHABLE"}
            })
            continue

        cap_responses = []
        at_least_one_success = False

        for cap in caps:
            try:
                executed_value = await dev.execute(data.context, cap)
                _LOGGER.debug(f"Executed {cap.type} on {dev_id}: {executed_value}")

                hass.bus.async_fire(
                    EVENT_DEVICE_ACTION,
                    {ATTR_ENTITY_ID: dev_id, ATTR_CAPABILITY: cap.model_dump(exclude_none=True)},
                    context=data.context,
                )

                # Для on_off всегда value = null в ответе на action
                cap_responses.append({
                    "type": str(cap.type),
                    "state": {
                        "instance": str(cap.state.instance),
                        "value": None,
                        "action_result": {"status": "DONE"}
                    }
                })
                at_least_one_success = True

            except Exception as exc:
                _LOGGER.exception(f"Error on {cap.type} for {dev_id}")
                cap_responses.append({
                    "type": str(cap.type),
                    "state": {
                        "instance": str(cap.state.instance),
                        "value": None,
                        "action_result": {"status": "ERROR", "error_code": "INTERNAL_ERROR"}
                    }
                })

        device_resp = {
            "id": dev_id,
            "capabilities": cap_responses,
            "action_result": {"status": "DONE"} if at_least_one_success else {"status": "ERROR", "error_code": "INTERNAL_ERROR"}
        }

        devices_list.append(device_resp)
        _LOGGER.debug(f"Device response: {device_resp}")

    full_payload = {"devices": devices_list}
    _LOGGER.debug(f"RETURNING PAYLOAD: {full_payload}")

    return full_payload


@HANDLERS.register("/user/unlink")
async def async_user_unlink(_hass: HomeAssistant, data: RequestData, _payload: str) -> None:
    data.entry_data.unlink_platform(data.platform)