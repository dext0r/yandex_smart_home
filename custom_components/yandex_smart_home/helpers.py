"""Helper classes for Yandex Smart Home integration."""
from __future__ import annotations

from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from . import const
from .const import DOMAIN, NOTIFIERS, STORE_CACHE_ATTRS


class Config:
    """Hold the configuration for Yandex Smart Home."""

    def __init__(self,
                 hass: HomeAssistant,
                 entry: ConfigEntry,
                 entity_config: dict[str, Any] | None,
                 should_expose: Callable[[str], bool]):
        """Initialize the configuration."""
        self._hass = hass
        self._data = entry.data
        self._options = entry.options
        self.cache: CacheStore | None = None
        self.entity_config = entity_config or {}
        self.should_expose = should_expose

    async def async_init(self):
        self.cache = CacheStore(self._hass)
        await self.cache.async_load()

    @property
    def is_reporting_state(self) -> bool:
        """Return if we're actively reporting states."""
        if self.is_cloud_connection:
            return True

        return bool(self._hass.data[DOMAIN][NOTIFIERS])

    @property
    def is_cloud_connection(self) -> bool:
        return self._data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD

    @property
    def is_direct_connection(self) -> bool:
        return self._data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_DIRECT

    @property
    def cloud_instance_id(self) -> str | None:
        return self._data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_ID]

    @property
    def cloud_connection_token(self) -> str | None:
        return self._data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN]

    @property
    def user_id(self) -> str | None:
        """User id for service calls, used only in cloud connection."""
        return self._options.get(const.CONF_USER_ID)

    @property
    def pressure_unit(self) -> str:
        return self._data[const.CONF_PRESSURE_UNIT]

    @property
    def beta(self) -> bool:
        return self._data[const.CONF_BETA]

    @property
    def notifier(self) -> list[ConfigType]:
        return self._data.get(const.CONF_NOTIFIER, {})

    @property
    def devices_discovered(self) -> bool:
        return self._data[const.CONF_DEVICES_DISCOVERED]

    def get_entity_config(self, entity_id: str) -> dict[str, Any]:
        return self.entity_config.get(entity_id, {})


class CacheStore:
    _STORAGE_VERSION = 1
    _STORAGE_KEY = f'{DOMAIN}.cache'

    def __init__(self, hass):
        self._hass = hass
        self._store = Store(hass, self._STORAGE_VERSION, self._STORAGE_KEY)
        self._data = {STORE_CACHE_ATTRS: {}}

    def get_attr_value(self, entity_id: str, attr: str) -> Any | None:
        """Return a cached value of attribute for entity."""
        if entity_id not in self._data[STORE_CACHE_ATTRS]:
            return None

        return self._data[STORE_CACHE_ATTRS][entity_id].get(attr)

    @callback
    def save_attr_value(self, entity_id: str, attr: str, value: Any):
        """Cache entity's attribute value to disk."""
        if entity_id not in self._data[STORE_CACHE_ATTRS]:
            self._data[STORE_CACHE_ATTRS][entity_id] = {}
            has_changed = True
        else:
            has_changed = self._data[STORE_CACHE_ATTRS][entity_id][attr] != value

        self._data[STORE_CACHE_ATTRS][entity_id][attr] = value

        if has_changed:
            self._store.async_delay_save(lambda: self._data, 5.0)

    async def async_load(self):
        data = await self._store.async_load()
        if data:
            self._data = data


class RequestData:
    """Hold data associated with a particular request."""

    def __init__(self,
                 config: Config,
                 request_user_id: str | None,
                 request_id: str | None = None,
                 user_id: str | None = None):
        """Initialize the request data."""
        self.config = config
        self.context = Context(user_id=user_id)
        self.request_user_id = request_user_id
        self.request_id = request_id
