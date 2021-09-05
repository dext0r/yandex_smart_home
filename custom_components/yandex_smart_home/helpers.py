"""Helper classes for Yandex Smart Home integration."""
from __future__ import annotations
from typing import Any, Callable

from homeassistant.core import HomeAssistant, Context

from .const import DOMAIN, NOTIFIERS


class Config:
    """Hold the configuration for Yandex Smart Home."""

    def __init__(self, hass: HomeAssistant, settings: dict[str, Any], notifier: list[dict[str, Any]],
                 should_expose: Callable[[str], bool], entity_config: dict[str, Any] | None):
        """Initialize the configuration."""
        self._hass = hass
        self.settings = settings
        self.notifier = notifier
        self.should_expose = should_expose
        self.entity_config = entity_config or {}

    @property
    def is_reporting_state(self) -> bool:
        """Return if we're actively reporting states."""
        return bool(self._hass.data[DOMAIN][NOTIFIERS])

    def get_entity_config(self, entity_id: str) -> dict[str, Any]:
        return self.entity_config.get(entity_id, {})


class RequestData:
    """Hold data associated with a particular request."""

    def __init__(self, config: Config, user_id: str, request_id: str | None):
        """Initialize the request data."""
        self.config = config
        self.context = Context(user_id=user_id)
        self.request_id = request_id
