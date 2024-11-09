from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION, SERVICE_RELOAD
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture, patch_yaml_files

from custom_components.yandex_smart_home import DOMAIN, YandexSmartHome
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_CONNECTION_TYPE,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_NOTIFIER,
    CONF_NOTIFIER_OAUTH_TOKEN,
    CONF_NOTIFIER_SKILL_ID,
    CONF_NOTIFIER_USER_ID,
    EntityFilterSource,
)


async def test_bad_config(hass: HomeAssistant) -> None:
    with patch_yaml_files({YAML_CONFIG_FILE: "yandex_smart_home:\n  bad: true"}):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_valid_config(hass: HomeAssistant) -> None:
    with patch_yaml_files({YAML_CONFIG_FILE: load_fixture("valid-config.yaml")}):
        config = await async_integration_yaml_config(hass, DOMAIN)

    if (MAJOR_VERSION == 2024 and MINOR_VERSION >= 8) or MAJOR_VERSION >= 2025:
        service_key = "action"
    else:
        service_key = "service"

    hass_for_template: HomeAssistant | None = hass
    if MAJOR_VERSION == 2024 and int(MINOR_VERSION) == 8:
        hass_for_template = None

    assert config
    assert DOMAIN in config

    assert config[DOMAIN]["notifier"] == [
        {
            "oauth_token": "AgAAAAAEEo2aYYR7m-CEyS7SEiUJjnKez3v3GZe",
            "skill_id": "d38d4c39-5846-ba53-67acc27e08bc",
            "user_id": "e8701ad48ba05a91604e480dd60899a3",
        }
    ]
    assert config[DOMAIN]["settings"] == {"beta": True}
    assert config[DOMAIN]["color_profile"] == {"test": {"red": 16711680, "green": 65280, "warm_white": 3000}}
    assert config[DOMAIN]["filter"] == {
        "include_domains": ["switch", "light", "climate"],
        "include_entities": ["media_player.tv", "media_player.tv_lg", "media_player.receiver"],
        "include_entity_globs": ["sensor.temperature_*"],
        "exclude_entities": ["light.highlight"],
        "exclude_entity_globs": ["sensor.weather_*"],
        "exclude_domains": [],
    }

    entity_config = config[DOMAIN]["entity_config"]
    assert len(entity_config) == 16

    assert entity_config["switch.kitchen"] == {
        "name": "Выключатель",
    }
    assert entity_config["light.living_room"] == {
        "name": "Люстра",
        "modes": {"scene": {"sunrise": ["Wake up"], "alarm": ["Blink"]}},
        "color_profile": "natural",
    }
    assert entity_config["media_player.tv_lg"] == {
        "custom_ranges": {
            "channel": {
                "set_value": {
                    service_key: "media_player.play_media",
                    "entity_id": ["media_player.stupid_tv"],
                    "data": {
                        "media_content_type": "channel",
                        "media_content_id": Template("{{ value }}", hass_for_template),
                    },
                },
                "increase_value": {service_key: "script.next_channel_via_ir"},
                "decrease_value": {service_key: "script.prev_channel_via_ir"},
                "range": {"min": 0.0, "max": 999.0},
            },
            "volume": {
                "increase_value": {service_key: "script.increase_volume"},
                "decrease_value": {service_key: "script.decrease_volume"},
            },
        },
    }

    assert entity_config["fan.xiaomi_miio_device"] == {
        "name": "Увлажнитель",
        "room": "Гостиная",
        "type": "devices.types.humidifier",
        "properties": [
            {"type": "temperature", "entity": "sensor.temperature_158d000444c824"},
            {"type": "humidity", "attribute": "humidity"},
            {"type": "float.water_level", "attribute": "depth"},
            {"type": "event.water_level", "attribute": "water_level"},
        ],
    }

    assert entity_config["climate.tion_breezer"] == {
        "name": "Проветриватель",
        "modes": {
            "fan_speed": {
                "auto": ["auto"],
                "min": ["1", "1.0"],
                "low": ["2", "2.0"],
                "medium": ["3", "3.0"],
                "high": ["4", "4.0"],
                "turbo": ["5", "5.0"],
                "max": ["6", "6.0"],
            }
        },
    }

    assert entity_config["media_player.receiver"] == {
        "type": "devices.types.media_device.receiver",
        "range": {"max": 95.0, "min": 20.0, "precision": 2.0},
    }

    assert entity_config["media_player.cast"] == {
        "support_set_channel": False,
        "features": ["volume_mute", "volume_set", "next_previous_track"],
    }

    assert entity_config["climate.ac_living_room"] == {
        "name": "Кондиционер",
        "room": "Гостиная",
        "type": "devices.types.thermostat.ac",
        "custom_toggles": {
            "ionization": {
                "state_entity_id": "switch.ac_ionizer",
                "turn_on": {service_key: "switch.turn_on", "entity_id": ["switch.ac_ionizer"]},
                "turn_off": {service_key: "switch.turn_off", "entity_id": ["switch.ac_ionizer"]},
            },
            "backlight": {
                "state_entity_id": "input_boolean.ac_lighting",
                "turn_on": {service_key: "input_boolean.turn_on", "entity_id": ["input_boolean.ac_lighting"]},
                "turn_off": {service_key: "input_boolean.turn_off", "entity_id": ["input_boolean.ac_lighting"]},
            },
        },
    }

    assert isinstance(entity_config["switch.r4s1_kettle_boil"]["error_code_template"], Template)
    del entity_config["switch.r4s1_kettle_boil"]["error_code_template"]
    assert entity_config["switch.r4s1_kettle_boil"] == {
        "name": "Чайник",
        "room": "Кухня",
        "custom_ranges": {
            "temperature": {
                "state_attribute": "temperature",
                "set_value": {
                    service_key: "climate.set_temperature",
                    "data": {"temperature": Template("{{ value }}", hass_for_template)},
                    "target": {"entity_id": ["climate.r4s1_kettle_temp"]},
                },
                "range": {"min": 40.0, "max": 90.0, "precision": 10.0},
            }
        },
        "properties": [
            {"type": "temperature", "entity": "climate.r4s1_kettle_temp", "attribute": "current_temperature"}
        ],
    }

    assert entity_config["cover.ir_cover"] == {
        "name": "Глупые шторы",
        "state_unknown": True,
    }

    assert entity_config["input_text.button"] == {
        "name": "Кнопка на автоматизации",
        "device_class": "button",
    }

    assert entity_config["lock.front_door"] == {
        "type": "devices.types.openable",
        "turn_on": False,
    }

    assert entity_config["switch.water_valve"] == {
        "custom_modes": {"input_source": {"state_entity_id": "sensor.water_valve_input_source"}},
        "custom_ranges": {"open": {"state_entity_id": "sensor.water_valve_angel"}},
        "custom_toggles": {"backlight": {"state_entity_id": "sensor.water_valve_led"}},
        "properties": [{"type": "temperature", "value_template": Template("{{ 3 + 5 }}", hass_for_template)}],
    }

    assert entity_config["climate.ac"] == {
        "turn_on": {"data": {"mode": "cool"}, "entity_id": ["climate.ac"], service_key: "climate.turn_on"},
    }

    assert entity_config["switch.templates"] == {
        "custom_modes": {"input_source": {"state_template": Template("buz", hass_for_template)}, "thermostat": False},
        "custom_ranges": {"open": {"state_template": Template("foo", hass_for_template)}, "volume": False},
        "custom_toggles": {"backlight": {"state_template": Template("bar", hass_for_template)}, "mute": False},
    }

    assert entity_config["sensor.sun"] == {
        "properties": [
            {
                "target_unit_of_measurement": "K",
                "type": "temperature",
                "unit_of_measurement": "°C",
                "value_template": Template("{{ 15000000 }}", hass_for_template),
            },
            {
                "target_unit_of_measurement": "bar",
                "type": "pressure",
                "unit_of_measurement": "mmHg",
                "value_template": Template("{{ 0 }}", hass_for_template),
            },
        ]
    }


