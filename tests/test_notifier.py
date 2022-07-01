import asyncio
import logging
import time
from unittest.mock import PropertyMock, patch

from aiohttp.client_exceptions import ClientConnectionError
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    EVENT_HOMEASSISTANT_STARTED,
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
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.const import (
    CONF_NOTIFIER_OAUTH_TOKEN,
    CONF_NOTIFIER_SKILL_ID,
    CONF_NOTIFIER_USER_ID,
    CONFIG,
    DOMAIN,
    NOTIFIERS,
)
from custom_components.yandex_smart_home.entity import YandexEntityCallbackState
from custom_components.yandex_smart_home.notifier import (
    YandexCloudNotifier,
    YandexDirectNotifier,
    async_setup_notifier,
    async_start_notifier,
    async_unload_notifier,
)
from custom_components.yandex_smart_home.smart_home import RequestData, async_devices

from . import BASIC_CONFIG, REQ_ID, MockConfig, generate_entity_filter


class MockYandexEntityCallbackState(YandexEntityCallbackState):
    # noinspection PyMissingConstructor
    def __init__(self, device_id, capabilities=None, properties=None):
        self.device_id = device_id
        self.old_state = None
        self.capabilities = capabilities or []
        self.properties = properties or []


@pytest.fixture(autouse=True, name='mock_call_later')
def mock_call_later_fixture():
    with patch('custom_components.yandex_smart_home.notifier.async_call_later') as mock_call_later:
        yield mock_call_later


def _mock_entry_with_cloud_connection(_=None, devices_discovered=False) -> MockConfigEntry:
    return MockConfigEntry(data={
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        const.CONF_DEVICES_DISCOVERED: devices_discovered,
        const.CONF_CLOUD_INSTANCE: {
            const.CONF_CLOUD_INSTANCE_ID: 'test_instance',
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: 'foo',
        }
    })


def _mock_entry_with_direct_connection(hass_admin_user, devices_discovered=False) -> MockConfigEntry:
    return MockConfigEntry(data={
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        const.CONF_DEVICES_DISCOVERED: devices_discovered,
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
async def test_notifier_async_start(hass, entry, hass_admin_user):
    async_setup_notifier(hass)

    config = MockConfig(entry=entry(hass_admin_user))
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_event_handler') as mock_evh:
        await async_start_notifier(hass)
        await hass.async_block_till_done()
        assert len(hass.data[DOMAIN][NOTIFIERS]) == 1

        hass.bus.async_fire(EVENT_STATE_CHANGED, {'test': True})
        await hass.async_block_till_done()
        mock_evh.assert_called_once()
        assert mock_evh.call_args[0][0].data == {'test': True}


async def test_notifier_schedule_discovery_on_start(hass, mock_call_later, hass_admin_user):
    async_setup_notifier(hass)

    entry = _mock_entry_with_cloud_connection(devices_discovered=True)
    entry.add_to_hass(hass)

    config = MockConfig(entry=entry)
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    await async_start_notifier(hass)

    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]

    assert notifier._unsub_send_discovery is None
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert notifier._unsub_send_discovery is not None

    await async_unload_notifier(hass)
    await hass.async_block_till_done()

    # noinspection PyUnresolvedReferences
    notifier._unsub_send_discovery.assert_called_once()


async def test_notifier_schedule_discovery_on_config_change(hass, mock_call_later, hass_admin_user):
    async_setup_notifier(hass)

    entry = _mock_entry_with_cloud_connection(devices_discovered=True)
    entry.add_to_hass(hass)

    config = MockConfig(entry=entry)
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    await async_start_notifier(hass)

    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_schedule_discovery') as mock:
        hass.bus.async_fire(const.EVENT_CONFIG_CHANGED)
        await hass.async_block_till_done()
        mock.assert_called_once_with(5)


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
    assert n1._format_log_message('test') == 'test'

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
async def test_notifier_event_handler_not_ready(hass, hass_admin_user, entry, mock_call_later):
    async_setup_notifier(hass)

    config = MockConfig(entry=entry(hass_admin_user, devices_discovered=False))
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }
    await async_start_notifier(hass)

    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1

    state_switch = State('switch.test', STATE_ON, attributes={
        ATTR_VOLTAGE: '3.5'
    })
    hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)

    mock_call_later.reset_mock()
    hass.states.async_set(state_switch.entity_id, 'off')
    await hass.async_block_till_done()
    mock_call_later.assert_not_called()

    hass.data[DOMAIN][CONFIG] = MockConfig(
        entry=entry(hass_admin_user, devices_discovered=True),
        entity_filter=generate_entity_filter(include_entity_globs=['*'])
    )
    hass.states.async_set(state_switch.entity_id, 'on')
    await hass.async_block_till_done()
    mock_call_later.assert_called_once()
    assert '_report_states' in str(mock_call_later.call_args[0][2].target)


