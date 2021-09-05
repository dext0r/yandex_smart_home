from unittest.mock import patch

from homeassistant.const import STATE_OFF
from homeassistant.core import State

from custom_components.yandex_smart_home.capability import MuteCapability, OnOffCapability, PauseCapability
from custom_components.yandex_smart_home.smart_home import handle_devices_execute

from . import BASIC_DATA


async def test_devices_execute(hass):
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

        assert await handle_devices_execute(hass, BASIC_DATA, message) == {
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
