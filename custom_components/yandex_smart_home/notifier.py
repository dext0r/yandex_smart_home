from __future__ import annotations

import logging
import asyncio
from time import time
from typing import Any

from aiohttp import ContentTypeError
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    DOMAIN, CONFIG, DATA_CONFIG, CONF_NOTIFIER, CONF_SKILL_OAUTH_TOKEN,
    CONF_SKILL_ID, CONF_NOTIFIER_USER_ID, NOTIFIERS,
    CONF_ENTITY_PROPERTIES, CONF_ENTITY_PROPERTY_ENTITY,
)
from .helpers import YandexEntity

_LOGGER = logging.getLogger(__name__)

SKILL_API_URL = 'https://dialogs.yandex.net/api/v1/skills'
DISCOVERY_URL = '/callback/discovery'
STATE_URL = '/callback/state'


class YandexNotifier:
    def __init__(self, hass: HomeAssistant, conf: dict[str, str]):
        self.hass = hass
        self.property_entities = self.get_property_entities()
        self.oauth_token = conf[CONF_SKILL_OAUTH_TOKEN]
        self.skill_id = conf[CONF_SKILL_ID]
        self.user_id = conf[CONF_NOTIFIER_USER_ID]

        self.session = async_create_clientsession(self.hass)

    def format_log_message(self, message: str) -> str:
        if len(self.hass.data[DOMAIN][NOTIFIERS]) > 1:
            return f'[{self.skill_id} | {self.user_id}] {message}'

        return message

    def get_property_entities(self) -> dict[str, Any]:
        cfg = self.hass.data[DOMAIN][DATA_CONFIG].entity_config
        rv = {}

        for entity in cfg:
            custom_entity_config = cfg.get(entity, {})
            for property_config in custom_entity_config.get(CONF_ENTITY_PROPERTIES):
                if CONF_ENTITY_PROPERTY_ENTITY in property_config:
                    property_entity_id = property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
                    devs = set(rv.get(property_entity_id, []))
                    devs.add(entity)
                    rv.update({property_entity_id: devs})

        return rv

    async def async_validate_config(self):
        if await self.hass.auth.async_get_user(self.user_id) is None:
            raise ValueError(f'User {self.user_id} does not exist')

    async def async_notify_skill(self, devices):
        try:
            url = f'{SKILL_API_URL}/{self.skill_id}'
            headers = {'Authorization': f'OAuth {self.oauth_token}'}
            ts = time()

            if devices:
                url_tail = STATE_URL
                payload = {'user_id': self.user_id, 'devices': devices}
            else:
                url_tail = DISCOVERY_URL
                payload = {'user_id': self.user_id}

            request_data = {'ts': ts, 'payload': payload}
            _LOGGER.debug(f'Request: {url}{url_tail} (POST data: {request_data})')
            r = await self.session.post(f'{url}{url_tail}', headers=headers, json=request_data)

            response_body, error_message = await r.read(), ''
            try:
                response_data = await r.json()
                error_message = response_data['error_message']
            except (ValueError, KeyError, ContentTypeError):
                if r.status != 202:
                    error_message = response_body[:100]

            if r.status != 202 or error_message:
                _LOGGER.error(self.format_log_message(f'Failed to send state notification: {error_message}'))
        except Exception:
            _LOGGER.exception(self.format_log_message('Failed to send state notification'))

    async def async_event_handler(self, event: Event):
        devices = []
        entity_list = []
        event_entity_id = event.data.get('entity_id')
        old_state = event.data.get('old_state')
        new_state = event.data.get('new_state')

        if not old_state or old_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return
        if not new_state or new_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return

        entity_list.append(event_entity_id)
        if event_entity_id in self.property_entities.keys():
            entity_list = entity_list + list(self.property_entities.get(event_entity_id, {}))

        for entity in entity_list:
            if entity in CLOUD_NEVER_EXPOSED_ENTITIES or not self.hass.data[DOMAIN][DATA_CONFIG].should_expose(entity):
                continue

            state = new_state if entity == event_entity_id else self.hass.states.get(entity)
            yandex_entity = YandexEntity(self.hass, self.hass.data[DOMAIN][DATA_CONFIG], state)
            device = yandex_entity.notification_serialize(event_entity_id)
            if entity == event_entity_id:
                old_entity = YandexEntity(self.hass, self.hass.data[DOMAIN][DATA_CONFIG], old_state)
                if old_entity.notification_serialize(event_entity_id) == device:  # нет изменений
                    continue

            if device['capabilities'] or device['properties']:
                devices.append(device)
                entity_text = entity
                if entity != event_entity_id:
                    entity_text = f'{entity_text} => {event_entity_id}'

                _LOGGER.debug(self.format_log_message(
                    f'Notify Yandex about new state {entity_text}: {new_state.state}'
                ))

        if devices:
            await asyncio.sleep(.1)
            await self.async_notify_skill(devices)


async def async_setup_notifier(hass: HomeAssistant) -> bool:
    """Set up notifiers."""
    if not hass.data[DOMAIN][CONFIG][CONF_NOTIFIER]:
        _LOGGER.debug('Notifier disabled: no config')
        return False

    hass.data[DOMAIN][NOTIFIERS] = []  # type: list[YandexNotifier]
    for conf in hass.data[DOMAIN][CONFIG][CONF_NOTIFIER]:
        try:
            notifier = YandexNotifier(hass, conf)
            await notifier.async_validate_config()

            hass.data[DOMAIN][NOTIFIERS].append(notifier)
        except Exception as exc:
            raise ConfigEntryNotReady from exc

    async def state_change_listener(event: Event):
        await asyncio.gather(*[n.async_event_handler(event) for n in hass.data[DOMAIN][NOTIFIERS]])

    # noinspection PyUnusedLocal
    async def ha_start_listener(event: Event):
        await asyncio.sleep(10)

        for n in hass.data[DOMAIN][NOTIFIERS]:  # type: YandexNotifier
            await n.async_notify_skill([])
            _LOGGER.debug(n.format_log_message('Device list update initiated'))

    hass.bus.async_listen('state_changed', state_change_listener)
    hass.bus.async_listen('homeassistant_started', ha_start_listener)

    return True
