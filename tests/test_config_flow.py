from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from homeassistant.components import http
from homeassistant.config_entries import SOURCE_IGNORE, SOURCE_USER
from homeassistant.const import CONF_ENTITIES, CONF_ID, CONF_NAME, CONF_PLATFORM, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.yandex_smart_home import ConnectionType, SmartHomePlatform, YandexSmartHome, cloud
from custom_components.yandex_smart_home.config_flow import DOMAIN, ConfigFlowHandler, async_config_entry_title
from custom_components.yandex_smart_home.const import (
    CLOUD_BASE_URL,
    CONF_CLOUD_INSTANCE,
    CONF_CLOUD_INSTANCE_CONNECTION_TOKEN,
    CONF_CLOUD_INSTANCE_ID,
    CONF_CLOUD_INSTANCE_PASSWORD,
    CONF_CONNECTION_TYPE,
    CONF_ENTRY_ALIASES,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_LINKED_PLATFORMS,
    CONF_SKILL,
    CONF_USER_ID,
    EntityFilterSource,
)
from custom_components.yandex_smart_home.http import YandexSmartHomeUnauthorizedView

from . import test_cloud

try:
    from homeassistant.core_config import async_process_ha_core_config
except ImportError:
    from homeassistant.config import async_process_ha_core_config  # type: ignore[attr-defined, no-redef]


if TYPE_CHECKING:
    from homeassistant.auth.models import User
    from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def _async_mock_config_entry(
    hass: HomeAssistant, data: ConfigType, options: ConfigType | None = None
) -> MockConfigEntry:
    if data[CONF_CONNECTION_TYPE] in [ConnectionType.CLOUD, ConnectionType.CLOUD_PLUS]:
        data[CONF_CLOUD_INSTANCE] = {
            CONF_CLOUD_INSTANCE_ID: "test",
            CONF_CLOUD_INSTANCE_PASSWORD: "secret",
            CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
        }
        if data[CONF_CONNECTION_TYPE] == ConnectionType.CLOUD_PLUS:
            data.setdefault(CONF_PLATFORM, SmartHomePlatform.YANDEX)
    else:
        data.setdefault(CONF_CONNECTION_TYPE, ConnectionType.DIRECT)
        data.setdefault(CONF_PLATFORM, SmartHomePlatform.YANDEX)

    return MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        title=await async_config_entry_title(hass, data, options or {}),
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


async def _async_forward_to_step_skill_yandex(hass: HomeAssistant) -> ConfigFlowResult:
    await async_process_ha_core_config(hass, {"external_url": "https://example.com"})

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "platform_direct"

    result4 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PLATFORM: SmartHomePlatform.YANDEX}
    )
    assert result4["type"] == FlowResultType.FORM
    assert result4["step_id"] == "skill_yandex_direct"
    assert result4["description_placeholders"] == {"external_url": "https://example.com"}
    return result4


