"""Yandex Smart Home request handlers."""
import logging
from typing import Any, Callable, Coroutine

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.util.decorator import Registry

from .const import EVENT_DEVICE_ACTION, EVENT_DEVICE_DISCOVERY
from .device import Device
from .error import SmartHomeError, SmartHomeUserError
from .helpers import RequestData
from .schema import (
    ActionRequest,
    ActionResult,
    ActionResultCapability,
    ActionResultCapabilityState,
    ActionResultDevice,
    DeviceDescription,
    DeviceList,
    DeviceState,
    DeviceStates,
    Error,
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
        _LOGGER.error(f"Unexpected action {action!r}")
        return Response(request_id=data.request_id, payload=Error(error_code=ResponseCode.INTERNAL_ERROR))

    # noinspection PyBroadException
    try:
        return Response(request_id=data.request_id, payload=await handler(hass, data, payload))
    except SmartHomeError as err:
        _LOGGER.error(f"{err.message} ({err.code})")
        return Response(request_id=data.request_id, payload=Error(error_code=ResponseCode(err.code)))
    except Exception:
        _LOGGER.exception("Unexpected exception")
        return Response(request_id=data.request_id, payload=Error(error_code=ResponseCode.INTERNAL_ERROR))


@HANDLERS.register("/user/devices")
async def async_device_list(hass: HomeAssistant, data: RequestData, _payload: str) -> DeviceList:
    """Handle request that return information about supported user devices.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/get-devices.html
    """
    devices: list[DeviceDescription] = []
    ent_reg = entity_registry.async_get(hass)
    dev_reg = device_registry.async_get(hass)
    area_reg = area_registry.async_get(hass)

    hass.bus.async_fire(EVENT_DEVICE_DISCOVERY, context=data.context)

    for state in hass.states.async_all():
        device = Device(hass, data.config, state.entity_id, state)
        if not device.should_expose:
            continue

        if (description := await device.describe(ent_reg, dev_reg, area_reg)) is not None:
            devices.append(description)
        else:
            _LOGGER.debug(f"Missing capabilities and properties for {device.id}")

    assert data.request_user_id
    return DeviceList(user_id=data.request_user_id, devices=devices)


@HANDLERS.register("/user/devices/query")
async def async_devices_query(hass: HomeAssistant, data: RequestData, payload: str) -> DeviceStates:
    """Handle request that return information about the states of user devices.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-devices-query.html
    """
    request = StatesRequest.parse_raw(payload)
    states: list[DeviceState] = []

    for device_id in [rd.id for rd in request.devices]:
        device = Device(hass, data.config, device_id, hass.states.get(device_id))
        if not device.should_expose:
            _LOGGER.warning(
                f"State requested for unexposed entity {device.id}. Please either expose the entity via "
                f"filters in component configuration or delete the device from Yandex."
            )

        states.append(device.query())

    return DeviceStates(devices=states)


@HANDLERS.register("/user/devices/action")
async def async_devices_action(hass: HomeAssistant, data: RequestData, payload: str) -> ActionResult:
    """Handle request that changes current state of user devices.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-action.html
    """
    request = ActionRequest.parse_raw(payload)
    results: list[ActionResultDevice] = []

    for device_id, actions in [(rd.id, rd.capabilities) for rd in request.payload.devices]:
        device = Device(hass, data.config, device_id, hass.states.get(device_id))

        if device.unavailable:
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
            except (SmartHomeError, SmartHomeUserError) as err:
                if isinstance(err, SmartHomeError):
                    _LOGGER.error(f"{err.message} ({err.code})")

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

            hass.bus.async_fire(
                EVENT_DEVICE_ACTION,
                {ATTR_ENTITY_ID: device_id, "capability": action.as_dict()},
                context=data.context,
            )

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
async def async_user_unlink(_hass: HomeAssistant, _data: RequestData, _payload: str) -> None:
    """Handle request indicates that the user has unlink the account.

    https://yandex.ru/dev/dialogs/smart-home/doc/reference/unlink.html
    """
    return None
