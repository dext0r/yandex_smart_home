"""Support for Actions on Yandex Smart Home."""
import logging
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN, CONF_EXPOSE_BY_DEFAULT, DEFAULT_EXPOSE_BY_DEFAULT,
    CONF_EXPOSED_DOMAINS, DEFAULT_EXPOSED_DOMAINS,
    CONF_ENTITY_CONFIG, CONF_EXPOSE, CONF_ROOM
)
from .http import async_register_http

_LOGGER = logging.getLogger(__name__)

ENTITY_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_EXPOSE): cv.boolean,
    vol.Optional(CONF_ROOM): cv.string,
})

YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(CONF_EXPOSE_BY_DEFAULT,
                     default=DEFAULT_EXPOSE_BY_DEFAULT): cv.boolean,
        vol.Optional(CONF_EXPOSED_DOMAINS,
                     default=DEFAULT_EXPOSED_DOMAINS): cv.ensure_list,
        vol.Optional(CONF_ENTITY_CONFIG): {cv.entity_id: ENTITY_SCHEMA},
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, yaml_config: Dict[str, Any]):
    """Activate Yandex Smart Home component."""
    config = yaml_config.get(DOMAIN, {})
    async_register_http(hass, config)

    return True
