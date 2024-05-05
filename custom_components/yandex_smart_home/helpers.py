"""Helper classes for Yandex Smart Home integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .schema import ResponseCode

if TYPE_CHECKING:
    from homeassistant.core import Context, HomeAssistant

    from .entry_data import ConfigEntryData

STORE_CACHE_ATTRS = "attrs"


class APIError(HomeAssistantError):
    """Base API error."""

    def __init__(self, code: ResponseCode, message: str):
        """Init the error."""

        super().__init__(message)
        self.code = code
        self.message = message


class ActionNotAllowed(HomeAssistantError):
    """Error producted when change capability state is not allowed, no logging."""

    def __init__(self, code: ResponseCode = ResponseCode.REMOTE_CONTROL_DISABLED):
        """Init the error."""

        self.code = code


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


@dataclass
class RequestData:
    """Hold data associated with a particular request."""

    entry_data: ConfigEntryData
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
