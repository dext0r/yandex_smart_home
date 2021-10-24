from homeassistant.const import HTTP_NOT_FOUND, HTTP_OK, HTTP_SERVICE_UNAVAILABLE, HTTP_UNAUTHORIZED
from homeassistant.setup import async_setup_component

from custom_components.yandex_smart_home import async_unload_entry
from custom_components.yandex_smart_home.http import (
    YandexSmartHomePingView,
    YandexSmartHomeUnauthorizedView,
    YandexSmartHomeView,
)

from . import REQ_ID


async def test_unauthorized_view(hass_platform, aiohttp_client, config_entry):
    http_client = await aiohttp_client(hass_platform.http.app)
    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTP_OK

    await async_unload_entry(hass_platform, config_entry)
    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTP_NOT_FOUND


async def test_ping(hass_platform, aiohttp_client, config_entry):
    http_client = await aiohttp_client(hass_platform.http.app)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTP_OK
    assert await response.text() == 'OK: 2'

    await async_unload_entry(hass_platform, config_entry)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTP_SERVICE_UNAVAILABLE


async def test_smart_home_view_unloaded(hass_platform, hass_client, config_entry):
    http_client = await hass_client()

    await async_unload_entry(hass_platform, config_entry)
    response = await http_client.get(YandexSmartHomeView.url + '/user/unlink')
    assert response.status == HTTP_NOT_FOUND


async def test_smart_home_view_unauthorized(hass_platform, aiohttp_client):
    http_client = await aiohttp_client(hass_platform.http.app)

    response = await http_client.get(YandexSmartHomeView.url + '/user/unlink')
    assert response.status == HTTP_UNAUTHORIZED


async def test_user_unlink(hass_platform, hass_client):
    http_client = await hass_client()
    response = await http_client.post(
        YandexSmartHomeView.url + '/user/unlink',
        headers={'X-Request-Id': REQ_ID}
    )
    assert response.status == HTTP_OK
    assert await response.json() == {'request_id': REQ_ID}


async def test_user_devices(hass_platform, hass_client, hass_admin_user):
    http_client = await hass_client()
    response = await http_client.get(
        YandexSmartHomeView.url + '/user/devices',
        headers={'X-Request-Id': REQ_ID}
    )

    assert response.status == HTTP_OK
    assert await response.json() == {
        'request_id': REQ_ID,
        'payload': {
            'user_id': hass_admin_user.id,
            'devices': [{
                'id': 'sensor.outside_temp',
                'name': 'Outside Temperature',
                'type': 'devices.types.sensor',
                'capabilities': [],
                'properties': [{
                    'type': 'devices.properties.float',
                    'retrievable': True,
                    'reportable': False,
                    'parameters': {
                        'instance': 'temperature',
                        'unit': 'unit.temperature.celsius'
                    }
                }],
                'device_info': {
                    'model': 'sensor.outside_temp',
                }
            }, {
                'id': 'light.kitchen',
                'name': 'Kitchen Light',
                'type': 'devices.types.light',
                'capabilities': [{
                    'type': 'devices.capabilities.color_setting',
                    'retrievable': True,
                    'reportable': False,
                    'parameters': {
                        'color_model': 'rgb',
                        'temperature_k': {'min': 2000, 'max': 6535}
                    }
                }, {
                    'type': 'devices.capabilities.range',
                    'retrievable': True,
                    'reportable': False,
                    'parameters': {
                        'instance': 'brightness',
                        'random_access': True,
                        'range': {
                            'min': 1,
                            'max': 100,
                            'precision': 1
                        },
                        'unit': 'unit.percent'
                    }
                }, {
                    'type': 'devices.capabilities.on_off',
                    'retrievable': True,
                    'reportable': False
                }],
                'properties': [],
                'device_info': {
                    'model': 'light.kitchen',
                }
            }]
        }
    }


async def test_user_devices_query(hass_platform, hass_client):
    http_client = await hass_client()
    response = await http_client.post(
        YandexSmartHomeView.url + '/user/devices/query',
        json={'devices': [{'id': 'sensor.outside_temp'}]},
        headers={'X-Request-Id': REQ_ID}
    )
    assert response.status == HTTP_OK
    assert await response.json() == {
        'request_id': REQ_ID,
        'payload': {
            'devices': [{
                'id': 'sensor.outside_temp',
                'capabilities': [],
                'properties': [{
                    'type': 'devices.properties.float',
                    'state': {'instance': 'temperature', 'value': 15.6}
                }]
            }]
        }
    }

    response = await http_client.post(
        YandexSmartHomeView.url + '/user/devices/query',
        json={'devices': [{'id': 'sensor.not_existed'}]},
        headers={'X-Request-Id': REQ_ID}
    )
    assert response.status == HTTP_OK
    assert await response.json() == {
        'request_id': REQ_ID,
        'payload': {
            'devices': [{
                'id': 'sensor.not_existed',
                'error_code': 'DEVICE_UNREACHABLE'
            }]
        }
    }


async def test_user_devices_action(hass_platform, hass_client):
    await async_setup_component(hass_platform, 'switch', {'switch': {'platform': 'demo'}})
    await hass_platform.async_block_till_done()

    assert hass_platform.states.get('switch.ac').state == 'off'

    http_client = await hass_client()

    payload = {
        'payload': {
            'devices': [{
                'id': 'switch.ac',
                'capabilities': [{
                    'type': 'devices.capabilities.on_off',
                    'state': {
                        'instance': 'on',
                        'value': True
                    }
                }]
            }]
        }
    }
    response = await http_client.post(
        YandexSmartHomeView.url + '/user/devices/action',
        json=payload,
        headers={'X-Request-Id': REQ_ID}
    )
    assert response.status == HTTP_OK
    assert await response.json() == {
        'request_id': REQ_ID,
        'payload': {
            'devices': [{
                'id': 'switch.ac',
                'capabilities': [{
                    'type': 'devices.capabilities.on_off',
                    'state': {
                        'instance': 'on',
                        'action_result': {'status': 'DONE'}
                    }
                }]
            }]
        }
    }

    await hass_platform.async_block_till_done()
    assert hass_platform.states.get('switch.ac').state == 'on'
