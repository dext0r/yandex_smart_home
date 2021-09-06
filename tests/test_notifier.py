import time
from unittest.mock import patch

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    ELECTRIC_POTENTIAL_VOLT,
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

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.const import (
    CONF_NOTIFIER_USER_ID,
    CONF_SKILL_ID,
    CONF_SKILL_OAUTH_TOKEN,
    CONFIG,
    DOMAIN,
    NOTIFIERS,
)
from custom_components.yandex_smart_home.notifier import (
    DISCOVERY_URL,
    SKILL_API_URL,
    STATE_URL,
    YandexNotifier,
    async_setup_notifier,
)

from . import BASIC_CONFIG, REQ_ID, MockConfig


async def test_notifier_async_setup(hass, hass_admin_user):
    config = MockConfig(
        notifier=[{
            CONF_NOTIFIER_USER_ID: hass_admin_user.id,
            CONF_SKILL_OAUTH_TOKEN: 'token',
            CONF_SKILL_ID: 'skill_id',
        }, {
            CONF_NOTIFIER_USER_ID: 'invalid',
            CONF_SKILL_OAUTH_TOKEN: 'token',
            CONF_SKILL_ID: 'skill_id',
        }]
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_notifier(hass, reload=False)

    config = MockConfig(
        notifier=[{
            CONF_NOTIFIER_USER_ID: hass_admin_user.id,
            CONF_SKILL_OAUTH_TOKEN: 'token',
            CONF_SKILL_ID: 'skill_id',
        }]
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_send_discovery') as mock_discovery, \
         patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_event_handler') as mock_evh, \
         patch('custom_components.yandex_smart_home.notifier.DISCOVERY_REQUEST_DELAY', 0):
        await async_setup_notifier(hass, reload=False)
        assert len(hass.data[DOMAIN][NOTIFIERS]) == 1

        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
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

    n1 = YandexNotifier(hass, 'n1_token', 'n1_skill_id', hass_admin_user.id)
    n2 = YandexNotifier(hass, 'n2_token', 'n2_skill_id', hass_admin_user.id)
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [n1],
    }
    assert n1.format_log_message('test') == 'test'

    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [n1, n2],
    }
    assert n1.format_log_message('test') == f'[n1_skill_id | {hass_admin_user.id}] test'


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
                    const.CONF_ENTITY_PROPERTY_TYPE: const.PROPERTY_TYPE_TEMPERATURE,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.temperature'
                }, {
                    const.CONF_ENTITY_PROPERTY_TYPE: const.PROPERTY_TYPE_HUMIDITY,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.humidity'
                }]
            },
            'switch.test_2': {
                const.CONF_ENTITY_CUSTOM_MODES: {},
                const.CONF_ENTITY_CUSTOM_TOGGLES: {},
                const.CONF_ENTITY_CUSTOM_RANGES: {},
                const.CONF_ENTITY_PROPERTIES: [{
                    const.CONF_ENTITY_PROPERTY_TYPE: const.PROPERTY_TYPE_HUMIDITY,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.humidity'
                }]
            }
        }
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    notifier = YandexNotifier(hass, '', '', hass_admin_user.id)
    assert notifier.get_property_entities() == {
        'input_boolean.pause': ['switch.test_1'],
        'input_number.volume': ['switch.test_1'],
        'input_select.dishwashing': ['switch.test_1'],
        'sensor.temperature': ['switch.test_1'],
        'sensor.humidity': ['switch.test_1', 'switch.test_2']
    }


async def test_notifier_event_handler(hass, hass_admin_user):
    config = MockConfig(
        should_expose=lambda e: e != 'sensor.not_expose',
        notifier=[{
            CONF_NOTIFIER_USER_ID: hass_admin_user.id,
            CONF_SKILL_OAUTH_TOKEN: '',
            CONF_SKILL_ID: '',
        }],
        entity_config={
            'switch.test': {
                const.CONF_ENTITY_CUSTOM_MODES: {},
                const.CONF_ENTITY_CUSTOM_TOGGLES: {},
                const.CONF_ENTITY_CUSTOM_RANGES: {},
                const.CONF_ENTITY_PROPERTIES: [{
                    const.CONF_ENTITY_PROPERTY_TYPE: const.PROPERTY_TYPE_HUMIDITY,
                    const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.humidity'
                }]
            }
        }
    )
    hass.data[DOMAIN] = {
        CONFIG: config,
        NOTIFIERS: [],
    }

    with patch('custom_components.yandex_smart_home.notifier.YandexNotifier.async_send_state') as mock_notify:
        await async_setup_notifier(hass, reload=False)
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
            ATTR_UNIT_OF_MEASUREMENT: ELECTRIC_POTENTIAL_VOLT,
        }
        hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_not_called()

        state_switch.attributes = {
            ATTR_VOLTAGE: '3',
            ATTR_UNIT_OF_MEASUREMENT: ELECTRIC_POTENTIAL_VOLT,
        }
        hass.states.async_set(state_switch.entity_id, state_switch.state, state_switch.attributes)
        await hass.async_block_till_done()
        mock_notify.assert_called_once()
        mock_notify.reset_mock()


async def test_notifier_notify_skill(hass, hass_admin_user, aioclient_mock):
    hass.data[DOMAIN] = {
        CONFIG: BASIC_CONFIG,
        NOTIFIERS: [],
    }

    token = '7b3909b0-447c-4d36-9159-6908b06a1c32'
    skill_id = '0aaa1468-602d-4232-a9e2-62a18f32760f'
    now = time.time()
    notifier = YandexNotifier(hass, token, skill_id, hass_admin_user.id)

    aioclient_mock.post(
        f'{SKILL_API_URL}/{skill_id}/{DISCOVERY_URL}',
        status=202,
        json={'request_id': REQ_ID, 'status': 'ok'},
    )

    with patch('time.time', return_value=now):
        await notifier.async_send_discovery()

    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][2] == {'ts': now, 'payload': {'user_id': hass_admin_user.id}}
    assert aioclient_mock.mock_calls[0][3] == {'Authorization': f'OAuth {token}'}
    aioclient_mock.clear_requests()

    aioclient_mock.post(
        f'{SKILL_API_URL}/{skill_id}/{STATE_URL}',
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
        f'{SKILL_API_URL}/{skill_id}/{STATE_URL}',
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
        f'{SKILL_API_URL}/{skill_id}/{STATE_URL}',
        status=500,
        content='ERROR',
    )
    await notifier.async_send_state(['err'])
    assert aioclient_mock.call_count == 1
    aioclient_mock.clear_requests()

    with patch.object(YandexNotifier, 'log_request') as m:
        m.side_effect = Exception
        await notifier.async_send_state(['err'])
        assert aioclient_mock.call_count == 0
