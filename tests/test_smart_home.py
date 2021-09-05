from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import State

from custom_components.yandex_smart_home.capability import MuteCapability, OnOffCapability, PauseCapability
from custom_components.yandex_smart_home.helpers import RequestData
from custom_components.yandex_smart_home.smart_home import async_devices_execute, async_devices_query

from . import BASIC_DATA, REQ_ID, MockConfig


async def test_async_devices_execute(hass):
    class MockOnOffCapability(OnOffCapability):
        def supported(self, *args, **kwargs):
            return True

        async def set_state(self, data, state):
            pass

    class MockMuteCapability(MuteCapability):
        def supported(self, *args, **kwargs):
            return True

        async def set_state(self, data, state):
            pass

    class MockPauseCapability(PauseCapability):
        def supported(self, *args, **kwargs):
            return True

        async def set_state(self, *args, **kwargs):
            raise Exception('fail set_state')

    switch_1 = State('switch.test_1', STATE_OFF)
    switch_2 = State('switch.test_2', STATE_OFF)
    hass.states.async_set(switch_1.entity_id, switch_1.state, switch_1.attributes)
    hass.states.async_set(switch_2.entity_id, switch_2.state, switch_2.attributes)

    with patch('custom_components.yandex_smart_home.capability.CAPABILITIES',
               [MockOnOffCapability, MockMuteCapability, MockPauseCapability]):
        message = {
            'payload': {
                'devices': [{
                    'id': switch_1.entity_id,
                    'capabilities': [{
                        'type': MockOnOffCapability.type,
                        'state': {
                            'instance': 'on',
                            'value': True
                        }
                    }, {
                        'type': MockPauseCapability.type,
                        'state': {
                            'instance': MockPauseCapability.instance,
                            'value': True
                        }
                    }]
                }, {
                    'id': switch_2.entity_id,
                    'capabilities': [{
                        'type': 'unsupported',
                        'state': {
                            'instance': 'on',
                            'value': True
                        }
                    }, {
                        'type': MockMuteCapability.type,
                        'state': {
                            'instance': 'unsupported',
                            'value': True
                        }
                    }]
                }, {
                    'id': 'not_exist',
                    'capabilities': [{
                        'type': MockOnOffCapability.type,
                        'state': {
                            'instance': 'on',
                            'value': True
                        }
                    }]
                }]

            }
        }

        assert await async_devices_execute(hass, BASIC_DATA, message) == {
            'devices': [{
                'id': 'switch.test_1',
                'capabilities': [{
                    'type': 'devices.capabilities.on_off',
                    'state': {'instance': 'on', 'action_result': {'status': 'DONE'}}
                }, {
                    'type': 'devices.capabilities.toggle',
                    'state': {
                        'instance': 'pause',
                        'action_result': {
                            'status': 'ERROR',
                            'error_code': 'INTERNAL_ERROR'
                        }
                    }
                }]
            }, {
                'id': 'switch.test_2',
                'capabilities': [{
                    'type': 'unsupported',
                    'state': {
                        'instance': 'on',
                        'action_result': {
                            'status': 'ERROR',
                            'error_code': 'NOT_SUPPORTED_IN_CURRENT_MODE'
                        }
                    }
                }, {
                    'type': 'devices.capabilities.toggle',
                    'state': {
                        'instance': 'unsupported',
                        'action_result': {
                            'status': 'ERROR',
                            'error_code': 'NOT_SUPPORTED_IN_CURRENT_MODE'
                        }
                    }
                }]
            }, {
                'id': 'not_exist',
                'error_code': 'DEVICE_UNREACHABLE'
            }]
        }


async def test_async_devices_query(hass):
    switch_1 = State('switch.test_1', STATE_OFF)
    switch_not_expose = State('switch.not_expose', STATE_ON)
    hass.states.async_set(switch_1.entity_id, switch_1.state, switch_1.attributes)
    hass.states.async_set(switch_not_expose.entity_id, switch_not_expose.state, switch_not_expose.attributes)

    config = MockConfig(
        should_expose=lambda s: s != 'switch.not_expose'
    )
    data = RequestData(config, 'test', REQ_ID)
    message = {
        'devices': [
            {'id': switch_1.entity_id},
            {'id': switch_not_expose.entity_id},
            {'id': 'invalid'}
        ]
    }

    assert await async_devices_query(hass, data, message) == {
        'devices': [{
            'id': 'switch.test_1',
            'capabilities': [{
                'type': 'devices.capabilities.on_off',
                'state': {'instance': 'on', 'value': False}
            }],
            'properties': []
        }, {
            'id': 'switch.not_expose',
            'capabilities': [{
                'type': 'devices.capabilities.on_off',
                'state': {'instance': 'on', 'value': True}
            }],
            'properties': []
        }, {
            'id': 'invalid',
            'error_code': 'DEVICE_UNREACHABLE'
        }]
    }
