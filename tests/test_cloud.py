from asyncio import TimeoutError
import json
from typing import Any
from unittest.mock import patch

from aiohttp import WSMessage, WSMsgType
from homeassistant import core
from homeassistant.components import switch
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import DATA_CLIENTSESSION
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, YandexSmartHome
from custom_components.yandex_smart_home.cloud import CloudManager


class MockWSConnection:
    def __init__(self, url, headers, **kwargs):
        self.headers = headers
        self.url = url
        self.close_code: int | None = kwargs.get("ws_close_code")
        self.closed = False
        self.msg = kwargs.get("msg", []) or []
        self.send_queue = []

    def __aiter__(self):
        return self

    def __anext__(self):
        return self._async_next_msg()

    async def _async_next_msg(self):
        try:
            return self.msg.pop(0)
        except IndexError:
            raise StopAsyncIteration

    async def close(self):
        self.closed = True

    async def send_str(self, s):
        self.send_queue.append(s)


class MockSession:
    def __init__(self, aioclient, ws_close_code=None, msg=None):
        self.aioclient = aioclient
        self.ws: MockWSConnection | None = None
        self.ws_close_code = ws_close_code
        self.msg = msg

    async def ws_connect(self, *args, **kwargs):
        kwargs["ws_close_code"] = self.ws_close_code
        kwargs["msg"] = self.msg
        self.ws = MockWSConnection(*args, **kwargs)
        return self.ws


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    session: MockSession | None = None,
    aiohttp_client: Any | None = None,
):
    hass.data[DATA_CLIENTSESSION] = session or MockSession(aiohttp_client)

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


def _get_manager(hass: HomeAssistant, config_entry: MockConfigEntry) -> CloudManager:
    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_entry_data(config_entry)
    # noinspection PyProtectedMember
    return entry_data._cloud_manager


@pytest.fixture(name="mock_call_later")
def mock_call_later_fixture():
    with patch("custom_components.yandex_smart_home.cloud.async_call_later") as mock_call_later:
        yield mock_call_later


async def test_cloud_connect(hass_platform, config_entry_cloud, aioclient_mock, caplog):
    hass = hass_platform

    session = MockSession(aioclient_mock)
    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect:
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_not_called()
        assert session.ws.headers["Authorization"] == "Bearer token-foo"
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)

    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect, patch.object(session, "ws_connect", side_effect=Exception()):
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_called_once()
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)

    caplog.clear()
    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect, patch.object(session, "ws_connect", side_effect=TimeoutError()):
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_called_once()
        assert caplog.messages[-1] == "Failed to connect to Yandex Smart Home cloud"
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)

    session = MockSession(aioclient_mock, ws_close_code=1000)
    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect:
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_called_once()
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)


async def test_cloud_disconnect_connected(hass_platform, config_entry_cloud, aioclient_mock):
    hass = hass_platform
    session = MockSession(aioclient_mock)
    await async_setup_entry(hass, config_entry_cloud, session=session)
    manager = _get_manager(hass, config_entry_cloud)
    await hass.config_entries.async_unload(config_entry_cloud.entry_id)

    assert session.ws.closed is True
    assert manager._ws_active is False
    assert manager._unsub_connect is None


async def test_cloud_disconnect_scheduled(hass_platform, config_entry_cloud, aioclient_mock):
    hass = hass_platform
    session = MockSession(aioclient_mock, ws_close_code=1001)
    await async_setup_entry(hass, config_entry_cloud, session=session)
    manager = _get_manager(hass, config_entry_cloud)
    assert manager._ws_active is True
    assert manager._unsub_connect is not None

    await hass.config_entries.async_unload(config_entry_cloud.entry_id)
    await hass.async_block_till_done()

    assert session.ws.closed is True
    assert manager._ws_active is False
    assert manager._unsub_connect is None


async def test_cloud_try_reconnect(hass_platform, config_entry_cloud, aioclient_mock, mock_call_later):
    hass = hass_platform
    session = MockSession(aioclient_mock, ws_close_code=1000)

    with patch.object(session, "ws_connect", side_effect=TimeoutError()):
        await async_setup_entry(hass, config_entry_cloud, session=session)

    manager = _get_manager(hass, config_entry_cloud)

    mock_call_later.assert_called_once()
    assert manager._ws_reconnect_delay == 4

    mock_call_later.reset_mock()
    with patch.object(session, "ws_connect", side_effect=TimeoutError()):
        await manager.async_connect()
    mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 8

    for _ in range(1, 10):
        mock_call_later.reset_mock()
        with patch.object(session, "ws_connect", side_effect=TimeoutError()):
            await manager.async_connect()
        mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 180

    mock_call_later.reset_mock()
    await manager.async_connect()
    mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 4

    mock_call_later.reset_mock()
    await manager.async_disconnect()
    manager._try_reconnect()
    mock_call_later.assert_not_called()


