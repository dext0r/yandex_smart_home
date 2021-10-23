"""Tests for yandex_smart_home integration."""
from __future__ import annotations

from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yandex_smart_home import SETTINGS_SCHEMA
from custom_components.yandex_smart_home.helpers import Config, RequestData


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
        self._should_expose = should_expose
        self.entity_config = entity_config or {}

        if not self._data:
            self._data.update(SETTINGS_SCHEMA(data={}))

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


REQ_ID = '5ca6622d-97b5-465c-a494-fd9954f7599a'

BASIC_CONFIG = MockConfig()

BASIC_DATA = RequestData(BASIC_CONFIG, 'test', REQ_ID)