@pytest.mark.parametrize('entry', [_mock_entry_with_cloud_connection, _mock_entry_with_direct_connection])
async def test_notifier_event_handler(hass, hass_admin_user, entry, mock_call_later):
    async_setup_notifier(hass)

    config = MockConfig(
        entry=entry(hass_admin_user, devices_discovered=True),
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
        },
        entity_filter=generate_entity_filter(exclude_entities=['sensor.not_expose'])
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }
    await async_start_notifier(hass)

    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]

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
    assert len(notifier._pending) == 0

    for s in [STATE_UNAVAILABLE, STATE_UNKNOWN, None]:
        hass.states.async_set(state_temp.entity_id, s, state_temp.attributes)
        await hass.async_block_till_done()
        assert len(notifier._pending) == 0

    assert notifier._unsub_pending is None
    mock_call_later.reset_mock()
    hass.states.async_set(state_temp.entity_id, '6', state_temp.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 1
    assert notifier._unsub_pending is not None
    mock_call_later.assert_called_once()
    assert '_report_states' in str(mock_call_later.call_args[0][2].target)
    mock_call_later.reset_mock()
    notifier._pending.clear()

    hass.states.async_set(state_not_expose.entity_id, '4', state_not_expose.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 0

    hass.states.async_set(state_humidity.entity_id, '60', state_humidity.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 2
    assert [s.device_id for s in notifier._pending] == ['sensor.humidity', 'switch.test']
    mock_call_later.assert_not_called()
    notifier._pending.clear()

    state_switch.attributes = {
        ATTR_VOLTAGE: '3.5',
        ATTR_UNIT_OF_MEASUREMENT: 'V',
    }
    hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 0

    state_switch.attributes = {
        ATTR_VOLTAGE: '3',
        ATTR_UNIT_OF_MEASUREMENT: 'V',
    }
    hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
    await hass.async_block_till_done()
    assert len(notifier._pending) == 1
    notifier._pending.clear()

    hass.states.async_remove(state_switch.entity_id)
    hass.states.async_set(state_humidity.entity_id, '70', state_humidity.attributes)
    await hass.async_block_till_done()

    await async_unload_notifier(hass)


async def test_notifier_check_for_devices_discovered(hass_platform_cloud_connection, caplog):
    hass = hass_platform_cloud_connection
    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier._async_send_callback') as mock_send_cb:
        await notifier.async_send_discovery(None)
        mock_send_cb.assert_not_called()

    with patch('custom_components.yandex_smart_home.cloud.CloudManager.connect', return_value=None):
        await async_devices(hass, RequestData(hass.data[DOMAIN][CONFIG], None, None), {})
        await hass.async_block_till_done()

    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]
    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier._async_send_callback') as mock_send_cb:
        await notifier.async_send_discovery(None)
        mock_send_cb.assert_called_once()


async def test_notifier_schedule_initial_report(hass_platform_cloud_connection, mock_call_later):
    hass = hass_platform_cloud_connection

    hass.bus.async_fire(const.EVENT_DEVICE_DISCOVERY)
    await hass.async_block_till_done()

    assert len(mock_call_later.call_args_list) == 3

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_initial_report') as mock_ir:
        await mock_call_later.call_args_list[0][0][2].target(None)
        mock_ir.assert_called()


async def test_notifier_send_initial_report(hass_platform_cloud_connection):
    hass = hass_platform_cloud_connection
    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]
    hass.data[DOMAIN][CONFIG]._entity_filter = generate_entity_filter(
        include_entity_globs=['*'],
        exclude_entities=['switch.test']
    )

    hass.states.async_set('switch.test', 'on')
    await hass.async_block_till_done()

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier._ready', new_callable=PropertyMock(
            return_value=False
    )):
        await notifier.async_initial_report()
        assert len(notifier._pending) == 0

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier._ready', new_callable=PropertyMock(
            return_value=True
    )):
        await notifier.async_initial_report()
        assert len(notifier._pending) == 2
        assert notifier._pending[0].capabilities == []
        assert notifier._pending[0].properties == [{
            'state': {'instance': 'temperature', 'value': 15.6},
            'type': 'devices.properties.float'
        }]
        print(notifier._pending[1].device_id)
        assert notifier._pending[1].capabilities == [
            {'state': {'instance': 'temperature_k', 'value': 4200}, 'type': 'devices.capabilities.color_setting'},
            {'state': {'instance': 'brightness', 'value': 70}, 'type': 'devices.capabilities.range'},
            {'state': {'instance': 'on', 'value': True}, 'type': 'devices.capabilities.on_off'}
        ]
        assert notifier._pending[1].properties == []


