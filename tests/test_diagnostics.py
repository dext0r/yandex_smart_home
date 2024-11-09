from datetime import datetime
from http import HTTPStatus
from unittest import mock

from homeassistant.const import CONF_ID, CONF_PLATFORM, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entityfilter, issue_registry
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy import SnapshotAssertion

from custom_components.yandex_smart_home import DOMAIN
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_CLOUD_INSTANCE,
    CONF_CLOUD_INSTANCE_PASSWORD,
    CONF_CONNECTION_TYPE,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_SKILL,
    CONF_USER_ID,
    ConnectionType,
    EntityFilterSource,
)
from custom_components.yandex_smart_home.helpers import SmartHomePlatform


async def test_diagnostics(
    hass_platform: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_admin_user: MockUser,
    snapshot: SnapshotAssertion,
) -> None:
    hass = hass_platform
    yaml_config = {
        "filter": {"include_domains": ["light", "sensor", "binary_sensor"]},
        "entity_config": {
            "switch.with_template": {"error_code_template": '{{ "a" + "b" }}'},
            "light.kitchen": {"properties": [{"type": "temperature", "entity": "sensor.invalid"}]},
        },
        "notifier": [{"skill_id": "foo", "oauth_token": "token", "user_id": hass_admin_user.id}],
    }
    assert await async_setup_component(hass, "diagnostics", {})
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: yaml_config})

    hass.states.async_set("sensor.invalid", "foo")
    config_entry = MockConfigEntry(
        entry_id="fe76008998bdad631c33d60ef044b9ac",
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            CONF_CONNECTION_TYPE: ConnectionType.DIRECT,
            CONF_CLOUD_INSTANCE: {CONF_CLOUD_INSTANCE_PASSWORD: "foo"},
            CONF_PLATFORM: SmartHomePlatform.YANDEX,
        },
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]},
            CONF_SKILL: {CONF_ID: "skill_id", CONF_TOKEN: "oauth_token", CONF_USER_ID: "user_id"},
        },
    )
    config_entry.add_to_hass(hass)

    now = datetime(2024, 5, 7, 1, 10, 6)
    with mock.patch("homeassistant.helpers.event.dt_util.utcnow", return_value=now):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        issue_registry.async_create_issue(
            hass, DOMAIN, "foo", is_fixable=False, severity=IssueSeverity.CRITICAL, translation_key="foo"
        )

    client = await hass_client()
    response = await client.get(f"/api/diagnostics/config_entry/{config_entry.entry_id}")
    assert response.status == HTTPStatus.OK
    diagnostics = await response.json()
    for k in ("integration_manifest", "custom_components", "home_assistant", "minor_version", "setup_times"):
        diagnostics.pop(k, None)

    for k in ("minor_version", "created_at", "discovery_keys", "modified_at"):
        diagnostics["data"]["entry"].pop(k, None)

    assert diagnostics == snapshot
