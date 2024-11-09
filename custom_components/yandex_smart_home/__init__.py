"""The Yandex Smart Home component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_ID, CONF_PLATFORM, CONF_TOKEN, SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entityfilter import FILTER_SCHEMA, EntityFilter
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .config_schema import YANDEX_SMART_HOME_SCHEMA
from .const import (
    CONF_CLOUD_INSTANCE,
    CONF_CONNECTION_TYPE,
    CONF_DEVICES_DISCOVERED,
    CONF_ENTITY_CONFIG,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_LINKED_PLATFORMS,
    CONF_NOTIFIER,
    CONF_NOTIFIER_OAUTH_TOKEN,
    CONF_NOTIFIER_SKILL_ID,
    CONF_NOTIFIER_USER_ID,
    CONF_SKILL,
    CONF_USER_ID,
    DOMAIN,
    ConnectionType,
    EntityFilterSource,
)
from .entry_data import ConfigEntryData
from .helpers import SmartHomePlatform
from .http import async_register_http

if TYPE_CHECKING:
    from .cloud_stream import CloudStreamManager

_LOGGER = logging.getLogger(__name__)


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

        return {"yaml_config": async_redact_data(self._yaml_config, [CONF_NOTIFIER])}

    async def async_setup_entry(self, entry: ConfigEntry) -> bool:
        """Set up a config entry."""
        entity_config = self._yaml_config.get(CONF_ENTITY_CONFIG)

        entity_filter: EntityFilter | None = None
        if entry.options.get(CONF_FILTER_SOURCE) == EntityFilterSource.YAML:
            if entity_filter_config := self._yaml_config.get(CONF_FILTER):
                entity_filter = FILTER_SCHEMA(entity_filter_config)
        else:
            entity_filter = FILTER_SCHEMA(entry.options.get(CONF_FILTER, {}))

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
            CONF_CONNECTION_TYPE,
            CONF_CLOUD_INSTANCE,
            CONF_DEVICES_DISCOVERED,
            CONF_FILTER,
            CONF_USER_ID,
        ]
        for store in [data, options]:
            for key in list(store.keys()):
                if key not in preserve_keys:
                    store.pop(key, None)

        data.setdefault(CONF_CONNECTION_TYPE, ConnectionType.DIRECT)
        data.setdefault(CONF_DEVICES_DISCOVERED, True)

        version = 2
        hass.config_entries.async_update_entry(entry, data=data, options=options, version=version)
        _LOGGER.debug(f"Migration to version {version} successful")

    if version == 2:
        version = 3
        _LOGGER.debug(f"Migration to version {version} successful")

    if version == 3:
        options[CONF_FILTER_SOURCE] = EntityFilterSource.CONFIG_ENTRY
        if CONF_FILTER in component._yaml_config:
            options[CONF_FILTER_SOURCE] = EntityFilterSource.YAML

        version = 4
        hass.config_entries.async_update_entry(entry, data=data, options=options, version=version)
        _LOGGER.debug(f"Migration to version {version} successful")

    if version == 4:
        from .config_flow import DEFAULT_CONFIG_ENTRY_TITLE, PRE_V1_DIRECT_CONFIG_ENTRY_TITLE, async_config_entry_title

        title = entry.title
        data.setdefault(CONF_PLATFORM, SmartHomePlatform.YANDEX)

        if len(hass.config_entries.async_entries(DOMAIN)) == 1 and data[CONF_CONNECTION_TYPE] == ConnectionType.DIRECT:
            for notifier_config in component._yaml_config.get(CONF_NOTIFIER, []):
                options.setdefault(
                    CONF_SKILL,
                    {
                        CONF_USER_ID: notifier_config[CONF_NOTIFIER_USER_ID],
                        CONF_ID: notifier_config[CONF_NOTIFIER_SKILL_ID],
                        CONF_TOKEN: notifier_config[CONF_NOTIFIER_OAUTH_TOKEN],
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

    if version == 5:
        if data.get(CONF_DEVICES_DISCOVERED):
            data[CONF_LINKED_PLATFORMS] = [SmartHomePlatform.YANDEX]

        version = 6
        hass.config_entries.async_update_entry(entry, data=data, version=version)
        _LOGGER.debug(f"Migration to version {version} successful")

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    component: YandexSmartHome | None = hass.data.get(DOMAIN)
    if component:
        await component.async_remove_entry(entry)

    return None


async def _async_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry options update."""
    await hass.config_entries.async_reload(entry.entry_id)
    return None
