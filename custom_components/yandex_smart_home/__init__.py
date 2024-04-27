"""Support for Actions on Yandex Smart Home."""
from __future__ import annotations

import hashlib
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, MAJOR_VERSION, MINOR_VERSION, SERVICE_RELOAD
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entityfilter import BASE_FILTER_SCHEMA, FILTER_SCHEMA
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
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
_PYTEST = False

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
        vol.Optional(const.CONF_DEVICE_CLASS): vol.In(const.DEVICE_CLASS_BUTTON),
        vol.Optional(const.CONF_FEATURES): vol.All(cv.ensure_list, ycv.entity_features),
        vol.Optional(const.CONF_ENTITY_PROPERTIES, default=[]): [ENTITY_PROPERTY_SCHEMA],
        vol.Optional(const.CONF_SUPPORT_SET_CHANNEL): cv.boolean,
        vol.Optional(const.CONF_STATE_UNKNOWN): cv.boolean,
        vol.Optional(const.CONF_COLOR_PROFILE): cv.string,
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
        vol.Optional(const.CONF_FILTER): BASE_FILTER_SCHEMA,
        vol.Optional(const.CONF_ENTITY_CONFIG, default={}): vol.All(
            lambda value: value or {},
            {cv.entity_id: ENTITY_SCHEMA}
        ),
        vol.Optional(const.CONF_COLOR_PROFILE, default={}): vol.Schema({
            cv.string: {vol.In(const.COLOR_NAMES): vol.All(ycv.color_value)}
        })
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

    async def _device_discovery_listener(_: Event):
        for entry in hass.config_entries.async_entries(DOMAIN):
            if not entry.data[const.CONF_DEVICES_DISCOVERED]:
                data = dict(entry.data)
                data[const.CONF_DEVICES_DISCOVERED] = True

                hass.config_entries.async_update_entry(entry, data=data, options=entry.options)

    hass.bus.async_listen(EVENT_DEVICE_DISCOVERY, _device_discovery_listener)

    async def _handle_reload(*_):
        config = await async_integration_yaml_config(hass, DOMAIN)
        if config:
            hass.data[DOMAIN][YAML_CONFIG] = config.get(DOMAIN)
            _update_config_entries(hass)

    async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, _handle_reload)

    _update_config_entries(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    yaml_config = hass.data[DOMAIN][YAML_CONFIG] or {}

    entity_config = yaml_config.get(const.CONF_ENTITY_CONFIG)
    entity_filter_config = yaml_config.get(const.CONF_FILTER, entry.options.get(const.CONF_FILTER))

    config = Config(
        hass=hass,
        entry=entry,
        entity_config=entity_config,
        entity_filter=FILTER_SCHEMA(entity_filter_config) if entity_filter_config else None
    )
    await config.async_init()
    hass.data[DOMAIN][CONFIG] = config

    if config.is_cloud_connection:
        cloud_manager = CloudManager(hass, config, async_get_clientsession(hass))
        hass.data[DOMAIN][CLOUD_MANAGER] = cloud_manager

        # FIXME: mocking fails sometimes
        if not _PYTEST:
            hass.loop.create_task(cloud_manager.connect())  # pragma: no cover

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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if int(MAJOR_VERSION) < 2024 or (int(MAJOR_VERSION) == 2024 and int(MINOR_VERSION) < 4):
        entry.version = 1
        hass.config_entries.async_update_entry(entry)
    else:
        hass.config_entries.async_update_entry(entry, version=1)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
    hass.bus.async_fire(EVENT_CONFIG_CHANGED)


def get_config_entry_data_from_yaml_config(data: dict, options: dict, yaml_config: ConfigType | None) -> (dict, dict):
    data, options = data.copy(), options.copy()
    data.setdefault(const.CONF_CONNECTION_TYPE, const.CONNECTION_TYPE_DIRECT)
    data.setdefault(const.CONF_DEVICES_DISCOVERED, True)  # <0.3 migration

    for v in [const.PRESSURE_UNIT_MMHG, const.CONF_BETA, const.CONF_CLOUD_STREAM,
              const.CONF_NOTIFIER, const.YAML_CONFIG_HASH]:
        if v in data:
            del data[v]

    for v in [const.CONF_COLOR_PROFILE]:
        if v in options:
            del options[v]

    if yaml_config:
        data.update({
            const.CONF_NOTIFIER: yaml_config[const.CONF_NOTIFIER],
            const.YAML_CONFIG_HASH: _yaml_config_checksum(yaml_config)
        })
        options.update({
            const.CONF_COLOR_PROFILE: yaml_config[const.CONF_COLOR_PROFILE],
        })
        options.update(yaml_config[const.CONF_SETTINGS])
    else:
        options.update(SETTINGS_SCHEMA(data={}))

    if data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
        options[const.CONF_CLOUD_STREAM] = True

    return data, options


@callback
def _update_config_entries(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        data, options = get_config_entry_data_from_yaml_config(
            entry.data, entry.options, hass.data[DOMAIN][YAML_CONFIG]
        )

        hass.config_entries.async_update_entry(entry, data=data, options=options)


def _yaml_config_checksum(yaml_config: ConfigType) -> str:
    def _order_dict(d):
        return {k: _order_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}

    return hashlib.md5(repr(_order_dict(yaml_config)).encode('utf8')).hexdigest()
