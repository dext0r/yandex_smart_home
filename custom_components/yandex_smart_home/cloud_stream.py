"""Implement the Yandex Smart Home cloud connection manager for video streaming."""

import asyncio
from datetime import timedelta
import logging
from typing import Any, AsyncIterable, cast

from aiohttp import (
    ClientConnectionError,
    ClientResponseError,
    ClientSession,
    ClientWebSocketResponse,
    WSMessage,
    WSMsgType,
    web,
)
from aiohttp.web_request import Request as AIOWebRequest
from homeassistant.components.stream import Stream
from homeassistant.components.stream.core import StreamView
from homeassistant.components.stream.hls import (
    HlsInitView,
    HlsMasterPlaylistView,
    HlsPartView,
    HlsPlaylistView,
    HlsSegmentView,
)
from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant
from homeassistant.helpers.event import async_call_later
from multidict import MultiDictProxy
from pydantic import BaseModel
import yarl

try:
    from homeassistant.helpers.http import KEY_HASS  # type: ignore
except ImportError:
    KEY_HASS = "hass"  # type: ignore

from .const import CLOUD_STREAM_BASE_URL

_LOGGER = logging.getLogger(__name__)

RECONNECTION_DELAY = 2
WAIT_FOR_CONNECTION_TIMEOUT = 10


class Request(BaseModel):
    """Request from the cloud."""

    view: str
    sequence: str = ""
    part_num: str = ""
    url_query: str | None


class ResponseMeta(BaseModel):
    """Response metadata."""

    status_code: int
    headers: dict[str, str]


class WebRequest:
    """Represent minimal HTTP request to use in HomeAssistantView"""

    def __init__(self, hass: HomeAssistant, url: yarl.URL):
        """Initialize web request from url."""
        self.app = {KEY_HASS: hass}
        self._url = url

    @property
    def query(self) -> MultiDictProxy[str]:
        """Return parsed query parameters in decoded representation."""
        return MultiDictProxy(self._url.query)


class CloudStreamManager:
    """Class to manage cloud connection for streaming."""

    def __init__(self, hass: HomeAssistant, stream: Stream, session: ClientSession):
        """Initialize a cloud manager with stream and client session."""

        self._hass = hass
        self._stream = stream
        self._running_stream_id: str | None = None
        self._session = session
        self._connected = asyncio.Event()
        self._ws: ClientWebSocketResponse | None = None
        self._unsub_connect: CALLBACK_TYPE | None = None
        self._unsub_keepalive: CALLBACK_TYPE | None = None

    @property
    def stream_url(self) -> str | None:
        """Return URL to stream."""
        if not self._running_stream_id:
            return None

        return f"{CLOUD_STREAM_BASE_URL}/{self._running_stream_id}/master_playlist.m3u8"

    async def async_start(self) -> None:
        """Start connection."""
        if self._ws or not self._stream.access_token:
            return

        self._running_stream_id = self._stream.access_token
        self._hass.loop.create_task(self._async_connect())

        await asyncio.wait_for(self._connected.wait(), timeout=WAIT_FOR_CONNECTION_TIMEOUT)
        return await self._async_keepalive()

    async def _async_keepalive(self, *_: Any) -> None:
        """Disconnect if stream is not active anymore."""
        if self._stream.access_token != self._running_stream_id:
            return await self._async_disconnect()

        self._unsub_keepalive = async_call_later(self._hass, timedelta(seconds=1), HassJob(self._async_keepalive))
        return None

    async def _async_connect(self, *_: Any) -> None:
        """Connect to the cloud."""
        if not self._running_stream_id:
            return

        ws_url = f"{CLOUD_STREAM_BASE_URL}/{self._running_stream_id}/connect"

        # noinspection PyBroadException
        try:
            _LOGGER.debug(f"Connecting to {ws_url}")
            self._ws = await self._session.ws_connect(ws_url, heartbeat=30)

            _LOGGER.debug("Connection to Yandex Smart Home cloud established")
            self._connected.set()

            async for msg in cast(AsyncIterable[WSMessage], self._ws):
                if msg.type == WSMsgType.TEXT:
                    await self._on_message(msg)

            _LOGGER.debug(f"Disconnected: {self._ws.close_code}")
            if self._ws.close_code is not None:
                self._try_reconnect()
        except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError):
            _LOGGER.exception("Failed to connect to Yandex Smart Home cloud")
            self._try_reconnect()
        except Exception:
            _LOGGER.exception("Unexpected exception")
            self._try_reconnect()

        return None

    async def _async_disconnect(self, *_: Any) -> None:
        """Disconnect from the cloud."""
        self._running_stream_id = None
        self._connected.clear()

        if self._ws:
            await self._ws.close()
            self._ws = None

        for unsub in [self._unsub_connect, self._unsub_keepalive]:
            if unsub:
                unsub()

        self._unsub_connect = None
        self._unsub_keepalive = None

        return None

    async def _on_message(self, message: WSMessage) -> None:
        """Handle incoming request from the cloud."""
        _LOGGER.debug(f"Request: {message.data}")

        request = Request.parse_raw(message.data)
        request_url = yarl.URL.build(path=f"{request.view}", query=request.url_query)
        web_request = cast(AIOWebRequest, WebRequest(self._hass, request_url))

        views: dict[str, type[StreamView]] = {
            "master_playlist": HlsMasterPlaylistView,
            "playlist": HlsPlaylistView,
            "init": HlsInitView,
            "part": HlsPartView,
            "segment": HlsSegmentView,
        }

        view = views[request.view]()

        r = cast(
            web.Response,
            await view.get(web_request, self._stream.access_token or "", request.sequence, request.part_num),
        )
        assert self._ws is not None
        body = r.body if r.body is not None else b""
        assert isinstance(body, bytes)
        meta = ResponseMeta(status_code=r.status, headers=dict(r.headers))
        response = bytes(meta.json(), "utf-8") + b"\r\n" + body
        return await self._ws.send_bytes(response, compress=False)

    def _try_reconnect(self) -> None:
        """Schedule reconnection to the cloud."""

        _LOGGER.debug(f"Trying to reconnect in {RECONNECTION_DELAY} seconds")
        self._unsub_reconnect = async_call_later(self._hass, RECONNECTION_DELAY, HassJob(self._async_connect))
        return None
