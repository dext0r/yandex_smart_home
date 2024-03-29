from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import SOURCE_IGNORE, SOURCE_USER
from homeassistant.const import CONF_ENTITIES, CONF_ID
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import ConnectionType, YandexSmartHome, cloud, const
from custom_components.yandex_smart_home.config_flow import DOMAIN, ConfigFlowHandler, config_entry_title
from custom_components.yandex_smart_home.const import EntityFilterSource

from . import test_cloud

if TYPE_CHECKING:
    from homeassistant.auth.models import User
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

COMPONENT_PATH = "custom_components.yandex_smart_home"


def _mock_config_entry(data: ConfigType, options: ConfigType | None = None) -> MockConfigEntry:
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


async def async_forward_to_step_include_entities(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "include_entities"

    return result3["flow_id"]


async def _async_forward_to_step_update_filter(hass: HomeAssistant) -> FlowResult:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
    )


async def test_config_flow_duplicate(hass: HomeAssistant) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_config_flow_empty_entities(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_configure(
        await async_forward_to_step_include_entities(hass), {CONF_ENTITIES: []}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "include_entities"
    assert result["errors"] == {"base": "entities_not_selected"}


async def test_config_flow_update_filter(hass: HomeAssistant) -> None:
    result = await _async_forward_to_step_update_filter(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "update_filter"
    assert result["errors"] == {"base": "missing_config_entry"}

    entry1 = MockConfigEntry(domain=DOMAIN, title="Mock Entry 1", data={}, options={}, source=SOURCE_IGNORE)
    entry1.add_to_hass(hass)

    result = await _async_forward_to_step_update_filter(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "update_filter"
    assert result["errors"] == {"base": "missing_config_entry"}

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 2",
        data={},
        options={const.CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["switch.foo"]}},
        source=SOURCE_IGNORE,
    )
    entry2.add_to_hass(hass)
    result = await _async_forward_to_step_update_filter(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "update_filter"
    assert result["errors"] is None
    assert result["data_schema"] is not None
    assert len(result["data_schema"].schema.keys()) == 1
    assert [o["label"] for o in result["data_schema"].schema["id"].config["options"]] == ["Mock Entry 2"]

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ID: entry2.entry_id})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "include_entities"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"entities": ["switch.foo"]}

    entry3 = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    entry3.source = SOURCE_IGNORE
    entry3.add_to_hass(hass)

    result = await _async_forward_to_step_update_filter(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "update_filter"
    assert result["errors"] is None
    assert result["data_schema"] is not None
    assert len(result["data_schema"].schema.keys()) == 1
    assert [o["label"] for o in result["data_schema"].schema["id"].config["options"]] == ["Mock Entry 2", "YSH: Direct"]

    hass.states.async_set("climate.foo", "off")
    hass.states.async_set("fan.foo", "off")
    await hass.async_block_till_done()

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ID: entry3.entry_id})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "include_entities"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"entities": ["climate.foo", "fan.foo", "lock.test"]}


async def test_config_flow_cloud(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    test_cloud.mock_client_session(hass, test_cloud.MockSession(aioclient_mock))

    result2 = await hass.config_entries.flow.async_configure(
        await async_forward_to_step_include_entities(hass),
        {CONF_ENTITIES: ["foo.bar", "script.test"]},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "connection_type"
    assert result3["errors"] == {"base": "cannot_connect"}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result4["type"] == FlowResultType.FORM
    assert result4["step_id"] == "connection_type"
    assert result4["errors"] == {"base": "cannot_connect"}

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

    assert result5["type"] == FlowResultType.CREATE_ENTRY
    assert result5["title"] == "Yaha Cloud (12345678)"
    assert result5["description"] == "cloud"
    assert result5["data"] == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "1234567890", "password": "simple", "token": "foo"},
        "devices_discovered": False,
    }
    assert result5["options"] == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_direct(hass: HomeAssistant) -> None:
    result2 = await hass.config_entries.flow.async_configure(
        await async_forward_to_step_include_entities(hass), {CONF_ENTITIES: ["foo.bar", "script.test"]}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"
    assert result2["errors"] == {}

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"] == "YSH: Direct"
    assert result3["data"] == {"connection_type": "direct", "devices_discovered": False}
    assert result3["options"] == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_direct_filter_source_yaml(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.YAML}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "connection_type"

    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    await hass.async_block_till_done()

    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert result4["title"] == "YSH: Direct"
    assert result4["data"] == {"connection_type": "direct", "devices_discovered": False}
    assert result4["options"] == {"entry_aliases": True, "filter_source": "yaml"}

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_options_step_init_cloud(hass: HomeAssistant) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["expose_settings", "connection_type", "cloud_info", "context_user"]


async def test_options_step_init_direct(hass: HomeAssistant) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["expose_settings", "connection_type"]


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_step_connection_type_no_change(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"connection_type": connection_type}

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: connection_type}
    )
    await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY


async def test_options_step_connection_type_change_to_direct(hass: HomeAssistant) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD, "foo": "bar"})
    config_entry.add_to_hass(hass)
    assert config_entry.title == "Yaha Cloud (test)"

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"connection_type": ConnectionType.CLOUD}

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.title == "YSH: Direct"
    assert config_entry.data == {
        "connection_type": "direct",
        "cloud_instance": {"id": "test", "password": "secret", "token": "foo"},
        "foo": "bar",
    }


