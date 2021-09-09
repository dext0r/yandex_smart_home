"""Support for Actions on Yandex Smart Home."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entityfilter
from homeassistant.helpers.reload import async_integration_yaml_config
import voluptuous as vol

from . import const
from .const import CONF_DISABLED, CONFIG, DOMAIN, NOTIFIERS
from .helpers import Config
from .http import async_register_http
from .notifier import async_setup_notifier, async_unload_notifier

_LOGGER = logging.getLogger(__name__)


def property_type_validate(property_type: str) -> str:
    if property_type not in const.FLOAT_INSTANCES and property_type not in const.EVENT_INSTANCES:
        raise vol.Invalid(
            f'Property type {property_type!r} is not supported. '
            f'See valid types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html and '
            f'https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html'
        )

    return property_type


ENTITY_PROPERTY_SCHEMA = vol.All(
    cv.has_at_least_one_key(const.CONF_ENTITY_PROPERTY_ENTITY, const.CONF_ENTITY_PROPERTY_ATTRIBUTE),
    vol.Schema({
        vol.Required(const.CONF_ENTITY_PROPERTY_TYPE): vol.Schema(
            vol.All(str, property_type_validate)
        ),
        vol.Optional(const.CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(const.CONF_ENTITY_PROPERTY_ENTITY): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_PROPERTY_ATTRIBUTE): cv.string,
    }, extra=vol.PREVENT_EXTRA)
)


def mode_instance_validate(instance: str) -> str:
    if instance not in const.MODE_INSTANCES and instance not in const.COLOR_SETTING_SCENE:
        _LOGGER.error(
            f'Mode instance {instance!r} is not supported. '
            f'See valid modes at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html'
        )

        raise vol.Invalid(f'Mode instance {instance!r} is not supported.')

    return instance


def mode_validate(mode: str) -> str:
    if mode not in const.MODE_INSTANCE_MODES and mode not in const.COLOR_SCENES:
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
    vol.Optional(const.CONF_ENTITY_RANGE_MAX): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(const.CONF_ENTITY_RANGE_MIN): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(const.CONF_ENTITY_RANGE_PRECISION): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
}, extra=vol.PREVENT_EXTRA)

ENTITY_CUSTOM_MODE_SCHEMA = vol.Schema({
    vol.All(cv.string, mode_instance_validate): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_MODE_SET_MODE): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
    })
})


def range_instance_validate(instance: str) -> str:
    if instance not in const.RANGE_INSTANCES:
        _LOGGER.error(
            f'Range instance {instance!r} is not supported. '
            f'See valid values at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html'
        )

        raise vol.Invalid(f'Range instance {instance!r} is not supported.')

    return instance


ENTITY_CUSTOM_RANGE_SCHEMA = vol.Schema({
    vol.All(cv.string, range_instance_validate): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
        vol.Optional(const.CONF_ENTITY_RANGE): ENTITY_RANGE_SCHEMA,
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
    vol.Optional(const.CONF_NAME): cv.string,
    vol.Optional(const.CONF_ROOM): cv.string,
    vol.Optional(const.CONF_TYPE): cv.string,
    vol.Optional(const.CONF_TURN_ON): cv.SERVICE_SCHEMA,
    vol.Optional(const.CONF_TURN_OFF): cv.SERVICE_SCHEMA,
    vol.Optional(const.CONF_ENTITY_PROPERTIES, default=[]): [ENTITY_PROPERTY_SCHEMA],
    vol.Optional(const.CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID): cv.boolean,
    vol.Optional(const.CONF_ENTITY_RANGE, default={}): ENTITY_RANGE_SCHEMA,
    vol.Optional(const.CONF_ENTITY_MODE_MAP, default={}): ENTITY_MODE_MAP_SCHEMA,
    vol.Optional(const.CONF_ENTITY_CUSTOM_MODES, default={}): ENTITY_CUSTOM_MODE_SCHEMA,
    vol.Optional(const.CONF_ENTITY_CUSTOM_TOGGLES, default={}): ENTITY_CUSTOM_TOGGLE_SCHEMA,
    vol.Optional(const.CONF_ENTITY_CUSTOM_RANGES, default={}): ENTITY_CUSTOM_RANGE_SCHEMA,
})

NOTIFIER_SCHEMA = vol.Schema({
    vol.Required(const.CONF_SKILL_OAUTH_TOKEN): cv.string,
    vol.Required(const.CONF_SKILL_ID): cv.string,
    vol.Required(const.CONF_NOTIFIER_USER_ID): cv.string,
}, extra=vol.PREVENT_EXTRA)


def pressure_unit_validate(unit):
    if unit not in const.PRESSURE_UNITS_TO_YANDEX_UNITS:
        raise vol.Invalid(f'Pressure unit "{unit}" is not supported')

    return unit


SETTINGS_SCHEMA = vol.Schema({
    vol.Optional(const.CONF_PRESSURE_UNIT, default=const.PRESSURE_UNIT_MMHG): vol.Schema(
        vol.All(str, pressure_unit_validate)
    ),
})

YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(const.CONF_NOTIFIER, default=[]): vol.All(cv.ensure_list, [NOTIFIER_SCHEMA]),
        vol.Optional(const.CONF_SETTINGS, default={}): SETTINGS_SCHEMA,
        vol.Optional(const.CONF_FILTER, default={}): entityfilter.FILTER_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CONFIG, default={}): {cv.entity_id: ENTITY_SCHEMA},
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)


async def _async_update_config_from_yaml(hass: HomeAssistant, config: dict[str, Any]):
    domain_config = config.get(DOMAIN, {})
    hass.data[DOMAIN][CONFIG] = Config(
        hass=hass,
        settings=domain_config.get(const.CONF_SETTINGS, {}),
        notifier=domain_config.get(const.CONF_NOTIFIER, []),
        should_expose=domain_config.get(const.CONF_FILTER, {}),
        entity_config=domain_config.get(const.CONF_ENTITY_CONFIG)
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]):
    """Activate Yandex Smart Home component."""
    hass.data[DOMAIN] = {
        NOTIFIERS: [],
        CONFIG: None,
    }

    async_register_http(hass)

    # noinspection PyUnusedLocal
    async def _handle_reload(service):
        """Handle reload service call."""
        if not hass.data[DOMAIN][CONFIG]:
            raise ValueError('Integration is not enabled')

        new_config = await async_integration_yaml_config(hass, DOMAIN)
        if not new_config or DOMAIN not in new_config:
            raise ValueError('Configuration is invalid')

        await _async_update_config_from_yaml(hass, new_config)
        await async_setup_notifier(hass, reload=True)

    hass.helpers.service.async_register_admin_service(
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    if DOMAIN in config:
        hass.async_create_task(hass.config_entries.flow.async_init(
            DOMAIN, context={'source': SOURCE_IMPORT}
        ))

    return True


# noinspection PyUnusedLocal
async def async_setup_entry(hass, entry: ConfigEntry):
    is_reload = hass.data[DOMAIN].get(CONF_DISABLED)
    config = await async_integration_yaml_config(hass, DOMAIN)
    if not config or DOMAIN not in config:
        raise ConfigEntryNotReady('Configuration is missing or invalid')

    await _async_update_config_from_yaml(hass, config)
    await async_setup_notifier(hass, reload=is_reload)

    return True


# noinspection PyUnusedLocal
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if not hass.data[DOMAIN][CONFIG]:
        return True

    await async_unload_notifier(hass)
    hass.data[DOMAIN][CONFIG] = None
    hass.data[DOMAIN][CONF_DISABLED] = True

    return True
