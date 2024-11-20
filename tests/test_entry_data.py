from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.const import CONF_PLATFORM
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, YandexSmartHome
from custom_components.yandex_smart_home.capability_toggle import BacklightCapability
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_CONNECTION_TYPE,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
    CONF_ENTITY_CUSTOM_TOGGLES,
    CONF_LINKED_PLATFORMS,
    CONF_NOTIFIER,
    CONF_PRESSURE_UNIT,
    CONF_SETTINGS,
    CONF_USER_ID,
    ConnectionType,
)
from custom_components.yandex_smart_home.entry_data import ConfigEntryData
from custom_components.yandex_smart_home.helpers import APIError, SmartHomePlatform
from custom_components.yandex_smart_home.property_custom import (
    ButtonPressEventPlatformCustomProperty,
    MotionEventPlatformCustomProperty,
)
from custom_components.yandex_smart_home.schema import ResponseCode
from tests.test_device import (
    CONF_BACKLIGHT_ENTITY_ID,
    CONF_ENTITY_PROPERTIES,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
)

from . import MockConfigEntryData, generate_entity_filter


def test_entry_data_unknown_version(hass: HomeAssistant) -> None:
    entry_data = ConfigEntryData(hass, MockConfigEntry())
    assert entry_data.component_version == "unknown"


def test_entry_data_platform(hass: HomeAssistant) -> None:
    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN,
            version=ConfigFlowHandler.VERSION,
            data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        ),
    )
    assert entry_data.platform == "yandex"

    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN,
            version=ConfigFlowHandler.VERSION,
            data={CONF_CONNECTION_TYPE: ConnectionType.CLOUD},
        ),
    )
    assert entry_data.platform is None


def test_entry_data_trackable_templates(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    entry_data = MockConfigEntryData(
        hass=hass,
        entity_config={
            "sensor.outside_temp": {
                CONF_ENTITY_CUSTOM_TOGGLES: {
                    "pause": {CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "binary_sensor.pause"}
                },
            }
        },
        entity_filter=generate_entity_filter(include_entity_globs=["*"]),
    )

    with patch(
        "custom_components.yandex_smart_home.entry_data.get_custom_capability",
        side_effect=APIError(ResponseCode.INTERNAL_ERROR, "foo"),
    ):
        assert entry_data._get_trackable_templates() == {}
    assert caplog.messages == ["Failed to track custom capability: foo"]

    entry_data = MockConfigEntryData(
        hass=hass,
        entity_config={
            "sensor.outside_temp": {
                CONF_ENTITY_CUSTOM_TOGGLES: {
                    "pause": {CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "binary_sensor.pause"}
                },
                CONF_ENTITY_PROPERTIES: [
                    {CONF_ENTITY_PROPERTY_TYPE: "motion", CONF_ENTITY_PROPERTY_ENTITY: "binary_sensor.motion"},
                    {CONF_ENTITY_PROPERTY_TYPE: "button", CONF_ENTITY_PROPERTY_ENTITY: "event.button"},
                ],
            }
        },
        entity_filter=generate_entity_filter(include_entity_globs=["*"]),
    )

    assert len(entry_data._get_trackable_templates()) == 2


def test_entry_data_trackable_entity_states(hass: HomeAssistant) -> None:
    entry_data = MockConfigEntryData(
        hass=hass,
        entity_config={
            "sensor.foo": {
                CONF_ENTITY_PROPERTIES: [
                    {CONF_ENTITY_PROPERTY_TYPE: "motion", CONF_ENTITY_PROPERTY_ENTITY: "binary_sensor.motion"},
                    {CONF_ENTITY_PROPERTY_TYPE: "button", CONF_ENTITY_PROPERTY_ENTITY: "event.button"},
                ],
            },
            "sensor.bar": {
                CONF_ENTITY_PROPERTIES: [
                    {CONF_ENTITY_PROPERTY_TYPE: "motion", CONF_ENTITY_PROPERTY_ENTITY: "event.motion"},
                    {CONF_ENTITY_PROPERTY_TYPE: "button", CONF_ENTITY_PROPERTY_ENTITY: "event.button"},
                ],
            },
            "water_heater.kettle": {
                CONF_BACKLIGHT_ENTITY_ID: "light.kettle_backlight",
            },
            "switch.not_exposed": {
                CONF_ENTITY_PROPERTIES: [
                    {CONF_ENTITY_PROPERTY_TYPE: "button", CONF_ENTITY_PROPERTY_ENTITY: "event.button"},
                ],
            },
        },
        entity_filter=generate_entity_filter(
            include_entity_globs=["*"], exclude_entities=["switch.not_exposed", "light.kettle_backlight"]
        ),
    )

    assert entry_data._get_trackable_entity_states() == {
        "event.button": [
            (
                "sensor.foo",
                ButtonPressEventPlatformCustomProperty,
            ),
            (
                "sensor.bar",
                ButtonPressEventPlatformCustomProperty,
            ),
        ],
        "event.motion": [
            (
                "sensor.bar",
                MotionEventPlatformCustomProperty,
            ),
        ],
        "light.kettle_backlight": [
            (
                "water_heater.kettle",
                BacklightCapability,
            ),
        ],
    }


async def test_entry_data_get_context_user_id(hass: HomeAssistant, hass_read_only_user: User) -> None:
    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(domain=DOMAIN, version=ConfigFlowHandler.VERSION, data={}, options={CONF_USER_ID: "foo"}),
    )
    assert await entry_data.async_get_context_user_id() is None

    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(
            domain=DOMAIN,
            version=ConfigFlowHandler.VERSION,
            data={},
            options={CONF_USER_ID: hass_read_only_user.id},
        ),
    )
    assert await entry_data.async_get_context_user_id() is hass_read_only_user.id


async def test_entry_data_unsupported_linked_platform(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    entry_data = MockConfigEntryData(
        hass=hass,
        entry=MockConfigEntry(domain=DOMAIN, version=ConfigFlowHandler.VERSION, data={CONF_LINKED_PLATFORMS: ["foo"]}),
    )
    assert entry_data.linked_platforms == set()
    assert caplog.messages == ["Unsupported platform: foo"]


async def test_deprecated_pressure_unit(
    hass: HomeAssistant,
    config_entry_direct: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_pressure_unit") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    component._yaml_config = {CONF_SETTINGS: {CONF_PRESSURE_UNIT: "foo"}}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_pressure_unit") is not None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component._yaml_config = {CONF_SETTINGS: {}}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_pressure_unit") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)


async def test_deprecated_notifier(
    hass: HomeAssistant,
    config_entry_direct: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    component._yaml_config = {CONF_NOTIFIER: ["foo"]}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is not None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component._yaml_config = {}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component = hass.data[DOMAIN]
    component._yaml_config = {CONF_NOTIFIER: ["foo", "bar"]}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is not None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)

    component._yaml_config = {}
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_notifier") is None
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_yaml_several_notifiers") is None
    await hass.config_entries.async_unload(config_entry_direct.entry_id)
