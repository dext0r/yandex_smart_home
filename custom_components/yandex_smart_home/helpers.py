"""Helper classes for Yandex Smart Home integration."""
from __future__ import annotations

from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.typing import ConfigType

from . import const
from .const import DOMAIN, NOTIFIERS


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
        self.entity_config = entity_config or {}
        self.should_expose = should_expose

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


class RequestData:
    """Hold data associated with a particular request."""

    def __init__(self,
                 config: Config,
                 user_id: str | None,
                 request_id: str | None,
                 hass_user_id: str | None = None):
        """Initialize the request data."""
        self.config = config
        self.user_id = user_id
        self.context = Context(user_id=hass_user_id)
        self.request_id = request_id
