import asyncio
import base64
import json
import logging
import pickle
import re
from os import path
import time
from datetime import datetime, timezone

from .const import DOMAIN, CONF_SKILL, CONF_SKILL_NAME, CONF_SKILL_USER, CONF_ENTITY_CONFIG, CONF_FILTER
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, STATE_UNAVAILABLE, CONF_USERNAME, CONF_PASSWORD

from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.network import get_url, NoURLAvailableError
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.core import Event

from .helpers import RequestData, YandexEntity, Config
from .error import SmartHomeError
from .core.yandex_session import YandexSession

_LOGGER = logging.getLogger(__name__)

INDEX = 'https://dialogs.yandex.ru/developer'
SKILL_API_URL = 'https://dialogs.yandex.net/api/v1/skills'
TOKEN_URL = 'https://oauth.yandex.ru/authorize?response_type=token&client_id=c473ca268cd749d3a8371351a8f2bcbd'
DISCOVERY_URL = '/callback/discovery' # для параметров устройств
STATE_URL = '/callback/state' # для состояния устройств

class YandexSkill():

    def __init__(self, hass: HomeAssistantType, session: YandexSession):
        config = hass.data[DOMAIN]
        self.hass = hass
        self.config = Config(
            should_expose=config.get(CONF_FILTER),
            entity_config=config.get(CONF_ENTITY_CONFIG)
        )
        self.skill_name = config[CONF_SKILL][CONF_SKILL_NAME] if CONF_SKILL_NAME in config[CONF_SKILL] else 'Home Assistant'   
        self.session = session
        self.notification_session = ''
        self.csrf_token = ''
        self.skill_id = ''
        self.user_id = config[CONF_SKILL][CONF_SKILL_USER]
        self.oauth_token = ''
        self.should_expose = config.get(CONF_FILTER)
        
    async def async_init(self):
        try:        
            self.notification_session = async_create_clientsession(self.hass)
            if self.oauth_token == '':
                if not await self.get_oauth_token():
                    _LOGGER.error("Async Init Failed")
                    return False
            if self.skill_id == '':
                if not await self.get_skill_id():
                    _LOGGER.error("Async Init Failed")
                    return False
            
            await self.link_skill()
            
            return True
        except Exception:
            _LOGGER.exception("Async Init Failed")

    async def get_skill_id(self):
        try:
            if self.skill_id == '':
                # check if skill exists
                r = await self.session.get(f"{INDEX}/api/snapshot")
                assert r.status == 200, await r.read()
                data = await r.json()
                for skill in data['result']['skills']:
                    if skill['name'] == self.skill_name or skill['draft']['name'] == self.skill_name:
                        self.skill_id = skill['id']
                        _LOGGER.debug(f"Skill ID: {self.skill_id}")
                        return self.skill_id
            # create skill
            coro = self.create_skill()
            asyncio.create_task(coro)
        except Exception:
            _LOGGER.exception("Skill ID Failed")
        return False
            
    async def get_oauth_token(self):
        try:
            if self.oauth_token == '':
                r = await self.session.get(f"{TOKEN_URL}")
                assert r.status == 200, await r.read()
                data = dict(x.split('=', 1) for x in r.real_url.fragment.split('&'))   
                self.oauth_token = data.get('access_token')
                _LOGGER.debug(f"OAuth Token: {self.oauth_token}")
                return self.oauth_token
        except Exception:
            _LOGGER.exception("OAuth Token Failed")
        return False
           
    async def get_csrf_token(self):
        try:
            if self.csrf_token == '':
                r = await self.session.get(INDEX)
                assert r.status == 200, await r.read()
                data = await r.text()
                m = re.search(r'"secretkey":"(.+?)"', data)
                self.csrf_token = m[1]
                _LOGGER.debug(f"CSRF Token: {self.csrf_token}")
                return self.csrf_token
        except Exception:
            _LOGGER.exception("CSRF Token Failed")
        return
    
    async def async_notify_skill(self, devices: str):
        try:
            url = f"{SKILL_API_URL}/{self.skill_id}"
            headers = {"Authorization": "OAuth "+self.oauth_token}
            ts = time.time()
            if devices:
                url_tail = STATE_URL 
                payload = {"user_id": self.user_id, "devices": devices}
            else:
                url_tail = DISCOVERY_URL
                payload = {"user_id": self.user_id}
            data = {"ts": ts,"payload": payload}
            #_LOGGER.debug(f"Request sent: {data}")

            r = await self.notification_session.post(f"{url}{url_tail}", headers=headers,
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

    async def get_oauth_appid(self, session, hass_url = ''):
        oauth_appid = None
        try:
            if hass_url == '':
                # check external HTTPS URL
                try:
                    hass_url = get_url(self.hass, require_ssl=True, allow_internal=False)
                    _LOGGER.debug(f"External hass URL: {hass_url}")
                except NoURLAvailableError:
                    _LOGGER.error("Can't get external HTTPS URL")
                    return
            
            headers = {'x-csrf-token': self.csrf_token}
            created_at = datetime.now(tz=timezone.utc).astimezone(timezone.utc).isoformat('T','milliseconds').replace('+00:00','Z')
            updated_at = created_at
            payload = {
              "name": self.skill_name,
              "createdAt":created_at,
              "updatedAt":updated_at,
              "clientId":"https://social.yandex.net/",
              "authorizationUrl": hass_url + "/auth/authorize",
              "tokenUrl": hass_url + "/auth/token",
              "refreshTokenUrl": hass_url + "/auth/token",
              "clientSecret":"secret"
            }
            r = await session.post(f"{INDEX}/api/oauth/apps", headers=headers, 
                                   json=payload)
            assert r.status == 201, await r.read()
            data = await r.json()
            oauth_appid = data['result']['id']
            _LOGGER.debug(f"OAuth AppID: {oauth_appid}")
        except Exception:
            _LOGGER.exception("OAuth AppID Failed")
        return oauth_appid

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
            if self.skill_id !='':
                url = f"{INDEX}/skills/{self.skill_id}"
                _LOGGER.debug(f"Skill already exists: {url}")
                return
            
            csrf_token = await self.get_csrf_token()

            raw = base64.b64decode(self.session.cookie)

            session = async_create_clientsession(self.hass)
            session.cookie_jar._cookies = pickle.loads(raw)

            headers = {'x-csrf-token': csrf_token}

            # create new skill
            r = await session.post(f"{INDEX}/api/skills", headers=headers,
                                   json={'channel': 'smartHome'})
            assert r.status == 201, await r.read()
            data = await r.json()
            self.skill_id = data['result']['id']
            skill_url = f"{INDEX}/skills/{data['result']['id']}"
            
            # upload logo.png as skill logo
            filename = path.join(path.dirname(path.abspath(__file__)), 'logo.png')
            r = await session.post(
                f"{INDEX}/api/skills/{self.skill_id}/logo", headers=headers,
                data={'file': open(filename, 'rb')})
            assert r.status == 201, await r.read()
            data = await r.json()
            logo_id = data['result']['id']

            # get oauthAppId
            appid = await self.get_oauth_appid(session, hass_url)

            # settings
            payload = {
                "activationPhrases": [self.skill_name],
                "appMetricaApiKey": "",
                "backendSettings": {
                    "backendType": "webhook",
                    "functionId": "",
                    "uri": hass_url + '/api/' + DOMAIN
                },
                "exactSurfaces": [],
                "hideInStore": True, #False
                "logo2": None,
                "logoId": logo_id,
                "name": self.skill_name,
                "noteForModerator": "",
                "oauthAppId": appid,
                "publishingSettings": {
                    "brandVerificationWebsite": "",
                    "category": "utilities",
                    "secondaryTitle": "Home Assistant",
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
            r = await session.patch(f"{INDEX}/api/skills/{self.skill_id}/draft",
                                    headers=headers, json=payload)
            assert r.status == 200, await r.read()

            # check if webhook works ???
            # payload = {"text": "", "isDraft": True, "sessionId": "",
                       # "sessionSeq": 0, "surface": "mobile",
                       # "isAnonymousUser": False}
            # r = await session.post(f"{INDEX}/api/skills/{self.skill_id}/message",
                                    # headers=headers, json=payload)
            # assert r.status == 201, await r.read()
            # data = await r.json()
            # error = data['result'].get('error')
            # if error:
                # _LOGGER.debug(f"Ошибка при создании навыка: {error}")
                # self.hass.components.persistent_notification.async_create(
                    # f"При создании навыка: [ссылка]({skill_url})\n"
                    # f"возникла ошибка: `{error}`\n"
                    # f"Проверьте внешний доступ: {hass_url}",
                    # title="Yandex Smart Home")
                # #return

            # publish skill
            r = await session.post(f"{INDEX}/api/skills/{self.skill_id}/release",
                                    headers=headers)
            assert r.status == 201, await r.read()

            _LOGGER.debug("Навык успешно создан")
            self.hass.components.persistent_notification.async_create(
                f"Навык успешно создан: [ссылка]({skill_url})",
                title="Yandex Smart Home")

        except Exception:
            _LOGGER.exception("Create Skill Failed")
            
    async def link_skill(self):
        skill_linked = False
        iot_url = 'https://iot.quasar.yandex.ru/m/user/skills/' + self.skill_id
        linking_url = 'https://yandex.ru/quasar/iot/linking/' + self.skill_id

        r = await self.session.get(iot_url)
        assert r.status == 200, await r.read()
        data = await r.json()
        skill_linked = data.get('is_bound')
        _LOGGER.debug(f"Skill linked: {skill_linked}")
        if skill_linked:
            return True

        # check external HTTPS URL
        try:
            hass_url = get_url(self.hass, require_ssl=True, allow_internal=False)
            _LOGGER.debug(f"External hass URL: {hass_url}")
        except NoURLAvailableError:
            _LOGGER.error("Can't get external HTTPS URL")
            return False

        
        # link skill
        #get token
        token = ''

        
        auth_url = hass_url + "/auth/authorize?state=https%3A%2F%2Fsocial.yandex.ru%2Fbroker2%2Fauthz_in_web%2F" + token + "%2Fcallback&redirect_uri=https%3A%2F%2Fsocial.yandex.net%2Fbroker%2Fredirect&response_type=code&client_id=https%3A%2F%2Fsocial.yandex.net%2F"
        _LOGGER.debug(f"Auth url: {auth_url}")
        
        return skill_linked
