from __future__ import annotations

from asyncio import TimeoutError
import json
from unittest.mock import patch

from aiohttp import WSMessage, WSMsgType
from homeassistant import core
from homeassistant.components import switch
from homeassistant.const import Platform
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.cloud import CloudManager

from . import MockConfig


class MockWSConnection:
    def __init__(self, url, headers, **kwargs):
        self.headers = headers
        self.url = url
        self.close_code: int | None = kwargs.get("ws_close_code")
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
        pass

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


@pytest.fixture
def config():
    entry = MockConfigEntry(
        data={
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "test_instance",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
            },
        }
    )
    return MockConfig(entry=entry)


@pytest.fixture(autouse=True, name="mock_call_later")
def mock_call_later_fixture():
    with patch("custom_components.yandex_smart_home.cloud.async_call_later") as mock_call_later:
        yield mock_call_later


# noinspection PyTypeChecker
async def test_cloud_connect(hass_platform_cloud_connection, config, aioclient_mock, caplog):
    hass = hass_platform_cloud_connection

    session = MockSession(aioclient_mock)
    manager = CloudManager(hass, config, session)
    with patch.object(manager, "_try_reconnect", return_value=None) as mock_reconnect:
        await manager.connect()

        mock_reconnect.assert_not_called()
        assert session.ws.headers["Authorization"] == "Bearer foo"

    session = MockSession(aioclient_mock)
    manager = CloudManager(hass, config, session)
    with patch.object(session, "ws_connect", side_effect=Exception()), patch.object(
        manager, "_try_reconnect", return_value=None
    ) as mock_reconnect:
        await manager.connect()
        mock_reconnect.assert_called_once()

    caplog.clear()
    session = MockSession(aioclient_mock)
    manager = CloudManager(hass, config, session)
    with patch.object(session, "ws_connect", side_effect=TimeoutError()), patch.object(
        manager, "_try_reconnect", return_value=None
    ) as mock_reconnect:
        await manager.connect()
        mock_reconnect.assert_called_once()
        assert "Failed to connect" in caplog.records[-1].message

    session = MockSession(aioclient_mock, ws_close_code=1000)
    manager = CloudManager(hass, config, session)
    with patch.object(manager, "_try_reconnect", return_value=None) as mock_reconnect:
        await manager.connect()
        mock_reconnect.assert_called_once()


# noinspection PyTypeChecker
async def test_cloud_try_reconnect(hass_platform_cloud_connection, config, aioclient_mock, mock_call_later):
    hass = hass_platform_cloud_connection

    session = MockSession(aioclient_mock, ws_close_code=1000)
    manager = CloudManager(hass, config, session)

    with patch.object(session, "ws_connect", side_effect=TimeoutError()):
        await manager.connect()
    mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 4

    mock_call_later.reset_mock()
    with patch.object(session, "ws_connect", side_effect=TimeoutError()):
        await manager.connect()
    mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 8

    for _ in range(1, 10):
        mock_call_later.reset_mock()
        with patch.object(session, "ws_connect", side_effect=TimeoutError()):
            await manager.connect()
        mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 180

    mock_call_later.reset_mock()
    await manager.connect()
    mock_call_later.assert_called_once()

    assert manager._ws_reconnect_delay == 4

    await manager.disconnect()
    with patch.object(session, "ws_connect", return_value=None) as mock_ws_connect:
        await manager.connect()
        mock_ws_connect.assert_not_called()


# noinspection PyTypeChecker
async def test_cloud_fast_reconnect(hass_platform_cloud_connection, config, aioclient_mock, mock_call_later, caplog):
    hass = hass_platform_cloud_connection

    session = MockSession(aioclient_mock, ws_close_code=1000)
    manager = CloudManager(hass, config, session)

    for _ in range(1, 5):
        await manager.connect()
        assert manager._ws_reconnect_delay == 4

    await manager.connect()
    assert manager._ws_reconnect_delay == 180
    assert "too fast" in caplog.records[-2].message


# noinspection PyTypeChecker
async def test_cloud_messages_invalid_format(hass_platform_cloud_connection, config, aioclient_mock):
    hass = hass_platform_cloud_connection

    requests = ["foo"]
    session = MockSession(aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=r) for r in requests])
    manager = CloudManager(hass, config, session)

    with patch.object(manager, "_try_reconnect", return_value=None) as mock_reconnect:
        await manager.connect()
        mock_reconnect.assert_called_once()

    requests = [json.dumps({"request_id": "req", "_action": "foo"})]
    session = MockSession(aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=r) for r in requests])
    manager = CloudManager(hass, config, session)

    mock_reconnect.reset_mock()
    with patch.object(manager, "_try_reconnect", return_value=None) as mock_reconnect:
        await manager.connect()
        mock_reconnect.assert_called_once()

    requests = [json.dumps({"request_id": "req", "action": "/user/devices/query", "message": "not_{_json"})]
    session = MockSession(aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=r) for r in requests])
    manager = CloudManager(hass, config, session)

    with patch.object(manager, "_try_reconnect", return_value=None) as mock_reconnect:
        await manager.connect()
        mock_reconnect.assert_not_called()
    assert json.loads(session.ws.send_queue[0]) == {"payload": {"error_code": "INTERNAL_ERROR"}, "request_id": "req"}


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_cloud_req_user_devices(
    hass_platform_cloud_connection, config, aioclient_mock, expected_lingering_timers
):
    hass = hass_platform_cloud_connection
    requests = [{"request_id": "req_user_devices", "action": "/user/devices"}]
    session = MockSession(
        aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra={}, data=json.dumps(r)) for r in requests]
    )
    # noinspection PyTypeChecker
    manager = CloudManager(hass, config, session)
    await manager.connect()

    assert json.loads(session.ws.send_queue[0]) == {
        "request_id": "req_user_devices",
        "payload": {
            "user_id": "test_instance",
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


async def test_cloud_req_user_devices_query(hass_platform_cloud_connection, config, aioclient_mock):
    hass = hass_platform_cloud_connection
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
    # noinspection PyTypeChecker
    manager = CloudManager(hass, config, session)
    await manager.connect()

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


async def test_cloud_req_user_devices_action(hass_platform_cloud_connection, config, aioclient_mock):
    hass = hass_platform_cloud_connection
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
    # noinspection PyTypeChecker
    manager = CloudManager(hass, config, session)
    await manager.connect()
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

    await hass.async_block_till_done()
    assert hass.states.get("switch.ac").state == "on"
