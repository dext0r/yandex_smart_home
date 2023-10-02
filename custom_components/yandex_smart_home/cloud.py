"""Implement the Yandex Smart Home cloud connection manager."""
from asyncio import TimeoutError
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
import logging
from typing import AsyncIterable, cast

from aiohttp import (
    ClientConnectorError,
    ClientResponseError,
    ClientSession,
    ClientWebSocketResponse,
    WSMessage,
    WSMsgType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HassJob, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt
from pydantic import BaseModel

from . import handlers
from .const import (
    CLOUD_BASE_URL,
    CONF_CLOUD_INSTANCE,
    CONF_CLOUD_INSTANCE_CONNECTION_TOKEN,
    CONF_CLOUD_INSTANCE_ID,
    CONFIG,
    DOMAIN,
)
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

DEFAULT_RECONNECTION_DELAY = 2
MAX_RECONNECTION_DELAY = 180
FAST_RECONNECTION_TIME = timedelta(seconds=6)
FAST_RECONNECTION_THRESHOLD = 5
BASE_API_URL = f"{CLOUD_BASE_URL}/api/home_assistant/v1"


@dataclass
class CloudInstanceData:
    id: str
    password: str
    connection_token: str


class CloudRequest(BaseModel):
    request_id: str
    action: str
    message: str = ""


class CloudManager:
    def __init__(self, hass: HomeAssistant, config: Config, session: ClientSession):
        self._hass = hass
        self._instance_id = config.cloud_instance_id
        self._token = config.cloud_connection_token
        self._user_id = config.user_id
        self._session = session
        self._last_connection_at: datetime | None = None
        self._fast_reconnection_count = 0
        self._ws: ClientWebSocketResponse | None = None
        self._ws_reconnect_delay = DEFAULT_RECONNECTION_DELAY
        self._ws_active = True

        self._url = f"{BASE_API_URL}/connect"

    async def connect(self, *_):
        if not self._ws_active:
            return

        # noinspection PyBroadException
        try:
            _LOGGER.debug(f"Connecting to {self._url}")
            self._ws = await self._session.ws_connect(
                self._url, heartbeat=45, compress=15, headers={"Authorization": f"Bearer {self._token}"}
            )

            _LOGGER.debug("Connection to Yandex Smart Home cloud established")
            self._ws_reconnect_delay = DEFAULT_RECONNECTION_DELAY
            self._last_connection_at = dt.utcnow()

            async for msg in cast(AsyncIterable[WSMessage], self._ws):
                if msg.type == WSMsgType.TEXT:
                    await self._on_message(msg)

            _LOGGER.debug(f"Disconnected: {self._ws.close_code}")
            if self._ws.close_code is not None:
                self._try_reconnect()
        except (ClientConnectorError, ClientResponseError, TimeoutError):
            _LOGGER.exception("Failed to connect to Yandex Smart Home cloud")
            self._try_reconnect()
        except Exception:
            _LOGGER.exception("Unexpected exception")
            self._try_reconnect()

    async def disconnect(self, *_):
        self._ws_active = False

        if self._ws:
            await self._ws.close()

    async def _on_message(self, message: WSMessage):
        request = CloudRequest.parse_raw(message.data)
        _LOGGER.debug("Request: %s (message: %s)" % (request.action, request.message))

        data = RequestData(
            config=self._hass.data[DOMAIN][CONFIG],
            context=Context(user_id=self._user_id),
            request_user_id=self._instance_id,
            request_id=request.request_id,
        )

        result = await handlers.async_handle_request(self._hass, data, request.action, request.message)
        response = result.json(exclude_none=True)
        _LOGGER.debug(f"Response: {response}")

        await self._ws.send_str(response)

    def _try_reconnect(self):
        self._ws_reconnect_delay = min(2 * self._ws_reconnect_delay, MAX_RECONNECTION_DELAY)

        if self._last_connection_at and self._last_connection_at + FAST_RECONNECTION_TIME > dt.utcnow():
            self._fast_reconnection_count += 1
        else:
            self._fast_reconnection_count = 0

        if self._fast_reconnection_count >= FAST_RECONNECTION_THRESHOLD:
            self._ws_reconnect_delay = MAX_RECONNECTION_DELAY
            _LOGGER.warning(f"Reconnecting too fast, next reconnection in {self._ws_reconnect_delay} seconds")

        _LOGGER.debug(f"Trying to reconnect in {self._ws_reconnect_delay} seconds")
        async_call_later(self._hass, self._ws_reconnect_delay, HassJob(self.connect))


async def register_cloud_instance(hass: HomeAssistant) -> CloudInstanceData:
    session = async_create_clientsession(hass)

    response = await session.post(f"{BASE_API_URL}/instance/register")
    response.raise_for_status()

    return CloudInstanceData(**await response.json())


async def delete_cloud_instance(hass: HomeAssistant, entry: ConfigEntry):
    session = async_create_clientsession(hass)

    instance_id = entry.data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_ID]
    token = entry.data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_CONNECTION_TOKEN]

    response = await session.delete(
        f"{BASE_API_URL}/instance/{instance_id}", headers={"Authorization": f"Bearer {token}"}
    )
    if response.status != HTTPStatus.OK:
        _LOGGER.error(f"Failed to delete cloud instance, status code: {response.status}")
