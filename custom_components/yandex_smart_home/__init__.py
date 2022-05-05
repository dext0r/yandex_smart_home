"""Support for Actions on Yandex Smart Home."""
from __future__ import annotations

import hashlib
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, SERVICE_RELOAD
from homeassistant.core import Event, HomeAssistant, callback
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
    capability_video,
    config_validation as ycv,
    const,
    prop_custom,
    prop_event,
    prop_float,
)
from .cloud import CloudManager, delete_cloud_instance
from .cloud_stream import CloudStream
from .const import (
    CLOUD_MANAGER,
    CLOUD_STREAMS,
    CONFIG,
    DOMAIN,
    EVENT_CONFIG_CHANGED,
    EVENT_DEVICE_DISCOVERY,
    NOTIFIERS,
    YAML_CONFIG,
)
from .helpers import Config
from .http import async_register_http
from .notifier import YandexNotifier, async_setup_notifier, async_start_notifier, async_unload_notifier

_LOGGER = logging.getLogger(__name__)


ENTITY_PROPERTY_SCHEMA = vol.All(
    cv.has_at_least_one_key(const.CONF_ENTITY_PROPERTY_ENTITY, const.CONF_ENTITY_PROPERTY_ATTRIBUTE),
    vol.Schema({
        vol.Required(const.CONF_ENTITY_PROPERTY_TYPE): vol.Schema(vol.All(str, ycv.property_type)),
        vol.Optional(const.CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(const.CONF_ENTITY_PROPERTY_ENTITY): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_PROPERTY_ATTRIBUTE): cv.string,
    }, extra=vol.PREVENT_EXTRA)
)


ENTITY_MODE_MAP_SCHEMA = vol.Schema({
    vol.All(cv.string, ycv.mode_instance): vol.Schema({
        vol.All(cv.string, ycv.mode): [cv.string]
    })
})

ENTITY_RANGE_SCHEMA = vol.Schema({
    vol.Optional(const.CONF_ENTITY_RANGE_MAX): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(const.CONF_ENTITY_RANGE_MIN): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    vol.Optional(const.CONF_ENTITY_RANGE_PRECISION): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
}, extra=vol.PREVENT_EXTRA)

ENTITY_CUSTOM_MODE_SCHEMA = vol.Schema({
    vol.All(cv.string, ycv.mode_instance): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_MODE_SET_MODE): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
    })
})

ENTITY_CUSTOM_RANGE_SCHEMA = vol.Schema({
    vol.All(cv.string, ycv.range_instance): vol.All(
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
    vol.All(cv.string, ycv.toggle_instance): vol.Schema({
        vol.Required(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON): cv.SERVICE_SCHEMA,
        vol.Required(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
        vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
    })
})


ENTITY_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional(const.CONF_NAME): cv.string,
        vol.Optional(const.CONF_ROOM): cv.string,
        vol.Optional(const.CONF_TYPE): vol.All(cv.string, ycv.device_type),
        vol.Optional(const.CONF_TURN_ON): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_TURN_OFF): cv.SERVICE_SCHEMA,
        vol.Optional(const.CONF_FEATURES): vol.All(cv.ensure_list, ycv.entity_features),
        vol.Optional(const.CONF_ENTITY_PROPERTIES, default=[]): [ENTITY_PROPERTY_SCHEMA],
        vol.Optional(const.CONF_SUPPORT_SET_CHANNEL): cv.boolean,
        vol.Optional(const.CONF_STATE_UNKNOWN): cv.boolean,
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


SETTINGS_SCHEMA = vol.Schema({
    vol.Optional(const.CONF_PRESSURE_UNIT, default=const.PRESSURE_UNIT_MMHG): vol.Schema(
        vol.All(str, ycv.pressure_unit)
    ),
    vol.Optional(const.CONF_BETA, default=False): cv.boolean,
    vol.Optional(const.CONF_CLOUD_STREAM, default=False): cv.boolean
})


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


async def async_setup(hass: HomeAssistant, yaml_config: ConfigType):
    """Activate Yandex Smart Home component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][NOTIFIERS]: list[YandexNotifier] = []
    hass.data[DOMAIN][CONFIG]: Config | None = None
    hass.data[DOMAIN][YAML_CONFIG]: ConfigType | None = yaml_config.get(DOMAIN)
    hass.data[DOMAIN][CLOUD_MANAGER]: CloudManager | None = None
    hass.data[DOMAIN][CLOUD_STREAMS]: dict[str, CloudStream] = {}

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
        hass.data[DOMAIN][YAML_CONFIG] = (await async_integration_yaml_config(hass, DOMAIN)).get(DOMAIN)
        _update_config_entries(hass)

    hass.helpers.service.async_register_admin_service(DOMAIN, SERVICE_RELOAD, _handle_reload)

    _update_config_entries(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    yaml_config = hass.data[DOMAIN][YAML_CONFIG] or {}

    _async_import_options_from_data_if_missing(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    entity_filter = yaml_config.get(const.CONF_FILTER, {})
    if is_config_filter_empty(entity_filter) and const.CONF_FILTER in entry.options:
        entity_filter = entry.options[const.CONF_FILTER]

    config = Config(
        hass=hass,
        entry=entry,
        should_expose=FILTER_SCHEMA(entity_filter),
        entity_config=yaml_config.get(const.CONF_ENTITY_CONFIG, {})
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

    await async_unload_notifier(hass)

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
        await delete_cloud_instance(hass, entry)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
    hass.bus.async_fire(EVENT_CONFIG_CHANGED)


def _get_config_entry_data_from_yaml(data: dict, yaml_config: ConfigType | None) -> dict:
    data = data.copy()
    data.setdefault(const.CONF_CONNECTION_TYPE, const.CONNECTION_TYPE_DIRECT)
    if const.CONF_DEVICES_DISCOVERED not in data:  # pre-0.3 migration
        data.setdefault(const.CONF_DEVICES_DISCOVERED, True)
    data.setdefault(const.CONF_DEVICES_DISCOVERED, False)

    if yaml_config:
        data.update(yaml_config[const.CONF_SETTINGS])
        data.update({
            const.CONF_NOTIFIER: yaml_config[const.CONF_NOTIFIER],
            const.YAML_CONFIG_HASH: hashlib.md5(repr(yaml_config).encode('utf8')).hexdigest()
        })
    else:
        data.update(SETTINGS_SCHEMA(data={}))
        for v in [const.CONF_NOTIFIER, const.YAML_CONFIG_HASH]:
            if v in data:
                del data[v]

    if data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
        data[const.CONF_CLOUD_STREAM] = True

    return data


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


@callback
def _update_config_entries(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        hass.config_entries.async_update_entry(
            entry,
            data=_get_config_entry_data_from_yaml(entry.data, hass.data[DOMAIN][YAML_CONFIG])
        )


def is_config_filter_empty(config_filter: ConfigType) -> bool:
    for entities in config_filter.values():
        if entities:
            return False

    return True