async def _async_forward_to_step_expose_settings(hass: HomeAssistant, user: User) -> ConfigFlowResult:
    result = await hass.config_entries.flow.async_configure(
        (await _async_forward_to_step_skill_yandex(hass))["flow_id"],
        {CONF_ID: "foo", CONF_TOKEN: "foo", CONF_USER_ID: user.id},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "expose_settings"
    return result


async def _async_forward_to_step_include_entities(hass: HomeAssistant, user: User) -> ConfigFlowResult:
    result = await hass.config_entries.flow.async_configure(
        (await _async_forward_to_step_expose_settings(hass, user))["flow_id"],
        {CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "include_entities"
    return result


async def _async_forward_to_step_update_filter(hass: HomeAssistant, user: User) -> ConfigFlowResult:
    result = await hass.config_entries.flow.async_configure(
        (await _async_forward_to_step_expose_settings(hass, user))["flow_id"],
        {CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "update_filter"
    return result


async def _async_forward_to_step_maintenance(hass: HomeAssistant, config_entry: ConfigEntry) -> ConfigFlowResult:
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "maintenance"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "maintenance"
    return result2


async def test_config_flow_empty_entities(hass: HomeAssistant, hass_admin_user: User) -> None:
    result = await hass.config_entries.flow.async_configure(
        (await _async_forward_to_step_include_entities(hass, hass_admin_user))["flow_id"],
        {CONF_ENTITIES: []},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "include_entities"
    assert result["errors"] == {"base": "entities_not_selected"}


async def test_config_flow_update_filter(hass: HomeAssistant, hass_admin_user: User) -> None:
    result = await _async_forward_to_step_update_filter(hass, hass_admin_user)
    assert result["errors"] == {"base": "missing_config_entry"}

    entry1 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 1",
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={},
        source=SOURCE_IGNORE,
    )
    entry1.add_to_hass(hass)

    result = await _async_forward_to_step_update_filter(hass, hass_admin_user)
    assert result["errors"] == {"base": "missing_config_entry"}

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 2",
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["switch.foo"]}},
        source=SOURCE_IGNORE,
    )
    entry2.add_to_hass(hass)
    result = await _async_forward_to_step_update_filter(hass, hass_admin_user)
    assert result["errors"] is None
    assert result["data_schema"] is not None
    assert len(result["data_schema"].schema.keys()) == 1
    assert [o["label"] for o in result["data_schema"].schema["id"].config["options"]] == ["Mock Entry 2"]

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ID: entry2.entry_id})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "include_entities"
    assert result2["data_schema"] is not None
    assert result2["data_schema"]({}) == {"entities": ["switch.foo"]}

    entry3 = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: ConnectionType.DIRECT})
    entry3.source = SOURCE_IGNORE
    entry3.add_to_hass(hass)

    result = await _async_forward_to_step_update_filter(hass, hass_admin_user)
    assert result["errors"] is None
    assert result["data_schema"] is not None
    assert len(result["data_schema"].schema.keys()) == 1
    assert [o["label"] for o in result["data_schema"].schema["id"].config["options"]] == [
        "Mock Entry 2",
        "Yandex Smart Home: Direct",
    ]

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

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "connection_type"
    assert result3["errors"] == {"base": "cannot_connect"}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
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
        result4["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.CLOUD}
    )
    await hass.async_block_till_done()

    assert result5["type"] == FlowResultType.FORM
    assert result5["step_id"] == "expose_settings"

    result6 = await hass.config_entries.flow.async_configure(
        result5["flow_id"], {CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result6["type"] == FlowResultType.FORM
    assert result6["step_id"] == "include_entities"

    result7 = await hass.config_entries.flow.async_configure(
        result6["flow_id"],
        {CONF_ENTITIES: ["foo.bar", "script.test"]},
    )

    assert result7["type"] == FlowResultType.CREATE_ENTRY
    assert result7["title"] == "Yaha Cloud (12345678)"
    assert result7["description"] == "cloud"
    assert result7["data"] == {
        "connection_type": "cloud",
        "cloud_instance": {"id": "1234567890", "password": "simple", "token": "foo"},
    }
    assert result7["options"] == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_cloud_plus_yandex(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    test_cloud.mock_client_session(hass, test_cloud.MockSession(aioclient_mock))

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", status=500)
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.CLOUD_PLUS}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "connection_type"
    assert result3["errors"] == {"base": "cannot_connect"}

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/register", side_effect=Exception())
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.CLOUD_PLUS}
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
        result4["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.CLOUD_PLUS}
    )
    await hass.async_block_till_done()

    assert result5["type"] == FlowResultType.FORM
    assert result5["step_id"] == "platform_cloud_plus"

    result6 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PLATFORM: SmartHomePlatform.YANDEX}
    )
    assert result6["type"] == FlowResultType.FORM
    assert result6["step_id"] == "skill_yandex_cloud_plus"
    assert result6["description_placeholders"] == {"cloud_base_url": CLOUD_BASE_URL, "instance_id": "1234567890"}

    result7 = await hass.config_entries.flow.async_configure(
        result6["flow_id"],
        {
            CONF_NAME: "buz",
            CONF_ID: "c8f46d6c-ee32-4022-a286-91e8c208ed0b",
            CONF_TOKEN: "bar",
        },
    )
    assert result7["type"] == FlowResultType.FORM
    assert result7["step_id"] == "expose_settings"

    result8 = await hass.config_entries.flow.async_configure(
        result7["flow_id"], {CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result8["type"] == FlowResultType.FORM
    assert result8["step_id"] == "include_entities"

    result9 = await hass.config_entries.flow.async_configure(
        result8["flow_id"],
        {CONF_ENTITIES: ["foo.bar", "script.test"]},
    )

    assert result9["type"] == FlowResultType.CREATE_ENTRY
    assert result9["title"] == "Yandex Smart Home: Cloud Plus (c8f46d6c)"
    assert result9["description"] == "cloud_plus"
    assert result9["data"] == {
        "connection_type": "cloud_plus",
        "platform": "yandex",
        "cloud_instance": {"id": "1234567890", "password": "simple", "token": "foo"},
    }
    assert result9["options"] == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
        "skill": {"name": "buz", "id": "c8f46d6c-ee32-4022-a286-91e8c208ed0b", "token": "bar"},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_direct_missing_external_url(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "connection_type"

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: ConnectionType.DIRECT}
    )
    assert result3["type"] == FlowResultType.ABORT
    assert result3["reason"] == "missing_external_url"


async def test_config_flow_direct_duplicate_skill(
    hass: HomeAssistant, hass_admin_user: User, hass_owner_user: User
) -> None:
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 1",
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_SKILL: {
                CONF_ID: "id1",
                CONF_TOKEN: "token",
                CONF_USER_ID: hass_admin_user.id,
            }
        },
        source=SOURCE_IGNORE,
    )
    entry1.add_to_hass(hass)

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 2",
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: "foo"},
        options={
            CONF_SKILL: {
                CONF_ID: "id1",
                CONF_TOKEN: "token",
                CONF_USER_ID: hass_owner_user.id,
            }
        },
        source=SOURCE_IGNORE,
    )
    entry2.add_to_hass(hass)

    result = await _async_forward_to_step_skill_yandex(hass)
    assert result["data_schema"] is not None
    assert [o["value"] for o in result["data_schema"].schema["user_id"].config["options"]] == [
        hass_admin_user.id,
        hass_owner_user.id,
    ]

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ID: "id1",
            CONF_TOKEN: "bar",
            CONF_USER_ID: hass_admin_user.id,
        },
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "skill_yandex_direct"
    assert result2["errors"] == {"base": "already_configured"}

    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ID: "id1",
            CONF_TOKEN: "bar",
            CONF_USER_ID: hass_owner_user.id,
        },
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "expose_settings"


