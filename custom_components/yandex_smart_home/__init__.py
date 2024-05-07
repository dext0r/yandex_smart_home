"""The Yandex Smart Home component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_ID, CONF_PLATFORM, CONF_TOKEN, SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entityfilter import BASE_FILTER_SCHEMA, FILTER_SCHEMA, EntityFilter
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
import voluptuous as vol

from . import config_validation as ycv, const
from .cloud import delete_cloud_instance
from .const import CONF_SKILL, CONF_USER_ID, DOMAIN, ConnectionType, EntityFilterSource
from .entry_data import ConfigEntryData
from .helpers import SmartHomePlatform
from .http import async_register_http

if TYPE_CHECKING:
    from homeassistant.helpers import ConfigType

    from .cloud_stream import CloudStreamManager

_LOGGER = logging.getLogger(__name__)

ENTITY_PROPERTY_SCHEMA = vol.All(
    cv.has_at_least_one_key(
        const.CONF_ENTITY_PROPERTY_ENTITY,
        const.CONF_ENTITY_PROPERTY_ATTRIBUTE,
        const.CONF_ENTITY_PROPERTY_VALUE_TEMPLATE,
    ),
    vol.All(
        {
            vol.Required(const.CONF_ENTITY_PROPERTY_TYPE): vol.Schema(vol.All(str, ycv.property_type)),
            vol.Optional(const.CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(const.CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(const.CONF_ENTITY_PROPERTY_ENTITY): cv.entity_id,
            vol.Optional(const.CONF_ENTITY_PROPERTY_ATTRIBUTE): cv.string,
            vol.Optional(const.CONF_ENTITY_PROPERTY_VALUE_TEMPLATE): cv.template,
        },
        ycv.property_attributes,
    ),
)


ENTITY_MODE_MAP_SCHEMA = vol.Schema(
    {vol.All(cv.string, ycv.mode_instance): vol.Schema({vol.All(cv.string, ycv.mode): [cv.string]})}
)

ENTITY_RANGE_SCHEMA = vol.Schema(
    {
        vol.Optional(const.CONF_ENTITY_RANGE_MAX): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
        vol.Optional(const.CONF_ENTITY_RANGE_MIN): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
        vol.Optional(const.CONF_ENTITY_RANGE_PRECISION): vol.All(vol.Coerce(float), vol.Range(min=-100.0, max=1000.0)),
    },
)

ENTITY_CUSTOM_MODE_SCHEMA = vol.Schema(
    {
        vol.All(cv.string, ycv.mode_instance): vol.All(
            {
                vol.Optional(const.CONF_ENTITY_CUSTOM_MODE_SET_MODE): cv.SERVICE_SCHEMA,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE): cv.template,
            },
            ycv.custom_capability_state,
        )
    }
)

ENTITY_CUSTOM_RANGE_SCHEMA = vol.Schema(
    {
        vol.All(cv.string, ycv.range_instance): vol.All(
            {
                vol.Optional(const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE): vol.Any(cv.SERVICE_SCHEMA),
                vol.Optional(const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE): vol.Any(cv.SERVICE_SCHEMA),
                vol.Optional(const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE): vol.Any(cv.SERVICE_SCHEMA),
                vol.Optional(const.CONF_ENTITY_RANGE): ENTITY_RANGE_SCHEMA,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE): cv.template,
            },
            ycv.custom_capability_state,
        )
    }
)


ENTITY_CUSTOM_TOGGLE_SCHEMA = vol.Schema(
    {
        vol.All(cv.string, ycv.toggle_instance): vol.All(
            {
                vol.Optional(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON): cv.SERVICE_SCHEMA,
                vol.Optional(const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF): cv.SERVICE_SCHEMA,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID): cv.entity_id,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE): cv.string,
                vol.Optional(const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE): cv.template,
            },
            ycv.custom_capability_state,
        )
    }
)


ENTITY_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(const.CONF_NAME): cv.string,
            vol.Optional(const.CONF_ROOM): cv.string,
            vol.Optional(const.CONF_TYPE): vol.All(cv.string, ycv.device_type),
            vol.Optional(const.CONF_TURN_ON): vol.Any(cv.SERVICE_SCHEMA, cv.boolean),
            vol.Optional(const.CONF_TURN_OFF): vol.Any(cv.SERVICE_SCHEMA, cv.boolean),
            vol.Optional(const.CONF_DEVICE_CLASS): vol.In(const.DEVICE_CLASS_BUTTON),
            vol.Optional(const.CONF_FEATURES): vol.All(cv.ensure_list, ycv.entity_features),
            vol.Optional(const.CONF_ENTITY_PROPERTIES): [ENTITY_PROPERTY_SCHEMA],
            vol.Optional(const.CONF_SUPPORT_SET_CHANNEL): cv.boolean,
            vol.Optional(const.CONF_STATE_UNKNOWN): cv.boolean,
            vol.Optional(const.CONF_COLOR_PROFILE): cv.string,
            vol.Optional(const.CONF_ERROR_CODE_TEMPLATE): cv.template,
            vol.Optional(const.CONF_ENTITY_RANGE): ENTITY_RANGE_SCHEMA,
            vol.Optional(const.CONF_ENTITY_MODE_MAP): ENTITY_MODE_MAP_SCHEMA,
            vol.Optional(const.CONF_ENTITY_CUSTOM_MODES): ENTITY_CUSTOM_MODE_SCHEMA,
            vol.Optional(const.CONF_ENTITY_CUSTOM_TOGGLES): ENTITY_CUSTOM_TOGGLE_SCHEMA,
            vol.Optional(const.CONF_ENTITY_CUSTOM_RANGES): ENTITY_CUSTOM_RANGE_SCHEMA,
        }
    )
)

NOTIFIER_SCHEMA = vol.Schema(
    {
        vol.Required(const.CONF_NOTIFIER_OAUTH_TOKEN): cv.string,
        vol.Required(const.CONF_NOTIFIER_SKILL_ID): cv.string,
        vol.Required(const.CONF_NOTIFIER_USER_ID): cv.string,
    },
)


SETTINGS_SCHEMA = vol.All(
    cv.deprecated(const.CONF_PRESSURE_UNIT),
    {
        vol.Optional(const.CONF_PRESSURE_UNIT): cv.string,
        vol.Optional(const.CONF_BETA): cv.boolean,
        vol.Optional(const.CONF_CLOUD_STREAM): cv.boolean,
    },
)


YANDEX_SMART_HOME_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(const.CONF_NOTIFIER): vol.All(cv.ensure_list, [NOTIFIER_SCHEMA]),
            vol.Optional(const.CONF_SETTINGS): vol.All(lambda value: value or {}, SETTINGS_SCHEMA),
            vol.Optional(const.CONF_FILTER): BASE_FILTER_SCHEMA,
            vol.Optional(const.CONF_ENTITY_CONFIG): vol.All(lambda value: value or {}, {cv.entity_id: ENTITY_SCHEMA}),
            vol.Optional(const.CONF_COLOR_PROFILE): vol.Schema(
                {cv.string: {vol.All(ycv.color_name): vol.All(ycv.color_value)}}
            ),
        },
    )
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: YANDEX_SMART_HOME_SCHEMA}, extra=vol.ALLOW_EXTRA)


class YandexSmartHome:
    """Yandex Smart Home component main class."""

    def __init__(self, hass: HomeAssistant, yaml_config: ConfigType):
        """Initialize the Yandex Smart Home from yaml configuration."""
        self.cloud_streams: dict[str, CloudStreamManager] = {}

        self._hass = hass
        self._yaml_config = yaml_config
        self._entry_datas: dict[str, ConfigEntryData] = {}

        async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, self._handle_yaml_config_reload)

    async def _handle_yaml_config_reload(self, _: Any) -> None:
        """Handle yaml configuration reloading."""
        if config := await async_integration_yaml_config(self._hass, DOMAIN):
            self._yaml_config = config.get(DOMAIN, {})

        for entry in self._hass.config_entries.async_entries(DOMAIN):
            await _async_entry_update_listener(self._hass, entry)

        return None

    def get_entry_data(self, entry: ConfigEntry) -> ConfigEntryData:
        """Return a config entry data for a config entry."""
        return self._entry_datas[entry.entry_id]

    def get_direct_connection_entry_data(
        self, platform: SmartHomePlatform, user_id: str | None
    ) -> ConfigEntryData | None:
        """Return a config entry data with direct connection config entry."""
        for data in self._entry_datas.values():
            if (
                data.connection_type == ConnectionType.DIRECT
                and data.entry.state == ConfigEntryState.LOADED
                and data.platform == platform
            ):
                if user_id and data.skill and data.skill.user_id == user_id:
                    return data
                if not user_id:
                    return data

        return None

    def get_diagnostics(self) -> ConfigType:
        """Return diagnostics for the component."""
        from homeassistant.components.diagnostics import async_redact_data

        return {"yaml_config": async_redact_data(self._yaml_config, [const.CONF_NOTIFIER])}

    async def async_setup_entry(self, entry: ConfigEntry) -> bool:
        """Set up a config entry."""
        entity_config = self._yaml_config.get(const.CONF_ENTITY_CONFIG)

        entity_filter: EntityFilter | None = None
        if entry.options.get(const.CONF_FILTER_SOURCE) == EntityFilterSource.YAML:
            if entity_filter_config := self._yaml_config.get(const.CONF_FILTER):
                entity_filter = FILTER_SCHEMA(entity_filter_config)
        else:
            entity_filter = FILTER_SCHEMA(entry.options.get(const.CONF_FILTER, {}))

        data = ConfigEntryData(
            hass=self._hass,
            entry=entry,
            yaml_config=self._yaml_config,
            entity_config=entity_config,
            entity_filter=entity_filter,
        )

        self._entry_datas[entry.entry_id] = await data.async_setup()
        entry.async_on_unload(entry.add_update_listener(_async_entry_update_listener))

        return True

    async def async_unload_entry(self, entry: ConfigEntry) -> bool:
        """Unload a config entry."""
        data = self.get_entry_data(entry)
        await data.async_unload()
        return True

    async def async_remove_entry(self, entry: ConfigEntry) -> None:
        """Remove a config entry."""
        try:
            del self._entry_datas[entry.entry_id]
        except KeyError:
            pass

        return None


async def async_setup(hass: HomeAssistant, yaml_config: ConfigType) -> bool:
    """Activate Yandex Smart Home component."""
    hass.data[DOMAIN] = component = YandexSmartHome(hass, yaml_config.get(DOMAIN, {}))
    async_register_http(hass, component)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    component: YandexSmartHome = hass.data[DOMAIN]
    return await component.async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    component: YandexSmartHome = hass.data[DOMAIN]
    return await component.async_unload_entry(entry)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate the config entry upon new versions."""
    version = entry.version
    component: YandexSmartHome = hass.data[DOMAIN]
    data: ConfigType = {**entry.data}
    options: ConfigType = {**entry.options}

    _LOGGER.debug(f"Migrating from version {version}")

    if version == 1:
        preserve_keys = [
            const.CONF_CONNECTION_TYPE,
            const.CONF_CLOUD_INSTANCE,
            const.CONF_DEVICES_DISCOVERED,
            const.CONF_FILTER,
            const.CONF_USER_ID,
        ]
        for store in [data, options]:
            for key in list(store.keys()):
                if key not in preserve_keys:
                    store.pop(key, None)

        data.setdefault(const.CONF_CONNECTION_TYPE, ConnectionType.DIRECT)
        data.setdefault(const.CONF_DEVICES_DISCOVERED, True)

        version = 2
        hass.config_entries.async_update_entry(entry, data=data, options=options, version=version)
        _LOGGER.debug(f"Migration to version {version} successful")

    if version == 2:
        version = 3
        _LOGGER.debug(f"Migration to version {version} successful")

    if version == 3:
        options[const.CONF_FILTER_SOURCE] = EntityFilterSource.CONFIG_ENTRY
        if const.CONF_FILTER in component._yaml_config:
            options[const.CONF_FILTER_SOURCE] = EntityFilterSource.YAML

        version = 4
        hass.config_entries.async_update_entry(entry, data=data, options=options, version=version)
        _LOGGER.debug(f"Migration to version {version} successful")

    if version == 4:
        from .config_flow import DEFAULT_CONFIG_ENTRY_TITLE, PRE_V1_DIRECT_CONFIG_ENTRY_TITLE, async_config_entry_title

        title = entry.title
        data.setdefault(CONF_PLATFORM, SmartHomePlatform.YANDEX)

        if (
            len(hass.config_entries.async_entries(DOMAIN)) == 1
            and data[const.CONF_CONNECTION_TYPE] == ConnectionType.DIRECT
        ):
            for notifier_config in component._yaml_config.get(const.CONF_NOTIFIER, []):
                options.setdefault(
                    CONF_SKILL,
                    {
                        CONF_USER_ID: notifier_config[const.CONF_NOTIFIER_USER_ID],
                        CONF_ID: notifier_config[const.CONF_NOTIFIER_SKILL_ID],
                        CONF_TOKEN: notifier_config[const.CONF_NOTIFIER_OAUTH_TOKEN],
                    },
                )
                break

        if entry.title in (DEFAULT_CONFIG_ENTRY_TITLE, PRE_V1_DIRECT_CONFIG_ENTRY_TITLE):
            title = await async_config_entry_title(hass, data, options)

        version = 5
        hass.config_entries.async_update_entry(
            entry,
            title=title,
            data=data,
            options=options,
            version=version,
        )
        _LOGGER.debug(f"Migration to version {version} successful")

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    if entry.data.get(const.CONF_CONNECTION_TYPE) == ConnectionType.CLOUD:
        await delete_cloud_instance(
            hass,
            instance_id=entry.data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_ID],
            token=entry.data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN],
        )

    component: YandexSmartHome | None = hass.data.get(DOMAIN)
    if component:
        await component.async_remove_entry(entry)

    return None


async def _async_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry options update."""
    await hass.config_entries.async_reload(entry.entry_id)
    return None
