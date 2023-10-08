"""Config entry data for the Yandex Smart Home."""

import asyncio
import logging
from typing import Any, Self

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP, UnitOfPressure
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entityfilter import EntityFilter
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import DATA_CUSTOM_COMPONENTS

from . import const
from .cloud import CloudManager
from .color import ColorProfiles
from .const import DOMAIN, ConnectionType
from .helpers import CacheStore
from .notifier import NotifierConfig, YandexCloudNotifier, YandexDirectNotifier, YandexNotifier

_LOGGER = logging.getLogger(__name__)


class ConfigEntryData:
    """Class to hold config entry data."""

    cache: CacheStore

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        yaml_config: ConfigType | None = None,
        entity_config: ConfigType | None = None,
        entity_filter: EntityFilter | None = None,
    ):
        """Initialize."""
        self.entry = entry
        self.entity_config: ConfigType = entity_config or {}
        self._yaml_config: ConfigType = yaml_config or {}

        self._hass = hass
        self._entity_filter = entity_filter
        self._cloud_manager: CloudManager | None = None
        self._notifiers: list[YandexNotifier] = []
        self._notifier_configs: list[NotifierConfig] = []

    async def async_setup(self) -> Self:
        """Set up the config entry data."""

        self.cache = CacheStore(self._hass)
        await self.cache.async_load()

        if self.connection_type == ConnectionType.CLOUD:
            await self._async_setup_cloud_connection()

        self._notifier_configs = await self._get_notifier_configs()
        if self._hass.state == CoreState.running:
            await self._async_setup_notifiers()
        else:
            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._async_setup_notifiers)

        return self

    async def async_unload(self) -> None:
        """Unload the config entry data."""
        tasks = [asyncio.create_task(n.async_unload()) for n in self._notifiers]
        if self._cloud_manager:
            tasks.append(asyncio.create_task(self._cloud_manager.async_disconnect()))

        if tasks:
            await asyncio.wait(tasks)

        return None

    @property
    def is_reporting_states(self) -> bool:
        """Test if the config entry can report state changes."""
        return bool(self._notifier_configs)

    @property
    def use_cloud_stream(self) -> bool:
        """Test if the config entry use video streaming through the cloud."""
        if self.connection_type == ConnectionType.CLOUD:
            return True

        settings = self._yaml_config.get(const.CONF_SETTINGS, {})
        return bool(settings.get(const.CONF_CLOUD_STREAM))

    @property
    def connection_type(self) -> ConnectionType:
        """Return connection type."""
        return ConnectionType(str(self.entry.data.get(const.CONF_CONNECTION_TYPE)))

    @property
    def cloud_instance_id(self) -> str:
        """Return cloud instance id."""
        if self.connection_type == ConnectionType.CLOUD:
            return str(self.entry.data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_ID])

        raise ValueError("Config entry uses direct connection")

    @property
    def cloud_connection_token(self) -> str:
        """Return cloud connection token."""
        if self.connection_type == ConnectionType.CLOUD:
            return str(self.entry.data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN])

        raise ValueError("Config entry uses direct connection")

    @property
    def user_id(self) -> str | None:
        """Return user id for service calls (used only when cloud connection)."""
        return self.entry.options.get(const.CONF_USER_ID)

    @property
    def pressure_unit(self) -> str:
        settings = self._yaml_config.get(const.CONF_SETTINGS, {})
        return str(settings.get(const.CONF_PRESSURE_UNIT) or UnitOfPressure.MMHG.value)

    @property
    def color_profiles(self) -> ColorProfiles:
        """Return color profiles."""
        return ColorProfiles.from_dict(self._yaml_config.get(const.CONF_COLOR_PROFILE, {}))

    def get_entity_config(self, entity_id: str) -> ConfigType:
        """Return configuration for the entity."""
        return self.entity_config.get(entity_id, {})

    def should_expose(self, entity_id: str) -> bool:
        """Test if the entity should be exposed."""
        if self._entity_filter and not self._entity_filter.empty_filter:
            return self._entity_filter(entity_id)

        return False

    def discover_devices(self) -> bool:
        """Mark config entry has returned the device list once."""
        if self.entry.data.get(const.CONF_DEVICES_DISCOVERED):
            return False

        data = self.entry.data.copy()
        data[const.CONF_DEVICES_DISCOVERED] = True

        return self._hass.config_entries.async_update_entry(self.entry, data=data, options=self.entry.options)

    @property
    def version(self) -> str:
        """Return component version."""
        try:
            return str(self._hass.data[DATA_CUSTOM_COMPONENTS][DOMAIN].version)
        except KeyError:
            return "unknown"

    async def _async_setup_notifiers(self, *_: Any) -> None:
        """Set up notifiers."""
        if not self.entry.data.get(const.CONF_DEVICES_DISCOVERED) or not self._notifier_configs:
            return

        for config in self._notifier_configs:
            match self.connection_type:
                case ConnectionType.CLOUD:
                    self._notifiers.append(YandexCloudNotifier(self._hass, self, config))
                case ConnectionType.DIRECT:
                    self._notifiers.append(YandexDirectNotifier(self._hass, self, config))

        await asyncio.wait([asyncio.create_task(n.async_setup()) for n in self._notifiers])

        return None

    async def _async_setup_cloud_connection(self) -> None:
        """Set up the cloud connection."""
        self._cloud_manager = CloudManager(self._hass, self)

        self._hass.loop.create_task(self._cloud_manager.async_connect())
        return self.entry.async_on_unload(
            self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._cloud_manager.async_disconnect)
        )

    async def _get_notifier_configs(self) -> list[NotifierConfig]:
        """Return notifier configurations."""
        configs: list[NotifierConfig] = []

        match self.connection_type:
            case ConnectionType.CLOUD:
                configs.append(NotifierConfig(user_id=self.cloud_instance_id, token=self.cloud_connection_token))
            case ConnectionType.DIRECT:
                items = self._yaml_config.get(const.CONF_NOTIFIER, [])
                for item in items:
                    configs.append(
                        NotifierConfig(
                            user_id=item[const.CONF_NOTIFIER_USER_ID],
                            hass_user_id=item[const.CONF_NOTIFIER_USER_ID],
                            token=item[const.CONF_NOTIFIER_OAUTH_TOKEN],
                            skill_id=item[const.CONF_NOTIFIER_SKILL_ID],
                            verbose_log=len(items) > 1,
                        )
                    )

        for config in configs:
            try:
                await config.async_validate(self._hass)
            except Exception as exc:
                raise ConfigEntryNotReady from exc

        return configs