async def test_config_flow_direct_yandex(
    hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator, hass_admin_user: User
) -> None:
    await async_setup_component(hass, http.DOMAIN, {})
    http_client = await hass_client_no_auth()

    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTPStatus.NOT_FOUND

    result = await _async_forward_to_step_skill_yandex(hass)
    assert result["data_schema"] is not None
    assert [o["label"] for o in result["data_schema"].schema["user_id"].config["options"]] == ["Mock User"]

    response = await http_client.head(YandexSmartHomeUnauthorizedView.url)
    assert response.status == HTTPStatus.OK

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ID: "c8f46d6c-ee32-4022-a286-91e8c208ed0b",
            CONF_TOKEN: "bar",
            CONF_USER_ID: hass_admin_user.id,
        },
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "expose_settings"

    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "include_entities"

    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"], {CONF_ENTITIES: ["foo.bar", "script.test"]}
    )
    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert result4["description"] == "direct"
    assert result4["title"] == "Yandex Smart Home: Direct (Mock User / c8f46d6c)"
    assert result4["data"] == {"connection_type": "direct", "platform": "yandex"}
    assert result4["options"] == {
        "entry_aliases": True,
        "filter_source": "config_entry",
        "filter": {"include_entities": ["foo.bar", "script.test"]},
        "skill": {
            "id": "c8f46d6c-ee32-4022-a286-91e8c208ed0b",
            "token": "bar",
            "user_id": hass_admin_user.id,
        },
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_config_flow_direct_filter_source_yaml(hass: HomeAssistant, hass_admin_user: User) -> None:
    result = await hass.config_entries.flow.async_configure(
        (await _async_forward_to_step_expose_settings(hass, hass_admin_user))["flow_id"],
        {CONF_FILTER_SOURCE: EntityFilterSource.YAML},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Yandex Smart Home: Direct (Mock User / foo)"
    assert result["data"] == {"connection_type": "direct", "platform": "yandex"}
    assert result["options"] == {
        "entry_aliases": True,
        "filter_source": "yaml",
        "skill": {"id": "foo", "token": "foo", "user_id": hass_admin_user.id},
    }

    component: YandexSmartHome = hass.data[DOMAIN]
    assert len(component._entry_datas) == 1


async def test_options_step_init_cloud(hass: HomeAssistant) -> None:
    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["expose_settings", "cloud_credentials", "context_user", "maintenance"]


@pytest.mark.parametrize("platform", [SmartHomePlatform.YANDEX])
async def test_options_step_init_cloud_plus(hass: HomeAssistant, platform: SmartHomePlatform) -> None:
    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: ConnectionType.CLOUD_PLUS})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == [
        "expose_settings",
        "cloud_credentials",
        f"skill_{platform}_cloud_plus",
        "context_user",
        "maintenance",
    ]


