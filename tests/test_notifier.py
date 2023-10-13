import asyncio
import json
import logging
import time
from unittest.mock import patch

from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.const import ATTR_DEVICE_CLASS, EVENT_HOMEASSISTANT_STARTED, STATE_UNAVAILABLE
from homeassistant.core import CoreState, State
from homeassistant.helpers.aiohttp_client import DATA_CLIENTSESSION
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, ConnectionType, YandexSmartHome, const
from custom_components.yandex_smart_home.capability_custom import get_custom_capability
from custom_components.yandex_smart_home.capability_onoff import OnOffCapabilityBasic
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.notifier import (
    NotifierConfig,
    PendingStates,
    YandexCloudNotifier,
    YandexDirectNotifier,
)
from custom_components.yandex_smart_home.property_custom import ButtonPressCustomEventProperty, get_custom_property
from custom_components.yandex_smart_home.property_float import HumiditySensor, TemperatureSensor
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    EventPropertyInstance,
    FloatPropertyInstance,
    RangeCapabilityInstance,
    ResponseCode,
)

from . import BASIC_ENTRY_DATA, REQ_ID, MockConfigEntryData, generate_entity_filter, test_cloud

BASIC_CONFIG = NotifierConfig(user_id="bread", token="xyz", skill_id="a-b-c")


@pytest.fixture(name="mock_call_later")
def mock_call_later_fixture():
    with patch("custom_components.yandex_smart_home.notifier.async_call_later") as mock_call_later:
        yield mock_call_later


async def _async_set_state(hass, entity_id, new_state, attributes=None):
    hass.states.async_set(entity_id, new_state, attributes)
    await hass.async_block_till_done()


async def _assert_empty_list(coro):
    assert await coro == []


async def _assert_not_empty_list(coro):
    assert await coro != []


async def test_notifier_setup_config_invalid(hass, hass_admin_user, config_entry_direct, caplog):
    yaml_config = {
        const.CONF_NOTIFIER: [
            {
                const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
                const.CONF_NOTIFIER_OAUTH_TOKEN: "token",
                const.CONF_NOTIFIER_SKILL_ID: "skill_id",
            },
            {
                const.CONF_NOTIFIER_USER_ID: "invalid",
                const.CONF_NOTIFIER_OAUTH_TOKEN: "token",
                const.CONF_NOTIFIER_SKILL_ID: "skill_id",
            },
        ],
    }
    await async_setup_component(hass, DOMAIN, {DOMAIN: yaml_config})
    config_entry_direct.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_direct.entry_id)

    component: YandexSmartHome = hass.data[DOMAIN]
    with pytest.raises(KeyError):
        component.get_entry_data(config_entry_direct)
    assert (
        caplog.messages[-1] == "Config entry 'Mock Title' for yandex_smart_home integration not ready yet: "
        "User invalid does not exist; Retrying in background"
    )


async def test_notifier_setup_not_discovered(hass, hass_admin_user, aioclient_mock):
    hass.data[DATA_CLIENTSESSION] = test_cloud.MockSession(aioclient_mock)

    yaml_config = {
        const.CONF_NOTIFIER: [
            {
                const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
                const.CONF_NOTIFIER_OAUTH_TOKEN: "token",
                const.CONF_NOTIFIER_SKILL_ID: "skill_id",
            },
        ],
    }
    await async_setup_component(hass, DOMAIN, {DOMAIN: yaml_config})
    component: YandexSmartHome = hass.data[DOMAIN]

    config_entry_direct = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT},
    )
    config_entry_cloud = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "test",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
            },
        },
    )

    for config_entry in [config_entry_direct, config_entry_cloud]:
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)

        assert len(component.get_entry_data(config_entry)._notifier_configs) == 1
        assert len(component.get_entry_data(config_entry)._notifiers) == 0


