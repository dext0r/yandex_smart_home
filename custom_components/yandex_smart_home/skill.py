import asyncio
import base64
import json
import logging
import pickle
import re
from os import path
import time

from .const import DOMAIN, CONF_SKILL, CONF_SKILL_NAME, CONF_SKILL_USER, CONF_SKILL_OAUTH_TOKEN, CONF_ENTITY_CONFIG, CONF_FILTER
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES

from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.network import get_url, NoURLAvailableError
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.core import Event

from .helpers import RequestData, YandexEntity, Config
from .error import SmartHomeError

_LOGGER = logging.getLogger(__name__)

INDEX = 'https://dialogs.yandex.ru/developer'
SKILL_API_URL = 'https://dialogs.yandex.net/api/v1/skills'
DISCOVERY_URL = '/callback/discovery' # для параметров устройств
STATE_URL = '/callback/state' # для состояния устройств




class YandexSkill():

    def __init__(self, hass: HomeAssistantType, config: str):
        self.hass = hass
        self.config = Config(
            should_expose=self.config.get(CONF_FILTER),
            entity_config=self.config.get(CONF_ENTITY_CONFIG)
        )
        self.skill_name = config[CONF_SKILL][CONF_SKILL_NAME]
        self.user_id = config[CONF_SKILL][CONF_SKILL_USER]
        self.oauth_token = config[CONF_SKILL][CONF_SKILL_OAUTH_TOKEN]
        self.should_expose=self.config.get(CONF_FILTER)
        
    async def async_notify_skill(self, devices: str):
        try:
            cachefile = self.hass.config.path(f".yandex_station.json")

            if not path.isfile(cachefile):
                _LOGGER.error("Empty Yandex Login Data")
                return

            with open(cachefile, 'rt') as f:
                raw = json.load(f)

            raw = base64.b64decode(raw['cookie'])

            session = async_create_clientsession(self.hass)
            session.cookie_jar._cookies = pickle.loads(raw)

            # check if skill exists + get url & id
            r = await session.get(INDEX)
            assert r.status == 200, await r.read()
            data = await r.text()
            m = re.search(r'"secretkey":"(.+?)"', data)
            headers = {'x-csrf-token': m[1]}
            url=''
            skill_id = ''
            r = await session.get(f"{INDEX}/api/snapshot", headers=headers)
            assert r.status == 200, await r.read()
            data = await r.json()
            for skill in data['result']['skills']:
                if skill['name'] == self.skill_name or skill['draft']['name'] == self.skill_name:
                    url = f"{SKILL_API_URL}/{skill['id']}"
                    skill_id = skill['id']
                    #_LOGGER.debug(f"Skill ID: {skill_id}")
            headers = {"Authorization": "OAuth "+self.oauth_token,"Content-Type": "application/json"}
            ts = int(time.time())
            data = {"ts": ts,"payload": {"user_id": self.user_id, "devices": devices}}
            _LOGGER.debug(f"Request: {data}")

            r = await session.post(f"{url}{STATE_URL}", headers=headers,
                                   json=data)
            assert r.status == 202, await r.read()
            data = await r.json()
            error = data.get('error_message')
            if error:
                _LOGGER.debug(f"Ошибка при обновлении данных: {error}")
                return
            _LOGGER.debug(f"Result: {data}")
        except Exception:
            _LOGGER.exception("Notify Dialog")
    
    async def async_event_handler(self, event: Event):
        
        devices = []
        
        #if event.data.get('old_state') != None:
        entity_id = event.data.get('entity_id')
                
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return
            
        if not self.should_expose(entity_id):
            return
        
        new_state = event.data.get('new_state')
        _LOGGER.debug("Update "+entity_id+": "+new_state.state)
        if new_state:
            entity = YandexEntity(self.hass, self.config, new_state)
            devices.append(entity.query_serialize())
            await self.async_notify_skill(devices)
