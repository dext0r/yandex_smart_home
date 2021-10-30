import asyncio
import time
from unittest.mock import patch

from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    EVENT_STATE_CHANGED,
    PERCENTAGE,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)
from homeassistant.core import State
from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch_yaml_files

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.const import (
    CONF_NOTIFIER_OAUTH_TOKEN,
    CONF_NOTIFIER_SKILL_ID,
    CONF_NOTIFIER_USER_ID,
    CONFIG,
    DOMAIN,
    NOTIFIERS,
)
from custom_components.yandex_smart_home.notifier import (
    YandexCloudNotifier,
    YandexDirectNotifier,
    async_setup_notifier,
    async_start_notifier,
    async_unload_notifier,
)
from custom_components.yandex_smart_home.smart_home import RequestData, async_devices

from . import BASIC_CONFIG, REQ_ID, MockConfig


@pytest.fixture(autouse=True, name='mock_call_later')
def mock_call_later_fixture():
    with patch('custom_components.yandex_smart_home.notifier.async_call_later') as mock_call_later:
        yield mock_call_later


def _mock_entry_with_cloud_connection(*_) -> MockConfigEntry:
    return MockConfigEntry(data={
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        const.CONF_CLOUD_INSTANCE: {
            const.CONF_CLOUD_INSTANCE_ID: 'test_instance',
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: 'foo',
        }
    })


def _mock_entry_with_direct_connection(hass_admin_user) -> MockConfigEntry:
    return MockConfigEntry(data={
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        const.CONF_NOTIFIER: [{
            CONF_NOTIFIER_USER_ID: hass_admin_user.id,
            CONF_NOTIFIER_OAUTH_TOKEN: 'foo',
            CONF_NOTIFIER_SKILL_ID: ''
        }]
    })


async def test_notifier_async_start_direct_invalid(hass, mock_call_later, hass_admin_user):
    async_setup_notifier(hass)

    entry = MockConfigEntry(data={
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        const.CONF_NOTIFIER: [{
            CONF_NOTIFIER_USER_ID: hass_admin_user.id,
            CONF_NOTIFIER_OAUTH_TOKEN: 'token',
            CONF_NOTIFIER_SKILL_ID: 'skill_id',
        }, {
            CONF_NOTIFIER_USER_ID: 'invalid',
            CONF_NOTIFIER_OAUTH_TOKEN: 'token',
            CONF_NOTIFIER_SKILL_ID: 'skill_id'
        }]
    })
    config = MockConfig(entry=entry)
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }
    with pytest.raises(ConfigEntryNotReady):
        await async_start_notifier(hass)


@pytest.mark.parametrize('entry', [_mock_entry_with_cloud_connection, _mock_entry_with_direct_connection])
async def test_notifier_async_start(hass, entry, mock_call_later, hass_admin_user):
    async_setup_notifier(hass)

    config = MockConfig(entry=entry(hass_admin_user))
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_send_discovery') as mock_discovery, \
         patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_event_handler') as mock_evh, \
         patch('custom_components.yandex_smart_home.notifier.DISCOVERY_REQUEST_DELAY', 0):
        mock_call_later.reset_mock()

        await async_start_notifier(hass)
        assert len(hass.data[DOMAIN][NOTIFIERS]) == 1

        await hass.async_block_till_done()
        mock_call_later.assert_called_once()

        await mock_call_later.call_args[0][2]()
        mock_discovery.assert_called_once()

        hass.bus.async_fire(EVENT_STATE_CHANGED, {'test': True})
        await hass.async_block_till_done()
        mock_evh.assert_called_once()
        assert mock_evh.call_args[0][0].data == {'test': True}


async def test_notifier_format_log_message(hass, hass_admin_user):
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [],
    }

    n1 = YandexDirectNotifier(hass, hass_admin_user.id, 'n1_token', 'n1_skill_id')
    n2 = YandexDirectNotifier(hass, hass_admin_user.id, 'n2_token', 'n2_skill_id')
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [n1],
    }
    assert n1._format_log_message('test') == '[direct] test'

    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [n1, n2],
    }
    assert n1._format_log_message('test') == f'[n1_skill_id | {hass_admin_user.id}] test'