@pytest.mark.parametrize("platform", [SmartHomePlatform.YANDEX])
async def test_options_step_init_direct(hass: HomeAssistant, platform: SmartHomePlatform) -> None:
    config_entry = await _async_mock_config_entry(
        hass, data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: platform}
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == ["expose_settings", f"skill_{platform}_direct", "maintenance"]


async def test_options_step_cloud_credentinals(hass: HomeAssistant) -> None:
    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "cloud_credentials"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "cloud_credentials"
    assert result2["description_placeholders"] == {"skill": "Yaha Cloud", "id": "test", "password": "secret"}

    result3 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})
    assert result3["type"] == FlowResultType.MENU
    assert result3["step_id"] == "init"


async def test_options_step_cloud_credentinals_plus(hass: HomeAssistant) -> None:
    config_entry = await _async_mock_config_entry(
        hass,
        data={CONF_CONNECTION_TYPE: ConnectionType.CLOUD_PLUS},
        options={CONF_SKILL: {CONF_NAME: "foo"}},
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "cloud_credentials"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "cloud_credentials"
    assert result2["description_placeholders"] == {"skill": "foo", "id": "test", "password": "secret"}

    result3 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={})
    assert result3["type"] == FlowResultType.MENU
    assert result3["step_id"] == "init"


async def test_options_step_contex_user(hass: HomeAssistant, hass_admin_user: User, hass_read_only_user: User) -> None:
    assert hass_read_only_user

    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
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
    assert [o["value"] for o in result2["data_schema"].schema["user_id"].config["options"]] == [
        "none",
        hass_admin_user.id,
    ]

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={"user_id": hass_admin_user.id}
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options["user_id"] == hass_admin_user.id


