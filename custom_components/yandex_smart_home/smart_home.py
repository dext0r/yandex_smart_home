"""Support for Yandex Smart Home API."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util.decorator import Registry
from homeassistant.helpers import entity_registry, device_registry

from .const import (
    ERR_INTERNAL_ERROR, ERR_DEVICE_UNREACHABLE,
    ERR_DEVICE_NOT_FOUND
)
from .helpers import RequestData, YandexEntity
from .error import SmartHomeError

HANDLERS = Registry()
_LOGGER = logging.getLogger(__name__)


async def async_handle_message(hass, config, user_id, request_id, action,
                               message):
    """Handle incoming API messages."""
    data = RequestData(config, user_id, request_id)

    response = await _process(hass, data, action, message)

    if response and 'payload' in response and 'error_code' in response['payload']:
        _LOGGER.error('Error handling message %s: %s', message, response['payload'])

    return response


async def _process(hass, data, action, message):
    """Process a message."""
    handler = HANDLERS.get(action)

    if handler is None:
        return {
            'request_id': data.request_id,
            'payload': {'error_code': ERR_INTERNAL_ERROR}
        }

    try:
        result = await handler(hass, data, message)
    except SmartHomeError as err:
        _LOGGER.error('Handler process error: %s %s', err.code, err.message)
        return {
            'request_id': data.request_id,
            'payload': {'error_code': err.code}
        }
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception('Handler process unexpected error')
        return {
            'request_id': data.request_id,
            'payload': {'error_code': ERR_INTERNAL_ERROR}
        }

    if result is None:
        if data.request_id is None:
            return None
        else:
            return {'request_id': data.request_id}

    return {'request_id': data.request_id, 'payload': result}


# noinspection PyUnusedLocal
@HANDLERS.register('/user/devices')
async def async_devices_sync(hass: HomeAssistant, data: RequestData, message: dict[str, Any]):
    """Handle /user/devices request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/get-devices-docpage/
    """
    devices = []
    entity_reg = await entity_registry.async_get_registry(hass)
    dev_reg = await device_registry.async_get_registry(hass)

    for state in hass.states.async_all():
        entity, serialized = YandexEntity(hass, data.config, state), None
        if not entity.should_expose:
            continue

        if entity.supported:
            serialized = await entity.devices_serialize(entity_reg, dev_reg)

        if serialized is None:
            _LOGGER.debug(f'Unsupported entity: {entity.state!r}')
            continue

        devices.append(serialized)

    response = {
        'user_id': data.context.user_id,
        'devices': devices,
    }

    return response


@HANDLERS.register('/user/devices/query')
async def async_devices_query(hass, data, message):
    """Handle /user/devices/query request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-devices-query-docpage/
    """
    devices = []
    for device in message.get('devices', []):
        devid = device['id']
        state = hass.states.get(devid)

        if not state:
            # If we can't find a state, the device is unreachable
            devices.append({
                'id': devid,
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
async def handle_devices_execute(hass, data, message):
    """Handle /user/devices/action request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-action-docpage/
    """
    entities = {}
    devices = {}
    results = {}
    action_errors = {}

    for device in message['payload']['devices']:
        entity_id = device['id']
        devices[entity_id] = device

        if entity_id not in entities:
            state = hass.states.get(entity_id)

            if state is None:
                results[entity_id] = {
                    'id': entity_id,
                    'error_code': ERR_DEVICE_NOT_FOUND,
                }
                continue

            entities[entity_id] = YandexEntity(hass, data.config, state)

        for capability in device['capabilities']:
            try:
                await entities[entity_id].execute(data,
                                                  capability.get('type', ''),
                                                  capability.get('state', {}))
            except SmartHomeError as err:
                _LOGGER.error('%s: %s' % (err.code, err.message))
                if entity_id not in action_errors:
                    action_errors[entity_id] = {}
                action_errors[entity_id][capability['type']] = err.code

    final_results = list(results.values())

    for entity in entities.values():
        if entity.entity_id in results:
            continue

        entity.async_update()

        capabilities = []
        for capability in devices[entity.entity_id]['capabilities']:
            if capability['state'] is None or 'instance' not in capability[
                    'state']:
                continue
            if entity.entity_id in action_errors and capability['type'] in \
                    action_errors[entity.entity_id]:
                capabilities.append({
                    'type': capability['type'],
                    'state': {
                        'instance': capability['state']['instance'],
                        'action_result': {
                            'status': 'ERROR',
                            'error_code': action_errors[entity.entity_id][
                                capability['type']],
                        }
                    }
                })
            else:
                capabilities.append({
                    'type': capability['type'],
                    'state': {
                        'instance': capability['state']['instance'],
                        'action_result': {
                            'status': 'DONE',
                        }
                    }
                })

        final_results.append({
            'id': entity.entity_id,
            'capabilities': capabilities,
        })

    return {'devices': final_results}


# noinspection PyUnusedLocal
@HANDLERS.register('/user/unlink')
async def async_devices_disconnect(hass, data, message):
    """Handle /user/unlink request.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/unlink-docpage/
    """
    return None