async def test_notifier_lifecycle_discovered(hass, hass_admin_user, aioclient_mock):
    hass.data[DATA_CLIENTSESSION] = test_cloud.MockSession(aioclient_mock)

    yaml_config = {
        const.CONF_NOTIFIER: [
            {
                const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
                const.CONF_NOTIFIER_OAUTH_TOKEN: "token",
                const.CONF_NOTIFIER_SKILL_ID: "skill_id",
            },
            {
                const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
                const.CONF_NOTIFIER_OAUTH_TOKEN: "token2",
                const.CONF_NOTIFIER_SKILL_ID: "skill_id2",
            },
        ],
    }

    await async_setup_component(hass, DOMAIN, {DOMAIN: yaml_config})
    component: YandexSmartHome = hass.data[DOMAIN]

    config_entry_direct = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT, const.CONF_DEVICES_DISCOVERED: True},
    )
    config_entry_cloud = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "test",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
            },
            const.CONF_DEVICES_DISCOVERED: True,
        },
    )

    for config_entry in [config_entry_direct, config_entry_cloud]:
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)

    assert len(component.get_entry_data(config_entry_direct)._notifier_configs) == 2
    assert len(component.get_entry_data(config_entry_direct)._notifiers) == 2
    assert len(component.get_entry_data(config_entry_cloud)._notifier_configs) == 1
    assert len(component.get_entry_data(config_entry_cloud)._notifiers) == 1

    for config_entry in [config_entry_direct, config_entry_cloud]:
        for notifier in component.get_entry_data(config_entry)._notifiers:
            assert notifier._unsub_state_changed is not None
            assert notifier._unsub_initial_report is not None
            assert notifier._unsub_report_states is None
            assert notifier._unsub_discovery is not None

        await hass.config_entries.async_unload(config_entry.entry_id)

        for notifier in component.get_entry_data(config_entry)._notifiers:
            assert notifier._unsub_state_changed is None
            assert notifier._unsub_initial_report is None
            assert notifier._unsub_report_states is None
            assert notifier._unsub_discovery is None


async def test_notifier_postponed_setup(hass, hass_admin_user):
    yaml_config = {
        const.CONF_NOTIFIER: [
            {
                const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
                const.CONF_NOTIFIER_OAUTH_TOKEN: "token",
                const.CONF_NOTIFIER_SKILL_ID: "skill_id",
            }
        ],
    }
    await async_setup_component(hass, DOMAIN, {DOMAIN: yaml_config})
    component: YandexSmartHome = hass.data[DOMAIN]

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT, const.CONF_DEVICES_DISCOVERED: True},
    )
    with patch.object(hass, "state", return_value=CoreState.starting):
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        assert len(component.get_entry_data(config_entry)._notifiers) == 0
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        assert len(component.get_entry_data(config_entry)._notifiers) == 1


async def test_notifier_format_log_message(hass):
    direct = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, NotifierConfig(user_id="foo", skill_id="bar", token="x"), {})
    directv = YandexDirectNotifier(
        hass, BASIC_ENTRY_DATA, NotifierConfig(user_id="ivan", skill_id="sk", token="x", verbose_log=True), {}
    )
    cloud = YandexCloudNotifier(hass, BASIC_ENTRY_DATA, NotifierConfig(user_id="foo", skill_id="bar", token="x"), {})
    assert direct._format_log_message("test") == "test"
    assert directv._format_log_message("test") == "test (ivan@sk)"
    assert cloud._format_log_message("test") == "test"