async def test_options_step_contex_user_clear(hass: HomeAssistant, hass_admin_user: User) -> None:
    config_entry = await _async_mock_config_entry(
        hass,
        data={CONF_CONNECTION_TYPE: ConnectionType.CLOUD},
        options={CONF_USER_ID: "foo"},
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
    assert [o["value"] for o in result2["data_schema"].schema["user_id"].config["options"]] == [
        "none",
        hass_admin_user.id,
    ]

    result3 = await hass.config_entries.options.async_configure(result2["flow_id"], user_input={"user_id": "none"})
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert "user_id" not in config_entry.options


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.DIRECT])
async def test_options_flow_expose_settings(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    config_entry = await _async_mock_config_entry(
        hass,
        data={CONF_CONNECTION_TYPE: ConnectionType.CLOUD},
        options={CONF_ENTRY_ALIASES: False},
    )
    config_entry.add_to_hass(hass)
    assert config_entry.options[CONF_FILTER_SOURCE] == EntityFilterSource.CONFIG_ENTRY
    assert config_entry.options[CONF_ENTRY_ALIASES] is False

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
        user_input={CONF_FILTER_SOURCE: EntityFilterSource.YAML, CONF_ENTRY_ALIASES: True},
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

    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: connection_type})
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
        result2["flow_id"], {CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "update_filter"
    assert result3["errors"] == {"base": "missing_config_entry"}

    entry1 = MockConfigEntry(domain=DOMAIN, title="Mock Entry 1", data={}, options={}, source=SOURCE_IGNORE)
    entry1.add_to_hass(hass)

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"], {CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
    )
    assert result4["type"] == FlowResultType.FORM
    assert result4["step_id"] == "update_filter"
    assert result4["errors"] == {"base": "missing_config_entry"}

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Entry 2",
        data={},
        options={CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["switch.foo"]}},
        source=SOURCE_IGNORE,
    )
    entry2.add_to_hass(hass)
    result5 = await hass.config_entries.options.async_configure(
        result4["flow_id"], {CONF_FILTER_SOURCE: EntityFilterSource.GET_FROM_CONFIG_ENTRY}
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
async def test_options_flow_include_entities(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    await async_setup_component(hass, DOMAIN, {})

    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: connection_type})
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
        result2["flow_id"], user_input={CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
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

    config_entry = await _async_mock_config_entry(hass, {CONF_CONNECTION_TYPE: connection_type})
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
        result2["flow_id"], user_input={CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY}
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "include_entities"

    result4 = await hass.config_entries.options.async_configure(result["flow_id"], user_input={"entities": []})
    assert result4["errors"] == {"base": "entities_not_selected"}


@pytest.mark.parametrize("platform", [SmartHomePlatform.YANDEX])
async def test_options_flow_skill_missing_external_url(hass: HomeAssistant, platform: SmartHomePlatform) -> None:
    config_entry = await _async_mock_config_entry(
        hass, data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: platform}
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": f"skill_{platform}_direct"}
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "missing_external_url"


@pytest.mark.parametrize(
    "attr_to_change,expect_unlink",
    [
        (CONF_ID, True),
        (CONF_TOKEN, False),
        (CONF_USER_ID, True),
    ],
)
async def test_options_flow_skill_yandex_direct(
    hass: HomeAssistant, hass_admin_user: User, hass_owner_user: User, attr_to_change: str, expect_unlink: bool
) -> None:
    await async_process_ha_core_config(hass, {"external_url": "https://example.com"})

    skill = {CONF_ID: "foo", CONF_TOKEN: "token", CONF_USER_ID: hass_admin_user.id}
    config_entry = await _async_mock_config_entry(
        hass,
        data={
            CONF_CONNECTION_TYPE: ConnectionType.DIRECT,
            CONF_PLATFORM: SmartHomePlatform.YANDEX,
            CONF_LINKED_PLATFORMS: [SmartHomePlatform.YANDEX],
        },
        options={CONF_SKILL: skill.copy()},
    )
    config_entry.add_to_hass(hass)
    assert config_entry.title == "Yandex Smart Home: Direct (Mock User / foo)"

    config_entry_dup = await _async_mock_config_entry(
        hass,
        data={
            CONF_CONNECTION_TYPE: ConnectionType.DIRECT,
            CONF_PLATFORM: SmartHomePlatform.YANDEX,
            CONF_LINKED_PLATFORMS: [SmartHomePlatform.YANDEX],
        },
        options={CONF_SKILL: skill.copy()},
    )
    config_entry_dup.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "skill_yandex_direct"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "skill_yandex_direct"
    assert result2["description_placeholders"] == {"external_url": "https://example.com"}

    result3 = await hass.config_entries.options.async_configure(result2["flow_id"], user_input=skill)
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "skill_yandex_direct"
    assert result3["errors"] == {"base": "already_configured"}

    if attr_to_change == CONF_USER_ID:
        skill[CONF_USER_ID] = hass_owner_user.id
    else:
        skill[attr_to_change] += "bar"

    if attr_to_change in (CONF_TOKEN, CONF_ID):
        result3x = await hass.config_entries.options.async_configure(result2["flow_id"], user_input=skill)
        assert result3x["type"] == FlowResultType.FORM
        assert result3x["step_id"] == "skill_yandex_direct"
        assert result3x["errors"] == {"base": "already_configured"}

        hass.config_entries.async_update_entry(config_entry_dup, data={**config_entry_dup.data, CONF_PLATFORM: "foo"})
        await hass.async_block_till_done()

    result4 = await hass.config_entries.options.async_configure(result3["flow_id"], user_input=skill)
    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_SKILL] == skill

    await hass.async_block_till_done()

    if expect_unlink:
        assert config_entry.data[CONF_LINKED_PLATFORMS] == []
    if attr_to_change == CONF_ID:
        assert config_entry.title == "Yandex Smart Home: Direct (Mock User / foobar)"


