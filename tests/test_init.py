from unittest.mock import patch

from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import Context
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture, patch_yaml_files

from custom_components.yandex_smart_home import DOMAIN, ConnectionType, YandexSmartHome, cloud, const
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler

from . import test_cloud


async def test_bad_config(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: "yandex_smart_home:\n  bad: true"}):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_valid_config(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: load_fixture("valid-config.yaml")}):
        config = await async_integration_yaml_config(hass, DOMAIN)

    assert DOMAIN in config

    assert config[DOMAIN]["notifier"] == [
        {
            "oauth_token": "AgAAAAAEEo2aYYR7m-CEyS7SEiUJjnKez3v3GZe",
            "skill_id": "d38d4c39-5846-ba53-67acc27e08bc",
            "user_id": "e8701ad48ba05a91604e480dd60899a3",
        }
    ]
    assert config[DOMAIN]["settings"] == {"pressure_unit": "mmHg", "beta": True}
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
    assert len(entity_config) == 15

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
                    "service": "media_player.play_media",
                    "entity_id": ["media_player.stupid_tv"],
                    "data": {"media_content_type": "channel", "media_content_id": Template("{{ value }}", hass)},
                },
                "increase_value": {"service": "script.next_channel_via_ir"},
                "decrease_value": {"service": "script.prev_channel_via_ir"},
                "range": {"min": 0.0, "max": 999.0},
            },
            "volume": {
                "increase_value": {"service": "script.increase_volume"},
                "decrease_value": {"service": "script.decrease_volume"},
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
            {"type": "water_level", "attribute": "depth"},
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
                "turn_on": {"service": "switch.turn_on", "entity_id": ["switch.ac_ionizer"]},
                "turn_off": {"service": "switch.turn_off", "entity_id": ["switch.ac_ionizer"]},
            },
            "backlight": {
                "state_entity_id": "input_boolean.ac_lighting",
                "turn_on": {"service": "input_boolean.turn_on", "entity_id": ["input_boolean.ac_lighting"]},
                "turn_off": {"service": "input_boolean.turn_off", "entity_id": ["input_boolean.ac_lighting"]},
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
                    "service": "climate.set_temperature",
                    "data": {"temperature": Template("{{ value }}", hass)},
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

    assert entity_config["climate.ac"] == {
        "turn_on": {"data": {"mode": "cool"}, "entity_id": ["climate.ac"], "service": "climate.turn_on"},
    }

    assert entity_config["switch.templates"] == {
        "custom_modes": {"input_source": {"state_template": Template("buz", hass)}},
        "custom_ranges": {"open": {"state_template": Template("foo", hass)}},
        "custom_toggles": {"backlight": {"state_template": Template("bar", hass)}},
    }


async def test_empty_dict_config(hass):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
  entity_config:
"""
    }
    with patch_yaml_files(files):
        config = await async_integration_yaml_config(hass, DOMAIN)

    assert DOMAIN in config
    assert isinstance(config[DOMAIN]["settings"], dict)
    assert config[DOMAIN]["entity_config"] == {}


async def test_reload_no_config_entry(hass, hass_admin_user):
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


async def test_reload_with_config_entry(hass, hass_admin_user, hass_read_only_user, config_entry_direct, caplog):
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


async def test_setup_entry_filters(hass, hass_admin_user):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT},
        options={
            const.CONF_FILTER: {
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
        assert entry_data.should_expose("light.test") is True
        assert entry_data.should_expose("climate.test") is False


async def test_unload_entry(hass, config_entry_direct):
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
    assert entry_data.entry.state == ConfigEntryState.NOT_LOADED


async def test_remove_entry_direct(hass, config_entry_direct):
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1
    await hass.config_entries.async_remove(config_entry_direct.entry_id)
    assert len(component._entry_datas) == 0


async def test_remove_entry_cloud(hass, config_entry_cloud, aioclient_mock, caplog):
    await test_cloud.async_setup_entry(hass, config_entry_cloud, aiohttp_client=aioclient_mock)

    aioclient_mock.delete(f"{cloud.BASE_API_URL}/instance/i-test", status=500)
    await hass.config_entries.async_remove(config_entry_cloud.entry_id)
    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Failed to delete cloud instance, status code: 500"

    aioclient_mock.clear_requests()
    caplog.clear()

    await test_cloud.async_setup_entry(hass, config_entry_cloud, aiohttp_client=aioclient_mock)
    caplog.clear()

    aioclient_mock.delete(f"{cloud.BASE_API_URL}/instance/i-test", status=200)
    await hass.config_entries.async_remove(config_entry_cloud.entry_id)
    (method, url, data, headers) = aioclient_mock.mock_calls[0]
    assert headers == {"Authorization": "Bearer token-foo"}

    assert aioclient_mock.call_count == 1
    assert len(caplog.records) == 0


async def test_remove_entry_direct_unloaded(hass, config_entry_direct):
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_remove(config_entry_direct.entry_id)


async def test_remove_entry_cloud_unloaded(hass, config_entry_cloud, aioclient_mock):
    config_entry_cloud.add_to_hass(hass)

    aioclient_mock.delete(f"{cloud.BASE_API_URL}/instance/i-test", status=200)
    await hass.config_entries.async_remove(config_entry_cloud.entry_id)
    (method, url, data, headers) = aioclient_mock.mock_calls[0]
    assert headers == {"Authorization": "Bearer token-foo"}

    assert aioclient_mock.call_count == 1


async def test_remove_entry_unknown(hass):
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    entry = MockConfigEntry(domain=DOMAIN, version=ConfigFlowHandler.VERSION)
    entry.add_to_hass(hass)

    await hass.config_entries.async_remove(entry.entry_id)


async def test_migrate_entity_v1(hass):
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

    assert entity.version == 3
    assert entity.title == "Yandex Smart Home Test"
    assert entity.data == {
        "cloud_instance": {"id": "foo", "password": "bar", "token": "xxx"},
        "connection_type": "direct",
        "devices_discovered": False,
    }
    assert entity.options == {"filter": {"include_entities": ["switch.ac"]}, "user_id": "user"}

    entity = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="Yandex Smart Home Test",
    )
    entity.add_to_hass(hass)
    await hass.config_entries.async_setup(entity.entry_id)
    await hass.async_block_till_done()

    assert entity.version == 3
    assert entity.title == "Yandex Smart Home Test"
    assert entity.data == {
        "connection_type": "direct",
        "devices_discovered": True,
    }
    assert entity.options == {}


@pytest.mark.parametrize(
    "source_title,connection_type,expected_title",
    [
        ("Yandex Smart Home", "cloud", "Yaha Cloud (12345678)"),
        ("Yandex Smart Home Foo", "cloud", "Yandex Smart Home Foo"),
        ("Foo", "cloud", "Foo"),
        ("Yandex Smart Home", "direct", "YSH: Direct"),
        ("Yandex Smart Home Foo", "direct", "Yandex Smart Home Foo"),
        ("Foo", "direct", "Foo"),
    ],
)
async def test_migrate_entity_v2(hass, source_title, connection_type, expected_title):
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

    assert entry.version == 3
    assert entry.title == expected_title
    assert entry.data == {
        "connection_type": connection_type,
        "cloud_instance": {"id": "1234567890", "password": "bar", "token": "xxx"},
        "bar": "foo",
    }
    assert entry.options == {"foo": "bar"}
    await hass.config_entries.async_unload(entry.entry_id)
