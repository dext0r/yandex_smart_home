import asyncio
import logging
import time
from unittest.mock import patch

from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    EVENT_HOMEASSISTANT_STARTED,
    PERCENTAGE,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)
from homeassistant.core import CoreState, State
from homeassistant.helpers.aiohttp_client import DATA_CLIENTSESSION
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, YandexSmartHome, const
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.device import DeviceCallbackState
from custom_components.yandex_smart_home.notifier import NotifierConfig, YandexCloudNotifier, YandexDirectNotifier

from . import BASIC_ENTRY_DATA, REQ_ID, MockConfigEntryData, generate_entity_filter, test_cloud

BASIC_CONFIG = NotifierConfig(user_id="bread", token="xyz", skill_id="a-b-c")


class MockDeviceCallbackState(DeviceCallbackState):
    # noinspection PyMissingConstructor
    def __init__(self, device_id, capabilities=None, properties=None):
        self.device_id = device_id
        self.old_state = None
        self.capabilities = capabilities or []
        self.properties = properties or []


@pytest.fixture(name="mock_call_later")
def mock_call_later_fixture():
    with patch("custom_components.yandex_smart_home.notifier.async_call_later") as mock_call_later:
        yield mock_call_later


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
        data={const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT},
    )
    config_entry_cloud = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
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
        data={const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT, const.CONF_DEVICES_DISCOVERED: True},
    )
    config_entry_cloud = MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
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
            assert notifier._unsub_send_discovery is not None
            assert notifier._unsub_pending is None

        await hass.config_entries.async_unload(config_entry.entry_id)

        for notifier in component.get_entry_data(config_entry)._notifiers:
            assert notifier._unsub_state_changed is None
            assert notifier._unsub_initial_report is None
            assert notifier._unsub_send_discovery is None
            assert notifier._unsub_pending is None


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
        data={const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT, const.CONF_DEVICES_DISCOVERED: True},
    )
    with patch.object(hass, "state", return_value=CoreState.starting):
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        assert len(component.get_entry_data(config_entry)._notifiers) == 0
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        assert len(component.get_entry_data(config_entry)._notifiers) == 1


async def test_notifier_format_log_message(hass):
    direct = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, NotifierConfig(user_id="foo", skill_id="bar", token="x"))
    directv = YandexDirectNotifier(
        hass, BASIC_ENTRY_DATA, NotifierConfig(user_id="foo", skill_id="bar", token="x", verbose_log=True)
    )
    cloud = YandexCloudNotifier(hass, BASIC_ENTRY_DATA, NotifierConfig(user_id="foo", skill_id="bar", token="x"))
    assert direct._format_log_message("test") == "test"
    assert directv._format_log_message("test") == "test [bar | x]"
    assert cloud._format_log_message("test") == "test"


async def test_notifier_property_entities(hass):
    entry_data = MockConfigEntryData(
        entity_config={
            "switch.test_1": {
                const.CONF_ENTITY_CUSTOM_MODES: {
                    const.MODE_INSTANCE_DISHWASHING: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "input_select.dishwashing"
                    }
                },
                const.CONF_ENTITY_CUSTOM_TOGGLES: {
                    const.TOGGLE_INSTANCE_PAUSE: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "input_boolean.pause"
                    }
                },
                const.CONF_ENTITY_CUSTOM_RANGES: {
                    const.RANGE_INSTANCE_VOLUME: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "input_number.volume"
                    }
                },
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.temperature",
                    },
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.humidity",
                    },
                ],
            },
            "switch.test_2": {
                const.CONF_ENTITY_CUSTOM_MODES: {},
                const.CONF_ENTITY_CUSTOM_TOGGLES: {},
                const.CONF_ENTITY_CUSTOM_RANGES: {},
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.humidity",
                    }
                ],
            },
        }
    )

    notifier = YandexDirectNotifier(hass, entry_data, BASIC_CONFIG)
    assert notifier._get_property_entities() == {
        "input_boolean.pause": ["switch.test_1"],
        "input_number.volume": ["switch.test_1"],
        "input_select.dishwashing": ["switch.test_1"],
        "sensor.temperature": ["switch.test_1"],
        "sensor.humidity": ["switch.test_1", "switch.test_2"],
    }