async def test_notifier_property_entities(hass, hass_admin_user):
    config = MockConfig(
        entity_config={
            'switch.test_1': {
                const.CONF_ENTITY_CUSTOM_MODES: {
                    const.MODE_INSTANCE_DISHWASHING: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: 'input_select.dishwashing'
                    }
                },
                const.CONF_ENTITY_CUSTOM_TOGGLES: {
                    const.TOGGLE_INSTANCE_PAUSE: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: 'input_boolean.pause'
                    }
                },
                const.CONF_ENTITY_CUSTOM_RANGES: {
                    const.RANGE_INSTANCE_VOLUME: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: 'input_number.volume'
                    }
                },
                const.CONF_ENTITY_PROPERTIES: [{
                    const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.temperature'
                }, {
                    const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.humidity'
                }]
            },
            'switch.test_2': {
                const.CONF_ENTITY_CUSTOM_MODES: {},
                const.CONF_ENTITY_CUSTOM_TOGGLES: {},
                const.CONF_ENTITY_CUSTOM_RANGES: {},
                const.CONF_ENTITY_PROPERTIES: [{
                    const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.humidity'
                }]
            }
        }
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    notifier = YandexDirectNotifier(hass, '', '', hass_admin_user.id)
    assert notifier._get_property_entities() == {
        'input_boolean.pause': ['switch.test_1'],
        'input_number.volume': ['switch.test_1'],
        'input_select.dishwashing': ['switch.test_1'],
        'sensor.temperature': ['switch.test_1'],
        'sensor.humidity': ['switch.test_1', 'switch.test_2']
    }


@pytest.mark.parametrize('entry', [_mock_entry_with_cloud_connection, _mock_entry_with_direct_connection])
async def test_notifier_event_handler(hass, hass_admin_user, entry):
    async_setup_notifier(hass)

    config = MockConfig(
        entry=entry(hass_admin_user),
        should_expose=lambda e: e != 'sensor.not_expose',
        entity_config={
            'switch.test': {
                const.CONF_ENTITY_CUSTOM_MODES: {},
                const.CONF_ENTITY_CUSTOM_TOGGLES: {},
                const.CONF_ENTITY_CUSTOM_RANGES: {},
                const.CONF_ENTITY_PROPERTIES: [{
                    const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.humidity'
                }]
            }
        }
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }
    await async_start_notifier(hass)

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_send_state') as mock_notify:
        assert len(hass.data[DOMAIN][NOTIFIERS]) == 1

        state_switch = State('switch.test', STATE_ON, attributes={
            ATTR_VOLTAGE: '3.5'
        })
        state_temp = State('sensor.temp', '5', attributes={
            ATTR_UNIT_OF_MEASUREMENT: TEMP_CELSIUS,
            ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        })
        state_humidity = State('sensor.humidity', '95', attributes={
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
            ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
        })
        state_not_expose = State('sensor.not_expose', '3', attributes={
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
            ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
        })
        for s in state_switch, state_temp, state_humidity, state_not_expose:
            hass.states.async_set(s.entity_id, s.state, s.attributes)

        await hass.async_block_till_done()
        mock_notify.assert_not_called()

        for s in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
            hass.states.async_set(state_temp.entity_id, s, state_temp.attributes)
            await hass.async_block_till_done()
            mock_notify.assert_not_called()

        hass.states.async_set(state_temp.entity_id, '6', state_temp.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_called_once()
        mock_notify.reset_mock()

        hass.states.async_set(state_not_expose.entity_id, '4', state_not_expose.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_not_called()

        hass.states.async_set(state_humidity.entity_id, '60', state_humidity.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_called_once()
        assert [c['id'] for c in mock_notify.call_args[0][0]] == ['sensor.humidity', 'switch.test']
        mock_notify.reset_mock()

        state_switch.attributes = {
            ATTR_VOLTAGE: '3.5',
            ATTR_UNIT_OF_MEASUREMENT: 'V',
        }
        hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_not_called()

        state_switch.attributes = {
            ATTR_VOLTAGE: '3',
            ATTR_UNIT_OF_MEASUREMENT: 'V',
        }
        hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_called_once()
        mock_notify.reset_mock()

        hass.states.async_remove(state_switch.entity_id)
        hass.states.async_set(state_humidity.entity_id, '70', state_humidity.attributes)
        await hass.async_block_till_done()

    async_unload_notifier(hass)


async def test_notifier_check_for_devices_discovered(hass_platform_cloud_connection, caplog):
    hass = hass_platform_cloud_connection
    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1

    notifier = hass.data[DOMAIN][NOTIFIERS][0]

    await notifier.async_send_discovery(None)
    assert len(caplog.records) == 2
    assert 'devices is not discovered' in caplog.records[1].message
    caplog.clear()

    await notifier.async_send_state([])
    assert len(caplog.records) == 1
    assert 'devices is not discovered' in caplog.records[0].message
    caplog.clear()

    with patch_yaml_files({YAML_CONFIG_FILE: ''}), patch(
            'custom_components.yandex_smart_home.cloud.CloudManager.connect', return_value=None):
        await async_devices(hass, RequestData(hass.data[DOMAIN][CONFIG], None, None), {})
        await hass.async_block_till_done()

    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]
    with patch.object(notifier, '_log_request', side_effect=Exception()):
        caplog.clear()
        await notifier.async_send_discovery(None)
        assert len(caplog.records) == 2
        assert 'Failed to send state notification' in caplog.records[1].message
        caplog.clear()

        await notifier.async_send_state([])
        assert len(caplog.records) == 1
        assert 'Failed to send state notification' in caplog.records[0].message
        caplog.clear()

    with patch.object(notifier, '_log_request', side_effect=asyncio.TimeoutError()):
        caplog.clear()
        await notifier.async_send_discovery(None)
        assert len(caplog.records) == 2
        assert 'Failed to send state notification: TimeoutError()' in caplog.records[1].message
        caplog.clear()

        await notifier.async_send_state([])
        assert len(caplog.records) == 1
        assert 'Failed to send state notification: TimeoutError()' in caplog.records[0].message
        caplog.clear()


async def test_notifier_send_direct(hass, hass_admin_user, aioclient_mock):
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [],
    }

    token = '7b3909b0-447c-4d36-9159-6908b06a1c32'
    skill_id = '0aaa1468-602d-4232-a9e2-62a18f32760f'
    now = time.time()
    notifier = YandexDirectNotifier(hass, hass_admin_user.id, token, skill_id)

    aioclient_mock.post(
        f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/discovery',
        status=202,
        json={'request_id': REQ_ID, 'status': 'ok'},
    )

    with patch('time.time', return_value=now):
        await notifier.async_send_discovery(None)

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {'ts': now, 'payload': {'user_id': hass_admin_user.id}}
    assert aioclient_mock.mock_calls[0][3] == {'Authorization': f'OAuth {token}'}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state',
        status=202,
        json={'request_id': REQ_ID, 'status': 'ok'},
    )

    with patch('time.time', return_value=now):
        await notifier.async_send_state([])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {'ts': now, 'payload': {'devices': [], 'user_id': hass_admin_user.id}}
    assert aioclient_mock.mock_calls[0][3] == {'Authorization': f'OAuth {token}'}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state',
        status=400,
        json={'request_id': REQ_ID, 'status': 'error', 'error_message': 'some error'},
    )
    with patch('time.time', return_value=now):
        await notifier.async_send_state(['err'])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {
        'ts': now, 'payload': {'devices': ['err'], 'user_id': hass_admin_user.id}
    }
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/callback/state',
        status=500,
        content='ERROR',
    )
    await notifier.async_send_state(['err'])
    assert aioclient_mock.call_count == 1
    aioclient_mock.clear_requests()

    with patch.object(YandexDirectNotifier, '_log_request', side_effect=Exception):
        await notifier.async_send_state([])
        assert aioclient_mock.call_count == 0


