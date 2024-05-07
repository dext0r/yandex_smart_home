from asyncio import TimeoutError
import json
from typing import cast
from unittest.mock import MagicMock, patch

from aiohttp import ClientConnectionError, ClientSession, WSMessage, WSMsgType
from aiohttp.web import Response
from homeassistant.components.camera import DynamicStreamSettings
from homeassistant.components.stream import OUTPUT_IDLE_TIMEOUT, Stream, StreamOutput, StreamSettings
from homeassistant.components.stream.hls import HlsMasterPlaylistView
from homeassistant.core import HomeAssistant
import pytest
import yarl

from custom_components.yandex_smart_home.cloud_stream import CloudStreamManager, WebRequest


class MockWSConnection:
    def __init__(self, url, **kwargs):
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

    async def send_bytes(self, b, *_, **__):
        self.send_queue.append(b)


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


class MockStream(Stream):
    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            "test",
            {},
            StreamSettings(
                ll_hls=True,
                min_segment_duration=0,
                part_target_duration=0,
                hls_advance_part_limit=0,
                hls_part_timeout=0,
            ),
            DynamicStreamSettings(),
        )

    def endpoint_url(self, fmt: str) -> str:
        return "/foo"

    def add_provider(self, fmt: str, timeout: int = OUTPUT_IDLE_TIMEOUT) -> StreamOutput:
        pass


@pytest.fixture(autouse=True, name="mock_call_later")
def mock_call_later_fixture():
    with patch("custom_components.yandex_smart_home.cloud_stream.async_call_later") as mock_call_later:
        yield mock_call_later


async def test_cloud_stream_connect(hass, aioclient_mock, mock_call_later):
    session = MockSession(aioclient_mock)
    stream = MockStream(hass)
    cloud_stream = CloudStreamManager(hass, stream, cast(ClientSession, session))

    with patch.object(hass.loop, "create_task") as mock_async_create_task, patch(
        "custom_components.yandex_smart_home.cloud_stream.WAIT_FOR_CONNECTION_TIMEOUT", 0.1
    ):
        await cloud_stream.async_start()
        assert cloud_stream._ws is None
        mock_async_create_task.assert_not_called()

    stream.access_token = "foo"

    with patch.object(cloud_stream, "_async_connect"), patch(
        "custom_components.yandex_smart_home.cloud_stream.WAIT_FOR_CONNECTION_TIMEOUT", 0.1
    ):
        with pytest.raises(TimeoutError):
            await cloud_stream.async_start()

    with patch("custom_components.yandex_smart_home.cloud_stream.WAIT_FOR_CONNECTION_TIMEOUT", 1):
        await cloud_stream.async_start()
        assert cloud_stream._connected.is_set()


async def test_cloud_stream_try_reconnect(hass, aioclient_mock, caplog):
    session = MockSession(aioclient_mock)
    stream = MockStream(hass)
    cloud_stream = CloudStreamManager(hass, stream, cast(ClientSession, session))

    with patch.object(session, "ws_connect") as mock_ws_connect:
        await cloud_stream._async_connect()

        mock_ws_connect.assert_not_called()

    cloud_stream._running_stream_id = "foo"

    with patch.object(session, "ws_connect", side_effect=Exception()), patch.object(
        cloud_stream, "_try_reconnect", return_value=None
    ) as mock_reconnect:
        await cloud_stream._async_connect()

        mock_reconnect.assert_called_once()

    caplog.clear()
    with patch.object(session, "ws_connect", side_effect=ClientConnectionError()), patch.object(
        cloud_stream, "_try_reconnect", return_value=None
    ) as mock_reconnect:
        await cloud_stream._async_connect()
        mock_reconnect.assert_called_once()
        assert caplog.messages[-1] == "Failed to connect to Yandex Smart Home cloud"

    session = MockSession(aioclient_mock, ws_close_code=1000)
    stream = MockStream(hass)
    cloud_stream = CloudStreamManager(hass, stream, cast(ClientSession, session))
    cloud_stream._running_stream_id = "foo"

    caplog.clear()
    with patch("custom_components.yandex_smart_home.cloud_stream.async_call_later") as mock_reconnect:
        await cloud_stream._async_connect()
        mock_reconnect.assert_called_once()
        assert caplog.messages[-1] == "Trying to reconnect in 2 seconds"


async def test_cloud_stream_keepalive(hass, aioclient_mock, mock_call_later):
    session = MockSession(aioclient_mock)
    stream = MockStream(hass)
    stream.access_token = "foo"
    unsub_connect_mock = MagicMock()
    unsub_keepalive_mock = MagicMock()
    cloud_stream = CloudStreamManager(hass, stream, cast(ClientSession, session))
    cloud_stream._running_stream_id = "foo"
    cloud_stream._unsub_connect = unsub_connect_mock
    cloud_stream._ws = MockWSConnection(url="foo")

    await cloud_stream._async_keepalive()
    mock_call_later.assert_called_once()

    mock_call_later.reset_mock()
    stream.access_token = None

    cloud_stream._unsub_keepalive = unsub_keepalive_mock
    await cloud_stream._async_keepalive()
    mock_call_later.assert_not_called()
    assert not cloud_stream._connected.is_set()
    assert cloud_stream._ws is None
    assert cloud_stream._unsub_connect is None
    assert cloud_stream._unsub_keepalive is None
    unsub_connect_mock.assert_called_once()
    unsub_keepalive_mock.assert_called_once()


async def test_cloud_stream_handle_requests(hass, aioclient_mock):
    requests = [{"view": "master_playlist"}]
    stream = MockStream(hass)
    session = MockSession(
        aioclient_mock, msg=[WSMessage(type=WSMsgType.TEXT, extra=None, data=json.dumps(r)) for r in requests]
    )
    cloud_stream = CloudStreamManager(hass, stream, cast(ClientSession, session))
    cloud_stream._running_stream_id = "foo"
    with patch.object(HlsMasterPlaylistView, "get", return_value=Response(body=b"master")):
        await cloud_stream._async_connect()

    assert session.ws.send_queue == [b'{"status_code": 200, "headers": {}}\r\nmaster']


async def test_cloud_stream_web_request(hass):
    r = WebRequest(hass, yarl.URL("/test?foo=bar"))
    assert r.query == {"foo": "bar"}
