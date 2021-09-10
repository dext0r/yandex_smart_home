"""Tests for yandex_smart_home integration."""
from __future__ import annotations

from typing import Any, Callable, Optional

from homeassistant.core import HomeAssistant

from custom_components.yandex_smart_home.const import CONF_BETA
from custom_components.yandex_smart_home.helpers import Config, RequestData


class MockConfig(Config):
    # noinspection PyMissingConstructor
    def __init__(self, hass: HomeAssistant = None, settings: dict[str, Any] = None,
                 notifier: list[dict[str, Any]] = None,
                 should_expose: Callable[[str], bool] = None,
                 entity_config: Optional[dict[str, Any]] = None):
        """Initialize the configuration."""
        self._hass = hass
        self.settings = settings or {
            CONF_BETA: True
        }
        self.notifier = notifier or []
        self._should_expose = should_expose
        self.entity_config = entity_config or {}

    @property
    def is_reporting_state(self) -> bool:
        """Return if we're actively reporting states."""
        return True

    def should_expose(self, state):
        """Expose it all."""
        return self._should_expose is None or self._should_expose(state)


REQ_ID = '5ca6622d-97b5-465c-a494-fd9954f7599a'

BASIC_CONFIG = MockConfig()

BASIC_DATA = RequestData(BASIC_CONFIG, 'test', REQ_ID)
