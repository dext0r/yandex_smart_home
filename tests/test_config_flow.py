from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.components import http
from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.const import CONF_ENTITIES
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch_yaml_files

from custom_components.yandex_smart_home import async_setup, cloud, const
from custom_components.yandex_smart_home.config_flow import DOMAIN

COMPONENT_PATH = "custom_components.yandex_smart_home"


@pytest.fixture
async def setup(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    await async_setup(hass, {})


def _mock_config_entry_with_options_populated(data: dict):
    if data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
        data[const.CONF_CLOUD_INSTANCE] = {
            const.CONF_CLOUD_INSTANCE_ID: "test",
            const.CONF_CLOUD_INSTANCE_PASSWORD: "secret",
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
        }

    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options={
            "filter": {
                "include_domains": [
                    "fan",
                    "humidifier",
                    "vacuum",
                    "media_player",
                    "climate",
                ],
                "include_entities": ["lock.test"],
            },
        },
    )


async def test_config_flow_duplicate(hass, setup):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


async def test_config_flow_empty_entities(hass, setup, aioclient_mock):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "include_entities"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ENTITIES: []})
    assert result2["type"] == "form"
    assert result2["step_id"] == "include_entities"
    assert result2["errors"] == {"base": "entities_not_selected"}


async def test_config_flow_cloud(hass, setup, aioclient_mock):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "include_entities"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITIES: ["foo.bar", "script.test"]}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
    )
    assert result3["type"] == "form"
    assert result3["step_id"] == "connection_type"
    assert result3["errors"]["base"] == "cannot_connect"

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
    )
    assert result4["type"] == "form"
    assert result4["step_id"] == "connection_type"
    assert result4["errors"]["base"] == "cannot_connect"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{cloud.BASE_API_URL}/instance/register",
        status=202,
        json={"id": "test", "password": "simple", "connection_token": "foo"},
    )

    with patch(f"{COMPONENT_PATH}.async_setup", return_value=True) as mock_setup, patch(
        f"{COMPONENT_PATH}.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result5 = await hass.config_entries.flow.async_configure(
            result4["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
        )
        await hass.async_block_till_done()

        assert result5["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result5["description"] == "cloud"
        assert result5["data"] == {
            "connection_type": "cloud",
            "devices_discovered": False,
            "cloud_instance": {"id": "test", "password": "simple", "token": "foo"},
        }
        assert result5["options"] == {
            "cloud_stream": True,
            "beta": False,
            "pressure_unit": "mmHg",
            "filter": {"include_entities": ["foo.bar", "script.test"]},
        }
        mock_setup.assert_called_once()
        mock_setup_entry.assert_called_once()


async def test_config_flow_direct(hass, setup):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "include_entities"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITIES: ["foo.bar", "script.test"]}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    with patch(f"{COMPONENT_PATH}.async_setup", return_value=True) as mock_setup, patch(
        f"{COMPONENT_PATH}.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT}
        )
        await hass.async_block_till_done()

        assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result3["data"] == {"connection_type": "direct", "devices_discovered": False}
        assert result3["options"] == {
            "beta": False,
            "pressure_unit": "mmHg",
            "cloud_stream": False,
            "filter": {"include_entities": ["foo.bar", "script.test"]},
        }

        mock_setup.assert_called_once()
        mock_setup_entry.assert_called_once()


async def test_config_flow_with_yaml_no_filter(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch_yaml_files(
        {
            YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
    beta: true
    cloud_stream: true"""
        }
    ):
        await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "include_entities"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITIES: ["foo.bar", "script.test"]}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    with patch(f"{COMPONENT_PATH}.async_setup", return_value=True) as mock_setup, patch(
        f"{COMPONENT_PATH}.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT}
        )
        await hass.async_block_till_done()

        assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result3["data"] == {
            "connection_type": "direct",
            "devices_discovered": False,
            "notifier": [],
            "yaml_config_hash": "ada8341a9ec9194c4091b8ac15867ff4",
        }
        assert result3["options"] == {
            "beta": True,
            "pressure_unit": "mmHg",
            "cloud_stream": True,
            "color_profile": {},
            "filter": {"include_entities": ["foo.bar", "script.test"]},
        }

        mock_setup.assert_called_once()
        mock_setup_entry.assert_called_once()


async def test_config_flow_with_yaml_filter(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch_yaml_files(
        {
            YAML_CONFIG_FILE: """
yandex_smart_home:
  filter:
    include_domains:
      - script"""
        }
    ):
        await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] == "form"
        assert result["step_id"] == "filter_yaml"

        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        assert result2["type"] == "form"
        assert result2["step_id"] == "connection_type"
        assert result2["errors"] == {}

        with patch(f"{COMPONENT_PATH}.async_setup", return_value=True) as mock_setup, patch(
            f"{COMPONENT_PATH}.async_setup_entry", return_value=True
        ) as mock_setup_entry:
            result3 = await hass.config_entries.flow.async_configure(
                result["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT}
            )
            await hass.async_block_till_done()

            assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result3["data"] == {
                "connection_type": "direct",
                "devices_discovered": False,
                "notifier": [],
                "yaml_config_hash": "4ea38d1f0319e1e44a5321e2cb41d360",
            }
            assert result3["options"] == {
                "beta": False,
                "pressure_unit": "mmHg",
                "cloud_stream": False,
                "color_profile": {},
            }

            mock_setup.assert_called_once()
            mock_setup_entry.assert_called_once()


async def test_options_step_init_cloud(hass, setup):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == ["include_entities", "connection_type", "cloud_info", "cloud_settings"]


async def test_options_step_init_direct(hass, setup):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"
    assert result["menu_options"] == ["include_entities", "connection_type"]


@pytest.mark.parametrize("connection_type", [const.CONNECTION_TYPE_CLOUD, const.CONNECTION_TYPE_DIRECT])
async def test_options_step_connection_type_no_change(hass, setup, connection_type):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: connection_type,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == connection_type

    with patch(f"{COMPONENT_PATH}.async_setup", return_value=True) as mock_setup, patch(
        f"{COMPONENT_PATH}.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result3 = await hass.config_entries.options.async_configure(
            result2["flow_id"], {const.CONF_CONNECTION_TYPE: connection_type}
        )
        await hass.async_block_till_done()

        assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        mock_setup.assert_not_called()
        mock_setup_entry.assert_not_called()


async def test_options_step_connection_type_change_to_direct(hass, setup):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == const.CONNECTION_TYPE_CLOUD

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT}
    )
    await hass.async_block_till_done()

    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert dict(config_entry.data) == {
        "connection_type": "direct",
        "cloud_instance": {"id": "test", "password": "secret", "token": "foo"},
        "devices_discovered": True,
    }


async def test_options_step_connection_type_change_to_cloud(hass, setup, aioclient_mock):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == const.CONNECTION_TYPE_DIRECT

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
    )
    assert result3["type"] == "form"
    assert result3["step_id"] == "connection_type"
    assert result3["errors"]["base"] == "cannot_connect"

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
    )
    assert result4["type"] == "form"
    assert result4["step_id"] == "connection_type"
    assert result4["errors"]["base"] == "cannot_connect"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{cloud.BASE_API_URL}/instance/register",
        status=202,
        json={"id": "test", "password": "change_to_cloud", "connection_token": "foo"},
    )
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
    )

    assert result4["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert dict(config_entry.data) == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "test", "password": "change_to_cloud", "token": "foo"},
        "devices_discovered": True,
    }


async def test_options_step_connection_type_change_to_cloud_again(hass, setup, aioclient_mock):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "again",
                const.CONF_CLOUD_INSTANCE_PASSWORD: "secret",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
            },
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == const.CONNECTION_TYPE_DIRECT

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD}
    )

    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert dict(config_entry.data) == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "again", "password": "secret", "token": "foo"},
        "devices_discovered": True,
    }


async def test_options_step_cloud_info(hass, setup):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "cloud_info"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "cloud_info"
    assert result2["description_placeholders"] == {"id": "test", "password": "secret"}

    result3 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})
    assert result3["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result3["step_id"] == "menu"


async def test_options_step_cloud_settings(hass, setup, hass_admin_user):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "cloud_settings"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "cloud_settings"
    assert len(result2["data_schema"].schema["user_id"].container) == 1

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={"user_id": hass_admin_user.id}
    )
    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options["user_id"] == hass_admin_user.id
    assert "filter" in config_entry.options


async def test_options_step_include_entities_with_yaml_filters(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch_yaml_files(
        {
            YAML_CONFIG_FILE: """
yandex_smart_home:
  filter:
    include_domains:
      - script"""
        }
    ):
        await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))

    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "include_entities"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "filter_yaml"

    result3 = await hass.config_entries.options.async_configure(result2["flow_id"], user_input={})
    assert result3["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result3["step_id"] == "menu"


@pytest.mark.parametrize("connection_type", [const.CONNECTION_TYPE_CLOUD, const.CONNECTION_TYPE_DIRECT])
async def test_options_flow_include_entities(hass, setup, connection_type):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: connection_type,
        }
    )
    config_entry.add_to_hass(hass)

    hass.states.async_set("climate.foo", "off")
    hass.states.async_set("fan.foo", "off")
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "include_entities"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "include_entities"
    assert list(result2["data_schema"].schema.keys())[0].default() == ["climate.foo", "fan.foo", "lock.test"]

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={"entities": ["climate.foo", "fan.foo", "lock.test", "script.foo"]}
    )
    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        "filter": {"include_entities": ["climate.foo", "fan.foo", "lock.test", "script.foo"]},
    }


@pytest.mark.parametrize("connection_type", [const.CONNECTION_TYPE_CLOUD, const.CONNECTION_TYPE_DIRECT])
async def test_options_flow_filter_no_entities(hass, setup, connection_type):
    config_entry = _mock_config_entry_with_options_populated(
        {
            const.CONF_CONNECTION_TYPE: connection_type,
        }
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "menu"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "include_entities"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "include_entities"

    result3 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"entities": []})
    assert result3["errors"]["base"] == "entities_not_selected"
