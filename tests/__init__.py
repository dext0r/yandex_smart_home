"""Tests for yandex_smart_home integration."""
from typing import Any
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import entityfilter
from homeassistant.helpers.typing import ConfigType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN
from custom_components.yandex_smart_home.entry_data import ConfigEntryData
from custom_components.yandex_smart_home.helpers import STORE_CACHE_ATTRS, CacheStore, RequestData


class MockConfigEntryData(ConfigEntryData):
    def __init__(
        self,
        hass: HomeAssistant | None = None,
        entry: ConfigEntry | None = None,
        yaml_config: ConfigType | None = None,
        entity_config: dict[str, Any] | None = None,
        entity_filter: entityfilter.EntityFilter | None = None,
    ):
        if not entry:
            entry = MockConfigEntry(domain=DOMAIN, data={}, options={})

        super().__init__(hass, entry, yaml_config, entity_config, entity_filter)

        self.cache = MockCacheStore()

    @property
    def is_reporting_states(self) -> bool:
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
        self._data = {STORE_CACHE_ATTRS: {}}
        self._store = MockStore()


def generate_entity_filter(include_entity_globs=None, exclude_entities=None) -> entityfilter.EntityFilter:
    return entityfilter.EntityFilter(
        {
            entityfilter.CONF_INCLUDE_DOMAINS: [],
            entityfilter.CONF_INCLUDE_ENTITY_GLOBS: include_entity_globs or [],
            entityfilter.CONF_INCLUDE_ENTITIES: [],
            entityfilter.CONF_EXCLUDE_DOMAINS: [],
            entityfilter.CONF_EXCLUDE_ENTITY_GLOBS: [],
            entityfilter.CONF_EXCLUDE_ENTITIES: exclude_entities or [],
        }
    )


REQ_ID: str = "5ca6622d-97b5-465c-a494-fd9954f7599a"

BASIC_ENTRY_DATA: MockConfigEntryData = MockConfigEntryData(
    entry=MockConfigEntry(domain=DOMAIN, data={}, options={}),
    entity_filter=generate_entity_filter(include_entity_globs=["*"]),
)

BASIC_REQUEST_DATA: RequestData = RequestData(
    entry_data=BASIC_ENTRY_DATA, context=Context(), request_user_id="test", request_id=REQ_ID
)