async def test_cloud_fast_reconnect(hass_platform, config_entry_cloud, aioclient_mock, mock_call_later, caplog):
    hass = hass_platform
    session = MockSession(aioclient_mock, ws_close_code=1001)
    await async_setup_entry(hass, config_entry_cloud, session=session)
    manager = _get_manager(hass, config_entry_cloud)

    for _ in range(1, 4):
        await manager.async_connect()
        assert manager._ws_reconnect_delay == 4

    await manager.async_connect()
    assert manager._ws_reconnect_delay == 180
    assert caplog.messages[-2] == "Reconnecting too fast, next reconnection in 180 seconds"


async def test_cloud_messages_invalid_format(hass_platform, config_entry_cloud, aioclient_mock):
    hass = hass_platform

    requests = ["foo"]
    session = MockSession(aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=r) for r in requests])
    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect:
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_called_once()
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)

    requests = [json.dumps({"request_id": "req", "_action": "foo"})]
    session = MockSession(aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=r) for r in requests])
    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect:
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_called_once()
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)

    requests = [json.dumps({"request_id": "req", "action": "/user/devices/query", "message": "not_{_json"})]
    session = MockSession(aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=r) for r in requests])
    with patch(
        "custom_components.yandex_smart_home.cloud.CloudManager._try_reconnect", return_value=None
    ) as mock_reconnect:
        await async_setup_entry(hass, config_entry_cloud, session=session)
        mock_reconnect.assert_not_called()
        await hass.config_entries.async_unload(config_entry_cloud.entry_id)
        assert json.loads(session.ws.send_queue[0]) == {
            "payload": {"error_code": "INTERNAL_ERROR"},
            "request_id": "req",
        }


async def test_cloud_req_user_devices(hass_platform, config_entry_cloud, aioclient_mock):
    hass = hass_platform

    requests = [{"request_id": "req_user_devices", "action": "/user/devices"}]
    session = MockSession(
        aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=json.dumps(r)) for r in requests]
    )
    with patch("homeassistant.config_entries.ConfigEntries.async_update_entry"):  # prevent reloading after discovery
        await async_setup_entry(hass, config_entry_cloud, session=session)

    assert json.loads(session.ws.send_queue[0]) == {
        "request_id": "req_user_devices",
        "payload": {
            "user_id": "i-test",
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
                    "capabilities": [],
                    "properties": [
                        {
                            "type": "devices.properties.event",
                            "retrievable": True,
                            "reportable": True,
                            "parameters": {"instance": "open", "events": [{"value": "opened"}, {"value": "closed"}]},
                        }
                    ],
                    "device_info": {"model": "binary_sensor.front_door"},
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
                                "range": {"min": 1, "max": 100, "precision": 1},
                                "unit": "unit.percent",
                            },
                        },
                        {"type": "devices.capabilities.on_off", "retrievable": True, "reportable": True},
                    ],
                    "properties": [],
                    "device_info": {
                        "model": "light.kitchen",
                    },
                },
            ],
        },
    }


async def test_cloud_req_user_devices_query(hass_platform, config_entry_cloud, aioclient_mock):
    hass = hass_platform

    requests = [
        {
            "request_id": "req_user_devices_query_1",
            "action": "/user/devices/query",
            "message": json.dumps({"devices": [{"id": "sensor.outside_temp"}]}),
        },
        {
            "request_id": "req_user_devices_query_2",
            "action": "/user/devices/query",
            "message": json.dumps({"devices": [{"id": "sensor.not_existed"}]}),
        },
    ]
    session = MockSession(
        aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=json.dumps(r)) for r in requests]
    )
    await async_setup_entry(hass, config_entry_cloud, session=session)

    assert json.loads(session.ws.send_queue[0]) == {
        "request_id": "req_user_devices_query_1",
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
    assert json.loads(session.ws.send_queue[1]) == {
        "request_id": "req_user_devices_query_2",
        "payload": {"devices": [{"id": "sensor.not_existed", "error_code": "DEVICE_UNREACHABLE"}]},
    }


async def test_cloud_req_user_devices_action(hass_platform, config_entry_cloud, aioclient_mock):
    hass = hass_platform

    requests = [
        {
            "request_id": "req_user_devices_action",
            "action": "/user/devices/action",
            "message": json.dumps(
                {
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
            ),
        }
    ]

    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SWITCH],
    ):
        await async_setup_component(hass, core.DOMAIN, {})
        await async_setup_component(hass, switch.DOMAIN, {switch.DOMAIN: {"platform": "demo"}})
        await hass.async_block_till_done()

    assert hass.states.get("switch.ac").state == "off"

    session = MockSession(
        aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=json.dumps(r)) for r in requests]
    )
    await async_setup_entry(hass, config_entry_cloud, session=session)
    await hass.async_block_till_done()

    assert json.loads(session.ws.send_queue[0]) == {
        "request_id": "req_user_devices_action",
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

    assert hass.states.get("switch.ac").state == "on"
