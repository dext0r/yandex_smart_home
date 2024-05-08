"""The Yandex Smart Home request handlers."""

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
    ActionResult,
    ActionResultCapability,
    ActionResultCapabilityState,
    ActionResultDevice,
    DeviceDescription,
    DeviceList,
    DeviceStates,
    FailedActionResult,
    Response,
    ResponseCode,
    ResponsePayload,
    StatesRequest,
    SuccessActionResult,
)

_LOGGER = logging.getLogger(__name__)

HANDLERS: Registry[
    str,
    Callable[
        [HomeAssistant, RequestData, str],
        Coroutine[Any, Any, ResponsePayload | None],
    ],
] = Registry()


async def async_handle_request(hass: HomeAssistant, data: RequestData, action: str, payload: str) -> Response:
    """Handle incoming API request."""
    handler = HANDLERS.get(action)

    if handler is None:
        _LOGGER.error(f"Unexpected action '{action}'")
        return Response(request_id=data.request_id)

    try:
        return Response(request_id=data.request_id, payload=await handler(hass, data, payload))
    except APIError as err:
        _LOGGER.error(f"{err.message} ({err.code})")
        return Response(request_id=data.request_id)
    except Exception:
        # return always 200 due to blocking error on device page
        _LOGGER.exception("Unexpected exception")
        return Response(request_id=data.request_id)


@HANDLERS.register("/user/devices")
async def async_device_list(hass: HomeAssistant, data: RequestData, _payload: str) -> DeviceList:
    """Handle request that return information about supported user devices.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/get-devices.html
    """
    assert data.request_user_id

    devices: list[DeviceDescription] = []
    for device in await async_get_devices(hass, data.entry_data):
        if (description := await async_get_device_description(hass, device)) is not None:
            devices.append(description)

    data.entry_data.link_platform(data.platform)
    return DeviceList(user_id=data.request_user_id, devices=devices)


@HANDLERS.register("/user/devices/query")
async def async_devices_query(hass: HomeAssistant, data: RequestData, payload: str) -> DeviceStates:
    """Handle request that return information about the states of user devices.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-devices-query.html
    """
    request = StatesRequest.parse_raw(payload)
    states = await async_get_device_states(hass, data.entry_data, [rd.id for rd in request.devices])
    return DeviceStates(devices=states)


@HANDLERS.register("/user/devices/action")
async def async_devices_action(hass: HomeAssistant, data: RequestData, payload: str) -> ActionResult:
    """Handle request that changes current state of user devices.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-action.html
    """
    request = ActionRequest.parse_raw(payload)
    results: list[ActionResultDevice] = []

    for device_id, actions in [(rd.id, rd.capabilities) for rd in request.payload.devices]:
        device = Device(hass, data.entry_data, device_id, hass.states.get(device_id))

        if device.unavailable:
            hass.bus.async_fire(
                EVENT_DEVICE_ACTION,
                {ATTR_ENTITY_ID: device_id, ATTR_ERROR_CODE: ResponseCode.DEVICE_UNREACHABLE.value},
                context=data.context,
            )

            results.append(
                ActionResultDevice(
                    id=device_id, action_result=FailedActionResult(error_code=ResponseCode.DEVICE_UNREACHABLE)
                )
            )
            continue

        capability_results: list[ActionResultCapability] = []
        for action in actions:
            try:
                value = await device.execute(data.context, action)
                hass.bus.async_fire(
                    EVENT_DEVICE_ACTION,
                    {ATTR_ENTITY_ID: device_id, ATTR_CAPABILITY: action.as_dict()},
                    context=data.context,
                )
            except (APIError, ActionNotAllowed) as err:
                if isinstance(err, APIError):
                    _LOGGER.error(f"{err.message} ({err.code.value})")

                hass.bus.async_fire(
                    EVENT_DEVICE_ACTION,
                    {ATTR_ENTITY_ID: device_id, ATTR_CAPABILITY: action.as_dict(), ATTR_ERROR_CODE: err.code.value},
                    context=data.context,
                )

                capability_results.append(
                    ActionResultCapability(
                        type=action.type,
                        state=ActionResultCapabilityState(
                            instance=action.state.instance,
                            action_result=FailedActionResult(error_code=ResponseCode(err.code)),
                        ),
                    )
                )
                continue

            capability_results.append(
                ActionResultCapability(
                    type=action.type,
                    state=ActionResultCapabilityState(
                        instance=action.state.instance,
                        value=value,
                        action_result=SuccessActionResult(),
                    ),
                )
            )

        results.append(ActionResultDevice(id=device_id, capabilities=capability_results))

    return ActionResult(devices=results)


@HANDLERS.register("/user/unlink")
async def async_user_unlink(_hass: HomeAssistant, data: RequestData, _payload: str) -> None:
    """Handle request indicates that the user has unlink the account.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/unlink.html
    """
    data.entry_data.unlink_platform(data.platform)
