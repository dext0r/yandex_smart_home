from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import json
import logging
import time
from typing import Any

from aiohttp import ContentTypeError
from homeassistant.const import EVENT_STATE_CHANGED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later

from . import const
from .const import CONF_NOTIFIER_OAUTH_TOKEN, CONF_NOTIFIER_SKILL_ID, CONF_NOTIFIER_USER_ID, CONFIG, DOMAIN, NOTIFIERS
from .entity import YandexEntity
from .helpers import Config

_LOGGER = logging.getLogger(__name__)

DISCOVERY_REQUEST_DELAY = 10


class YandexNotifier(ABC):
    def __init__(self, hass: HomeAssistant, user_id: str, token: str):
        self._hass = hass
        self._user_id = user_id
        self._token = token

        self._property_entities = self._get_property_entities()
        self._session = async_create_clientsession(hass)

    @property
    @abstractmethod
    def _base_url(self) -> str:
        pass

    @property
    @abstractmethod
    def _request_headers(self) -> dict[str, str]:
        pass

    @property
    def _config(self) -> Config:
        return self._hass.data[DOMAIN][CONFIG]

    def _format_log_message(self, message: str) -> str:
        return message

    @staticmethod
    def _log_request(url: str, data: dict[str, Any]):
        request_json = json.dumps(data)
        _LOGGER.debug(f'Request: {url} (POST data: {request_json})')

    def _get_property_entities(self) -> dict[str, list[str]]:
        rv = {}

        for entity_id, entity_config in self._config.entity_config.items():
            for property_config in entity_config.get(const.CONF_ENTITY_PROPERTIES):
                property_entity_id = property_config.get(const.CONF_ENTITY_PROPERTY_ENTITY)
                if property_entity_id:
                    rv.setdefault(property_entity_id, [])
                    if entity_id not in rv[property_entity_id]:
                        rv[property_entity_id].append(entity_id)

            for custom_capabilities_config in [entity_config.get(const.CONF_ENTITY_CUSTOM_MODES),
                                               entity_config.get(const.CONF_ENTITY_CUSTOM_TOGGLES),
                                               entity_config.get(const.CONF_ENTITY_CUSTOM_RANGES)]:
                for custom_capability in custom_capabilities_config.values():
                    state_entity_id = custom_capability.get(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
                    if state_entity_id:
                        rv.setdefault(state_entity_id, [])
                        rv[state_entity_id].append(entity_id)

        return rv

    async def async_send_state(self, devices: list):
        await self._async_send_callback(f'{self._base_url}/state', {'devices': devices})

    async def async_send_discovery(self, _):
        _LOGGER.debug(self._format_log_message('Device list update initiated'))
        await self._async_send_callback(f'{self._base_url}/discovery', {})

    # noinspection PyBroadException
    async def _async_send_callback(self, url: str, payload: dict[str, Any]):
        if not self._config.devices_discovered:
            _LOGGER.debug('Home Assistant devices is not discovered by Yandex yet')
            return

        try:
            payload['user_id'] = self._user_id
            request_data = {'ts': time.time(), 'payload': payload}

            self._log_request(url, request_data)
            r = await self._session.post(url, headers=self._request_headers, json=request_data, timeout=5)

            response_body, error_message = await r.read(), ''
            try:
                response_data = await r.json()
                error_message = response_data['error_message']
            except (AttributeError, ValueError, KeyError, ContentTypeError):
                if r.status != 202:
                    error_message = response_body[:100]

            if r.status != 202 or error_message:
                _LOGGER.error(
                    self._format_log_message(f'Failed to send state notification: [{r.status}] {error_message}')
                )
        except Exception:
            _LOGGER.exception(self._format_log_message('Failed to send state notification'))

    async def async_event_handler(self, event: Event):
        devices = []
        event_entity_id = event.data.get('entity_id')
        old_state = event.data.get('old_state')
        new_state = event.data.get('new_state')

        if not old_state or old_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return
        if not new_state or new_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return

        reportable_entity_ids = [event_entity_id]
        if event_entity_id in self._property_entities.keys():
            reportable_entity_ids.extend(list(self._property_entities.get(event_entity_id, {})))

        for entity_id in reportable_entity_ids:
            state = new_state
            if entity_id != event_entity_id:
                state = self._hass.states.get(entity_id)

            yandex_entity = YandexEntity(self._hass, self._config, state)

            if not yandex_entity.should_expose:
                continue

            device = yandex_entity.notification_serialize(event_entity_id)
            if entity_id == event_entity_id:
                old_yandex_entity = YandexEntity(self._hass, self._config, old_state)
                if old_yandex_entity.notification_serialize(event_entity_id) == device:
                    continue

            if device.get('capabilities') or device.get('properties'):
                devices.append(device)
                entity_text = entity_id
                if entity_id != event_entity_id:
                    entity_text = f'{entity_text} => {event_entity_id}'

                _LOGGER.debug(self._format_log_message(
                    f'Notify Yandex about new state {entity_text}: {new_state.state}'
                ))

        if devices:
            await self.async_send_state(devices)


class YandexDirectNotifier(YandexNotifier):
    def __init__(self, hass: HomeAssistant, user_id: str, token: str, skill_id: str):
        self._skill_id = skill_id

        super().__init__(hass, user_id, token)

    @property
    def _base_url(self) -> str:
        return f'https://dialogs.yandex.net/api/v1/skills/{self._skill_id}/callback'

    @property
    def _request_headers(self) -> dict[str, str]:
        return {'Authorization': f'OAuth {self._token}'}

    def _format_log_message(self, message: str) -> str:
        if len(self._hass.data[DOMAIN][NOTIFIERS]) > 1:
            return f'[{self._skill_id} | {self._user_id}] {message}'

        return message

    async def async_validate_config(self):
        if await self._hass.auth.async_get_user(self._user_id) is None:
            raise ValueError(f'User {self._user_id} does not exist')


class YandexCloudNotifier(YandexNotifier):
    @property
    def _base_url(self) -> str:
        return 'https://yaha-cloud.ru/api/home_assistant/v1/callback'

    @property
    def _request_headers(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self._token}'}


@callback
def async_setup_notifier(hass: HomeAssistant):
    """Set up notifiers."""
    async def state_change_listener(event: Event):
        await asyncio.gather(*[n.async_event_handler(event) for n in hass.data[DOMAIN][NOTIFIERS]])

    hass.bus.async_listen(EVENT_STATE_CHANGED, state_change_listener)


async def async_start_notifier(hass: HomeAssistant):
    config = hass.data[DOMAIN][CONFIG]
    if config.is_direct_connection:
        if not hass.data[DOMAIN][CONFIG].notifier:
            _LOGGER.debug('Notifier disabled: no config')

        for conf in hass.data[DOMAIN][CONFIG].notifier:
            try:
                notifier = YandexDirectNotifier(
                    hass,
                    conf[CONF_NOTIFIER_USER_ID],
                    conf[CONF_NOTIFIER_OAUTH_TOKEN],
                    conf[CONF_NOTIFIER_SKILL_ID],
                )
                await notifier.async_validate_config()
                async_call_later(hass, DISCOVERY_REQUEST_DELAY, notifier.async_send_discovery)

                hass.data[DOMAIN][NOTIFIERS].append(notifier)
            except Exception as exc:
                raise ConfigEntryNotReady from exc

    if config.is_cloud_connection:
        notifier = YandexCloudNotifier(hass, config.cloud_instance_id, config.cloud_connection_token)
        async_call_later(hass, DISCOVERY_REQUEST_DELAY, notifier.async_send_discovery)

        hass.data[DOMAIN][NOTIFIERS].append(notifier)


@callback
def async_unload_notifier(hass: HomeAssistant):
    hass.data[DOMAIN][NOTIFIERS]: list[YandexNotifier] = []