@pytest.mark.parametrize(
    "attr_to_change,expect_unlink",
    [
        (CONF_ID, True),
        (CONF_TOKEN, False),
        (CONF_NAME, False),
    ],
)
async def test_options_flow_skill_yandex_cloud_plus(
    hass: HomeAssistant, attr_to_change: str, expect_unlink: bool
) -> None:
    skill = {CONF_NAME: "bar", CONF_ID: "foo", CONF_TOKEN: "token"}
    config_entry = await _async_mock_config_entry(
        hass,
        data={
            CONF_CONNECTION_TYPE: ConnectionType.CLOUD_PLUS,
            CONF_PLATFORM: SmartHomePlatform.YANDEX,
            CONF_LINKED_PLATFORMS: [SmartHomePlatform.YANDEX],
        },
        options={CONF_SKILL: skill.copy()},
    )
    config_entry.add_to_hass(hass)
    assert config_entry.title == "Yandex Smart Home: Cloud Plus (foo)"

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "skill_yandex_cloud_plus"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "skill_yandex_cloud_plus"
    assert result2["description_placeholders"] == {"cloud_base_url": CLOUD_BASE_URL, "instance_id": "test"}

    skill[attr_to_change] += "bar"

    result3 = await hass.config_entries.options.async_configure(result2["flow_id"], user_input=skill)
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_SKILL] == skill

    await hass.async_block_till_done()

    if expect_unlink:
        assert config_entry.data[CONF_LINKED_PLATFORMS] == []
    if attr_to_change == CONF_ID:
        assert config_entry.title == "Yandex Smart Home: Cloud Plus (foobar)"