async def test_notifier_send_cloud(hass, hass_admin_user, aioclient_mock):
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [],
    }

    token = 'foo'
    now = time.time()
    notifier = YandexCloudNotifier(hass, hass_admin_user.id, token)

    aioclient_mock.post(
        'https://yaha-cloud.ru/api/home_assistant/v1/callback/discovery',
        status=202,
        json={'request_id': REQ_ID, 'status': 'ok'},
    )

    with patch('time.time', return_value=now):
        await notifier.async_send_discovery(None)

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {'ts': now, 'payload': {'user_id': hass_admin_user.id}}
    assert aioclient_mock.mock_calls[0][3] == {'Authorization': f'Bearer {token}'}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        'https://yaha-cloud.ru/api/home_assistant/v1/callback/state',
        status=202,
        json={'request_id': REQ_ID, 'status': 'ok'},
    )

    with patch('time.time', return_value=now):
        await notifier.async_send_state([])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {'ts': now, 'payload': {'devices': [], 'user_id': hass_admin_user.id}}
    assert aioclient_mock.mock_calls[0][3] == {'Authorization': f'Bearer {token}'}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        'https://yaha-cloud.ru/api/home_assistant/v1/callback/state',
        status=400,
        json={'request_id': REQ_ID, 'status': 'error', 'error_message': 'some error'},
    )
    with patch('time.time', return_value=now):
        await notifier.async_send_state(['err'])

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {
        'ts': now, 'payload': {'devices': ['err'], 'user_id': hass_admin_user.id}
    }
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        'https://yaha-cloud.ru/api/home_assistant/v1/callback/state',
        status=500,
        content='ERROR',
    )
    await notifier.async_send_state(['err'])
    assert aioclient_mock.call_count == 1
    aioclient_mock.clear_requests()

    with patch.object(YandexDirectNotifier, '_log_request', side_effect=Exception):
        await notifier.async_send_state([])
        assert aioclient_mock.call_count == 0

    aioclient_mock.clear_requests()
    await notifier._session.close()
    await notifier.async_send_state([])

    assert aioclient_mock.call_count == 0