async def test_notifier_event_handler(hass, mock_call_later):
    entry_data = MockConfigEntryData(
        entity_config={
            "switch.test": {
                const.CONF_ENTITY_CUSTOM_MODES: {},
                const.CONF_ENTITY_CUSTOM_TOGGLES: {},
                const.CONF_ENTITY_CUSTOM_RANGES: {},
                const.CONF_ENTITY_PROPERTIES: [
                    {
                        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
                        const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.humidity",
                    }
                ],
            }
        },
        entity_filter=generate_entity_filter(exclude_entities=["sensor.not_expose"]),
    )

    state_switch = State("switch.test", STATE_ON, attributes={ATTR_VOLTAGE: "3.5"})
    state_temp = State(
        "sensor.temp",
        "5",
        attributes={
            ATTR_UNIT_OF_MEASUREMENT: TEMP_CELSIUS,
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
        },
    )
    state_humidity = State(
        "sensor.humidity",
        "95",
        attributes={
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
            ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
        },
    )
    state_not_expose = State(
        "sensor.not_expose",
        "3",
        attributes={
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
            ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY,
        },
    )
    for s in state_switch, state_temp, state_humidity, state_not_expose:
        hass.states.async_set(s.entity_id, s.state, s.attributes)
    await hass.async_block_till_done()

    notifier = YandexDirectNotifier(hass, entry_data, BASIC_CONFIG)
    await notifier.async_setup()
    assert len(notifier._pending) == 0

    for s in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
        hass.states.async_set(state_temp.entity_id, s, state_temp.attributes)
        await hass.async_block_till_done()
        assert len(notifier._pending) == 0

    assert notifier._unsub_pending is None
    mock_call_later.reset_mock()
    hass.states.async_set(state_temp.entity_id, "6", state_temp.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 1
    assert notifier._unsub_pending is not None
    mock_call_later.assert_called_once()
    assert "_report_states" in str(mock_call_later.call_args[0][2].target)
    mock_call_later.reset_mock()
    notifier._pending.clear()

    hass.states.async_set(state_not_expose.entity_id, "4", state_not_expose.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 0

    hass.states.async_set(state_humidity.entity_id, "60", state_humidity.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 2
    assert [s.device_id for s in notifier._pending] == ["sensor.humidity", "switch.test"]
    mock_call_later.assert_not_called()
    notifier._pending.clear()

    state_switch.attributes = {
        ATTR_VOLTAGE: "3.5",
        ATTR_UNIT_OF_MEASUREMENT: "V",
    }
    hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 0

    state_switch.attributes = {
        ATTR_VOLTAGE: "3",
        ATTR_UNIT_OF_MEASUREMENT: "V",
    }
    hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 1
    notifier._pending.clear()


async def test_notifier_send_initial_report(hass_platform, mock_call_later):
    entry_data = MockConfigEntryData(
        entity_filter=generate_entity_filter(exclude_entities=["switch.test"]),
    )
    notifier = YandexDirectNotifier(hass_platform, entry_data, BASIC_CONFIG)

    hass_platform.states.async_set("switch.test", "on")
    await hass_platform.async_block_till_done()

    await notifier._async_initial_report()
    assert len(notifier._pending) == 2
    assert notifier._pending[0].capabilities == []
    assert notifier._pending[0].properties == [
        {"state": {"instance": "temperature", "value": 15.6}, "type": "devices.properties.float"}
    ]
    assert notifier._pending[1].capabilities == [
        {"state": {"instance": "temperature_k", "value": 4200}, "type": "devices.capabilities.color_setting"},
        {"state": {"instance": "brightness", "value": 70}, "type": "devices.capabilities.range"},
        {"state": {"instance": "on", "value": True}, "type": "devices.capabilities.on_off"},
    ]
    assert notifier._pending[1].properties == []


async def test_notifier_send_callback_exception(hass, caplog):
    notifier = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG)

    with patch.object(notifier, "_log_request", side_effect=ClientConnectionError()):
        caplog.clear()
        await notifier.async_send_discovery()
        assert caplog.messages[-1] == "Failed to send state notification: ClientConnectionError()"
        assert caplog.records[1].levelno == logging.WARN
        caplog.clear()

    with patch.object(notifier, "_log_request", side_effect=asyncio.TimeoutError()):
        await notifier.async_send_state([])
        assert caplog.messages[-1] == "Failed to send state notification: TimeoutError()"
        assert caplog.records[0].levelno == logging.DEBUG


async def test_notifier_report_states(hass, mock_call_later):
    notifier = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG)

    notifier._pending.append(MockDeviceCallbackState("foo", properties=["prop"]))
    notifier._pending.append(MockDeviceCallbackState("bar", capabilities=["cap"]))

    with patch.object(notifier, "async_send_state") as mock_send_state:
        await notifier._async_report_states()
        assert mock_send_state.call_args[0][0] == [
            {"id": "foo", "properties": ["prop"], "capabilities": []},
            {"id": "bar", "properties": [], "capabilities": ["cap"]},
        ]
        mock_call_later.assert_not_called()

    notifier._pending.append(MockDeviceCallbackState("foo", properties=["prop"]))
    with patch.object(
        notifier,
        "async_send_state",
        side_effect=lambda v: notifier._pending.append(MockDeviceCallbackState("test")),
    ) as mock_send_state:
        await notifier._async_report_states()
        assert mock_send_state.call_args[0][0] == [{"id": "foo", "properties": ["prop"], "capabilities": []}]
        mock_call_later.assert_called_once()
        assert "_async_report_states" in str(mock_call_later.call_args[0][2].target)

    notifier._pending.clear()
    mock_call_later.reset_mock()
    notifier._pending.append(MockDeviceCallbackState("foo", properties=["prop"], capabilities=["cap"]))
    notifier._pending.append(MockDeviceCallbackState("bar", properties=["prop1"], capabilities=["cap1"]))
    notifier._pending.append(MockDeviceCallbackState("bar", properties=["prop2"]))
    notifier._pending.append(MockDeviceCallbackState("bar", properties=["prop3"]))

    with patch.object(notifier, "async_send_state") as mock_send_state:
        await notifier._async_report_states()
        assert mock_send_state.call_args[0][0] == [
            {"id": "foo", "properties": ["prop"], "capabilities": ["cap"]},
            {"id": "bar", "properties": ["prop3", "prop2", "prop1"], "capabilities": ["cap1"]},
        ]
        mock_call_later.assert_not_called()


async def test_notifier_send_direct(hass, aioclient_mock, caplog):
    notifier = YandexDirectNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG)
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
    assert aioclient_mock.mock_calls[0][2] == {"ts": now, "payload": {"user_id": user_id}}
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": f"OAuth {token}"}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )

    with patch("time.time", return_value=now):
        await notifier.async_send_state([])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {"ts": now, "payload": {"devices": [], "user_id": user_id}}
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": f"OAuth {token}"}
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state",
        status=400,
        json={"request_id": REQ_ID, "status": "error", "error_message": "some error"},
    )
    with patch("time.time", return_value=now):
        await notifier.async_send_state(["err"])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {
        "ts": now,
        "payload": {"devices": ["err"], "user_id": user_id},
    }
    assert caplog.messages[-1] == "Failed to send state notification: [400] some error"
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        f"https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state",
        status=500,
        content="ERROR",
    )
    await notifier.async_send_state(["err"])
    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Failed to send state notification: [500] ERROR"
    aioclient_mock.clear_requests()
    caplog.clear()

    with patch.object(notifier, "_log_request", side_effect=Exception):
        await notifier.async_send_state([])
        assert aioclient_mock.call_count == 0
    assert "Failed to send state notification" in caplog.messages[-1]


