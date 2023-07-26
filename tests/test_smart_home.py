from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import State
from homeassistant.helpers.template import Template
from homeassistant.util.decorator import Registry

from custom_components.yandex_smart_home.capability_onoff import OnOffCapability
from custom_components.yandex_smart_home.capability_toggle import ToggleCapability
from custom_components.yandex_smart_home.const import ERR_INTERNAL_ERROR, ERR_INVALID_ACTION, EVENT_DEVICE_ACTION
from custom_components.yandex_smart_home.error import SmartHomeError
from custom_components.yandex_smart_home.helpers import RequestData
from custom_components.yandex_smart_home.smart_home import (
    async_devices,
    async_devices_execute,
    async_devices_query,
    async_handle_message,
)

from . import BASIC_DATA, REQ_ID, MockConfig, generate_entity_filter


async def test_async_handle_message(hass):
    handlers = Registry()

    # noinspection PyUnusedLocal
    @handlers.register('error')
    async def error(*args, **kwargs):
        raise SmartHomeError(ERR_INVALID_ACTION, '')

    # noinspection PyUnusedLocal
    @handlers.register('exception')
    async def exception(*args, **kwargs):
        raise ValueError('some handle error')

    # noinspection PyUnusedLocal
    @handlers.register('none')
    async def none(*args, **kwargs):
        return None

    with patch('custom_components.yandex_smart_home.smart_home.HANDLERS', handlers):
        assert await async_handle_message(hass, BASIC_DATA, 'missing', {}) == {
            'request_id': REQ_ID,
            'payload': {
                'error_code': ERR_INTERNAL_ERROR
            }
        }

        assert await async_handle_message(hass, BASIC_DATA, 'error', {}) == {
            'request_id': REQ_ID,
            'payload': {
                'error_code': ERR_INVALID_ACTION
            }
        }

        assert await async_handle_message(hass, BASIC_DATA, 'exception', {}) == {
            'request_id': REQ_ID,
            'payload': {
                'error_code': ERR_INTERNAL_ERROR
            }
        }

        assert await async_handle_message(hass, BASIC_DATA, 'none', {}) == {
            'request_id': REQ_ID,
        }