async def test_notifier_track_templates(hass_platform, mock_call_later, caplog):
    hass = hass_platform
    entry_data = MockConfigEntryData(
        hass=hass,
        entity_config={
            "light.kitchen": {
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "temperature",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "binary_sensor.foo",  # it fails
                    },
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "humidity",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.float",
                    },
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "pressure",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.float",
                    },
                ]
            },
            "sensor.outside_temp": {
                const.CONF_ENTITY_MODE_MAP: {"dishwashing": {"fowl": ["one"], "two": ["two"]}},
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "button",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.button",
                    },
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "co2_level",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.float",
                    },
                ],
                const.CONF_ENTITY_CUSTOM_MODES: {
                    "dishwashing": {const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "sensor.dishwashing"},
                },
                const.CONF_ENTITY_CUSTOM_TOGGLES: {
                    "pause": {const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "binary_sensor.pause"}
                },
                const.CONF_ENTITY_CUSTOM_RANGES: {
                    "volume": {const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "sensor.volume"}
                },
            },
            "switch.not_exposed": {
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "humidity",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.float",
                    },
                ]
            },
        },
        entity_filter=generate_entity_filter(exclude_entities=["switch.not_exposed"]),
    )

    hass.states.async_set("sensor.button", "click")
    hass.states.async_set("sensor.float", "10")
    caplog.clear()
    notifier = YandexDirectNotifier(hass_platform, entry_data, BASIC_CONFIG, entry_data._get_trackable_states())
    await notifier.async_setup()

    assert notifier._template_changes_tracker is not None
    assert notifier._pending.empty is True
    assert caplog.messages[:1] == [
        "Failed to track custom property: Unsupported entity binary_sensor.foo for "
        "temperature instance of light.kitchen",
    ]

    # event
    mock_call_later.reset_mock()
    await _async_set_state(hass, "sensor.button", "click", {"foo": "bar"})
    assert notifier._pending.empty is True
    await _async_set_state(hass, "sensor.button", "double_click", {"foo": "bar"})
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["sensor.outside_temp"]
    assert len(pending["sensor.outside_temp"]) == 1
    assert pending["sensor.outside_temp"][0].get_value() == "double_click"
    mock_call_later.assert_called_once()
    assert mock_call_later.call_args[1]["delay"] == 0
    assert notifier._unsub_report_states is not None

    # float
    mock_call_later.reset_mock()
    await _async_set_state(hass, "sensor.float", "50")
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["light.kitchen", "sensor.outside_temp"]
    assert pending["light.kitchen"][0].get_value() == 50
    assert pending["light.kitchen"][0].instance == "humidity"
    assert pending["light.kitchen"][1].get_value() == 50
    assert pending["light.kitchen"][1].instance == "pressure"
    assert pending["sensor.outside_temp"][0].get_value() == 50
    assert pending["sensor.outside_temp"][0].instance == "co2_level"
    caplog.clear()
    await _async_set_state(hass, "sensor.float", "q")
    assert notifier._pending.empty is True
    assert caplog.messages[-1] == "Unsupported value 'q' for instance co2_level of sensor.outside_temp"
    mock_call_later.assert_not_called()

    # mode
    mock_call_later.reset_mock()
    notifier._unsub_report_states = None
    await _async_set_state(hass, "sensor.dishwashing", "x")
    assert notifier._pending.empty is True
    caplog.clear()
    await _async_set_state(hass, "sensor.dishwashing", "one")
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["sensor.outside_temp"]
    assert len(pending["sensor.outside_temp"]) == 1
    assert pending["sensor.outside_temp"][0].get_value() == "fowl"
    assert (
        caplog.messages[-1]
        == "State report with value 'fowl' scheduled for <CustomModeCapability device_id=sensor.outside_temp "
        "instance=dishwashing value_template=Template<template=(one) renders=2>>"
    )
    await _async_set_state(hass, "sensor.dishwashing", "unavailable")
    assert notifier._pending.empty is True
    mock_call_later.assert_called_once()
    assert mock_call_later.call_args[1]["delay"] == 1
    assert notifier._unsub_report_states is not None

    # toggle
    await _async_set_state(hass, "binary_sensor.pause", "off")
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["sensor.outside_temp"]
    assert len(pending["sensor.outside_temp"]) == 1
    assert pending["sensor.outside_temp"][0].get_value() is False
    await _async_set_state(hass, "binary_sensor.pause", "unavailable")
    assert notifier._pending.empty is True
    await _async_set_state(hass, "binary_sensor.pause", "on")
    pending = await notifier._pending.async_get_all()
    assert pending["sensor.outside_temp"][0].get_value() is True

    # range
    await _async_set_state(hass, "sensor.volume", "50")
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["sensor.outside_temp"]
    assert len(pending["sensor.outside_temp"]) == 1
    assert pending["sensor.outside_temp"][0].get_value() == 50
    await _async_set_state(hass, "sensor.volume", "unavailable")
    assert notifier._pending.empty is True

    await notifier.async_unload()
    assert notifier._template_changes_tracker is None


