"""Support for Actions on Yandex Smart Home."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, SERVICE_RELOAD
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entityfilter import BASE_FILTER_SCHEMA, FILTER_SCHEMA
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from . import (  # noqa: F401
    capability_color,
    capability_custom,
    capability_mode,
    capability_onoff,
    capability_range,
    capability_toggle,
    const,
    prop_custom,
    prop_event,
    prop_float,
)
from .cloud import CloudManager, delete_cloud_instance
from .const import CLOUD_MANAGER, CONFIG, DOMAIN, EVENT_DEVICE_DISCOVERY, NOTIFIERS
from .helpers import Config
from .http import async_register_http
from .notifier import YandexNotifier, async_setup_notifier, async_start_notifier, async_unload_notifier
from .prop_float import PRESSURE_UNITS_TO_YANDEX_UNITS

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
    vol.All(cv.string, range_instance_validate): vol.All(
        cv.has_at_least_one_key(
            const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE,
            const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE,
            const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE,
        ),
        vol.Schema({
            vol.Optional(const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE): vol.Any(cv.SERVICE_SCHEMA),
            vol.Optional(const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE): vol.Any(cv.SERVICE_SCHEMA),
            vol.Optional(const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE): vol.Any(cv.SERVICE_SCHEMA),
            vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
            vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
            vol.Optional(const.CONF_ENTITY_RANGE): ENTITY_RANGE_SCHEMA,
        })
    )
})


ENTITY_CUSTOM_TOGGLE_SCHEMA = vol.Schema({
    vol.All(cv.string, toggle_instance_validate): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON): cv.SERVICE_SCHEMA,
        vol.Required(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
    })
})


def features_validate(features):
    for feature in features:
        if feature not in const.MEDIA_PLAYER_FEATURES:
            raise vol.Invalid(f'Feature {feature!r} is not supported')

    return features


def device_type_validate(device_type: str) -> str:
    if device_type not in const.TYPES:
        _LOGGER.error(
            f'Device type {device_type!r} is not supported. '
            f'See valid device types at https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html'
        )

        raise vol.Invalid(f'Device type {device_type!r} is not supported.')

    return device_type


ENTITY_SCHEMA = vol.All(
    cv.deprecated(const.CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID),
    vol.Schema({
        vol.Optional(const.CONF_NAME): cv.string,
        vol.Optional(const.CONF_ROOM): cv.string,
        vol.Optional(const.CONF_TYPE): vol.All(cv.string, device_type_validate),
        vol.Optional(const.CONF_TURN_ON): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_TURN_OFF): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_FEATURES): vol.All(cv.ensure_list, features_validate),
        vol.Optional(const.CONF_ENTITY_PROPERTIES, default=[]): [ENTITY_PROPERTY_SCHEMA],
        vol.Optional(const.CONF_SUPPORT_SET_CHANNEL): cv.boolean,
        vol.Optional(const.CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID): cv.boolean,
        vol.Optional(const.CONF_ENTITY_RANGE, default={}): ENTITY_RANGE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_MODE_MAP, default={}): ENTITY_MODE_MAP_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_MODES, default={}): ENTITY_CUSTOM_MODE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_TOGGLES, default={}): ENTITY_CUSTOM_TOGGLE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_RANGES, default={}): ENTITY_CUSTOM_RANGE_SCHEMA,
    })
)

NOTIFIER_SCHEMA = vol.Schema({
    vol.Required(const.CONF_NOTIFIER_OAUTH_TOKEN): cv.string,
    vol.Required(const.CONF_NOTIFIER_SKILL_ID): cv.string,
    vol.Required(const.CONF_NOTIFIER_USER_ID): cv.string,
}, extra=vol.PREVENT_EXTRA)


def pressure_unit_validate(unit):
    if unit not in PRESSURE_UNITS_TO_YANDEX_UNITS:
        raise vol.Invalid(f'Pressure unit "{unit}" is not supported')

    return unit


SETTINGS_SCHEMA = vol.Schema({
    vol.Optional(const.CONF_PRESSURE_UNIT, default=const.PRESSURE_UNIT_MMHG): vol.Schema(
        vol.All(str, pressure_unit_validate)
    ),
    vol.Optional(const.CONF_BETA, default=False): cv.boolean
})


def is_config_filter_empty(yaml_config: ConfigType) -> bool:
    for entities in yaml_config.get(const.CONF_FILTER, {}).values():
        if entities:
            return False

    return True


YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(const.CONF_NOTIFIER, default=[]): vol.All(cv.ensure_list, [NOTIFIER_SCHEMA]),
        vol.Optional(const.CONF_SETTINGS, default={}): vol.All(lambda value: value or {}, SETTINGS_SCHEMA),
        vol.Optional(const.CONF_FILTER, default={}): BASE_FILTER_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CONFIG, default={}): vol.All(
            lambda value: value or {},
            {cv.entity_id: ENTITY_SCHEMA}
        ),
    }, extra=vol.PREVENT_EXTRA))

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: YANDEX_SMART_HOME_SCHEMA
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, _: ConfigType):
    """Activate Yandex Smart Home component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][NOTIFIERS]: list[YandexNotifier] = []
    hass.data[DOMAIN][CONFIG]: Config | None = None
    hass.data[DOMAIN][CLOUD_MANAGER]: CloudManager | None = None

    async_register_http(hass)
    async_setup_notifier(hass)

    def _device_discovery_listener(_: Event):
        for entry in hass.config_entries.async_entries(DOMAIN):
            if not entry.data[const.CONF_DEVICES_DISCOVERED]:
                data = dict(entry.data)
                data[const.CONF_DEVICES_DISCOVERED] = True

                hass.config_entries.async_update_entry(entry, data=data, options=entry.options)

    hass.bus.async_listen(EVENT_DEVICE_DISCOVERY, _device_discovery_listener)

    async def _handle_reload(*_):
        current_entries = hass.config_entries.async_entries(DOMAIN)
        reload_tasks = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in current_entries
        ]

        await asyncio.gather(*reload_tasks)

    hass.helpers.service.async_register_admin_service(DOMAIN, SERVICE_RELOAD, _handle_reload)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    yaml_config = await async_integration_yaml_config(hass, DOMAIN)
    if yaml_config is None:
        raise ConfigEntryNotReady('Configuration is missing or invalid')

    _async_update_config_entry_from_yaml(hass, entry, yaml_config)
    _async_import_options_from_data_if_missing(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    yaml_domain_config = yaml_config.get(DOMAIN, {})
    filters = yaml_domain_config.get(const.CONF_FILTER, {})
    if is_config_filter_empty(yaml_domain_config) and const.CONF_FILTER in entry.options:
        filters = entry.options[const.CONF_FILTER]

    config = Config(
        hass=hass,
        entry=entry,
        should_expose=FILTER_SCHEMA(filters),
        entity_config=yaml_domain_config.get(const.CONF_ENTITY_CONFIG, {})
    )
    await config.async_init()
    hass.data[DOMAIN][CONFIG] = config

    if config.is_cloud_connection:
        cloud_manager = CloudManager(hass, config, async_get_clientsession(hass))
        hass.data[DOMAIN][CLOUD_MANAGER] = cloud_manager

        hass.loop.create_task(cloud_manager.connect())
        entry.async_on_unload(
            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, cloud_manager.disconnect
            )
        )

    await async_start_notifier(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, _: ConfigEntry):
    if hass.data[DOMAIN][CLOUD_MANAGER]:
        hass.async_create_task(hass.data[DOMAIN][CLOUD_MANAGER].disconnect())

    hass.data[DOMAIN][CONFIG]: Config | None = None
    hass.data[DOMAIN][CLOUD_MANAGER]: CloudManager | None = None

    async_unload_notifier(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
        await delete_cloud_instance(hass, entry)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_update_config_entry_from_yaml(hass: HomeAssistant, entry: ConfigEntry, yaml_config: ConfigType):
    """Update a config entry with the latest yaml."""
    data = entry.data.copy()
    data.setdefault(const.CONF_CONNECTION_TYPE, const.CONNECTION_TYPE_DIRECT)
    if const.CONF_DEVICES_DISCOVERED not in data:  # pre-0.3 migration
        data.setdefault(const.CONF_DEVICES_DISCOVERED, True)
    data.setdefault(const.CONF_DEVICES_DISCOVERED, False)

    if DOMAIN in yaml_config:
        data.update(yaml_config[DOMAIN][const.CONF_SETTINGS])
        data.update({
            const.CONF_NOTIFIER: yaml_config[DOMAIN][const.CONF_NOTIFIER]
        })
    else:
        data.update(SETTINGS_SCHEMA(data={}))

    hass.config_entries.async_update_entry(entry, data=data)


@callback
def _async_import_options_from_data_if_missing(hass: HomeAssistant, entry: ConfigEntry):
    options = dict(entry.options)
    data = dict(entry.data)
    modified = False

    for option in [const.CONF_FILTER]:
        if option not in entry.options and option in entry.data:
            options[option] = entry.data[option]
            del data[option]
            modified = True

    if modified:
        hass.config_entries.async_update_entry(entry, data=data, options=options)