async def test_async_devices_execute(hass):
    class MockCapabilityA(OnOffCapability):
        def supported(self) -> bool:
            return True

        def get_value(self) -> float | str | None:
            return None

        async def set_state(self, data, state):
            pass

        async def _set_state(self, data: RequestData, state: dict[str, Any]):
            pass

    class MockCapabilityB(ToggleCapability):
        instance = 'b'

        def supported(self) -> bool:
            return True

        def get_value(self) -> float | str | None:
            return None

        async def set_state(self, data, state):
            return {'foo': 'bar', 'int': 0}

    class MockCapabilityWithFail(ToggleCapability):
        instance = 'fail'

        def supported(self) -> bool:
            return True

        def get_value(self) -> float | str | None:
            return None

        async def set_state(self, *args, **kwargs):
            raise Exception('fail set_state')

    switch_1 = State('switch.test_1', STATE_OFF)
    switch_2 = State('switch.test_2', STATE_OFF)
    switch_3 = State('switch.test_3', STATE_UNAVAILABLE)
    hass.states.async_set(switch_1.entity_id, switch_1.state, switch_1.attributes)
    hass.states.async_set(switch_2.entity_id, switch_2.state, switch_2.attributes)
    hass.states.async_set(switch_3.entity_id, switch_3.state, switch_3.attributes)
    device_action_event = Mock()
    hass.bus.async_listen(EVENT_DEVICE_ACTION, device_action_event)

    with patch('custom_components.yandex_smart_home.capability.CAPABILITIES',
               [MockCapabilityA, MockCapabilityB, MockCapabilityWithFail]):
        message = {
            'payload': {
                'devices': [{
                    'id': switch_1.entity_id,
                    'capabilities': [{
                        'type': MockCapabilityA.type,
                        'state': {
                            'instance': MockCapabilityA.instance,
                            'value': True
                        }
                    }, {
                        'type': MockCapabilityB.type,
                        'state': {
                            'instance': MockCapabilityB.instance,
                            'value': True
                        }
                    }, {
                        'type': MockCapabilityWithFail.type,
                        'state': {
                            'instance': MockCapabilityWithFail.instance,
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
                        'type': MockCapabilityB.type,
                        'state': {
                            'instance': 'unsupported',
                            'value': True
                        }
                    }]
                }, {
                    'id': switch_3.entity_id,
                    'capabilities': [{
                        'type': MockCapabilityA.type,
                        'state': {
                            'instance': MockCapabilityA.instance,
                            'value': True
                        }
                    }]
                }, {
                    'id': 'not_exist',
                    'capabilities': [{
                        'type': MockCapabilityA.type,
                        'state': {
                            'instance': MockCapabilityA.instance,
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
                        'instance': 'b',
                        'action_result': {
                            'status': 'DONE',
                        },
                        'value': {
                            'foo': 'bar',
                            'int': 0
                        }
                    }
                }, {
                    'type': 'devices.capabilities.toggle',
                    'state': {
                        'instance': 'fail',
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
                'id': 'switch.test_3',
                'error_code': 'DEVICE_UNREACHABLE'
            }, {
                'id': 'not_exist',
                'error_code': 'DEVICE_UNREACHABLE'
            }]
        }

        await hass.async_block_till_done()

        assert device_action_event.call_count == 2
        args, _ = device_action_event.call_args_list[0]
        assert args[0].as_dict()['data'] == {
            'entity_id': 'switch.test_1',
            'capability': {
                'state': {
                    'instance': 'on', 'value': True
                },
                'type': 'devices.capabilities.on_off'
            }
        }

        args, _ = device_action_event.call_args_list[1]
        assert args[0].as_dict()['data'] == {
            'entity_id': 'switch.test_1',
            'capability': {
                'state': {
                    'instance': 'b', 'value': True
                },
                'type': 'devices.capabilities.toggle'
            }
        }


async def test_async_devices_execute_error_template(hass, caplog):
    class MockCapabilityA(OnOffCapability):
        def supported(self) -> bool:
            return True

        def get_value(self) -> float | str | None:
            return None

        async def set_state(self, data, state):
            pass

        async def _set_state(self, data: RequestData, state: dict[str, Any]):
            pass

    class MockCapabilityB(ToggleCapability):
        instance = 'b'

        def supported(self) -> bool:
            return True

        def get_value(self) -> float | str | None:
            return None

        async def set_state(self, data, state):
            pass

    class MockCapabilityC(ToggleCapability):
        instance = 'c'

        def supported(self) -> bool:
            return True

        def get_value(self) -> float | str | None:
            return None

        async def set_state(self, data, state):
            pass

    config = MockConfig(
        entity_config={
            'switch.test': {
                'error_code_template': Template("""
                    {% if capability.type == "devices.capabilities.on_off" and capability.state.instance == "on" and
                          capability.state.value %}
                        NOT_ENOUGH_WATER
                    {% elif capability.state.instance == 'b' %}
                        {% if is_state('sensor.foo', 'bar') %}
                            CONTAINER_FULL
                        {% endif %}
                    {% elif capability.state.instance == 'c' and capability.state.value %}
                        WAT?
                    {% endif %}
                """)
            }
        }
    )
    data = RequestData(config, 'test', REQ_ID)

    switch = State('switch.test', STATE_OFF)
    hass.states.async_set(switch.entity_id, switch.state, switch.attributes)

    with patch('custom_components.yandex_smart_home.capability.CAPABILITIES',
               [MockCapabilityA, MockCapabilityB, MockCapabilityC]):
        message = {
            'payload': {
                'devices': [{
                    'id': switch.entity_id,
                    'capabilities': [{
                        'type': MockCapabilityA.type,
                        'state': {
                            'instance': MockCapabilityA.instance,
                            'value': True
                        }
                    }, {
                        'type': MockCapabilityB.type,
                        'state': {
                            'instance': MockCapabilityB.instance,
                            'value': True
                        }
                    }, {
                        'type': MockCapabilityC.type,
                        'state': {
                            'instance': MockCapabilityC.instance,
                            'value': True
                        }
                    }]
                }]
            }
        }

        caplog.clear()
        assert await async_devices_execute(hass, data, message) == {
            'devices': [{
                'id': 'switch.test',
                'capabilities': [{
                    'type': 'devices.capabilities.on_off',
                    'state': {'instance': 'on', 'action_result': {'status': 'ERROR', 'error_code': 'NOT_ENOUGH_WATER'}}
                }, {
                    'type': 'devices.capabilities.toggle',
                    'state': {'instance': 'b', 'action_result': {'status': 'DONE'}}
                }, {
                    'type': 'devices.capabilities.toggle',
                    'state': {'instance': 'c', 'action_result': {'status': 'ERROR', 'error_code': 'INTERNAL_ERROR'}}
                }]
            }]
        }

        assert 'Invalid error code' in caplog.records[-1].message

        hass.states.async_set('sensor.foo', 'bar')
        message = {
            'payload': {
                'devices': [{
                    'id': switch.entity_id,
                    'capabilities': [{
                        'type': MockCapabilityB.type,
                        'state': {
                            'instance': MockCapabilityB.instance,
                            'value': True
                        }
                    }]
                }]
            }
        }

        assert await async_devices_execute(hass, data, message) == {
            'devices': [{
                'id': 'switch.test',
                'capabilities': [{
                    'type': 'devices.capabilities.toggle',
                    'state': {'instance': 'b', 'action_result': {'status': 'ERROR', 'error_code': 'CONTAINER_FULL'}}
                }]
            }]
        }


async def test_async_devices(hass):
    switch_1 = State('switch.test_1', STATE_OFF)
    switch_not_expose = State('switch.not_expose', STATE_ON)
    sensor = State('sensor.test', '33')
    hass.states.async_set(switch_1.entity_id, switch_1.state, switch_1.attributes)
    hass.states.async_set(switch_not_expose.entity_id, switch_not_expose.state, switch_not_expose.attributes)
    hass.states.async_set(sensor.entity_id, sensor.state, sensor.attributes)

    config = MockConfig(
        entity_filter=generate_entity_filter(exclude_entities=['switch.not_expose'])
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
    assert await async_devices(hass, data, {}) == {
        'user_id': 'test',
        'devices': [{
            'id': 'switch.test_1',
            'name': 'test 1',
            'type': 'devices.types.switch',
            'capabilities': [{
                'type': 'devices.capabilities.on_off',
                'retrievable': True,
                'reportable': True}
            ],
            'properties': [],
            'device_info': {'model': 'switch.test_1'}
        }]
    }