async def test_notifier_send_cloud(hass, aioclient_mock, caplog):
    notifier = YandexCloudNotifier(hass, BASIC_ENTRY_DATA, BASIC_CONFIG)
    token = BASIC_CONFIG.token
    user_id = BASIC_CONFIG.user_id
    now = time.time()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/discovery",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )

    with patch("time.time", return_value=now):
        await notifier.async_send_discovery(None)

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {"ts": now, "payload": {"user_id": user_id}}
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": f"Bearer {token}"}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/state",
        status=202,
        json={"request_id": REQ_ID, "status": "ok"},
    )

    with patch("time.time", return_value=now):
        await notifier.async_send_state([])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {"ts": now, "payload": {"devices": [], "user_id": user_id}}
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": f"Bearer {token}"}
    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/state",
        status=400,
        json={"request_id": REQ_ID, "status": "error", "error_message": "some error"},
    )
    with patch("time.time", return_value=now):
        await notifier.async_send_state(["err"])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {
        "ts": now,
        "payload": {"devices": ["err"], "user_id": user_id},
    }
    assert caplog.messages[-1] == "Failed to send state notification: [400] some error"
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        "https://yaha-cloud.ru/api/home_assistant/v1/callback/state",
        status=500,
        content="ERROR",
    )
    await notifier.async_send_state(["err"])
    assert aioclient_mock.call_count == 1
    assert caplog.messages[-1] == "Failed to send state notification: [500] ERROR"
    aioclient_mock.clear_requests()
    caplog.clear()

    with patch.object(notifier, "_log_request", side_effect=Exception):
        await notifier.async_send_state([])
        assert aioclient_mock.call_count == 0
    assert "Failed to send state notification" in caplog.messages[-1]
