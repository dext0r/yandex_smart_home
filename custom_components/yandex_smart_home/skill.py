import asyncio
import base64
import json
import logging
import pickle
import re
from os import path
import time

from .const import DOMAIN, CONF_SKILL, CONF_SKILL_NAME, CONF_SKILL_USER, CONF_SKILL_OAUTH_TOKEN, CONF_ENTITY_CONFIG, CONF_FILTER
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, STATE_UNAVAILABLE

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
            should_expose=config.get(CONF_FILTER),
            entity_config=config.get(CONF_ENTITY_CONFIG)
        )
        self.skill_name = config[CONF_SKILL][CONF_SKILL_NAME]
        self.session = ''
        self.skill_id = ''
        self.user_id = config[CONF_SKILL][CONF_SKILL_USER]
        self.oauth_token = config[CONF_SKILL][CONF_SKILL_OAUTH_TOKEN]
        self.should_expose = config.get(CONF_FILTER)
        self.start_session()
        
    def start_session(self):
        try:
            cachefile = self.hass.config.path(f".yandex_station.json")

            if not path.isfile(cachefile):
                _LOGGER.error("Empty Yandex Login Data")
                return

            with open(cachefile, 'rt') as f:
                raw = json.load(f)

            raw = base64.b64decode(raw['cookie'])

            self.session = async_create_clientsession(self.hass)
            self.session.cookie_jar._cookies = pickle.loads(raw)
            
        except Exception:
            _LOGGER.exception("Session Start Failed")

    async def get_skill_id(self):
        try:
            if self.skill_id == '':
                # check if skill exists
                r = await self.session.get(INDEX)
                assert r.status == 200, await r.read()
                data = await r.text()
                m = re.search(r'"secretkey":"(.+?)"', data)
                headers = {'x-csrf-token': m[1]}
                r = await self.session.get(f"{INDEX}/api/snapshot", headers=headers)
                assert r.status == 200, await r.read()
                data = await r.json()
                for skill in data['result']['skills']:
                    if skill['name'] == self.skill_name or skill['draft']['name'] == self.skill_name:
                        self.skill_id = skill['id']
                        _LOGGER.debug(f"Skill ID: {self.skill_id}")
        except Exception:
            _LOGGER.exception("Skill ID Failed")
           
    async def async_notify_skill(self, devices: str):
        try:
            if self.skill_id == '':
                await self.get_skill_id()
            url = f"{SKILL_API_URL}/{self.skill_id}"
            headers = {"Authorization": "OAuth "+self.oauth_token,"Content-Type": "application/json"}
            #ts = int(time.time())
            ts = time.time()
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
                _LOGGER.debug(f"Ошибка при обновлении данных: {error}")
                return
            #_LOGGER.debug(f"Result recieved: {data}")
        except Exception:
            _LOGGER.exception("Notify Skill Failed")
    
    async def async_event_handler(self, event: Event):
        
        devices = []
        new_state = event.data.get('new_state')
        entity_id = event.data.get('entity_id')
        if event.data.get('old_state') is None:
            return
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return
            
        if not self.should_expose(entity_id):
            return

        if new_state.state == STATE_UNAVAILABLE:
            return
            
        _LOGGER.debug("Update "+entity_id+": "+new_state.state)
        if new_state:
            entity = YandexEntity(self.hass, self.config, new_state)
            device = entity.query_serialize()
            if device['capabilities'] or device['properties']:
                devices.append(device)
            if devices:
                await self.async_notify_skill(devices)

    async def create_skill(self):
        # check external HTTPS URL
        try:
            hass_url = get_url(self.hass, require_ssl=True, allow_internal=False)
            _LOGGER.debug(f"External hass URL: {hass_url}")
        except NoURLAvailableError:
            _LOGGER.error("Can't get external HTTPS URL")
            return

        try:
            # check if skill exists
            r = await self.session.get(INDEX)
            assert r.status == 200, await r.read()
            data = await r.text()
            m = re.search(r'"secretkey":"(.+?)"', data)
            headers = {'x-csrf-token': m[1]}

            r = await self.session.get(f"{INDEX}/api/snapshot", headers=headers)
            assert r.status == 200, await r.read()
            data = await r.json()
            for skill in data['result']['skills']:
                if skill['name'] == self.skill_name or skill['draft']['name'] == self.skill_name:
                    url = f"{INDEX}/skills/{skill['id']}"
                    _LOGGER.debug(f"Skill already exists: {url}")
                    return

            # create new skill
            r = await self.session.post(f"{INDEX}/api/skills", headers=headers,
                                   json={'channel': 'smartHome'})
            assert r.status == 201, await r.read()
            data = await r.json()
            self.skill_id = data['result']['id']
            skill_url = f"{INDEX}/skills/{data['result']['id']}"

            filename = path.join(path.dirname(path.abspath(__file__)), 'logo.png')
            r = await self.session.post(
                f"{INDEX}/api/skills/{self.skill_id}/logo", headers=headers,
                data={'file': open(filename, 'rb')})
            assert r.status == 201, await r.read()
            data = await r.json()
            logo_id = data['result']['id']

            payload = {
                "activationPhrases": [self.skill_name],
                "appMetricaApiKey": "",
                "backendSettings": {
                    "backendType": "webhook",
                    "functionId": "",
                    "uri": hass_url + '/api/' + DOMAIN
                },
                "exactSurfaces": [],
                "hideInStore": False,
                "logo2": None,
                "logoId": logo_id,
                "name": self.skill_name,
                "noteForModerator": "",
                "oauthAppId": None,
                "publishingSettings": {
                    "brandVerificationWebsite": "",
                    "category": "utilities",
                    "description": "Home Assistant",
                    "developerName": "Home Assistant",
                    "email": "",
                    "explicitContent": None,
                    "structuredExamples": [{
                        "activationPhrase": self.skill_name,
                        "marker": "запусти навык",
                        "request": ""
                    }]
                },
                "requiredInterfaces": [],
                "rsyPlatformId": "",
                "skillAccess": "private",
                "surfaceBlacklist": [],
                "surfaceWhitelist": [],
                "useStateStorage": False,
                "voice": "shitova.us",
                "yaCloudGrant": False
            }
            r = await self.session.patch(f"{INDEX}/api/skills/{self.skill_id}/draft",
                                    headers=headers, json=payload)
            assert r.status == 200, await r.read()

            # check if webhook works
            payload = {"text": "", "isDraft": True, "sessionId": "",
                       "sessionSeq": 0, "surface": "mobile",
                       "isAnonymousUser": False}
            r = await self.session.post(f"{INDEX}/api/skills/{self.skill_id}/message",
                                   headers=headers, json=payload)
            assert r.status == 201, await r.read()
            data = await r.json()
            error = data['result'].get('error')
            if error:
                _LOGGER.debug(f"Ошибка при создании навыка: {error}")
                self.hass.components.persistent_notification.async_create(
                    f"При создании навыка: [ссылка]({skill_url})\n"
                    f"возникла ошибка: `{error}`\n"
                    f"Проверьте внешний доступ: {hass_url}",
                    title="Yandex Dialogs")
                return

            # publish skill
            r = await self.session.post(f"{INDEX}/api/skills/{self.skill_id}/release",
                                   headers=headers)
            assert r.status == 201, await r.read()

            _LOGGER.debug("Навык успешно создан")
            self.hass.components.persistent_notification.async_create(
                f"Навык успешно создан: [ссылка]({skill_url})",
                title="Yandex Dialogs")

        except Exception:
            _LOGGER.exception("Create Skill")
