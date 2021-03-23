"""Support for Actions on Yandex Smart Home."""
import asyncio
import logging
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, Event
from homeassistant.const import CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_TOKEN
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entityfilter
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    DOMAIN, CONF_ENTITY_CONFIG, CONF_FILTER, CONF_ROOM, CONF_TYPE,
    CONF_ENTITY_PROPERTIES, CONF_ENTITY_PROPERTY_ENTITY, CONF_ENTITY_PROPERTY_ATTRIBUTE, CONF_ENTITY_PROPERTY_TYPE,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID, CONF_RELATIVE_VOLUME_ONLY, CONF_ENTITY_RANGE, CONF_ENTITY_RANGE_MAX, 
    CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_PRECISION, CONF_ENTITY_MODE_MAP,
    CONF_SKILL, CONF_SKILL_NAME, CONF_SKILL_USER, CONF_PROXY)

from .http import async_register_http
from .core import utils
from .core.yandex_session import YandexSession
from .skill import YandexSkill

_LOGGER = logging.getLogger(__name__)

ENTITY_PROPERTY_SCHEMA = vol.Schema({
    vol.Optional(CONF_ENTITY_PROPERTY_TYPE): cv.string,
    vol.Optional(CONF_ENTITY_PROPERTY_ENTITY): cv.string,
    vol.Optional(CONF_ENTITY_PROPERTY_ATTRIBUTE): cv.string,
}, extra=vol.PREVENT_EXTRA)

ENTITY_RANGE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ENTITY_RANGE_MAX): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(CONF_ENTITY_RANGE_MIN): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(CONF_ENTITY_RANGE_PRECISION): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
}, extra=vol.PREVENT_EXTRA)

ENTITY_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_ROOM): cv.string,
    vol.Optional(CONF_TYPE): cv.string,
    vol.Optional(CONF_ENTITY_PROPERTIES, default=[]): [ENTITY_PROPERTY_SCHEMA],
    vol.Optional(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID): cv.boolean,
    vol.Optional(CONF_RELATIVE_VOLUME_ONLY): cv.boolean,
    vol.Optional(CONF_ENTITY_RANGE, default={}): ENTITY_RANGE_SCHEMA,
    vol.Optional(CONF_ENTITY_MODE_MAP, default={}): {cv.string: {cv.string: [cv.string]}},
})

SKILL_SCHEMA = vol.Schema({
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_TOKEN): cv.string,
    vol.Optional(CONF_PROXY): cv.string,
    vol.Optional(CONF_SKILL_NAME): cv.string,
    vol.Optional(CONF_SKILL_USER): cv.string,
}, extra=vol.PREVENT_EXTRA)

YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(CONF_SKILL, default={}): SKILL_SCHEMA,
        vol.Optional(CONF_FILTER, default={}): entityfilter.FILTER_SCHEMA,
        vol.Optional(CONF_ENTITY_CONFIG, default={}): {cv.entity_id: ENTITY_SCHEMA},
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, yaml_config: Dict[str, Any]):
    """Activate Yandex Smart Home component."""
    hass.data[DOMAIN] = yaml_config.get(DOMAIN, {})
    async_register_http(hass, hass.data[DOMAIN])
    
    await _setup_entry_from_config(hass)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    async def update_cookie_and_token(**kwargs):
        hass.config_entries.async_update_entry(entry, data=kwargs)
    
    config = hass.data[DOMAIN][CONF_SKILL]
    session = async_create_clientsession(hass)
    yandex = YandexSession(session, **entry.data)
    yandex.proxy = config.get(CONF_PROXY)
    yandex.add_update_listener(update_cookie_and_token)

    if not await yandex.refresh_cookies():
        hass.components.persistent_notification.async_create(
            "Необходимо заново авторизоваться в Яндексе. Для этого [добавьте "
            "новую интеграцию](/config/integrations) с тем же логином.",
            title="Yandex Smart Home")
        return False
    
    if CONF_SKILL_NAME in entry.options and CONF_SKILL_NAME not in hass.data[DOMAIN][CONF_SKILL]:
        hass.data[DOMAIN][CONF_SKILL][CONF_SKILL_NAME] = entry.options[CONF_SKILL_NAME]
    if CONF_SKILL_USER in entry.options and CONF_SKILL_USER not in hass.data[DOMAIN][CONF_SKILL]:
        hass.data[DOMAIN][CONF_SKILL][CONF_SKILL_USER] = entry.options[CONF_SKILL_USER]
    
    await _setup_skill(hass, yandex)
    
    return True
    
async def _setup_entry_from_config(hass: HomeAssistant):
    """Support legacy config from YAML."""
    _LOGGER.info("Trying to import config into entry...")
    if CONF_SKILL not in hass.data[DOMAIN]:
        _LOGGER.debug("No skill config")
        return
        
    config = hass.data[DOMAIN][CONF_SKILL]
    if CONF_USERNAME not in config:
        _LOGGER.debug("No username inside config - nothing to import")
        return
    
    # check if already configured
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.unique_id == config[CONF_USERNAME]:
            _LOGGER.info("Config entry already configured")
            return
    
    if CONF_TOKEN not in config:
        # load config/.yandex_station.json
        x_token = utils.load_token_from_json(hass)
        if x_token:
            _LOGGER.info("x_token is inside json")
            config['x_token'] = x_token
    else:
        config['x_token'] = config[CONF_TOKEN]
        _LOGGER.info("Got x_token from config")
        
    # need username and token or password
    if 'x_token' not in config and CONF_PASSWORD not in config:
        _LOGGER.error("No password or x_token inside config")
        return
    _LOGGER.info("Credentials configured inside config - BEGIN IMPORT")
    
    hass.async_create_task(hass.config_entries.flow.async_init(
        DOMAIN, context={'source': SOURCE_IMPORT}, data=config
    ))
    
async def _setup_skill(hass: HomeAssistant, session: YandexSession):
    """Set up connection to Yandex Dialogs."""
    _LOGGER.info("Skill Setup") 
    try:
        skill = YandexSkill(hass, session)
        if not await skill.async_init():
            _LOGGER.error("Skill Setup Failed") 
            return False
            
        async def listener(event: Event):
            await skill.async_event_handler(event)
        
        hass.bus.async_listen('state_changed', listener)
        
    except Exception:
        _LOGGER.exception("Skill Setup error")
        return False
