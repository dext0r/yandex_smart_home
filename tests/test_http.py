from http import HTTPStatus
import logging
from unittest.mock import patch

from homeassistant import core
from homeassistant.components import http, switch
from homeassistant.const import Platform
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components import yandex_smart_home
from custom_components.yandex_smart_home import DOMAIN, const
from custom_components.yandex_smart_home.http import (
    YandexSmartHomePingView,
    YandexSmartHomeUnauthorizedView,
    YandexSmartHomeView,
)

from . import REQ_ID


@pytest.fixture(autouse=True)
def debug_logging():
    logging.getLogger("custom_components.yandex_smart_home.http").setLevel(logging.DEBUG)


async def test_http_request(hass, aiohttp_client):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "test",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
            },
        },
        options={},
    )

    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    await yandex_smart_home.async_setup(hass, {})

    http_client = await aiohttp_client(hass.http.app)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert await response.text() == "Error: Integration is not enabled"

    await yandex_smart_home.async_setup_entry(hass, config_entry)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert await response.text() == "Error: Integration uses cloud connection"


async def test_http_unauthorized_view(hass_platform, aiohttp_client, config_entry):
    http_client = await aiohttp_client(hass_platform.http.app)
    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTPStatus.OK

    await yandex_smart_home.async_unload_entry(hass_platform, config_entry)
    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_http_ping_view(hass_platform, aiohttp_client, config_entry, expected_lingering_timers):
    http_client = await aiohttp_client(hass_platform.http.app)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.OK
    assert await response.text() == "OK: 2"

    await yandex_smart_home.async_unload_entry(hass_platform, config_entry)
    response = await http_client.get(YandexSmartHomePingView.url)
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE


async def test_http_unloaded_config_entry(hass_platform, hass_client, config_entry):
    http_client = await hass_client()

    await yandex_smart_home.async_unload_entry(hass_platform, config_entry)
    response = await http_client.get(YandexSmartHomeView.url + "/user/unlink")
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert await response.text() == "Error: Integration is not enabled"


async def test_http_unauthorized(hass_platform, aiohttp_client, socket_enabled):
    http_client = await aiohttp_client(hass_platform.http.app)

    response = await http_client.get(YandexSmartHomeView.url + "/user/unlink")
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_http_user_unlink(hass_platform, hass_client):
    http_client = await hass_client()
    response = await http_client.post(YandexSmartHomeView.url + "/user/unlink", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert await response.json() == {"request_id": REQ_ID}


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_http_user_devices(hass_platform, hass_client, hass_admin_user: MockUser, expected_lingering_timers):
    http_client = await hass_client()
    response = await http_client.get(YandexSmartHomeView.url + "/user/devices", headers={"X-Request-Id": REQ_ID})

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
                    "capabilities": [],
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
                    "properties": [],
                    "device_info": {
                        "model": "light.kitchen",
                    },
                },
            ],
        },
    }


async def test_http_user_devices_query(hass_platform, hass_client):
    http_client = await hass_client()
    response = await http_client.post(
        YandexSmartHomeView.url + "/user/devices/query",
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
                    "capabilities": [],
                    "properties": [
                        {"type": "devices.properties.float", "state": {"instance": "temperature", "value": 15.6}}
                    ],
                }
            ]
        },
    }

    response = await http_client.post(
        YandexSmartHomeView.url + "/user/devices/query",
        json={"devices": [{"id": "sensor.not_existed"}]},
        headers={"X-Request-Id": REQ_ID},
    )
    assert response.status == HTTPStatus.OK
    assert await response.json() == {
        "request_id": REQ_ID,
        "payload": {"devices": [{"id": "sensor.not_existed", "error_code": "DEVICE_UNREACHABLE"}]},
    }


async def test_http_user_devices_action(hass_platform, hass_client):
    hass = hass_platform

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
        YandexSmartHomeView.url + "/user/devices/action", json=payload, headers={"X-Request-Id": REQ_ID}
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
