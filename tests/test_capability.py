from __future__ import annotations

from typing import Any, Optional

from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_ON
from homeassistant.core import HomeAssistant, State

# noinspection PyProtectedMember
from custom_components.yandex_smart_home.capability import CAPABILITIES, _Capability, _RangeCapability
from custom_components.yandex_smart_home.helpers import Config

from . import BASIC_CONFIG


def get_capabilities(hass: HomeAssistant, config: Config, state: State,
                     capability_type: str, instance: str) -> list[_Capability]:
    caps = []

    for Capability in CAPABILITIES:
        capability = Capability(hass, config, state)

        if capability.type != capability_type or capability.instance != instance:
            continue

        if capability.supported(state.domain,
                                state.attributes.get(ATTR_SUPPORTED_FEATURES, 0),
                                config.get_entity_config(state.entity_id),
                                state.attributes):
            caps.append(capability)

    return caps


def get_exact_one_capability(hass: HomeAssistant, config: Config, state: State,
                             capability_type: str, instance: str) -> _Capability | _RangeCapability:

    caps = get_capabilities(hass, config, state, capability_type, instance)
    assert len(caps) == 1
    return caps[0]


def assert_exact_one_capability(hass: HomeAssistant, config: Config, state: State,
                                capability_type: str, instance: str):
    assert len(get_capabilities(hass, config, state, capability_type, instance)) == 1


def assert_no_capabilities(hass: HomeAssistant, config: Config, state: State,
                           capability_type: str, instance: str):
    assert len(get_capabilities(hass, config, state, capability_type, instance)) == 0


def test_capability(hass):
    class TestCapabilityWithParametersNoValue(_Capability):
        type = 'test_type'
        instance = 'test_instance'

        def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
            return True

        def parameters(self) -> Optional[dict[str, Any]]:
            return {'param': 'value'}

        def get_value(self):
            return None

        async def set_state(self, data, state):
            pass

    cap = TestCapabilityWithParametersNoValue(hass, BASIC_CONFIG, State('switch.test', STATE_ON))
    assert cap.description() == {
        'type': 'test_type',
        'retrievable': True,
        'reportable': True,
        'parameters': {
            'param': 'value',
        }
    }
    assert cap.get_state() is None

    class TestCapability(_Capability):
        type = 'test_type'
        instance = 'test_instance'

        def supported(self, domain: str, features: int, entity_config: dict[str, Any], attributes: dict[str, Any]):
            return True

        def parameters(self) -> Optional[dict[str, Any]]:
            return None

        def get_value(self):
            return 'v'

        async def set_state(self, data, state):
            pass

    cap = TestCapability(hass, BASIC_CONFIG, State('switch.test', STATE_ON))
    assert cap.description() == {
        'type': 'test_type',
        'retrievable': True,
        'reportable': True,
    }
    assert cap.get_state() == {
        'type': 'test_type',
        'state': {
            'instance': 'test_instance',
            'value': 'v',
        }
    }
