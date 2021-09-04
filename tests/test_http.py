from unittest.mock import patch

from homeassistant.components import http
from homeassistant.components.demo.light import DemoLight
from homeassistant.components.demo.sensor import DemoSensor
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT
from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_UNAUTHORIZED,
    TEMP_CELSIUS,
)
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import patch_yaml_files

from custom_components.yandex_smart_home import DOMAIN, async_setup, async_setup_entry, async_unload_entry
from custom_components.yandex_smart_home.http import (
    YandexSmartHomePingView,
    YandexSmartHomeUnauthorizedView,
    YandexSmartHomeView,
)

from . import REQ_ID


@pytest.fixture
def hass_platform(loop, hass, config_entry):
    demo_sensor = DemoSensor(
        unique_id='outside_temp',
        name='Outside Temperature',
        state=15.6,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        unit_of_measurement=TEMP_CELSIUS,
        battery=None
    )
    demo_sensor.hass = hass
    demo_sensor.entity_id = 'sensor.outside_temp'

    demo_light = DemoLight(
        unique_id='light_kitchen',
        name='Kitchen Light',
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = 'light.kitchen'

    loop.run_until_complete(
        demo_sensor.async_update_ha_state()
    )
    loop.run_until_complete(
        demo_light.async_update_ha_state()
    )

    loop.run_until_complete(
        async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    )
    loop.run_until_complete(
        hass.async_block_till_done()
    )

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None), patch_yaml_files({
        YAML_CONFIG_FILE: 'yandex_smart_home:'
    }):
        loop.run_until_complete(async_setup(hass, {DOMAIN: {}}))
        loop.run_until_complete(async_setup_entry(hass, config_entry))

    return hass


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
                    'type': 'devices.capabilities.on_off',
                    'retrievable': True,
                    'reportable': False
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
                    'type': 'devices.capabilities.color_setting',
                    'retrievable': True,
                    'reportable': False,
                    'parameters': {
                        'color_model': 'rgb',
                        'temperature_k': {'min': 2000, 'max': 6535}
                    }
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
