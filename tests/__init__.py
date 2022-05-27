"""Tests for yandex_smart_home integration."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entityfilter
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, const, get_config_entry_data_from_yaml_config
from custom_components.yandex_smart_home.helpers import CacheStore, Config, RequestData


class MockConfig(Config):
    def __init__(self,
                 hass: HomeAssistant | None = None,
                 entry: ConfigEntry | None = None,
                 entity_config: dict[str, Any] | None = None,
                 entity_filter: entityfilter.EntityFilter | None = None):
        if not entry:
            data, options = get_config_entry_data_from_yaml_config({}, {}, None)
            entry = MockConfigEntry(domain=DOMAIN, data=data, options=options)

        super().__init__(hass, entry, entity_config, entity_filter)

        self.cache = MockCacheStore()

    @property
    def is_reporting_state(self) -> bool:
        return True

    @property
    def beta(self):
        return False


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


def generate_entity_filter(include_entity_globs=None, exclude_entities=None) -> entityfilter.EntityFilter:
    return entityfilter.EntityFilter({
        entityfilter.CONF_INCLUDE_DOMAINS: [],
        entityfilter.CONF_INCLUDE_ENTITY_GLOBS: include_entity_globs or [],
        entityfilter.CONF_INCLUDE_ENTITIES: [],
        entityfilter.CONF_EXCLUDE_DOMAINS: [],
        entityfilter.CONF_EXCLUDE_ENTITY_GLOBS: [],
        entityfilter.CONF_EXCLUDE_ENTITIES: exclude_entities or [],
    })


REQ_ID = '5ca6622d-97b5-465c-a494-fd9954f7599a'

BASIC_CONFIG = MockConfig(
    entity_filter=generate_entity_filter(include_entity_globs=['*'])
)

BASIC_DATA = RequestData(BASIC_CONFIG, 'test', REQ_ID)
