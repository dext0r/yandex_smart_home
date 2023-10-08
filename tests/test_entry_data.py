from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home.entry_data import ConfigEntryData


def test_entry_data_unknown_version(hass):
    entry_data = ConfigEntryData(hass, MockConfigEntry())
    assert entry_data.version == "unknown"
