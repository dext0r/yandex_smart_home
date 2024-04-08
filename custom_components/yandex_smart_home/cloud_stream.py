from __future__ import annotations

import asyncio
from asyncio import TimeoutError
from dataclasses import asdict, dataclass
from datetime import timedelta
import json
import logging
from typing import Any, cast

from aiohttp import (
    ClientConnectionError,
    ClientResponseError,
    ClientSession,
    ClientWebSocketResponse,
    WSMessage,
    WSMsgType,
)
from aiohttp.web_request import Request as AIOWebRequest
from homeassistant.components.stream import Stream
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
import yarl

try:
    from homeassistant.helpers.http import KEY_HASS
except ImportError:
    KEY_HASS = 'hass'

from .const import CLOUD_STREAM_BASE_URL

_LOGGER = logging.getLogger(__name__)

RECONNECTION_DELAY = 2
WAIT_FOR_CONNECTION_TIMEOUT = 10


@dataclass
class Request:
    view: str
    sequence: str = None
    part_num: str = None
    url_query: str = None


@dataclass
class ResponseMeta:
    status_code: int
    headers: dict[str, Any] | None = None


class WebRequest:
    def __init__(self, hass: HomeAssistant, url: yarl.URL):
        self.app = {KEY_HASS: hass}
        self._url = url

    @property
    def query(self) -> MultiDictProxy[str]:
        return MultiDictProxy(self._url.query)


class CloudStream:
    def __init__(self, hass: HomeAssistant, stream: Stream, session: ClientSession):
        self._hass = hass
        self._stream = stream
        self._running_stream_id: str | None = None
        self._session = session
        self._unsub_reconnect: CALLBACK_TYPE | None = None
        self._connected = asyncio.Event()
        self._ws: ClientWebSocketResponse | None = None

    @property
    def stream_url(self) -> str | None:
        if not self._running_stream_id:
            return None

        return f'{CLOUD_STREAM_BASE_URL}/{self._running_stream_id}/master_playlist.m3u8'

    async def start(self):
        if self._ws or not self._stream.access_token:
            return

        self._running_stream_id = self._stream.access_token
        self._hass.loop.create_task(self._connect())

        await asyncio.wait_for(self._connected.wait(), timeout=WAIT_FOR_CONNECTION_TIMEOUT)
        await self._keepalive()

    async def _keepalive(self, *_):
        if self._stream.access_token != self._running_stream_id:
            return await self._disconnect()

        async_call_later(self._hass, timedelta(seconds=1), HassJob(self._keepalive))

    async def _connect(self, *_):
        if not self._running_stream_id:
            return

        ws_url = f'{CLOUD_STREAM_BASE_URL}/{self._running_stream_id}/connect'

        # noinspection PyBroadException
        try:
            _LOGGER.debug(f'Connecting to {ws_url}')
            self._ws = await self._session.ws_connect(ws_url, heartbeat=30)

            _LOGGER.debug('Connection to Yandex Smart Home cloud established')
            self._connected.set()

            async for msg in self._ws:  # type: WSMessage
                if msg.type == WSMsgType.TEXT:
                    await self._handle_request(msg.json())

            _LOGGER.debug(f'Disconnected: {self._ws.close_code}')
            if self._ws.close_code is not None:
                self._try_reconnect()
        except (ClientConnectionError, ClientResponseError, TimeoutError):
            _LOGGER.exception('Failed to connect to Yandex Smart Home cloud')
            self._try_reconnect()
        except Exception:
            _LOGGER.exception('Unexpected exception')
            self._try_reconnect()

    async def _disconnect(self, *_):
        self._running_stream_id = None
        self._connected.clear()

        if self._unsub_reconnect:
            self._unsub_reconnect()
            self._unsub_reconnect = None

        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _handle_request(self, payload: dict):
        _LOGGER.debug(f'Request: {payload}')

        request = Request(**payload)
        request_url = yarl.URL.build(path=f'{request.view}', query=request.url_query)
        web_request = cast(AIOWebRequest, WebRequest(self._hass, request_url))

        views = {
            'master_playlist': HlsMasterPlaylistView,
            'playlist': HlsPlaylistView,
            'init': HlsInitView,
            'part': HlsPartView,
            'segment': HlsSegmentView
        }

        view = views[request.view]()

        r = await view.get(web_request, self._stream.access_token, request.sequence, request.part_num)
        body = r.body if r.body is not None else b''
        meta = ResponseMeta(status_code=r.status, headers=dict(r.headers))
        response = bytes(json.dumps(asdict(meta)), 'utf-8') + b'\r\n' + body
        await self._ws.send_bytes(response, compress=False)

    def _try_reconnect(self):
        _LOGGER.debug(f'Trying to reconnect in {RECONNECTION_DELAY} seconds')
        self._unsub_reconnect = async_call_later(self._hass, RECONNECTION_DELAY, HassJob(self._connect))
