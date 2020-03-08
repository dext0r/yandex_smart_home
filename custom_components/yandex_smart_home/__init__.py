"""Support for Actions on Yandex Smart Home."""
import logging
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entityfilter

from .const import (
    DOMAIN, CONF_ENTITY_CONFIG, CONF_FILTER, CONF_ROOM, CONF_TYPE,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID, CONF_RELATIVE_VOLUME_ONLY,
    CONF_OPERATION_MODE_ON,
    CONF_SUPPORT_SERVICE_TURN_ON_OFF)
from .http import async_register_http

_LOGGER = logging.getLogger(__name__)

ENTITY_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_ROOM): cv.string,
    vol.Optional(CONF_TYPE): cv.string,
    vol.Optional(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID): cv.boolean,
    vol.Optional(CONF_RELATIVE_VOLUME_ONLY): cv.boolean,
    vol.Optional(CONF_OPERATION_MODE_ON): cv.string,
    vol.Optional(CONF_SUPPORT_SERVICE_TURN_ON_OFF): cv.boolean,
})

YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(CONF_FILTER, default={}): entityfilter.FILTER_SCHEMA,
        vol.Optional(CONF_ENTITY_CONFIG, default={}): {cv.entity_id:
                                                       ENTITY_SCHEMA},
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, yaml_config: Dict[str, Any]):
    """Activate Yandex Smart Home component."""
    config = yaml_config.get(DOMAIN, {})
    async_register_http(hass, config)

    return True
