"""Support for Actions on Yandex Smart Home."""
import logging
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entityfilter

from . import const
from .const import (
    DOMAIN, CONFIG, DATA_CONFIG, CONF_ENTITY_CONFIG, CONF_FILTER, CONF_ROOM, CONF_TYPE,
    CONF_ENTITY_PROPERTIES, CONF_ENTITY_PROPERTY_ENTITY, CONF_ENTITY_PROPERTY_ATTRIBUTE, CONF_ENTITY_PROPERTY_TYPE,
    CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID, CONF_ENTITY_RANGE, CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_PRECISION, CONF_ENTITY_MODE_MAP, COLOR_SETTING_SCENE,
    CONF_SETTINGS, CONF_PRESSURE_UNIT, PRESSURE_UNIT_MMHG, PRESSURE_UNITS_TO_YANDEX_UNITS,
    PROPERTY_TYPE_TO_UNITS, PROPERTY_TYPE_EVENT_VALUES, MODE_INSTANCES, MODE_INSTANCE_MODES, COLOR_SCENES,
    CONF_NOTIFIER, CONF_SKILL_OAUTH_TOKEN, CONF_SKILL_ID, CONF_NOTIFIER_USER_ID, NOTIFIER_ENABLED
)
from .helpers import Config
from .http import async_register_http
from .notifier import async_setup_notifier

_LOGGER = logging.getLogger(__name__)


def property_type_validate(property_type: str) -> str:
    if property_type not in PROPERTY_TYPE_TO_UNITS and property_type not in PROPERTY_TYPE_EVENT_VALUES:
        raise vol.Invalid(
            f'Property type {property_type!r} is not supported. '
            f'See valid types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html and '
            f'https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html'
        )

    return property_type


ENTITY_PROPERTY_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_ENTITY_PROPERTY_ENTITY, CONF_ENTITY_PROPERTY_ATTRIBUTE),
    vol.Schema({
        vol.Required(CONF_ENTITY_PROPERTY_TYPE): vol.Schema(
            vol.All(str, property_type_validate)
        ),
        vol.Optional(CONF_ENTITY_PROPERTY_ENTITY): cv.entity_id,
        vol.Optional(CONF_ENTITY_PROPERTY_ATTRIBUTE): cv.string,
    }, extra=vol.PREVENT_EXTRA)
)


def mode_instance_validate(instance: str) -> str:
    if instance not in MODE_INSTANCES and instance not in COLOR_SETTING_SCENE:
        _LOGGER.error(
            f'Mode instance {instance!r} is not supported. '
            f'See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html'
        )

        raise vol.Invalid(f'Mode instance {instance!r} is not supported.')

    return instance


def mode_validate(mode: str) -> str:
    if mode not in MODE_INSTANCE_MODES and mode not in COLOR_SCENES:
        _LOGGER.error(
            f'Mode {mode!r} is not supported. '
            f'See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html and '
            f'https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html#discovery__discovery-'
            f'parameters-color-setting-table__entry__75'
        )

        raise vol.Invalid(f'Mode {mode!r} is not supported.')

    return mode


ENTITY_MODE_MAP_SCHEMA = vol.Schema({
    vol.All(cv.string, mode_instance_validate): vol.Schema({
        vol.All(cv.string, mode_validate): [cv.string]
    })
})


def toggle_instance_validate(instance: str) -> str:
    if instance not in const.TOGGLE_INSTANCES:
        _LOGGER.error(
            f'Toggle instance {instance!r} is not supported. '
            f'See valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html'
        )

        raise vol.Invalid(f'Toggle instance {instance!r} is not supported.')

    return instance


ENTITY_RANGE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ENTITY_RANGE_MAX): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(CONF_ENTITY_RANGE_MIN): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(CONF_ENTITY_RANGE_PRECISION): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
}, extra=vol.PREVENT_EXTRA)

ENTITY_CUSTOM_MODE_SCHEMA = vol.Schema({
    vol.All(cv.string, mode_instance_validate): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_MODE_SET_MODE): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
    })
})

ENTITY_CUSTOM_TOGGLE_SCHEMA = vol.Schema({
    vol.All(cv.string, toggle_instance_validate): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON): cv.SERVICE_SCHEMA,
        vol.Required(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
    })
})

ENTITY_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_ROOM): cv.string,
    vol.Optional(CONF_TYPE): cv.string,
    vol.Optional(CONF_ENTITY_PROPERTIES, default=[]): [ENTITY_PROPERTY_SCHEMA],
    vol.Optional(CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID): cv.boolean,
    vol.Optional(CONF_ENTITY_RANGE, default={}): ENTITY_RANGE_SCHEMA,
    vol.Optional(CONF_ENTITY_MODE_MAP, default={}): ENTITY_MODE_MAP_SCHEMA,
    vol.Optional(const.CONF_ENTITY_CUSTOM_MODES, default={}): ENTITY_CUSTOM_MODE_SCHEMA,
    vol.Optional(const.CONF_ENTITY_CUSTOM_TOGGLES, default={}): ENTITY_CUSTOM_TOGGLE_SCHEMA,
})

NOTIFIER_SCHEMA = vol.Schema({
    vol.Required(CONF_SKILL_OAUTH_TOKEN): cv.string,
    vol.Required(CONF_SKILL_ID): cv.string,
    vol.Required(CONF_NOTIFIER_USER_ID): cv.string,
}, extra=vol.PREVENT_EXTRA)


def pressure_unit_validate(unit):
    if unit not in PRESSURE_UNITS_TO_YANDEX_UNITS:
        raise vol.Invalid(f'Pressure unit "{unit}" is not supported')

    return unit


SETTINGS_SCHEMA = vol.Schema({
    vol.Optional(CONF_PRESSURE_UNIT, default=PRESSURE_UNIT_MMHG): vol.Schema(
        vol.All(str, pressure_unit_validate)
    ),
})

YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(CONF_NOTIFIER, default=[]): vol.All(cv.ensure_list, [NOTIFIER_SCHEMA]),
        vol.Optional(CONF_SETTINGS, default={}): SETTINGS_SCHEMA,
        vol.Optional(CONF_FILTER, default={}): entityfilter.FILTER_SCHEMA,
        vol.Optional(CONF_ENTITY_CONFIG, default={}): {cv.entity_id: ENTITY_SCHEMA},
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, yaml_config: Dict[str, Any]):
    """Activate Yandex Smart Home component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][CONFIG] = yaml_config.get(DOMAIN, {})
    hass.data[DOMAIN][DATA_CONFIG] = Config(
        settings=hass.data[DOMAIN][CONFIG].get(CONF_SETTINGS),
        should_expose=hass.data[DOMAIN][CONFIG].get(CONF_FILTER),
        entity_config=hass.data[DOMAIN][CONFIG].get(CONF_ENTITY_CONFIG)
    )
    async_register_http(hass)
    hass.data[DOMAIN][NOTIFIER_ENABLED] = await async_setup_notifier(hass)

    return True
