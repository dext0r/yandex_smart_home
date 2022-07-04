from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import deque
import json
import logging
import time
from typing import Any

from aiohttp import ContentTypeError
from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, Event, HassJob, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_call_later

from . import const
from .const import (
    CONF_NOTIFIER_OAUTH_TOKEN,
    CONF_NOTIFIER_SKILL_ID,
    CONF_NOTIFIER_USER_ID,
    CONFIG,
    DOMAIN,
    EVENT_CONFIG_CHANGED,
    NOTIFIERS,
)
from .entity import YandexEntity, YandexEntityCallbackState
from .helpers import Config

_LOGGER = logging.getLogger(__name__)

DISCOVERY_REQUEST_DELAY = 15
DISCOVERY_REQUEST_DELAY_ON_CONFIG_RELOAD = 5
INITIAL_REPORT_DELAY = 5
REPORT_STATE_WINDOW = 1


class YandexNotifier(ABC):
    def __init__(self, hass: HomeAssistant, user_id: str, token: str):
        self._hass = hass
        self._user_id = user_id
        self._token = token

        self._property_entities = self._get_property_entities()
        self._session = async_create_clientsession(hass)

        self._unsub_pending: CALLBACK_TYPE | None = None
        self._unsub_send_discovery: CALLBACK_TYPE | None = None
        self._pending: deque[YandexEntityCallbackState] = deque()
        self._report_states_job = HassJob(self._report_states)

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

    @property
    def _ready(self) -> bool:
        return self._config and self._config.devices_discovered

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

    async def _report_states(self, *_):
        devices = {}
        attrs = ['properties', 'capabilities']

        while len(self._pending):
            state = self._pending.popleft()

            devices.setdefault(
                state.device_id,
                dict({attr: [] for attr in attrs}, **{'id': state.device_id})
            )
            for attr in attrs:
                devices[state.device_id][attr][:0] = getattr(state, attr)

        await self.async_send_state(list(devices.values()))

        if len(self._pending):
            self._unsub_pending = async_call_later(self._hass, REPORT_STATE_WINDOW, self._report_states_job)
        else:
            self._unsub_pending = None

    async def async_send_state(self, devices: list):
        await self._async_send_callback(f'{self._base_url}/state', {'devices': devices})

    async def async_send_discovery(self, _=None):
        if not self._ready:
            return

        _LOGGER.debug(self._format_log_message('Device list update initiated'))
        await self._async_send_callback(f'{self._base_url}/discovery', {})

    async def async_schedule_discovery(self, delay: int):
        self._unsub_send_discovery = async_call_later(self._hass, delay, HassJob(self.async_send_discovery))

    # noinspection PyBroadException
    async def _async_send_callback(self, url: str, payload: dict[str, Any]):
        if self._session.closed:
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
                _LOGGER.warning(
                    self._format_log_message(f'Failed to send state notification: [{r.status}] {error_message}')
                )
        except ClientConnectionError as e:
            _LOGGER.warning(self._format_log_message(f'Failed to send state notification: {e!r}'))
        except asyncio.TimeoutError as e:
            _LOGGER.debug(self._format_log_message(f'Failed to send state notification: {e!r}'))
        except Exception:
            _LOGGER.exception(self._format_log_message('Failed to send state notification'))

    async def async_event_handler(self, event: Event):
        if not self._ready:
            return

        event_entity_id = event.data.get(ATTR_ENTITY_ID)
        old_state = event.data.get('old_state')
        new_state = event.data.get('new_state')

        if not old_state or old_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return
        if not new_state or new_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return

        reportable_entity_ids = {event_entity_id}
        if event_entity_id in self._property_entities.keys():
            reportable_entity_ids.update(self._property_entities.get(event_entity_id, {}))

        for entity_id in sorted(reportable_entity_ids):
            state = new_state
            if entity_id != event_entity_id:
                state = self._hass.states.get(entity_id)
                if not state:
                    continue

            yandex_entity = YandexEntity(self._hass, self._config, state)
            if not yandex_entity.should_expose:
                continue

            callback_state = YandexEntityCallbackState(yandex_entity, event_entity_id)
            if entity_id == event_entity_id and entity_id not in self._property_entities.keys():
                callback_state.old_state = YandexEntityCallbackState(
                    YandexEntity(self._hass, self._config, old_state),
                    event_entity_id
                )

            if callback_state.should_report:
                entity_text = entity_id
                if entity_id != event_entity_id:
                    entity_text = f'{entity_text} => {event_entity_id}'

                _LOGGER.debug(self._format_log_message(
                    f'Scheduling report state to Yandex for {entity_text}: {new_state.state}'
                ))
                self._pending.append(callback_state)

                if self._unsub_pending is None:
                    delay = 0 if callback_state.should_report_immediately else REPORT_STATE_WINDOW
                    self._unsub_pending = async_call_later(self._hass, delay, self._report_states_job)

    async def async_initial_report(self):
        if not self._ready:
            return

        _LOGGER.debug('Reporting initial states')
        for state in self._hass.states.async_all():
            yandex_entity = YandexEntity(self._hass, self._config, state)
            if not yandex_entity.should_expose:
                continue

            callback_state = YandexEntityCallbackState(
                yandex_entity, event_entity_id=state.entity_id, initial_report=True
            )

            if callback_state.should_report:
                self._pending.append(callback_state)

                if self._unsub_pending is None:
                    self._unsub_pending = async_call_later(self._hass, 0, self._report_states_job)

    async def async_unload(self):
        if self._unsub_send_discovery:
            self._unsub_send_discovery()


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
    unsub_initial_report: CALLBACK_TYPE | None = None

    async def _state_change_listener(event: Event):
        await asyncio.gather(*[n.async_event_handler(event) for n in hass.data[DOMAIN][NOTIFIERS]])

    hass.bus.async_listen(EVENT_STATE_CHANGED, _state_change_listener)

    async def _schedule_discovery(event: Event):
        delay = DISCOVERY_REQUEST_DELAY
        if event.event_type == EVENT_CONFIG_CHANGED:
            delay = DISCOVERY_REQUEST_DELAY_ON_CONFIG_RELOAD

        await asyncio.gather(*[n.async_schedule_discovery(delay) for n in hass.data[DOMAIN][NOTIFIERS]])

    async def _schedule_initial_report(_: Event):
        nonlocal unsub_initial_report

        async def _initial_report(_: Event):
            nonlocal unsub_initial_report
            unsub_initial_report = None

            await asyncio.gather(*[n.async_initial_report() for n in hass.data[DOMAIN][NOTIFIERS]])

        if unsub_initial_report is None:
            unsub_initial_report = async_call_later(hass, INITIAL_REPORT_DELAY, HassJob(_initial_report))

    hass.bus.async_listen(EVENT_HOMEASSISTANT_STARTED, _schedule_discovery)
    hass.bus.async_listen(EVENT_CONFIG_CHANGED, _schedule_discovery)
    hass.bus.async_listen(const.EVENT_DEVICE_DISCOVERY, _schedule_initial_report)


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

                hass.data[DOMAIN][NOTIFIERS].append(notifier)
            except Exception as exc:
                raise ConfigEntryNotReady from exc

    if config.is_cloud_connection:
        hass.data[DOMAIN][NOTIFIERS].append(
            YandexCloudNotifier(hass, config.cloud_instance_id, config.cloud_connection_token)
        )


async def async_unload_notifier(hass: HomeAssistant):
    await asyncio.gather(*[notifier.async_unload() for notifier in hass.data[DOMAIN][NOTIFIERS]])

    hass.data[DOMAIN][NOTIFIERS]: list[YandexNotifier] = []