async def test_empty_dict_config(hass: HomeAssistant) -> None:
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
  entity_config:
"""
    }
    with patch_yaml_files(files):
        config = await async_integration_yaml_config(hass, DOMAIN)

    assert config
    assert DOMAIN in config
    assert isinstance(config[DOMAIN]["settings"], dict)
    assert config[DOMAIN]["entity_config"] == {}


async def test_reload_no_config_entry(hass: HomeAssistant, hass_admin_user: User) -> None:
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    component: YandexSmartHome = hass.data[DOMAIN]
    assert component._yaml_config.get("entity_config") is None

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      name: Test
"""
    }
    with patch_yaml_files(files):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
        )
        await hass.async_block_till_done()

    assert component._yaml_config["entity_config"]["sensor.test"]["name"] == "Test"


async def test_reload_with_config_entry(
    hass: HomeAssistant,
    hass_admin_user: User,
    hass_read_only_user: User,
    config_entry_direct: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)
    await hass.async_block_till_done()

    component: YandexSmartHome = hass.data[DOMAIN]
    assert component._yaml_config == {}

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      name: Test
"""
    }
    with patch_yaml_files(files):
        with pytest.raises(Unauthorized):
            await hass.services.async_call(
                DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_read_only_user.id)
            )

        with patch("homeassistant.config_entries.ConfigEntries.async_reload") as mock_reload_entry:
            await hass.services.async_call(
                DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
            )
            await hass.async_block_till_done()
            mock_reload_entry.assert_called_once()

    assert component._yaml_config["entity_config"]["sensor.test"]["name"] == "Test"

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  invalid: true
"""
    }
    with patch_yaml_files(files):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
        )
        await hass.async_block_till_done()

    assert component._yaml_config["entity_config"]["sensor.test"]["name"] == "Test"
    assert "Invalid config" in caplog.messages[-1]


