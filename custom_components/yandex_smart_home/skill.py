import asyncio
import base64
import json
import logging

from time import time

from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, STATE_UNAVAILABLE
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.core import HomeAssistant, Event

from .const import (
    DOMAIN, CONF_SKILL, CONF_SKILL_OAUTH_TOKEN, CONF_SETTINGS, 
    CONF_SKILL_ID, CONF_SKILL_USER_ID, CONF_ENTITY_CONFIG, CONF_FILTER, NOTIFIER
)
from .helpers import YandexEntity, Config
from .error import SmartHomeError

_LOGGER = logging.getLogger(__name__)

SKILL_API_URL = 'https://dialogs.yandex.net/api/v1/skills'
DISCOVERY_URL = '/callback/discovery' # для параметров устройств
STATE_URL = '/callback/state' # для состояния устройств

async def setup_notification(hass: HomeAssistant, config):
    """Set up notification."""
    _LOGGER.info("Skill Setup")
    hass.data[DOMAIN][NOTIFIER] = False
    try:
        if not config[CONF_SKILL]:
            _LOGGER.error("Skill Setup Failed: No Config")
            return False

        skill = YandexSkillLight(hass, config)
        if not skill.init():
            _LOGGER.error("Skill Setup Failed")
            return False
        
        hass.data[DOMAIN][NOTIFIER] = True
        
        async def listener(event: Event):
            await skill.async_event_handler(event)
        
        hass.bus.async_listen('state_changed', listener)
        
    except Exception:
        _LOGGER.exception("Skill Setup Error")
        return False

class YandexSkillLight():

    def __init__(self, hass: HomeAssistantType, config):
        self.hass = hass
        self.oauth_token = config[CONF_SKILL][CONF_SKILL_OAUTH_TOKEN] if CONF_SKILL_OAUTH_TOKEN in config[CONF_SKILL] else ''
        self.skill_id = config[CONF_SKILL][CONF_SKILL_ID] if CONF_SKILL_ID in config[CONF_SKILL] else ''
        self.user_id = config[CONF_SKILL][CONF_SKILL_USER_ID] if CONF_SKILL_USER_ID in config[CONF_SKILL] else ''
        self.should_expose = config.get(CONF_FILTER)
        self.config = Config(
            settings=config.get(CONF_SETTINGS),
            should_expose=self.should_expose,
            entity_config=config.get(CONF_ENTITY_CONFIG)
        )
        self.session = None
                
    def init(self):
        try:
            if self.oauth_token == '':
                _LOGGER.error("Async Init Failed: No OAuth Token")
                return False
            _LOGGER.info(f"OAuth Token: {self.oauth_token}")
            if self.skill_id == '':
                _LOGGER.error("Async Init Failed: No skill ID")
                return False
            _LOGGER.info(f"Skill ID: {self.skill_id}")
            if self.user_id == '':
                _LOGGER.error("Async Init Failed: No user ID")
                return False
            _LOGGER.info(f"User ID: {self.user_id}")
            self.session = async_create_clientsession(self.hass)
        except Exception:
            _LOGGER.exception("Async Init Failed")
            self.hass.components.persistent_notification.async_create(
                "Ошибка при инициализации компонента (уведомление навыка об изменении состояния устройств работать не будет).",
                title="Yandex Smart Home")
            return False
        return True
                
    async def async_notify_skill(self, devices: str):
        try:
            url = f"{SKILL_API_URL}/{self.skill_id}"
            headers = {"Authorization": "OAuth "+self.oauth_token}
            ts = time()
            if devices:
                url_tail = STATE_URL 
                payload = {"user_id": self.user_id, "devices": devices}
            else:
                url_tail = DISCOVERY_URL
                payload = {"user_id": self.user_id}
            data = {"ts": ts,"payload": payload}
            #_LOGGER.debug(f"Request sent: {data}")

            r = await self.session.post(f"{url}{url_tail}", headers=headers,
                                   json=data)
            assert r.status == 202, await r.read()
            data = await r.json()
            error = data.get('error_message')
            if error:
                _LOGGER.error(f"Ошибка при обновлении данных: {error}")
                return
            #_LOGGER.debug(f"Result recieved: {data}")
        except Exception:
            _LOGGER.exception("Notify Skill Failed")
    
    async def async_event_handler(self, event: Event):
        devices = []
        entity_id = event.data.get('entity_id')
        old_state = event.data.get('old_state')
        new_state = event.data.get('new_state')
        if old_state is None:
            return
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES or not self.should_expose(entity_id):
            return
        if new_state and new_state.state != STATE_UNAVAILABLE:
            old_entity = YandexEntity(self.hass, self.config, old_state)
            entity = YandexEntity(self.hass, self.config, new_state)
            device = entity.query_serialize()
            if old_entity.query_serialize() != device: # есть изменения
                if device['capabilities'] or device['properties']:
                    devices.append(device)
                    if devices:
                        await self.async_notify_skill(devices)
                        _LOGGER.info("Update "+entity_id+": "+new_state.state)
