from http import HTTPStatus
from unittest.mock import patch

from homeassistant import core
from homeassistant.auth.models import Credentials
from homeassistant.components import demo
from homeassistant.const import CONF_ID, CONF_PLATFORM, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.yandex_smart_home import DOMAIN, SmartHomePlatform
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_CONNECTION_TYPE,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_SKILL,
    CONF_USER_ID,
    ConnectionType,
    EntityFilterSource,
)

from . import REQ_ID

CLIENT_ID_YANDEX = "https://social.yandex.net"


@pytest.fixture
async def hass_access_token_yandex(
    hass: HomeAssistant, hass_admin_user: MockUser, hass_admin_credential: Credentials
) -> str:
    refresh_token = await hass.auth.async_create_refresh_token(
        hass_admin_user, CLIENT_ID_YANDEX, credential=hass_admin_credential
    )
    return hass.auth.async_create_access_token(refresh_token)


async def test_http_anonymous_views(
    hass_platform_direct: HomeAssistant, aiohttp_client: ClientSessionGenerator
) -> None:
    http_client = await aiohttp_client(hass_platform_direct.http.app)
    response = await http_client.head("/api/yandex_smart_home/v1.0")
    assert response.status == HTTPStatus.OK

    response = await http_client.get("/api/yandex_smart_home/v1.0/ping")
    assert response.status == HTTPStatus.OK
    assert await response.text() == "Yandex Smart Home"


async def test_http_unauthorized(hass_platform_direct: HomeAssistant, aiohttp_client: ClientSessionGenerator) -> None:
    http_client = await aiohttp_client(hass_platform_direct.http.app)

    response = await http_client.get("/api/yandex_smart_home/v1.0/user/unlink")
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_http_unknown_platform(
    hass_platform_direct: HomeAssistant, hass_client: ClientSessionGenerator, caplog: pytest.LogCaptureFixture
) -> None:
    http_client = await hass_client()
    response = await http_client.post("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert caplog.messages[-2] == "Request from unsupported platform, client_id: https://example.com/app"


async def test_http_config_entry_selection(
    hass_platform: HomeAssistant,
    hass_client: ClientSessionGenerator,
    aiohttp_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    issue_registry: ir.IssueRegistry,
) -> None:
    hass = hass_platform

    await async_setup_component(hass, DOMAIN, {})

    user_foo = MockUser(name="User Foo").add_to_hass(hass)
    http_client_foo = await hass_client(
        hass.auth.async_create_access_token(await hass.auth.async_create_refresh_token(user_foo, CLIENT_ID_YANDEX))
    )

    user_bar = MockUser(name="User Bar").add_to_hass(hass)
    http_client_bar = await hass_client(
        hass.auth.async_create_access_token(await hass.auth.async_create_refresh_token(user_bar, CLIENT_ID_YANDEX))
    )

    user_baz = MockUser(name="User Baz").add_to_hass(hass)
    http_client_baz = await hass_client(
        hass.auth.async_create_access_token(await hass.auth.async_create_refresh_token(user_baz, CLIENT_ID_YANDEX))
    )

    caplog.clear()
    response = await http_client_foo.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert caplog.messages[-2] == "Failed to find Yandex Smart Home integration for request from yandex (user User Foo)"
    assert issue_registry.async_get_issue(DOMAIN, f"missing_integration_yandex_{user_foo.id}") is not None

    entry_foo = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["light.kitchen"]},
            CONF_SKILL: {
                CONF_USER_ID: user_foo.id,
                CONF_ID: "foo",
                CONF_TOKEN: "token",
            },
        },
    )
    entry_foo.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_foo.entry_id)
    response = await http_client_foo.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert (await response.json())["payload"]["user_id"] == user_foo.id
    assert [d["id"] for d in (await response.json())["payload"]["devices"]] == ["light.kitchen"]
    assert issue_registry.async_get_issue(DOMAIN, f"missing_integration_yandex_{user_foo.id}") is None

    # fallback to another user config entry
    response = await http_client_bar.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert (await response.json())["payload"]["user_id"] == user_foo.id

    entry_baz = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["sensor.outside_temp"]},
            CONF_SKILL: {
                CONF_USER_ID: user_baz.id,
                CONF_ID: "foo",
                CONF_TOKEN: "token",
            },
        },
    )
    entry_baz.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_baz.entry_id)

    # two entry, strict selection
    response = await http_client_bar.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert issue_registry.async_get_issue(DOMAIN, f"missing_integration_yandex_{user_bar.id}") is not None

    response = await http_client_baz.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert (await response.json())["payload"]["user_id"] == user_baz.id
    assert [d["id"] for d in (await response.json())["payload"]["devices"]] == ["sensor.outside_temp"]