async def test_setup_entry_filters(hass: HomeAssistant, hass_admin_user: User) -> None:
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: "direct"},
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {
                "include_domains": [
                    "media_player",
                    "climate",
                ],
                "exclude_entities": ["climate.front_gate"],
            },
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]

    with patch_yaml_files({YAML_CONFIG_FILE: ""}):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
        )
        await hass.async_block_till_done()

        entry_data = component.get_entry_data(config_entry)
        assert entry_data.should_expose("media_player.test") is True
        assert entry_data.should_expose("climate.test") is True
        assert entry_data.should_expose("climate.front_gate") is False

    with patch_yaml_files({YAML_CONFIG_FILE: "yandex_smart_home:"}):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
        )
        await hass.async_block_till_done()

        entry_data = component.get_entry_data(config_entry)
        assert entry_data.should_expose("media_player.test") is True
        assert entry_data.should_expose("climate.test") is True
        assert entry_data.should_expose("climate.front_gate") is False

    with patch_yaml_files(
        {
            YAML_CONFIG_FILE: """
yandex_smart_home:
  filter:
    include_domains:
      - light"""
        }
    ):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
        )
        await hass.async_block_till_done()

        entry_data = component.get_entry_data(config_entry)
        assert entry_data.should_expose("media_player.test") is True
        assert entry_data.should_expose("climate.test") is True
        assert entry_data.should_expose("climate.front_gate") is False

        options = config_entry.options.copy()
        options[CONF_FILTER_SOURCE] = EntityFilterSource.YAML
        hass.config_entries.async_update_entry(config_entry, options=options)
        await hass.async_block_till_done()

        entry_data = component.get_entry_data(config_entry)
        assert entry_data.should_expose("light.test") is True
        assert entry_data.should_expose("climate.test") is False

    with patch_yaml_files({YAML_CONFIG_FILE: "default_config:"}):
        await hass.services.async_call(
            DOMAIN, SERVICE_RELOAD, blocking=True, context=Context(user_id=hass_admin_user.id)
        )
        await hass.async_block_till_done()

        entry_data = component.get_entry_data(config_entry)
        assert entry_data._entity_filter is None
        assert entry_data.should_expose("media_player.test") is False
        assert entry_data.should_expose("light.test") is False
        assert entry_data.should_expose("climate.test") is False


