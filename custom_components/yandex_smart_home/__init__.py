"""Support for Actions on Yandex Smart Home."""
import logging
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, Event
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entityfilter

from .const import (
    DOMAIN, CONF_ENTITY_CONFIG, CONF_FILTER, CONF_ROOM, CONF_TYPE,
    CONF_ENTITY_PROPERTIES, CONF_ENTITY_PROPERTY_ENTITY, CONF_ENTITY_PROPERTY_ATTRIBUTE, CONF_ENTITY_PROPERTY_TYPE,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID, CONF_RELATIVE_VOLUME_ONLY, CONF_ENTITY_RANGE, CONF_ENTITY_RANGE_MAX, 
    CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_PRECISION, CONF_ENTITY_MODE_MAP,
    CONF_SETTINGS, CONF_PRESSURE_UNIT, PRESSURE_UNIT_MMHG, PRESSURE_UNITS_TO_YANDEX_UNITS,
    CONF_SKILL, CONF_SKILL_OAUTH_TOKEN, CONF_SKILL_ID, CONF_SKILL_USER_ID)
from .http import async_register_http
from .skill import YandexSkillLight

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

def pressure_unit_validate(unit):
    if not unit in PRESSURE_UNITS_TO_YANDEX_UNITS:
        raise vol.Invalid(f'Pressure unit "{unit}" is not supported')

    return unit

SKILL_SCHEMA = vol.Schema({
    vol.Optional(CONF_SKILL_OAUTH_TOKEN): cv.string,
    vol.Optional(CONF_SKILL_ID): cv.string,
    vol.Optional(CONF_SKILL_USER_ID): cv.string,
}, extra=vol.PREVENT_EXTRA)

SETTINGS_SCHEMA = vol.Schema({
    vol.Optional(CONF_PRESSURE_UNIT, default=PRESSURE_UNIT_MMHG): vol.Schema(
        vol.All(str, pressure_unit_validate)
    ),
})

YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(CONF_SKILL, default={}): SKILL_SCHEMA,
        vol.Optional(CONF_SETTINGS, default={}): SETTINGS_SCHEMA,
        vol.Optional(CONF_FILTER, default={}): entityfilter.FILTER_SCHEMA,
        vol.Optional(CONF_ENTITY_CONFIG, default={}): {cv.entity_id: ENTITY_SCHEMA},
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, yaml_config: Dict[str, Any]):
    """Activate Yandex Smart Home component."""

    config = yaml_config.get(DOMAIN, {})
    async_register_http(hass, config)
    
    await _setup_skill(hass, config)

    return True

async def _setup_skill(hass: HomeAssistant, config):
    """Set up connection to Yandex Dialogs."""
    _LOGGER.info("Skill Setup") 
    try:
        skill = YandexSkillLight(hass, config)
        if not skill:
            _LOGGER.error("Skill Setup Failed") 
            return False
            
        async def listener(event: Event):
            await skill.async_event_handler(event)
        
        hass.bus.async_listen('state_changed', listener)
        
    except Exception:
        _LOGGER.exception("Skill Setup error")
        return False