async def test_options_step_connection_type_change_to_cloud(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    config_entry.add_to_hass(hass)
    assert config_entry.title == "YSH: Direct"

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"connection_type": ConnectionType.DIRECT}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "connection_type"
    assert result3["errors"] == {"base": "cannot_connect"}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result4["type"] == FlowResultType.FORM
    assert result4["step_id"] == "connection_type"
    assert result4["errors"] == {"base": "cannot_connect"}

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{cloud.BASE_API_URL}/instance/register",
        status=202,
        json={"id": "test", "password": "change_to_cloud", "connection_token": "foo"},
    )
    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )

    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.title == "Yaha Cloud (test)"
    assert config_entry.data == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "test", "password": "change_to_cloud", "token": "foo"},
    }


async def test_options_step_connection_type_change_to_cloud_again(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
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
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "connection_type"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"connection_type": ConnectionType.DIRECT}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.title == "Yaha Cloud (again)"
    assert config_entry.data == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "again", "password": "secret", "token": "foo"},
    }


async def test_options_step_cloud_info(hass: HomeAssistant) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "cloud_info"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "cloud_info"
    assert result2["description_placeholders"] == {"id": "test", "password": "secret"}

    result3 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})
    assert result3["type"] == FlowResultType.MENU
    assert result3["step_id"] == "init"


async def test_options_step_contex_user(hass: HomeAssistant, hass_admin_user: User) -> None:
    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "context_user"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "context_user"
    assert result2["data_schema"] is not None
    assert len(result2["data_schema"].schema["user_id"].config["options"]) == 2

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={"user_id": hass_admin_user.id}
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options["user_id"] == hass_admin_user.id


async def test_options_step_contex_user_clear(hass: HomeAssistant, hass_admin_user: User) -> None:
    config_entry = _mock_config_entry(
        data={const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}, options={const.CONF_USER_ID: "foo"}
    )
    config_entry.add_to_hass(hass)
    assert "user_id" in config_entry.options

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "context_user"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "context_user"
    assert result2["data_schema"] is not None
    assert len(result2["data_schema"].schema["user_id"].config["options"]) == 2
    assert result2["data_schema"].schema["user_id"].config["options"][1]["value"] == hass_admin_user.id

    result3 = await hass.config_entries.options.async_configure(result2["flow_id"], user_input={"user_id": "none"})
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert "user_id" not in config_entry.options


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_expose_settings(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    config_entry = _mock_config_entry(
        data={const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD}, options={const.CONF_ENTRY_ALIASES: False}
    )
    config_entry.add_to_hass(hass)
    assert config_entry.options[const.CONF_FILTER_SOURCE] == EntityFilterSource.CONFIG_ENTRY
    assert config_entry.options[const.CONF_ENTRY_ALIASES] is False

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={const.CONF_FILTER_SOURCE: EntityFilterSource.YAML, const.CONF_ENTRY_ALIASES: True},
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        "entry_aliases": True,
        "filter_source": "yaml",
        "filter": {
            "include_domains": ["fan", "humidifier", "vacuum", "media_player", "climate"],
            "include_entities": ["lock.test"],
        },
    }


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_update_filter(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    await async_setup_component(hass, DOMAIN, {})

    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "update_filter"
    assert result3["errors"] == {"base": "missing_config_entry"}

    entry1 = MockConfigEntry(domain=DOMAIN, title="Mock Entry 1", data={}, options={}, source=SOURCE_IGNORE)
    entry1.add_to_hass(hass)

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
    )
    assert result4["type"] == FlowResultType.FORM
    assert result4["step_id"] == "update_filter"
    assert result4["errors"] == {"base": "missing_config_entry"}

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 2",
        data={},
        options={const.CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["switch.foo"]}},
        source=SOURCE_IGNORE,
    )
    entry2.add_to_hass(hass)
    result5 = await hass.config_entries.options.async_configure(
        result4["flow_id"], {const.CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
    )
    assert result5["type"] == FlowResultType.FORM
    assert result5["step_id"] == "update_filter"
    assert result5["errors"] is None
    assert result5["data_schema"] is not None
    assert len(result5["data_schema"].schema.keys()) == 1
    assert [o["label"] for o in result5["data_schema"].schema["id"].config["options"]] == ["Mock Entry 2"]

    result6 = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_ID: entry2.entry_id})
    assert result6["type"] == FlowResultType.FORM
    assert result6["step_id"] == "include_entities"
    assert result6["data_schema"] is not None
    assert result6["data_schema"]({}) == {"entities": ["switch.foo"]}
    entities = result6["data_schema"]({})["entities"]

    result7 = await hass.config_entries.options.async_configure(
        result6["flow_id"], user_input={CONF_ENTITIES: entities}
    )
    assert result7["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["switch.foo"]},
    }


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_include_entities(hass: HomeAssistant, connection_type: HomeAssistant) -> None:
    await async_setup_component(hass, DOMAIN, {})

    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    hass.states.async_set("climate.foo", "off")
    hass.states.async_set("fan.foo", "off")
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "include_entities"
    assert result3["data_schema"] is not None
    assert result3["data_schema"]({}) == {"entities": ["climate.foo", "fan.foo", "lock.test"]}

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], user_input={"entities": ["climate.foo", "fan.foo", "lock.test", "script.foo"]}
    )
    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["climate.foo", "fan.foo", "lock.test", "script.foo"]},
    }


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_filter_no_entities(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    await async_setup_component(hass, DOMAIN, {})

    config_entry = _mock_config_entry({const.CONF_CONNECTION_TYPE: connection_type})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "expose_settings"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "include_entities"

    result4 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"entities": []})
    assert result4["errors"] == {"base": "entities_not_selected"}


async def test_config_entry_title_default() -> None:
    assert config_entry_title({}) == "Yandex Smart Home"