async def test_unload_entry(hass: HomeAssistant, config_entry_direct: MockConfigEntry) -> None:
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_entry_data(config_entry_direct)
    assert entry_data.entry.state == ConfigEntryState.LOADED

    with pytest.raises(ValueError):
        assert entry_data.cloud_connection_token

    with pytest.raises(ValueError):
        assert entry_data.cloud_instance_id

    await hass.config_entries.async_unload(config_entry_direct.entry_id)
    assert entry_data.entry.state == ConfigEntryState.NOT_LOADED  # type: ignore[comparison-overlap]


async def test_remove_entry(hass: HomeAssistant, config_entry_direct: MockConfigEntry) -> None:
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1
    await hass.config_entries.async_remove(config_entry_direct.entry_id)
    assert len(component._entry_datas) == 0


async def test_remove_entry_unloaded(hass: HomeAssistant, config_entry_direct: MockConfigEntry) -> None:
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_remove(config_entry_direct.entry_id)


async def test_remove_entry_unknown(hass: HomeAssistant) -> None:
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    entry = MockConfigEntry(domain=DOMAIN, version=ConfigFlowHandler.VERSION)
    entry.add_to_hass(hass)

    await hass.config_entries.async_remove(entry.entry_id)


async def test_migrate_entity_v1(hass: HomeAssistant) -> None:
    entity = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="Yandex Smart Home Test",
        data={
            "devices_discovered": False,
            "connection_type": "direct",
            "cloud_instance": {"id": "foo", "password": "bar", "token": "xxx"},
            "notifier": [],
            "yaml_config_hash": "33cc1b5c66d9e4516c50b607952862a2",
            "abc": [],
        },
        options={
            "filter": {"include_entities": ["switch.ac"]},
            "color_profile": {},
            "pressure_unit": "mmHg",
            "cloud_stream": True,
            "beta": True,
            "ddd": [],
            "user_id": "user",
        },
    )
    entity.add_to_hass(hass)
    await hass.config_entries.async_setup(entity.entry_id)
    await hass.async_block_till_done()

    assert entity.version == 6
    assert entity.title == "Yandex Smart Home Test"
    assert entity.data == {
        "cloud_instance": {"id": "foo", "password": "bar", "token": "xxx"},
        "connection_type": "direct",
        "platform": "yandex",
        "devices_discovered": False,
    }
    assert entity.options == {
        "filter_source": "config_entry",
        "filter": {"include_entities": ["switch.ac"]},
        "user_id": "user",
    }

    entity = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="Yandex Smart Home Test",
    )
    entity.add_to_hass(hass)
    await hass.config_entries.async_setup(entity.entry_id)
    await hass.async_block_till_done()

    assert entity.version == 6
    assert entity.title == "Yandex Smart Home Test"
    assert entity.data == {
        "connection_type": "direct",
        "platform": "yandex",
        "linked_platforms": ["yandex"],
        "devices_discovered": True,
    }
    assert entity.options == {"filter_source": "config_entry"}


async def test_migrate_entity_v3_with_config(hass: HomeAssistant) -> None:
    await async_setup_component(hass, DOMAIN, {DOMAIN: {"filter": {}}})

    entity = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        title="Yandex Smart Home",
        data={
            "connection_type": "direct",
            "devices_discovered": False,
        },
        options={"filter": {"include_entities": ["switch.ac"]}},
    )
    entity.add_to_hass(hass)
    await hass.config_entries.async_setup(entity.entry_id)
    await hass.async_block_till_done()

    assert entity.version == 6
    assert entity.title == "Yandex Smart Home: Direct"
    assert entity.data == {
        "connection_type": "direct",
        "platform": "yandex",
        "devices_discovered": False,
    }
    assert entity.options == {
        "filter_source": "yaml",
        "filter": {"include_entities": ["switch.ac"]},
    }