async def test_http_config_entry_no_skill(
    hass_platform: HomeAssistant,
    hass_client: ClientSessionGenerator,
    aiohttp_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hass = hass_platform

    await async_setup_component(hass, DOMAIN, {})

    user_foo = MockUser(name="User Foo").add_to_hass(hass)
    http_client_foo = await hass_client(
        hass.auth.async_create_access_token(await hass.auth.async_create_refresh_token(user_foo, CLIENT_ID_YANDEX))
    )

    user_bar = MockUser(name="User Bar").add_to_hass(hass)
    http_client_bar = await hass_client(
        hass.auth.async_create_access_token(await hass.auth.async_create_refresh_token(user_bar, CLIENT_ID_YANDEX))
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={CONF_FILTER_SOURCE: EntityFilterSource.YAML},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    response = await http_client_foo.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert (await response.json())["payload"]["user_id"] == user_foo.id
    response = await http_client_bar.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert (await response.json())["payload"]["user_id"] == user_bar.id


async def test_http_user_unlink(
    hass_platform_direct: HomeAssistant, hass_client: ClientSessionGenerator, hass_access_token_yandex: str
) -> None:
    http_client = await hass_client(hass_access_token_yandex)
    response = await http_client.post("/api/yandex_smart_home/v1.0/user/unlink", headers={"X-Request-Id": REQ_ID})
    assert response.status == HTTPStatus.OK
    assert await response.json() == {"request_id": REQ_ID}


async def test_http_user_devices(
    hass_platform_direct: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_access_token_yandex: str,
    hass_admin_user: MockUser,
) -> None:
    http_client = await hass_client(hass_access_token_yandex)
    response = await http_client.get("/api/yandex_smart_home/v1.0/user/devices", headers={"X-Request-Id": REQ_ID})

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
                            "reportable": True,
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
                            "reportable": True,
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
                            "reportable": True,
                            "parameters": {"color_model": "rgb", "temperature_k": {"min": 1500, "max": 6500}},
                        },
                        {
                            "type": "devices.capabilities.range",
                            "retrievable": True,
                            "reportable": True,
                            "parameters": {
                                "instance": "brightness",
                                "random_access": True,
                                "range": {"min": 1.0, "max": 100.0, "precision": 1.0},
                                "unit": "unit.percent",
                            },
                        },
                        {"type": "devices.capabilities.on_off", "retrievable": True, "reportable": True},
                    ],
                    "device_info": {
                        "model": "light.kitchen",
                    },
                },
            ],
        },
    }


async def test_http_user_devices_query(
    hass_platform_direct: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_access_token_yandex: str,
) -> None:
    http_client = await hass_client(hass_access_token_yandex)
    response = await http_client.post(
        "/api/yandex_smart_home/v1.0/user/devices/query",
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
        "/api/yandex_smart_home/v1.0/user/devices/query",
        json={"devices": [{"id": "sensor.not_existed"}]},
        headers={"X-Request-Id": REQ_ID},
    )
    assert response.status == HTTPStatus.OK
    assert await response.json() == {
        "request_id": REQ_ID,
        "payload": {"devices": [{"id": "sensor.not_existed", "error_code": "DEVICE_UNREACHABLE"}]},
    }


async def test_http_user_devices_action(
    hass_platform_direct: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_access_token_yandex: str,
) -> None:
    hass = hass_platform_direct

    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SWITCH],
    ):
        await async_setup_component(hass, core.DOMAIN, {})
        await async_setup_component(hass, demo.DOMAIN, {})
        await hass.async_block_till_done()

    state = hass.states.get("switch.ac")
    assert state is not None
    assert state.state == "off"

    http_client = await hass_client(hass_access_token_yandex)

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
        "/api/yandex_smart_home/v1.0/user/devices/action", json=payload, headers={"X-Request-Id": REQ_ID}
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
    state = hass.states.get("switch.ac")
    assert state is not None
    assert state.state == "on"
