from http import HTTPStatus
from unittest.mock import patch

from homeassistant import core
from homeassistant.components import switch
from homeassistant.const import Platform
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockUser

from custom_components.yandex_smart_home import DOMAIN
from custom_components.yandex_smart_home.http import (
    YandexSmartHomeAPIView,
    YandexSmartHomePingView,
    YandexSmartHomeUnauthorizedView,
)

from . import REQ_ID, test_cloud


async def test_http_request_with_yaml_config(hass, aiohttp_client):
    await async_setup_component(hass, DOMAIN, {})

    http_client = await aiohttp_client(hass.http.app)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert await response.text() == "Error: Integration is not enabled or use cloud connection"


async def test_http_request_with_cloud(hass_platform, aiohttp_client, config_entry_cloud):
    await test_cloud.async_setup_entry(hass_platform, config_entry_cloud, aiohttp_client=aiohttp_client)

    http_client = await aiohttp_client(hass_platform.http.app)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert await response.text() == "Error: Integration is not enabled or use cloud connection"


async def test_http_unauthorized_view(hass_platform_direct, aiohttp_client, config_entry_direct):
    http_client = await aiohttp_client(hass_platform_direct.http.app)
    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTPStatus.OK

    await hass_platform_direct.config_entries.async_unload(config_entry_direct.entry_id)
    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE


async def test_http_ping_view(hass_platform_direct, aiohttp_client, config_entry_direct):
    http_client = await aiohttp_client(hass_platform_direct.http.app)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.OK
    assert await response.text() == "OK: 3"

    await hass_platform_direct.config_entries.async_unload(config_entry_direct.entry_id)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE


async def test_http_unloaded_config_entry(hass_platform_direct, hass_client, config_entry_direct):
    http_client = await hass_client()

    await hass_platform_direct.config_entries.async_unload(config_entry_direct.entry_id)
    response = await http_client.get(YandexSmartHomeAPIView.url + "/user/unlink")
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert await response.text() == "Error: Integration is not enabled or use cloud connection"


async def test_http_unauthorized(hass_platform_direct, aiohttp_client):
    http_client = await aiohttp_client(hass_platform_direct.http.app)

    response = await http_client.get(YandexSmartHomeAPIView.url + "/user/unlink")
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_http_user_unlink(hass_platform_direct, hass_client):
    http_client = await hass_client()
    response = await http_client.post(YandexSmartHomeAPIView.url + "/user/unlink", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert await response.json() == {"request_id": REQ_ID}


async def test_http_user_devices(hass_platform_direct, hass_client, hass_admin_user: MockUser):
    http_client = await hass_client()
    response = await http_client.get(YandexSmartHomeAPIView.url + "/user/devices", headers={"X-Request-Id": REQ_ID})

    assert response.status == HTTPStatus.OK
    assert await response.json() == {
        "request_id": REQ_ID,
        "payload": {
            "user_id": hass_admin_user.id,
            "devices": [
                {
                    "id": "sensor.outside_temp",
                    "name": "Температура за бортом",
                    "type": "devices.types.sensor.climate",
                    "properties": [
                        {
                            "type": "devices.properties.float",
                            "retrievable": True,
                            "reportable": False,
                            "parameters": {"instance": "temperature", "unit": "unit.temperature.celsius"},
                        }
                    ],
                    "device_info": {
                        "model": "sensor.outside_temp",
                    },
                },
                {
                    "id": "binary_sensor.front_door",
                    "name": "Front Door",
                    "type": "devices.types.sensor.open",
                    "properties": [
                        {
                            "type": "devices.properties.event",
                            "retrievable": True,
                            "reportable": False,
                            "parameters": {
                                "instance": "open",
                                "events": [{"value": "opened"}, {"value": "closed"}],
                            },
                        }
                    ],
                    "device_info": {
                        "model": "binary_sensor.front_door",
                    },
                },
                {
                    "id": "light.kitchen",
                    "name": "Kitchen Light",
                    "type": "devices.types.light",
                    "capabilities": [
                        {
                            "type": "devices.capabilities.color_setting",
                            "retrievable": True,
                            "reportable": False,
                            "parameters": {"color_model": "rgb", "temperature_k": {"min": 1500, "max": 6500}},
                        },
                        {
                            "type": "devices.capabilities.range",
                            "retrievable": True,
                            "reportable": False,
                            "parameters": {
                                "instance": "brightness",
                                "random_access": True,
                                "range": {"min": 1.0, "max": 100.0, "precision": 1.0},
                                "unit": "unit.percent",
                            },
                        },
                        {"type": "devices.capabilities.on_off", "retrievable": True, "reportable": False},
                    ],
                    "device_info": {
                        "model": "light.kitchen",
                    },
                },
            ],
        },
    }


async def test_http_user_devices_query(hass_platform_direct, hass_client):
    http_client = await hass_client()
    response = await http_client.post(
        YandexSmartHomeAPIView.url + "/user/devices/query",
        json={"devices": [{"id": "sensor.outside_temp"}]},
        headers={"X-Request-Id": REQ_ID},
    )
    assert response.status == HTTPStatus.OK
    assert await response.json() == {
        "request_id": REQ_ID,
        "payload": {
            "devices": [
                {
                    "id": "sensor.outside_temp",
                    "properties": [
                        {"type": "devices.properties.float", "state": {"instance": "temperature", "value": 15.6}}
                    ],
                }
            ]
        },
    }

    response = await http_client.post(
        YandexSmartHomeAPIView.url + "/user/devices/query",
        json={"devices": [{"id": "sensor.not_existed"}]},
        headers={"X-Request-Id": REQ_ID},
    )
    assert response.status == HTTPStatus.OK
    assert await response.json() == {
        "request_id": REQ_ID,
        "payload": {"devices": [{"id": "sensor.not_existed", "error_code": "DEVICE_UNREACHABLE"}]},
    }


async def test_http_user_devices_action(hass_platform_direct, hass_client):
    hass = hass_platform_direct

    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SWITCH],
    ):
        await async_setup_component(hass, core.DOMAIN, {})
        await async_setup_component(hass, switch.DOMAIN, {switch.DOMAIN: {"platform": "demo"}})
        await hass.async_block_till_done()

    assert hass.states.get("switch.ac").state == "off"

    http_client = await hass_client()

    payload = {
        "payload": {
            "devices": [
                {
                    "id": "switch.ac",
                    "capabilities": [
                        {"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}}
                    ],
                }
            ]
        }
    }
    response = await http_client.post(
        YandexSmartHomeAPIView.url + "/user/devices/action", json=payload, headers={"X-Request-Id": REQ_ID}
    )
    assert response.status == HTTPStatus.OK
    assert await response.json() == {
        "request_id": REQ_ID,
        "payload": {
            "devices": [
                {
                    "id": "switch.ac",
                    "capabilities": [
                        {
                            "type": "devices.capabilities.on_off",
                            "state": {"instance": "on", "action_result": {"status": "DONE"}},
                        }
                    ],
                }
            ]
        },
    }

    await hass.async_block_till_done()
    assert hass.states.get("switch.ac").state == "on"
