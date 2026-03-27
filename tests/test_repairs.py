from http import HTTPStatus
import json
from typing import Any, cast
from unittest.mock import patch

from aiohttp.test_utils import TestClient
from homeassistant import core
from homeassistant.components import demo, repairs
from homeassistant.components.repairs.websocket_api import RepairsFlowIndexView, RepairsFlowResourceView
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_PLATFORM, STATE_UNAVAILABLE, Platform
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir, label_registry as lr
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES, CONF_INCLUDE_ENTITY_GLOBS
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.yandex_smart_home import DOMAIN, YandexSmartHome, handlers
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_ADD_LABEL,
    CONF_CONNECTION_TYPE,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_LABEL,
    ConnectionType,
    EntityFilterSource,
)
from custom_components.yandex_smart_home.helpers import RequestData, SmartHomePlatform

from . import REQ_ID, MockConfigEntry


async def _start_repair_fix_flow(client: TestClient, handler: str, issue_id: str) -> dict[str, Any]:
    """Start a flow from an issue."""
    url = RepairsFlowIndexView.url
    assert url
    resp = await client.post(url, json={"handler": handler, "issue_id": issue_id})
    assert resp.status == HTTPStatus.OK
    return cast(dict[str, Any], await resp.json())


async def _process_repair_fix_flow(
    client: TestClient, flow_id: int, json: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return the repairs list of issues."""
    assert RepairsFlowResourceView.url
    url = RepairsFlowResourceView.url.format(flow_id=flow_id)
    resp = await client.post(url, json=json)
    assert resp.status == HTTPStatus.OK
    return cast(dict[str, Any], await resp.json())


async def test_unexposed_entity_found_issue(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
) -> None:
    entry_data = {CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX}
    entry_config_flow = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        title="Config Flow",
        data=entry_data,
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {CONF_INCLUDE_ENTITY_GLOBS: []},
        },
    )
    entry_label = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        title="Label",
        data=entry_data,
        options={CONF_FILTER_SOURCE: EntityFilterSource.LABEL, CONF_LABEL: "foo"},
    )
    entry_yaml = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        title="YAML",
        data=entry_data,
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.YAML,
        },
    )

    for entry in (entry_config_flow, entry_label, entry_yaml):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    component: YandexSmartHome = hass.data[DOMAIN]

    switch_foo = State("switch.foo", STATE_UNAVAILABLE)
    switch_bar = State("switch.bar", STATE_UNAVAILABLE, {ATTR_FRIENDLY_NAME: "Bar Test Switch"})

    req_config_flow = RequestData(
        component.get_entry_data(entry_config_flow), Context(), SmartHomePlatform.YANDEX, "foo", REQ_ID
    )
    req_label = RequestData(component.get_entry_data(entry_label), Context(), SmartHomePlatform.YANDEX, "foo", REQ_ID)
    req_yaml = RequestData(component.get_entry_data(entry_yaml), Context(), SmartHomePlatform.YANDEX, "foo", REQ_ID)

    issue_registry.async_delete(DOMAIN, "missing_skill_data")
    assert len(issue_registry.issues) == 0

    payload_query = json.dumps({"devices": [{"id": switch_foo.entity_id}]})
    for data in (req_config_flow, req_label, req_yaml):
        await handlers.async_devices_query(hass, data, payload_query)

    assert len(issue_registry.issues) == 0

    payload_action = json.dumps(
        {
            "payload": {
                "devices": [
                    {
                        "id": switch_bar.entity_id,
                        "capabilities": [
                            {
                                "type": "devices.capabilities.on_off",
                                "state": {"instance": "on", "value": True},
                            },
                        ],
                    },
                ]
            }
        }
    )
    for data in (req_config_flow, req_label, req_yaml):
        await handlers.async_devices_action(hass, data, payload_action)

    assert len(issue_registry.issues) == 0

    hass.states.async_set(switch_foo.entity_id, switch_foo.state, switch_foo.attributes)
    hass.states.async_set(switch_bar.entity_id, switch_bar.state, switch_bar.attributes)

    # config entry
    await handlers.async_devices_query(hass, req_config_flow, payload_query)
    assert len(issue_registry.issues) == 1
    i = issue_registry.async_get_issue(DOMAIN, "unexposed_entity_found_config_entry")
    assert i is not None
    assert i.is_fixable
    assert i.translation_placeholders == {"entry_title": "Config Flow", "entities": "* `switch.foo` (foo)"}

    await handlers.async_devices_action(hass, req_config_flow, payload_action)
    assert len(issue_registry.issues) == 1
    i = issue_registry.async_get_issue(DOMAIN, "unexposed_entity_found_config_entry")
    assert i is not None
    assert i.translation_placeholders == {
        "entry_title": "Config Flow",
        "entities": "* `switch.bar` (Bar Test Switch)\n* `switch.foo` (foo)",
    }

    # label
    await handlers.async_devices_query(hass, req_label, payload_query)
    assert len(issue_registry.issues) == 2
    i = issue_registry.async_get_issue(DOMAIN, "unexposed_entity_found_label")
    assert i is not None
    assert i.is_fixable
    assert i.translation_placeholders == {"entry_title": "Label", "entities": "* `switch.foo` (foo)"}

    await handlers.async_devices_action(hass, req_label, payload_action)
    assert len(issue_registry.issues) == 2
    i = issue_registry.async_get_issue(DOMAIN, "unexposed_entity_found_label")
    assert i is not None
    assert i.translation_placeholders == {
        "entry_title": "Label",
        "entities": "* `switch.bar` (Bar Test Switch)\n* `switch.foo` (foo)",
    }

    # yaml
    await handlers.async_devices_query(hass, req_yaml, payload_query)
    assert len(issue_registry.issues) == 3
    i = issue_registry.async_get_issue(DOMAIN, "unexposed_entity_found_yaml")
    assert i is not None
    assert not i.is_fixable
    assert i.translation_placeholders == {"entry_title": "YAML", "entities": "* `- switch.foo`"}

    await handlers.async_devices_action(hass, req_yaml, payload_action)
    assert len(issue_registry.issues) == 3
    i = issue_registry.async_get_issue(DOMAIN, "unexposed_entity_found_yaml")
    assert i is not None
    assert i.translation_placeholders == {
        "entry_title": "YAML",
        "entities": "* `- switch.bar`\n* `- switch.foo`",
    }

    await hass.config_entries.async_unload(entry_config_flow.entry_id)
    assert len(issue_registry.issues) == 0


async def test_unexposed_entity_found_repair_empty(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
    config_entry_direct: MockConfigEntry,
) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    assert await async_setup_component(hass, repairs.DOMAIN, {})
    client = await hass_client()
    issue_id = "unexposed_entity_found_label"

    issue_registry.async_get_or_create(
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        data={"entry_id": "foo"},
        translation_key=issue_id,
    )
    data = await _start_repair_fix_flow(client, DOMAIN, issue_id)
    assert data["type"] == FlowResultType.CREATE_ENTRY
    assert len(issue_registry.issues) == 0

    config_entry_direct.add_to_hass(hass)
    issue_registry.async_get_or_create(
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        data={"entry_id": config_entry_direct.entry_id},
        translation_key=issue_id,
    )
    data = await _start_repair_fix_flow(client, DOMAIN, issue_id)
    assert data["type"] == FlowResultType.CREATE_ENTRY
    assert len(issue_registry.issues) == 0

    with pytest.raises(AssertionError):
        await _start_repair_fix_flow(client, DOMAIN, "foo")


async def test_unexposed_entity_found_repair_config_entry(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
) -> None:
    assert await async_setup_component(hass, repairs.DOMAIN, {})
    client = await hass_client()
    issue_id = "unexposed_entity_found_config_entry"
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {CONF_INCLUDE_ENTITIES: ["light.foo"]},
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_entry_data(entry)

    # no action
    entry_data.mark_entity_unexposed("switch.foo")
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    data = await _start_repair_fix_flow(client, DOMAIN, issue_id)
    assert data["type"] == FlowResultType.FORM

    data = await _process_repair_fix_flow(client, data["flow_id"], {CONF_INCLUDE_ENTITIES: False})
    assert data["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_FILTER][CONF_INCLUDE_ENTITIES] == ["light.foo"]
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None

    # modify entry
    entry_data.mark_entity_unexposed("switch.foo")
    entry_data.mark_entity_unexposed("switch.bar")
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    data = await _start_repair_fix_flow(client, DOMAIN, issue_id)
    assert data["type"] == FlowResultType.FORM

    data = await _process_repair_fix_flow(client, data["flow_id"], {CONF_INCLUDE_ENTITIES: True})
    assert data["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_FILTER][CONF_INCLUDE_ENTITIES] == ["light.foo", "switch.bar", "switch.foo"]
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_unexposed_entity_found_repair_label(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
    label_registry: lr.LabelRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM", [Platform.LIGHT, Platform.LOCK]
    ):
        await async_setup_component(hass, repairs.DOMAIN, {})
        await async_setup_component(hass, core.DOMAIN, {})
        await async_setup_component(hass, demo.DOMAIN, {})
    await hass.async_block_till_done()

    light1_entity = entity_registry.async_get("light.bed_light")
    assert light1_entity
    assert light1_entity.name is None
    assert light1_entity.area_id is None
    assert len(light1_entity.labels) == 0
    entity_registry.async_update_entity(light1_entity.entity_id, labels={"a", "b", "c"})

    light2_entity = entity_registry.async_get("light.office_rgbw_lights")
    assert light2_entity
    assert len(light2_entity.labels) == 0

    client = await hass_client()
    issue_id = "unexposed_entity_found_label"
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={CONF_FILTER_SOURCE: EntityFilterSource.LABEL, CONF_LABEL: "bar"},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_entry_data(entry)

    # no action
    entry_data.mark_entity_unexposed(light1_entity.entity_id)
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    data = await _start_repair_fix_flow(client, DOMAIN, issue_id)
    assert data["type"] == FlowResultType.FORM
    assert data["description_placeholders"] == {"label": "bar"}

    data = await _process_repair_fix_flow(client, data["flow_id"], {CONF_ADD_LABEL: False})
    assert data["type"] == FlowResultType.CREATE_ENTRY
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None
    light1_entity = entity_registry.async_get(light1_entity.entity_id)
    assert light1_entity
    assert light1_entity.labels == {"a", "b", "c"}

    # add labels
    label_registry.async_create("BaR")
    entry_data.mark_entity_unexposed(light1_entity.entity_id)
    entry_data.mark_entity_unexposed(light2_entity.entity_id)
    entry_data.mark_entity_unexposed("switch.not_existed")
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    data = await _start_repair_fix_flow(client, DOMAIN, issue_id)
    assert data["type"] == FlowResultType.FORM
    assert data["description_placeholders"] == {"label": "BaR"}

    data = await _process_repair_fix_flow(client, data["flow_id"], {CONF_ADD_LABEL: True})
    assert data["type"] == FlowResultType.CREATE_ENTRY
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None

    light1_entity = entity_registry.async_get(light1_entity.entity_id)
    assert light1_entity
    assert light1_entity.name is None
    assert light1_entity.area_id is None
    assert light1_entity.labels == {"a", "b", "c", "bar"}

    light2_entity = entity_registry.async_get(light2_entity.entity_id)
    assert light2_entity
    assert light2_entity.labels == {"bar"}