async def test_options_flow_maintenance_direct(hass: HomeAssistant) -> None:
    config_entry = await _async_mock_config_entry(
        hass, data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_LINKED_PLATFORMS: ["foo"]}
    )
    config_entry.add_to_hass(hass)

    result = await _async_forward_to_step_maintenance(hass, config_entry)
    assert result["data_schema"] is not None
    assert list(result["data_schema"].schema.keys()) == ["revoke_oauth_tokens", "unlink_all_platforms"]

    result_rot = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"revoke_oauth_tokens": True}
    )
    assert result_rot["type"] == FlowResultType.FORM
    assert result_rot["step_id"] == "maintenance"
    assert result_rot["errors"] == {"revoke_oauth_tokens": "manual_revoke_oauth_tokens"}

    assert config_entry.data[CONF_LINKED_PLATFORMS] == ["foo"]
    result_uap = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"unlink_all_platforms": True}
    )
    assert result_uap["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert config_entry.data[CONF_LINKED_PLATFORMS] == []


@pytest.mark.parametrize("connection_type", [ConnectionType.CLOUD, ConnectionType.CLOUD_PLUS])
async def test_options_flow_maintenance_cloud(hass: HomeAssistant, connection_type: ConnectionType) -> None:
    config_entry = await _async_mock_config_entry(
        hass, data={CONF_CONNECTION_TYPE: connection_type, CONF_LINKED_PLATFORMS: ["foo"]}
    )
    config_entry.add_to_hass(hass)

    result = await _async_forward_to_step_maintenance(hass, config_entry)
    assert result["data_schema"] is not None
    assert list(result["data_schema"].schema.keys()) == [
        "revoke_oauth_tokens",
        "unlink_all_platforms",
        "reset_cloud_instance_connection_token",
    ]

    assert config_entry.data[CONF_LINKED_PLATFORMS] == ["foo"]
    result_uap = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"unlink_all_platforms": True}
    )
    assert result_uap["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert config_entry.data[CONF_LINKED_PLATFORMS] == []


async def test_options_flow_maintenance_cloud_revoke_tokens(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    config_entry = await _async_mock_config_entry(hass, data={CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    result = await _async_forward_to_step_maintenance(hass, config_entry)

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/test/oauth/revoke-all", status=401)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"revoke_oauth_tokens": True}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "maintenance"
    assert result2["errors"] == {"revoke_oauth_tokens": "unknown"}
    assert result2["description_placeholders"] == {"error": "401, message='', url='http://example.com'"}

    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/test/oauth/revoke-all", status=200)
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={"revoke_oauth_tokens": True}
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_maintenance_cloud_reset_token(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    config_entry = await _async_mock_config_entry(hass, data={CONF_CONNECTION_TYPE: ConnectionType.CLOUD})
    config_entry.add_to_hass(hass)

    assert config_entry.data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_CONNECTION_TOKEN] == "foo"

    result = await _async_forward_to_step_maintenance(hass, config_entry)

    aioclient_mock.post(f"{cloud.BASE_API_URL}/instance/test/reset-connection-token", status=401)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"reset_cloud_instance_connection_token": True}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "maintenance"
    assert result2["errors"] == {"reset_cloud_instance_connection_token": "unknown"}
    assert result2["description_placeholders"] == {"error": "401, message='', url='http://example.com'"}

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{cloud.BASE_API_URL}/instance/test/reset-connection-token",
        status=200,
        json={"id": "1234567890", "password": "", "connection_token": "bar"},
    )
    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"], user_input={"reset_cloud_instance_connection_token": True}
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()
    assert config_entry.data[CONF_CLOUD_INSTANCE] == {
        CONF_CLOUD_INSTANCE_ID: "1234567890",
        CONF_CLOUD_INSTANCE_PASSWORD: "secret",
        CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "bar",
    }


async def test_config_entry_title_default(hass: HomeAssistant, hass_admin_user: User) -> None:
    cloud_title = await async_config_entry_title(
        hass,
        data={
            CONF_CONNECTION_TYPE: ConnectionType.CLOUD,
            CONF_CLOUD_INSTANCE: {CONF_CLOUD_INSTANCE_ID: "ATGtRbViJYNwgyu"},
        },
        options={},
    )
    assert cloud_title == "Yaha Cloud (ATGtRbVi)"

    direct_yandex = await async_config_entry_title(
        hass,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_SKILL: {
                CONF_ID: "c8f46d6c-ee32-4022-a286-91e8c208ed0b",
                CONF_TOKEN: "bar",
                CONF_USER_ID: hass_admin_user.id,
            }
        },
    )
    assert direct_yandex == "Yandex Smart Home: Direct (Mock User / c8f46d6c)"

    direct_yandex_no_user = await async_config_entry_title(
        hass,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_SKILL: {
                CONF_ID: "c8f46d6c-ee32-4022-a286-91e8c208ed0b",
                CONF_TOKEN: "bar",
                CONF_USER_ID: "foo",
            }
        },
    )
    assert direct_yandex_no_user == "Yandex Smart Home: Direct (c8f46d6c)"

    direct_yandex_no_skill = await async_config_entry_title(
        hass,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={},
    )
    assert direct_yandex_no_skill == "Yandex Smart Home: Direct"

    default = await async_config_entry_title(hass, {}, {})
    assert default == "Yandex Smart Home"
