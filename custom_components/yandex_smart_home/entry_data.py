"""Config entry data for the Yandex Smart Home."""

import asyncio
import logging
from typing import Any, Self, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entityfilter import EntityFilter
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import DATA_CUSTOM_COMPONENTS

from . import capability_custom, const, property_custom
from .capability_custom import CustomCapability, get_custom_capability
from .cloud import CloudManager
from .color import ColorProfiles
from .const import DOMAIN, ConnectionType
from .helpers import APIError, CacheStore
from .notifier import NotifierConfig, YandexCloudNotifier, YandexDirectNotifier, YandexNotifier
from .property_custom import CustomProperty, get_custom_property
from .schema import CapabilityType

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

        if self._yaml_config.get(const.CONF_SETTINGS, {}).get(const.CONF_PRESSURE_UNIT):
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                "deprecated_pressure_unit",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="deprecated_pressure_unit",
                learn_more_url="https://docs.yaha-cloud.ru/master/devices/sensor/float/#unit-conversion",
            )
        else:
            ir.async_delete_issue(self._hass, DOMAIN, "deprecated_pressure_unit")

        return self

    async def async_unload(self) -> None:
        """Unload the config entry data."""
        tasks = [asyncio.create_task(n.async_unload()) for n in self._notifiers]
        if self._cloud_manager:
            tasks.append(asyncio.create_task(self._cloud_manager.async_disconnect()))

        if tasks:
            await asyncio.wait(tasks)

        return None

    async def async_get_user_id(self) -> str | None:
        """Return user id for service calls (cloud connection only)."""
        if user_id := self.entry.options.get(const.CONF_USER_ID):
            if user := await self._hass.auth.async_get_user(user_id):
                return user.id

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
    def color_profiles(self) -> ColorProfiles:
        """Return color profiles."""
        return ColorProfiles.from_dict(self._yaml_config.get(const.CONF_COLOR_PROFILE, {}))

    def get_entity_config(self, entity_id: str) -> ConfigType:
        """Return configuration for the entity."""
        return cast(ConfigType, self.entity_config.get(entity_id, {}))

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

        track_templates = self._get_trackable_states()
        for config in self._notifier_configs:
            match self.connection_type:
                case ConnectionType.CLOUD:
                    self._notifiers.append(YandexCloudNotifier(self._hass, self, config, track_templates))
                case ConnectionType.DIRECT:
                    self._notifiers.append(YandexDirectNotifier(self._hass, self, config, track_templates))

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

    def _get_trackable_states(self) -> dict[Template, list[CustomCapability | CustomProperty]]:
        """Return states with their value templates."""
        templates: dict[Template, list[CustomCapability | CustomProperty]] = {}

        for device_id, entity_config in self.entity_config.items():
            if not self.should_expose(device_id):
                continue

            for capability_type, config_key in (
                (CapabilityType.MODE, const.CONF_ENTITY_CUSTOM_MODES),
                (CapabilityType.TOGGLE, const.CONF_ENTITY_CUSTOM_TOGGLES),
                (CapabilityType.RANGE, const.CONF_ENTITY_CUSTOM_RANGES),
            ):
                if config_key in entity_config:
                    for instance in entity_config[config_key]:
                        capability_config = entity_config[config_key][instance]
                        try:
                            capability = get_custom_capability(
                                self._hass,
                                self,
                                capability_config,
                                capability_type,
                                instance,
                                device_id,
                            )
                        except APIError as e:
                            _LOGGER.debug(f"Failed to track custom capability: {e}")
                            continue

                        template = capability_custom.get_value_template(device_id, capability_config)

                        if template:
                            templates.setdefault(template, [])
                            templates[template].append(capability)

            for property_config in entity_config.get(const.CONF_ENTITY_PROPERTIES, []):
                try:
                    template = property_custom.get_value_template(device_id, property_config)
                    templates.setdefault(template, [])
                    templates[template].append(get_custom_property(self._hass, self, property_config, device_id))
                except APIError as e:
                    _LOGGER.debug(f"Failed to track custom property: {e}")

        return templates
