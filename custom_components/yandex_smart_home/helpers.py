"""Helper classes for Yandex Smart Home integration."""
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers.entityfilter import EntityFilter
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from . import const
from .color import ColorProfiles
from .const import DOMAIN, NOTIFIERS, STORE_CACHE_ATTRS


class CacheStore:
    """Cache store for Yandex Smart Home."""

    _STORAGE_VERSION = 1
    _STORAGE_KEY = f"{DOMAIN}.cache"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize a cache store."""
        self._hass = hass
        self._store = Store[dict[str, Any]](hass, self._STORAGE_VERSION, self._STORAGE_KEY)
        self._data: dict[str, dict[str, Any]] = {STORE_CACHE_ATTRS: {}}

    def get_attr_value(self, entity_id: str, attr: str) -> Any | None:
        """Return a cached value of attribute for entity."""
        if entity_id not in self._data[STORE_CACHE_ATTRS]:
            return None

        return self._data[STORE_CACHE_ATTRS][entity_id].get(attr)

    @callback
    def save_attr_value(self, entity_id: str, attr: str, value: Any) -> None:
        """Cache entity's attribute value to disk."""
        if entity_id not in self._data[STORE_CACHE_ATTRS]:
            self._data[STORE_CACHE_ATTRS][entity_id] = {}
            has_changed = True
        else:
            has_changed = self._data[STORE_CACHE_ATTRS][entity_id][attr] != value

        self._data[STORE_CACHE_ATTRS][entity_id][attr] = value

        if has_changed:
            self._store.async_delay_save(lambda: self._data, 5.0)

        return None

    async def async_load(self) -> None:
        """Load store data."""
        data = await self._store.async_load()
        if data:
            self._data = data

        return None


class Config:
    """Hold the configuration for Yandex Smart Home integration."""

    cache: CacheStore

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entity_config: dict[str, Any] | None = None,
        entity_filter: EntityFilter | None = None,
    ):
        """Initialize the configuration."""
        self._hass = hass
        self._data = entry.data
        self._options = entry.options
        self._entity_filter = entity_filter

        self.entity_config = entity_config or {}

    async def async_init(self) -> None:
        """Addinitional initialization."""
        self.cache = CacheStore(self._hass)
        await self.cache.async_load()
        return None

    @property
    def is_reporting_state(self) -> bool:
        """Test if the integration can report changes."""
        if self.is_cloud_connection:
            return True

        return bool(self._hass.data[DOMAIN][NOTIFIERS])

    @property
    def is_cloud_connection(self) -> bool:
        """Test if the integration use cloud connection."""
        return bool(self._data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD)

    @property
    def is_direct_connection(self) -> bool:
        """Test if the integration use direct connection."""
        return bool(self._data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_DIRECT)

    @property
    def use_cloud_stream(self) -> bool:
        """Test if the integration use video streaming through cloud."""
        return bool(self._options[const.CONF_CLOUD_STREAM])

    @property
    def cloud_instance_id(self) -> str:
        """Return cloud instance id."""
        return str(self._data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_ID])

    @property
    def cloud_connection_token(self) -> str:
        """Return cloud connection token."""
        return str(self._data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN])

    @property
    def user_id(self) -> str | None:
        """User id for service calls, used only in cloud connection."""
        return self._options.get(const.CONF_USER_ID)

    @property
    def pressure_unit(self) -> str:
        return str(self._options[const.CONF_PRESSURE_UNIT])

    @property
    def beta(self) -> bool:
        return bool(self._options[const.CONF_BETA])  # pragma: no cover

    @property
    def notifier(self) -> list[ConfigType]:
        """Return configuration for notifier."""
        return self._data.get(const.CONF_NOTIFIER, [])

    @property
    def color_profiles(self) -> ColorProfiles:
        """Return color profiles."""
        return ColorProfiles.from_dict(self._options.get(const.CONF_COLOR_PROFILE, {}))

    @property
    def devices_discovered(self) -> bool:
        """Test if device list was requested."""
        return bool(self._data[const.CONF_DEVICES_DISCOVERED])

    def get_entity_config(self, entity_id: str) -> dict[str, Any]:
        """Return configuration for the entity."""
        return self.entity_config.get(entity_id, {})

    def should_expose(self, entity_id: str) -> bool:
        """Test if the entity should be exposed."""
        if self._entity_filter and not self._entity_filter.empty_filter:
            return self._entity_filter(entity_id)

        return False


@dataclass
class RequestData:
    """Hold data associated with a particular request."""

    config: Config
    context: Context
    request_user_id: str | None
    request_id: str | None


class HasInstance(Protocol):
    """Protocol type for objects that has instance attribute."""

    instance: Any


_HasInstanceT = TypeVar("_HasInstanceT", bound=type[HasInstance])


class DictRegistry(dict[str, _HasInstanceT]):
    """Dict Registry for types with instance attribute."""

    def register(self, obj: _HasInstanceT) -> _HasInstanceT:
        """Register decorated type."""
        self[obj.instance] = obj
        return obj


_TypeT = TypeVar("_TypeT", bound=type[Any])


class ListRegistry(list[_TypeT]):
    """List Registry of items."""

    def register(self, obj: _TypeT) -> _TypeT:
        """Register decorated type."""
        self.append(obj)
        return obj