@pytest.mark.parametrize(
    "connection_type,expect_migration",
    [
        ("cloud", False),
        ("direct", True),
    ],
)
async def test_migrate_entity_v5_single_notifier(
    hass: HomeAssistant, connection_type: str, expect_migration: bool
) -> None:
    await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                CONF_NOTIFIER: [
                    {
                        CONF_NOTIFIER_SKILL_ID: "foo",
                        CONF_NOTIFIER_OAUTH_TOKEN: "bar",
                        CONF_NOTIFIER_USER_ID: "baz",
                    }
                ]
            }
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "connection_type": connection_type,
            "cloud_instance": {"id": "1234567890", "password": "bar", "token": "xxx"},
            "bar": "foo",
        },
        options={"foo": "bar"},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.yandex_smart_home.entry_data.ConfigEntryData._async_setup_cloud_connection"):
        await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 6
    if expect_migration:
        assert entry.options.get("skill", {}) == {"id": "foo", "token": "bar", "user_id": "baz"}
    else:
        assert entry.options.get("skill", {}) == {}

    await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("connection_type", ["cloud", "direct"])
async def test_migrate_entity_v5_several_notifiers(hass: HomeAssistant, connection_type: str) -> None:
    await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                CONF_NOTIFIER: [
                    {
                        CONF_NOTIFIER_SKILL_ID: "foo",
                        CONF_NOTIFIER_OAUTH_TOKEN: "bar",
                        CONF_NOTIFIER_USER_ID: "baz",
                    }
                ]
            }
        },
    )
    data = {
        "connection_type": connection_type,
        "cloud_instance": {"id": "1234567890", "password": "bar", "token": "xxx"},
        "bar": "foo",
    }
    options = {"foo": "bar"}

    entry1 = MockConfigEntry(domain=DOMAIN, version=2, data=data, options=options)
    entry1.add_to_hass(hass)
    entry2 = MockConfigEntry(domain=DOMAIN, version=2, data=data, options=options)
    entry2.add_to_hass(hass)
    with patch("custom_components.yandex_smart_home.entry_data.ConfigEntryData._async_setup_cloud_connection"):
        await hass.config_entries.async_setup(entry1.entry_id)
        await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    assert entry1.version == 6
    assert entry2.version == 6
    assert entry1.options.get("skill", {}) == {}
    assert entry2.options.get("skill", {}) == {}
    await hass.config_entries.async_unload(entry1.entry_id)
    await hass.config_entries.async_unload(entry2.entry_id)


async def test_migrate_entity_v5_notifier_downgrade(hass: HomeAssistant) -> None:
    await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                CONF_NOTIFIER: [
                    {
                        CONF_NOTIFIER_SKILL_ID: "foo",
                        CONF_NOTIFIER_OAUTH_TOKEN: "bar",
                        CONF_NOTIFIER_USER_ID: "baz",
                    }
                ]
            }
        },
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={"connection_type": "direct"},
        options={"foo": "bar", "skill": {"id": "skill_id", "token": "token", "user_id": "user"}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 6
    assert entry.options == {
        "filter_source": "config_entry",
        "foo": "bar",
        "skill": {"id": "skill_id", "token": "token", "user_id": "user"},
    }
    await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "source_title,connection_type,expected_title",
    [
        ("Yandex Smart Home", "cloud", "Yaha Cloud (12345678)"),
        ("Yandex Smart Home Foo", "cloud", "Yandex Smart Home Foo"),
        ("Foo", "cloud", "Foo"),
        ("Yandex Smart Home", "direct", "Yandex Smart Home: Direct"),
        ("YSH: Direct", "direct", "Yandex Smart Home: Direct"),
        ("Yandex Smart Home Foo", "direct", "Yandex Smart Home Foo"),
        ("Foo", "direct", "Foo"),
    ],
)
async def test_migrate_entity_v5_title(
    hass: HomeAssistant, source_title: str, connection_type: str, expected_title: str
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title=source_title,
        data={
            "connection_type": connection_type,
            "cloud_instance": {"id": "1234567890", "password": "bar", "token": "xxx"},
            "bar": "foo",
        },
        options={"foo": "bar"},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.yandex_smart_home.entry_data.ConfigEntryData._async_setup_cloud_connection"):
        await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 6
    assert entry.title == expected_title
    assert entry.data == {
        "connection_type": connection_type,
        "platform": "yandex",
        "cloud_instance": {"id": "1234567890", "password": "bar", "token": "xxx"},
        "bar": "foo",
    }
    assert entry.options == {"filter_source": "config_entry", "foo": "bar"}
    await hass.config_entries.async_unload(entry.entry_id)