async def test_notifier_state_changed(hass_platform, mock_call_later, caplog):
    hass = hass_platform
    entry_data = MockConfigEntryData(
        hass=hass,
        entity_filter=generate_entity_filter(exclude_entities=["switch.not_exposed"]),
    )

    notifier = YandexDirectNotifier(hass_platform, entry_data, BASIC_CONFIG, entry_data._get_trackable_states())
    await notifier.async_setup()

    await _async_set_state(hass, "switch.not_exposed", "on")
    await _async_set_state(hass, "switch.not_exposed", "off")
    assert notifier._pending.empty is True
    assert notifier._unsub_report_states is None

    caplog.clear()
    mock_call_later.reset_mock()
    await _async_set_state(hass, "sensor.button", "click", {ATTR_DEVICE_CLASS: "button"})
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["sensor.button"]
    assert len(pending["sensor.button"]) == 1
    assert pending["sensor.button"][0].get_value() == "click"
    assert caplog.messages[-1] == (
        "State report with value 'click' scheduled for <ButtonPressStateEventProperty "
        "device_id=sensor.button type=devices.properties.event instance=button>"
    )
    mock_call_later.assert_called_once()
    assert notifier._unsub_report_states is not None

    await _async_set_state(hass, "binary_sensor.front_door", "off", {ATTR_DEVICE_CLASS: "door"})
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["binary_sensor.front_door"]
    assert len(pending["binary_sensor.front_door"]) == 1
    assert pending["binary_sensor.front_door"][0].get_value() == "closed"

    light_state = hass.states.get("light.kitchen")
    await _async_set_state(hass, light_state.entity_id, "off", light_state.attributes)
    pending = await notifier._pending.async_get_all()
    assert list(pending.keys()) == ["light.kitchen"]
    assert len(pending["light.kitchen"]) == 1
    assert pending["light.kitchen"][0].get_value() is False
    assert caplog.messages[-1] == (
        "State report with value 'False' scheduled for <OnOffCapabilityBasic "
        "device_id=light.kitchen type=devices.capabilities.on_off instance=on>"
    )

    hass.states.async_remove("light.kitchen")
    assert notifier._pending.empty is True

    await notifier.async_unload()


async def test_notifier_initial_report(hass_platform, mock_call_later, caplog):
    entry_data = MockConfigEntryData(
        hass=hass_platform,
        entity_config={
            "light.kitchen": {
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: "temperature",
                        const.CONF_ENTITY_PROPERTY_ENTITY: "binary_sensor.foo",  # cursed property
                    }
                ]
            }
        },
        entity_filter=generate_entity_filter(exclude_entities=["switch.test"]),
    )
    notifier = YandexDirectNotifier(hass_platform, entry_data, BASIC_CONFIG, entry_data._get_trackable_states())

    hass_platform.states.async_set("switch.test", "on")
    hass_platform.states.async_set(
        "sensor.button", "on", {ATTR_DEVICE_CLASS: const.DEVICE_CLASS_BUTTON, "last_action": "click"}
    )

    await notifier._async_initial_report()
    mock_call_later.assert_called_once()

    devices = await notifier._pending.async_get_all()
    assert list(devices.keys()) == ["sensor.outside_temp", "light.kitchen"]

    sensor_states = [s.get_instance_state().as_dict() for s in devices["sensor.outside_temp"]]
    assert sensor_states == [
        {"state": {"instance": "temperature", "value": 15.6}, "type": "devices.properties.float"},
    ]

    light_states = [s.get_instance_state().as_dict() for s in devices["light.kitchen"] if s.get_instance_state()]
    assert light_states == [
        {"state": {"instance": "temperature_k", "value": 4200}, "type": "devices.capabilities.color_setting"},
        {"state": {"instance": "brightness", "value": 70}, "type": "devices.capabilities.range"},
        {"state": {"instance": "on", "value": True}, "type": "devices.capabilities.on_off"},
    ]

    assert notifier._pending.empty is True
    assert caplog.messages[-1:] == [
        "Failed to send initial report for properties: Unsupported entity binary_sensor.foo for temperature "
        "instance of light.kitchen"
    ]


async def test_notifier_send_callback_exception(hass, caplog):
    notifier = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG, {})

    with patch.object(notifier._session, "post", side_effect=ClientConnectionError()):
        caplog.clear()
        await notifier.async_send_discovery()
        assert caplog.records[-1].message == "Notification request failed: ClientConnectionError()"
        assert caplog.records[-1].levelno == logging.WARN
        caplog.clear()

    with patch.object(notifier._session, "post", side_effect=asyncio.TimeoutError()):
        await notifier.async_send_discovery()
        assert caplog.records[-1].message == "Notification request failed: TimeoutError()"
        assert caplog.records[-1].levelno == logging.DEBUG