async def test_notifier_async_send_callback(hass_platform_cloud_connection, caplog):
    hass = hass_platform_cloud_connection
    assert len(hass.data[DOMAIN][NOTIFIERS]) == 1
    notifier = hass.data[DOMAIN][NOTIFIERS][0]

    with patch.object(notifier, '_log_request', side_effect=ClientConnectionError()), patch(
            'custom_components.yandex_smart_home.notifier.YandexNotifier._ready',
            new_callable=PropertyMock(return_value=True)
    ):
        caplog.clear()
        await notifier.async_send_discovery(None)
        assert len(caplog.records) == 2
        assert 'Failed to send state notification: ClientConnectionError()' in caplog.records[1].message
        assert caplog.records[1].levelno == logging.WARN
        caplog.clear()

    with patch.object(notifier, '_log_request', side_effect=asyncio.TimeoutError()), patch(
            'custom_components.yandex_smart_home.notifier.YandexNotifier._ready',
            new_callable=PropertyMock(return_value=True)
    ):
        await notifier.async_send_state([])
        assert len(caplog.records) == 1
        assert 'Failed to send state notification: TimeoutError()' in caplog.records[0].message
        assert caplog.records[0].levelno == logging.DEBUG


async def test_notifier_report_states(hass, hass_admin_user, mock_call_later):
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [],
    }

    notifier = YandexCloudNotifier(hass, hass_admin_user.id, 'foo')

    notifier._pending.append(MockYandexEntityCallbackState('foo', properties=['prop']))
    notifier._pending.append(MockYandexEntityCallbackState('bar', capabilities=['cap']))

    with patch.object(notifier, 'async_send_state') as mock_send_state:
        await notifier._report_states(None)
        assert mock_send_state.call_args[0][0] == [
            {'id': 'foo', 'properties': ['prop'], 'capabilities': []},
            {'id': 'bar', 'properties': [], 'capabilities': ['cap']}
        ]
        mock_call_later.assert_not_called()

    notifier._pending.append(MockYandexEntityCallbackState('foo', properties=['prop']))
    with patch.object(notifier, 'async_send_state',
                      side_effect=lambda v: notifier._pending.append(
                          MockYandexEntityCallbackState('test')
                      )) as mock_send_state:
        await notifier._report_states(None)
        assert mock_send_state.call_args[0][0] == [{'id': 'foo', 'properties': ['prop'], 'capabilities': []}]
        mock_call_later.assert_called_once()
        assert '_report_states' in str(mock_call_later.call_args[0][2].target)

    notifier._pending.clear()
    mock_call_later.reset_mock()
    notifier._pending.append(MockYandexEntityCallbackState('foo', properties=['prop'], capabilities=['cap']))
    notifier._pending.append(MockYandexEntityCallbackState('bar', properties=['prop1'], capabilities=['cap1']))
    notifier._pending.append(MockYandexEntityCallbackState('bar', properties=['prop2']))
    notifier._pending.append(MockYandexEntityCallbackState('bar', properties=['prop3']))

    with patch.object(notifier, 'async_send_state') as mock_send_state:
        await notifier._report_states(None)
        assert mock_send_state.call_args[0][0] == [
            {'id': 'foo', 'properties': ['prop'], 'capabilities': ['cap']},
            {'id': 'bar', 'properties': ['prop3', 'prop2', 'prop1'], 'capabilities': ['cap1']},
        ]
        mock_call_later.assert_not_called()


async def test_notifier_send_direct(hass, hass_admin_user, aioclient_mock):
    config = MockConfig(
        entry=_mock_entry_with_direct_connection(hass_admin_user, devices_discovered=True)
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
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
    config = MockConfig(
        entry=_mock_entry_with_cloud_connection(hass_admin_user, devices_discovered=True)
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
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
