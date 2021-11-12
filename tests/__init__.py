"""Tests for yandex_smart_home integration."""
from __future__ import annotations

from typing import Any, Callable
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yandex_smart_home import SETTINGS_SCHEMA, const
from custom_components.yandex_smart_home.helpers import CacheStore, Config, RequestData


class MockConfig(Config):
    # noinspection PyMissingConstructor
    def __init__(self,
                 hass: HomeAssistant | None = None,
                 entry: ConfigEntry | None = None,
                 entity_config: dict[str, Any] | None = None,
                 should_expose: Callable[[str], bool] = None):
        """Initialize the configuration."""
        self._hass = hass
        self._data = entry.data if entry else {}
        self._options = entry.options if entry else {}
        self._should_expose = should_expose
        self.cache = MockCacheStore()
        self.entity_config = entity_config or {}

        if not self._data:
            self._data.update(SETTINGS_SCHEMA(data={}))
            self._data[const.CONF_CONNECTION_TYPE] = const.CONNECTION_TYPE_DIRECT
            self._data[const.CONF_DEVICES_DISCOVERED] = True

    @property
    def is_reporting_state(self) -> bool:
        """Return if we're actively reporting states."""
        return True

    def should_expose(self, state):
        """Expose it all."""
        return self._should_expose is None or self._should_expose(state)

    @property
    def beta(self):
        return True


class MockStore:
    def __init__(self, data=None):
        self._data = data
        self.async_delay_save = MagicMock()

    async def async_load(self):
        return self._data


class MockCacheStore(CacheStore):
    # noinspection PyMissingConstructor
    def __init__(self):
        self._data = {const.STORE_CACHE_ATTRS: {}}
        self._store = MockStore()


REQ_ID = '5ca6622d-97b5-465c-a494-fd9954f7599a'

BASIC_CONFIG = MockConfig()

BASIC_DATA = RequestData(BASIC_CONFIG, 'test', REQ_ID)