async def test_notifier_send_direct(hass, aioclient_mock, caplog):
    notifier = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG, {})
    token = BASIC_CONFIG.token
    skill_id = BASIC_CONFIG.skill_id
    user_id = BASIC_CONFIG.user_id
    now = time.time()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/discovery",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )

    with patch("time.time", return_value=now):
        await notifier.async_send_discovery()

    assert aioclient_mock.call_count == 1
    assert json.loads(aioclient_mock.mock_calls[0][2]._value) == {"ts": now, "payload": {"user_id": user_id}}
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": f"OAuth {token}"}
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )
    await notifier._pending.async_add(
        [ButtonPressCustomEventProperty(hass, BASIC_ENTRY_DATA, {}, "btn", Template("click", hass))],
        [],
    )

    with patch("time.time", return_value=now):
        await notifier._async_report_states()

    await hass.async_block_till_done()
    assert len(caplog.messages) == 1
    assert aioclient_mock.call_count == 1
    assert json.loads(aioclient_mock.mock_calls[0][2]._value) == {
        "ts": now,
        "payload": {
            "devices": [
                {
                    "id": "btn",
                    "properties": [
                        {"type": "devices.properties.event", "state": {"instance": "button", "value": "click"}}
                    ],
                }
            ],
            "user_id": user_id,
        },
    }
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": f"OAuth {token}"}
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/discovery",
        status=400,
        json={"request_id": REQ_ID, "status": "error", "error_message": "some error"},
    )
    await notifier.async_send_discovery()

    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Notification request failed: some error"
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/discovery",
        status=500,
        content=b"ERROR",
    )
    await notifier.async_send_discovery()
    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Notification request failed: ERROR"
    aioclient_mock.clear_requests()
    caplog.clear()

    with patch.object(notifier._session, "post", side_effect=Exception("boo")):
        await notifier.async_send_discovery()
        assert aioclient_mock.call_count == 0
    assert "Unexpected exception" in caplog.messages[-1]


async def test_notifier_send_cloud(hass, aioclient_mock, caplog):
    await async_setup_component(hass, DOMAIN, {})
    entry_data = MockConfigEntryData(hass, BASIC_ENTRY_DATA.entry)

    notifier = YandexCloudNotifier(hass, entry_data, BASIC_CONFIG, {})
    token = BASIC_CONFIG.token
    user_id = BASIC_CONFIG.user_id
    now = time.time()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/discovery",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )

    with patch("time.time", return_value=now):
        await notifier.async_send_discovery()

    assert aioclient_mock.call_count == 1
    assert json.loads(aioclient_mock.mock_calls[0][2]._value) == {"ts": now, "payload": {"user_id": user_id}}
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {token}"
    assert "yandex_smart_home/" in aioclient_mock.mock_calls[0][3]["User-Agent"]
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/state",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )
    await notifier._pending.async_add(
        [ButtonPressCustomEventProperty(hass, BASIC_ENTRY_DATA, {}, "btn", Template("click", hass))],
        [],
    )

    with patch("time.time", return_value=now):
        await notifier._async_report_states()

    await hass.async_block_till_done()
    assert len(caplog.messages) == 1
    assert aioclient_mock.call_count == 1
    assert json.loads(aioclient_mock.mock_calls[0][2]._value) == {
        "ts": now,
        "payload": {
            "devices": [
                {
                    "id": "btn",
                    "properties": [
                        {"type": "devices.properties.event", "state": {"instance": "button", "value": "click"}}
                    ],
                }
            ],
            "user_id": user_id,
        },
    }
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {token}"
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/discovery",
        status=400,
        json={"request_id": REQ_ID, "status": "error", "error_message": "some error"},
    )
    await notifier.async_send_discovery()

    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Notification request failed: some error"
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/discovery",
        status=500,
        content=b"ERROR",
    )
    await notifier.async_send_discovery()
    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Notification request failed: ERROR"
    aioclient_mock.clear_requests()
    caplog.clear()

    with patch.object(notifier._session, "post", side_effect=Exception("boo")):
        await notifier.async_send_discovery()
        assert aioclient_mock.call_count == 0
    assert "Unexpected exception" in caplog.messages[-1]


