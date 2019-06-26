"""Support for Actions on Yandex Smart Home."""
import logging
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entityfilter

from custom_components.yandex_smart_home.const import (
    DOMAIN, CONF_ENTITY_CONFIG, CONF_FILTER, CONF_ROOM
)
from custom_components.yandex_smart_home.http import async_register_http

_LOGGER = logging.getLogger(__name__)

ENTITY_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_ROOM): cv.string,
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
