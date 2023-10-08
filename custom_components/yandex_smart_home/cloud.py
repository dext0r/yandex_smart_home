"""Implement the Yandex Smart Home cloud connection manager."""
from __future__ import annotations

from asyncio import TimeoutError
from datetime import datetime, timedelta
from http import HTTPStatus
import logging
from typing import TYPE_CHECKING, Any, AsyncIterable, cast

from aiohttp import ClientConnectorError, ClientResponseError, ClientWebSocketResponse, WSMessage, WSMsgType, hdrs
from homeassistant.core import Context, HassJob
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE, async_create_clientsession, async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt
from pydantic import BaseModel

from . import handlers
from .const import CLOUD_BASE_URL, DOMAIN
from .helpers import RequestData

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

    from .entry_data import ConfigEntryData

_LOGGER = logging.getLogger(__name__)

DEFAULT_RECONNECTION_DELAY = 2
MAX_RECONNECTION_DELAY = 180
FAST_RECONNECTION_TIME = timedelta(seconds=6)
FAST_RECONNECTION_THRESHOLD = 5
BASE_API_URL = f"{CLOUD_BASE_URL}/api/home_assistant/v1"


class CloudInstanceData(BaseModel):
    """Hold settings for the cloud connection."""

    id: str
    password: str
    connection_token: str


class CloudRequest(BaseModel):
    """Request from the cloud."""

    request_id: str
    action: str
    message: str = ""


class CloudManager:
    """Class to manage cloud connection."""

    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData):
        """Initialize a cloud manager with entry data and client session."""
        self._hass = hass
        self._entry_data = entry_data
        self._session = async_get_clientsession(hass)
        self._last_connection_at: datetime | None = None
        self._fast_reconnection_count = 0
        self._ws: ClientWebSocketResponse | None = None
        self._ws_reconnect_delay = DEFAULT_RECONNECTION_DELAY
        self._ws_active = True
        self._unsub_connect: CALLBACK_TYPE | None = None

        self._url = f"{BASE_API_URL}/connect"

    async def async_connect(self, *_: Any) -> None:
        """Connect to the cloud."""
        # noinspection PyBroadException
        try:
            _LOGGER.debug(f"Connecting to {self._url}")
            self._ws = await self._session.ws_connect(
                self._url,
                heartbeat=45,
                compress=15,
                headers={
                    hdrs.AUTHORIZATION: f"Bearer {self._entry_data.cloud_connection_token}",
                    hdrs.USER_AGENT: f"{SERVER_SOFTWARE} {DOMAIN}/{self._entry_data.version}",
                },
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

        return None

    async def async_disconnect(self, *_: Any) -> None:
        """Disconnect from the cloud."""
        self._ws_active = False
        if self._ws:
            await self._ws.close()

        if self._unsub_connect:
            self._unsub_connect()
            self._unsub_connect = None

        return None

    async def _on_message(self, message: WSMessage) -> None:
        """Handle incoming request from the cloud."""
        request = CloudRequest.parse_raw(message.data)
        _LOGGER.debug("Request: %s (message: %s)" % (request.action, request.message))

        data = RequestData(
            entry_data=self._entry_data,
            context=Context(user_id=self._entry_data.user_id),
            request_user_id=self._entry_data.cloud_instance_id,
            request_id=request.request_id,
        )

        result = await handlers.async_handle_request(self._hass, data, request.action, request.message)
        response = result.as_json()
        _LOGGER.debug(f"Response: {response}")

        assert self._ws is not None
        await self._ws.send_str(response)
        return None

    def _try_reconnect(self) -> None:
        """Schedule reconnection to the cloud."""
        if not self._ws_active:
            return None

        self._ws_reconnect_delay = min(2 * self._ws_reconnect_delay, MAX_RECONNECTION_DELAY)

        if self._last_connection_at and self._last_connection_at + FAST_RECONNECTION_TIME > dt.utcnow():
            self._fast_reconnection_count += 1
        else:
            self._fast_reconnection_count = 0

        if self._fast_reconnection_count >= FAST_RECONNECTION_THRESHOLD:
            self._ws_reconnect_delay = MAX_RECONNECTION_DELAY
            _LOGGER.warning(f"Reconnecting too fast, next reconnection in {self._ws_reconnect_delay} seconds")

        _LOGGER.debug(f"Trying to reconnect in {self._ws_reconnect_delay} seconds")
        self._unsub_connect = async_call_later(self._hass, self._ws_reconnect_delay, HassJob(self.async_connect))
        return None


async def register_cloud_instance(hass: HomeAssistant) -> CloudInstanceData:
    """Register a new cloud instance."""
    session = async_create_clientsession(hass)

    response = await session.post(f"{BASE_API_URL}/instance/register")
    response.raise_for_status()

    return CloudInstanceData.parse_raw(await response.text())


async def delete_cloud_instance(hass: HomeAssistant, instance_id: str, token: str) -> None:
    """Delete a cloud instance from the cloud."""
    session = async_create_clientsession(hass)

    response = await session.delete(
        f"{BASE_API_URL}/instance/{instance_id}",
        headers={hdrs.AUTHORIZATION: f"Bearer {token}"},
    )
    if response.status != HTTPStatus.OK:
        _LOGGER.error(f"Failed to delete cloud instance, status code: {response.status}")

    return None