async def test_notifier_report_states(hass, mock_call_later, aioclient_mock, caplog):
    class MockCapabilityFail(OnOffCapabilityBasic):
        def get_value(self) -> bool | None:
            raise APIError(ResponseCode.INTERNAL_ERROR, "api error cap")

    class MockPropertyFail(TemperatureSensor):
        def supported(self) -> bool:
            return True

        def get_value(self) -> bool | None:
            raise APIError(ResponseCode.INTERNAL_ERROR, "api error prop")

    notifier = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG, {})
    skill_id = BASIC_CONFIG.skill_id
    user_id = BASIC_CONFIG.user_id
    now = time.time()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )

    await notifier._async_report_states()
    assert aioclient_mock.call_count == 0
    assert notifier._unsub_report_states is None

    await notifier._pending.async_add([OnOffCapabilityBasic(hass, BASIC_ENTRY_DATA, State("switch.on", "on"))], [])
    await notifier._pending.async_add([MockCapabilityFail(hass, BASIC_ENTRY_DATA, State("switch.fail", "on"))], [])
    await notifier._pending.async_add([TemperatureSensor(hass, BASIC_ENTRY_DATA, State("sensor.temperature", "5"))], [])
    await notifier._pending.async_add([HumiditySensor(hass, BASIC_ENTRY_DATA, State("sensor.temperature", "5"))], [])
    await notifier._pending.async_add([MockPropertyFail(hass, BASIC_ENTRY_DATA, State("sensor.fail", "5"))], [])

    assert notifier._pending.empty is False
    with patch("time.time", return_value=now):
        await notifier._async_report_states()
    await hass.async_block_till_done()
    assert caplog.messages[:2] == ["api error cap", "api error prop"]
    assert aioclient_mock.call_count == 1
    assert notifier._unsub_report_states is None
    request_body = json.loads(aioclient_mock.mock_calls[0][2]._value)
    assert request_body == {
        "payload": {
            "devices": [
                {
                    "capabilities": [
                        {"state": {"instance": "on", "value": True}, "type": "devices.capabilities.on_off"}
                    ],
                    "id": "switch.on",
                },
                {
                    "id": "sensor.temperature",
                    "properties": [
                        {"state": {"instance": "temperature", "value": 5.0}, "type": "devices.properties.float"},
                        {"state": {"instance": "humidity", "value": 5.0}, "type": "devices.properties.float"},
                    ],
                },
            ],
            "user_id": user_id,
        },
        "ts": now,
    }

    with patch.object(notifier._pending, "async_get_all", return_value=notifier._pending._device_states):
        await notifier._pending.async_add([OnOffCapabilityBasic(hass, BASIC_ENTRY_DATA, State("switch.on", "on"))], [])
        await notifier._async_report_states()
        await hass.async_block_till_done()
        assert notifier._pending.empty is False
        assert notifier._unsub_report_states is not None


async def test_notifier_pending_states(hass):
    ps = PendingStates()
    await ps.async_add([OnOffCapabilityBasic(hass, BASIC_ENTRY_DATA, State("switch.test", "on"))], [])
    assert ps._device_states["switch.test"][0].get_value() is True
    await ps.async_add([OnOffCapabilityBasic(hass, BASIC_ENTRY_DATA, State("switch.test", "off"))], [])
    assert ps._device_states["switch.test"][0].get_value() is False


async def test_notifier_capability_check_value_change(hass):
    ps = PendingStates()
    cap = get_custom_capability(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "sensor.empty",
        },
        CapabilityType.RANGE,
        RangeCapabilityInstance.OPEN,
        "foo",
    )
    await _assert_not_empty_list(ps.async_add([cap.new_with_value_template(Template("5"))], []))
    await _assert_empty_list(
        ps.async_add([cap.new_with_value_template(Template("5"))], [cap.new_with_value_template(Template("5"))])
    )
    await _assert_not_empty_list(
        ps.async_add([cap.new_with_value_template(Template("5"))], [cap.new_with_value_template(Template("6"))])
    )
    await _assert_not_empty_list(
        ps.async_add(
            [cap.new_with_value_template(Template("5"))], [cap.new_with_value_template(Template(STATE_UNAVAILABLE))]
        )
    )
    await _assert_empty_list(
        ps.async_add(
            [cap.new_with_value_template(Template(STATE_UNAVAILABLE))], [cap.new_with_value_template(Template("5"))]
        )
    )


