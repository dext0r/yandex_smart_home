import logging
from time import time
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from .const import (
    DOMAIN, CONFIG, DATA_CONFIG, CONF_NOTIFIER, CONF_SKILL_OAUTH_TOKEN,
    CONF_SKILL_ID, CONF_NOTIFIER_USER_ID, NOTIFIER_ENABLED
)
from .helpers import YandexEntity

_LOGGER = logging.getLogger(__name__)

SKILL_API_URL = 'https://dialogs.yandex.net/api/v1/skills'
DISCOVERY_URL = '/callback/discovery' # для параметров устройств
STATE_URL = '/callback/state' # для состояния устройств

def setup_notification(hass: HomeAssistant):
    """Set up notification."""
    _LOGGER.info("Notifier Setup")
    try:
        if not hass.data[DOMAIN][CONFIG][CONF_NOTIFIER]:
            _LOGGER.error("Notifier Setup Failed: No Config")
            return False

        notifier = YandexNotifier(hass)
        if not notifier.init():
            _LOGGER.error("Notifier Setup Failed")
            hass.components.persistent_notification.async_create(
                "Ошибка при инициализации (уведомление навыка об изменении состояния устройств работать не будет).",
                title="Yandex Smart Home")
            return False
        
        hass.data[DOMAIN][NOTIFIER_ENABLED] = True
        
        async def listener(event: Event):
            await notifier.async_event_handler(event)
        
        hass.bus.async_listen('state_changed', listener)
        
    except Exception:
        _LOGGER.exception("Notifier Setup Error")
        return False

class YandexNotifier():

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.oauth_token = hass.data[DOMAIN][CONFIG][CONF_NOTIFIER][CONF_SKILL_OAUTH_TOKEN] if CONF_SKILL_OAUTH_TOKEN in hass.data[DOMAIN][CONFIG][CONF_NOTIFIER] else ''
        self.skill_id = hass.data[DOMAIN][CONFIG][CONF_NOTIFIER][CONF_SKILL_ID] if CONF_SKILL_ID in hass.data[DOMAIN][CONFIG][CONF_NOTIFIER] else ''
        self.user_id = hass.data[DOMAIN][CONFIG][CONF_NOTIFIER][CONF_NOTIFIER_USER_ID] if CONF_NOTIFIER_USER_ID in hass.data[DOMAIN][CONFIG][CONF_NOTIFIER] else ''
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
                "Ошибка при инициализации (уведомление навыка об изменении состояния устройств работать не будет).",
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
            _LOGGER.exception("Notifier Failed")
    
    async def async_event_handler(self, event: Event):
        devices = []
        entity_id = event.data.get('entity_id')
        old_state = event.data.get('old_state')
        new_state = event.data.get('new_state')
        if not old_state or old_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return
        if not new_state or new_state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            return
        if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES or not self.hass.data[DOMAIN][DATA_CONFIG].should_expose(entity_id):
            return
        old_entity = YandexEntity(self.hass, self.hass.data[DOMAIN][DATA_CONFIG], old_state)
        entity = YandexEntity(self.hass, self.hass.data[DOMAIN][DATA_CONFIG], new_state)
        device = entity.query_serialize()
        if old_entity.query_serialize() != device: # есть изменения
            if device['capabilities'] or device['properties']:
                devices.append(device)
                if devices:
                    await self.async_notify_skill(devices)
                    _LOGGER.info("Update "+entity_id+": "+new_state.state)

