from unittest.mock import patch

from homeassistant.const import CONF_PLATFORM
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, ConnectionType, YandexSmartHome, const
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.entry_data import ConfigEntryData
from custom_components.yandex_smart_home.helpers import APIError, SmartHomePlatform
from custom_components.yandex_smart_home.schema import ResponseCode

from . import MockConfigEntryData, generate_entity_filter


def test_entry_data_unknown_version(hass):
    entry_data = ConfigEntryData(hass, MockConfigEntry())
    assert entry_data.version == "unknown"


def test_entry_data_platform(hass):
    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN,
            version=ConfigFlowHandler.VERSION,
            data={const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        ),
    )
    assert entry_data.platform == "yandex"

    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN,
            version=ConfigFlowHandler.VERSION,
            data={const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD},
        ),
    )
    assert entry_data.platform is None


def test_entry_data_trackable_states(hass, caplog):
    entry_data = MockConfigEntryData(
        hass=hass,
        entity_config={
            "sensor.outside_temp": {
                const.CONF_ENTITY_CUSTOM_TOGGLES: {
                    "pause": {const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "binary_sensor.pause"}
                },
            }
        },
        entity_filter=generate_entity_filter(include_entity_globs=["*"]),
    )

    with patch(
        "custom_components.yandex_smart_home.entry_data.get_custom_capability",
        side_effect=APIError(ResponseCode.INTERNAL_ERROR, "foo"),
    ):
        assert entry_data._get_trackable_states() == {}
    assert caplog.messages == ["Failed to track custom capability: foo"]


async def test_entry_data_get_context_user_id(hass, hass_read_only_user):
    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN, version=ConfigFlowHandler.VERSION, data={}, options={const.CONF_USER_ID: "foo"}
        ),
    )
    assert await entry_data.async_get_context_user_id() is None

    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN,
            version=ConfigFlowHandler.VERSION,
            data={},
            options={const.CONF_USER_ID: hass_read_only_user.id},
        ),
    )
    assert await entry_data.async_get_context_user_id() is hass_read_only_user.id


async def test_entry_data_unsupported_linked_platform(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN, version=ConfigFlowHandler.VERSION, data={const.CONF_LINKED_PLATFORMS: ["foo"]}
        ),
    )
    assert entry_data.linked_platforms == set()
    assert caplog.messages == ["Unsupported platform: foo"]


async def test_deprecated_pressure_unit(hass, config_entry_direct):
    issue_registry = ir.async_get(hass)

    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_pressure_unit") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    component._yaml_config = {const.CONF_SETTINGS: {const.CONF_PRESSURE_UNIT: "foo"}}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_pressure_unit") is not None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component._yaml_config = {const.CONF_SETTINGS: {}}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_pressure_unit") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)


async def test_deprecated_notifier(hass, config_entry_direct):
    issue_registry = ir.async_get(hass)

    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    component._yaml_config = {const.CONF_NOTIFIER: ["foo"]}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is not None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component._yaml_config = {}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    component._yaml_config = {const.CONF_NOTIFIER: ["foo", "bar"]}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is not None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component._yaml_config = {}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)