@pytest.mark.parametrize("instance", FloatPropertyInstance.__members__.values())
async def test_notifier_float_property_check_value_change(hass, instance):
    ps = PendingStates()
    prop = get_custom_property(hass, BASIC_ENTRY_DATA, {const.CONF_ENTITY_PROPERTY_TYPE: instance}, "sensor.foo")
    await _assert_not_empty_list(ps.async_add([prop.new_with_value_template(Template("5"))], []))
    await _assert_empty_list(
        ps.async_add([prop.new_with_value_template(Template("5"))], [prop.new_with_value_template(Template("5"))])
    )
    await _assert_not_empty_list(
        ps.async_add([prop.new_with_value_template(Template("5"))], [prop.new_with_value_template(Template("6"))])
    )
    await _assert_not_empty_list(
        ps.async_add(
            [prop.new_with_value_template(Template("5"))], [prop.new_with_value_template(Template(STATE_UNAVAILABLE))]
        )
    )
    await _assert_empty_list(
        ps.async_add(
            [prop.new_with_value_template(Template(STATE_UNAVAILABLE))], [prop.new_with_value_template(Template("5"))]
        )
    )


@pytest.mark.parametrize("instance", EventPropertyInstance.__members__.values())
async def test_notifier_binary_event_property_check_value_change(hass, instance):
    if instance in [EventPropertyInstance.BUTTON, EventPropertyInstance.VIBRATION]:
        pytest.skip()

    ps = PendingStates()
    prop = get_custom_property(hass, BASIC_ENTRY_DATA, {const.CONF_ENTITY_PROPERTY_TYPE: instance}, "binary_sensor.foo")
    await _assert_empty_list(ps.async_add([prop.new_with_value_template(Template("on"))], []))
    await _assert_empty_list(
        ps.async_add([prop.new_with_value_template(Template("on"))], [prop.new_with_value_template(Template("on"))])
    )
    await _assert_not_empty_list(
        ps.async_add([prop.new_with_value_template(Template("on"))], [prop.new_with_value_template(Template("off"))])
    )
    await _assert_empty_list(
        ps.async_add(
            [prop.new_with_value_template(Template("on"))], [prop.new_with_value_template(Template(STATE_UNAVAILABLE))]
        )
    )
    await _assert_empty_list(
        ps.async_add(
            [prop.new_with_value_template(Template(STATE_UNAVAILABLE))], [prop.new_with_value_template(Template("on"))]
        )
    )


@pytest.mark.parametrize(
    "instance,v", [(EventPropertyInstance.BUTTON, "click"), (EventPropertyInstance.VIBRATION, "on")]
)
async def test_notifier_reactive_event_property_check_value_change(hass, instance, v):
    ps = PendingStates()
    prop = get_custom_property(hass, BASIC_ENTRY_DATA, {const.CONF_ENTITY_PROPERTY_TYPE: instance}, "binary_sensor.foo")
    await _assert_not_empty_list(ps.async_add([prop.new_with_value_template(Template(v))], []))
    await _assert_empty_list(
        ps.async_add([prop.new_with_value_template(Template(v))], [prop.new_with_value_template(Template(v))])
    )
    await _assert_not_empty_list(
        ps.async_add([prop.new_with_value_template(Template(v))], [prop.new_with_value_template(Template("off"))])
    )
    await _assert_not_empty_list(
        ps.async_add(
            [prop.new_with_value_template(Template(v))], [prop.new_with_value_template(Template(STATE_UNAVAILABLE))]
        )
    )
    await _assert_empty_list(
        ps.async_add(
            [prop.new_with_value_template(Template(STATE_UNAVAILABLE))], [prop.new_with_value_template(Template(v))]
        )
    )
