"""Support for Yandex Smart Home API."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.util.decorator import Registry

from .const import ERR_DEVICE_UNREACHABLE, ERR_INTERNAL_ERROR, EVENT_DEVICE_ACTION, EVENT_DEVICE_DISCOVERY
from .entity import YandexEntity
from .error import SmartHomeError, SmartHomeUserError
from .helpers import DeviceActionRequest, RequestData

HANDLERS = Registry()
_LOGGER = logging.getLogger(__name__)


async def async_handle_message(hass: HomeAssistant,
                               data: RequestData,
                               action: str,
                               message: dict[str, Any]) -> dict[str, Any]:
    """Handle incoming API messages."""
    handler = HANDLERS.get(action)

    if handler is None:
        _LOGGER.error(f'Handler not found for {action!r}')
        return {
            'request_id': data.request_id,
            'payload': {'error_code': ERR_INTERNAL_ERROR}
        }

    # noinspection PyBroadException
    try:
        result = await handler(hass, data, message)
    except SmartHomeError as err:
        _LOGGER.error('Handler error: %s %s', err.code, err.message)
        return {
            'request_id': data.request_id,
            'payload': {'error_code': err.code}
        }
    except Exception:
        _LOGGER.exception('Handler unexpected error')
        return {
            'request_id': data.request_id,
            'payload': {'error_code': ERR_INTERNAL_ERROR}
        }

    if result is None:
        return {'request_id': data.request_id}

    return {
        'request_id': data.request_id,
        'payload': result
    }


# noinspection PyUnusedLocal
@HANDLERS.register('/user/devices')
async def async_devices(hass: HomeAssistant, data: RequestData, message: dict[str, Any]):
    """Handle /user/devices request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/get-devices-docpage/
    """
    devices = []
    ent_reg = entity_registry.async_get(hass)
    dev_reg = device_registry.async_get(hass)
    area_reg = area_registry.async_get(hass)

    hass.bus.async_fire(EVENT_DEVICE_DISCOVERY, context=data.context)

    for state in hass.states.async_all():
        entity = YandexEntity(hass, data.config, state)
        if not entity.should_expose:
            continue

        serialized = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
        if serialized is None:
            _LOGGER.debug(f'Unsupported entity: {entity.state!r}')
            continue

        devices.append(serialized)

    return {
        'user_id': data.request_user_id,
        'devices': devices,
    }


@HANDLERS.register('/user/devices/query')
async def async_devices_query(hass, data, message):
    """Handle /user/devices/query request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-devices-query-docpage/
    """
    devices = []
    for device in message.get('devices', []):
        entity_id = device['id']
        state = hass.states.get(entity_id)

        if state is None:
            devices.append({
                'id': entity_id,
                'error_code': ERR_DEVICE_UNREACHABLE
            })
            continue

        entity = YandexEntity(hass, data.config, state)
        if not entity.should_expose:
            _LOGGER.warning(
                f'State requested for unexposed entity {entity.entity_id}. Please either expose the entity via '
                f'filters in component configuration or delete the device from Yandex.'
            )

        devices.append(entity.query_serialize())

    return {'devices': devices}


@HANDLERS.register('/user/devices/action')
async def async_devices_execute(hass: HomeAssistant, data: RequestData, message: DeviceActionRequest) -> dict[str, Any]:
    """Handle /user/devices/action request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-action-docpage/
    """
    devices = []

    for device in message['payload']['devices']:
        entity_id = device['id']
        state = hass.states.get(entity_id)

        if state is None or state.state == STATE_UNAVAILABLE:
            devices.append({
                'id': entity_id,
                'error_code': ERR_DEVICE_UNREACHABLE,
            })
            continue

        entity = YandexEntity(hass, data.config, state)

        capabilities_result = []
        for capability in device['capabilities']:
            try:
                value = await entity.execute(data, capability)
            except (SmartHomeError, SmartHomeUserError) as e:
                if isinstance(e, SmartHomeError):
                    _LOGGER.error(f'{e.code}: {e.message}')

                capabilities_result.append({
                    'type': capability['type'],
                    'state': {
                        'instance': capability['state']['instance'],
                        'action_result': {
                            'status': 'ERROR',
                            'error_code': e.code
                        }
                    }
                })
                continue

            hass.bus.async_fire(
                EVENT_DEVICE_ACTION, {ATTR_ENTITY_ID: entity_id, 'capability': capability},
                context=data.context,
            )

            result = {
                'type': capability['type'],
                'state': {
                    'instance': capability['state']['instance'],
                    'action_result': {
                        'status': 'DONE',
                    }
                }
            }
            if value:
                result['state']['value'] = value

            capabilities_result.append(result)

        devices.append({
            'id': entity_id,
            'capabilities': capabilities_result
        })

    return {'devices': devices}


# noinspection PyUnusedLocal
@HANDLERS.register('/user/unlink')
async def async_devices_disconnect(hass: HomeAssistant, data: RequestData, message: dict[str, Any]):
    """Handle /user/unlink request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/unlink-docpage/
    """
    return None
