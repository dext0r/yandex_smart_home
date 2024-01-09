from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_ENTITIES
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import ConnectionType, YandexSmartHome, cloud, const
from custom_components.yandex_smart_home.config_flow import DOMAIN, ConfigFlowHandler, config_entry_title
from custom_components.yandex_smart_home.const import EntityFilterSource

from . import test_cloud

COMPONENT_PATH = "custom_components.yandex_smart_home"


def _mock_config_entry(data: ConfigType, options: ConfigType | None = None):
    if data[const.CONF_CONNECTION_TYPE] == ConnectionType.CLOUD:
        data[const.CONF_CLOUD_INSTANCE] = {
            const.CONF_CLOUD_INSTANCE_ID: "test",
            const.CONF_CLOUD_INSTANCE_PASSWORD: "secret",
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
        }

    return MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        title=config_entry_title(data),
        data=data,
        options=dict(
            {
                "filter_source": "config_entry",
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
            **(options or {}),
        ),
    )


async def _async_forward_to_step_include_entites(hass) -> str:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == "form"
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == "form"
    assert result3["step_id"] == "include_entities"

    return result3["flow_id"]


async def test_config_flow_duplicate(hass):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


async def test_config_flow_empty_entities(hass):
    result = await hass.config_entries.flow.async_configure(
        await _async_forward_to_step_include_entites(hass), {CONF_ENTITIES: []}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "include_entities"
    assert result["errors"] == {"base": "entities_not_selected"}


async def test_config_flow_cloud(hass, aioclient_mock):
    test_cloud.mock_client_session(hass, test_cloud.MockSession(aioclient_mock))

    result2 = await hass.config_entries.flow.async_configure(
        await _async_forward_to_step_include_entites(hass),
        {CONF_ENTITIES: ["foo.bar", "script.test"]},
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result3["type"] == "form"
    assert result3["step_id"] == "connection_type"
    assert result3["errors"]["base"] == "cannot_connect"

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result4["type"] == "form"
    assert result4["step_id"] == "connection_type"
    assert result4["errors"]["base"] == "cannot_connect"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{cloud.BASE_API_URL}/instance/register",
        status=202,
        json={"id": "1234567890", "password": "simple", "connection_token": "foo"},
    )

    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    await hass.async_block_till_done()

    assert result5["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result5["title"] == "Yaha Cloud (12345678)"
    assert result5["description"] == "cloud"
    assert result5["data"] == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "1234567890", "password": "simple", "token": "foo"},
        "devices_discovered": False,
    }
    assert result5["options"] == {
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_direct(hass):
    result2 = await hass.config_entries.flow.async_configure(
        await _async_forward_to_step_include_entites(hass), {CONF_ENTITIES: ["foo.bar", "script.test"]}
    )
    assert result2["type"] == "form"
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    await hass.async_block_till_done()

    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result3["title"] == "YSH: Direct"
    assert result3["data"] == {"connection_type": "direct", "devices_discovered": False}
    assert result3["options"] == {
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_direct_filter_source_yaml(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == "form"
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.YAML}
    )
    assert result3["type"] == "form"
    assert result3["step_id"] == "connection_type"

    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    await hass.async_block_till_done()

    assert result4["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result4["title"] == "YSH: Direct"
    assert result4["data"] == {"connection_type": "direct", "devices_discovered": False}
    assert result4["options"] == {"filter_source": "yaml"}

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_options_step_init_cloud(hass):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["expose_settings", "connection_type", "cloud_info", "cloud_settings"]


async def test_options_step_init_direct(hass):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["expose_settings", "connection_type"]


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_step_connection_type_no_change(hass, connection_type):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == connection_type

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: connection_type}
    )
    await hass.async_block_till_done()

    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


async def test_options_step_connection_type_change_to_direct(hass):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD, "foo": "bar"})
    config_entry.add_to_hass(hass)
    assert config_entry.title == "Yaha Cloud (test)"

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == ConnectionType.CLOUD

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    await hass.async_block_till_done()

    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.title == "YSH: Direct"
    assert dict(config_entry.data) == {
        "connection_type": "direct",
        "cloud_instance": {"id": "test", "password": "secret", "token": "foo"},
        "foo": "bar",
    }


async def test_options_step_connection_type_change_to_cloud(hass, aioclient_mock):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    config_entry.add_to_hass(hass)
    assert config_entry.title == "YSH: Direct"

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == ConnectionType.DIRECT

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result3["type"] == "form"
    assert result3["step_id"] == "connection_type"
    assert result3["errors"]["base"] == "cannot_connect"

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
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
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )

    assert result4["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.title == "Yaha Cloud (test)"
    assert dict(config_entry.data) == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "test", "password": "change_to_cloud", "token": "foo"},
    }


async def test_options_step_connection_type_change_to_cloud_again(hass, aioclient_mock):
    config_entry = _mock_config_entry(
        {
            const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT,
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
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "connection_type"
    assert list(result2["data_schema"].schema.keys())[0].default() == ConnectionType.DIRECT

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )

    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.title == "Yaha Cloud (again)"
    assert dict(config_entry.data) == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "again", "password": "secret", "token": "foo"},
    }


async def test_options_step_cloud_info(hass):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "cloud_info"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "cloud_info"
    assert result2["description_placeholders"] == {"id": "test", "password": "secret"}

    result3 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})
    assert result3["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result3["step_id"] == "init"


async def test_options_step_cloud_settings(hass, hass_admin_user):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

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


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_expose_settings(hass, connection_type):
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)
    assert config_entry.options[const.CONF_FILTER_SOURCE] == EntityFilterSource.CONFIG_ENTRY

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={const.CONF_FILTER_SOURCE: EntityFilterSource.YAML}
    )
    assert result3["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        "filter_source": "yaml",
        "filter": {
            "include_domains": ["fan", "humidifier", "vacuum", "media_player", "climate"],
            "include_entities": ["lock.test"],
        },
    }


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_include_entities(hass, connection_type):
    await async_setup_component(hass, DOMAIN, {})

    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    hass.states.async_set("climate.foo", "off")
    hass.states.async_set("fan.foo", "off")
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result3["step_id"] == "include_entities"
    assert list(result3["data_schema"].schema.keys())[0].default() == ["climate.foo", "fan.foo", "lock.test"]

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input={"entities": ["climate.foo", "fan.foo", "lock.test", "script.foo"]}
    )
    assert result4["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        "filter_source": "config_entry",
        "filter": {"include_entities": ["climate.foo", "fan.foo", "lock.test", "script.foo"]},
    }


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_filter_no_entities(hass, connection_type):
    await async_setup_component(hass, DOMAIN, {})

    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result3["step_id"] == "include_entities"

    result4 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"entities": []})
    assert result4["errors"]["base"] == "entities_not_selected"


async def test_config_entry_title_default():
    assert config_entry_title({}) == "Yandex Smart Home"
