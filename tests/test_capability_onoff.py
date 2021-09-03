import pytest

from homeassistant.components import (
    input_boolean,
    group,
    fan,
    switch,
    scene,
    cover,
    light,
    script,
)
from homeassistant.core import State
from homeassistant.core import DOMAIN as HA_DOMAIN
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES
)
from pytest_homeassistant_custom_component.common import async_mock_service
from custom_components.yandex_smart_home.capability import CAPABILITIES_ONOFF

from . import BASIC_CONFIG, BASIC_DATA
from .test_capability import get_exact_one_capability


@pytest.mark.parametrize(
    'state_domain,service_domain',
    [
        (input_boolean.DOMAIN, input_boolean.DOMAIN),
        (group.DOMAIN, HA_DOMAIN),
        (fan.DOMAIN, fan.DOMAIN),
        (switch.DOMAIN, switch.DOMAIN),
        (light.DOMAIN, light.DOMAIN),
    ],
)
async def test_capability_onoff_simple(hass, state_domain, service_domain):
    state_on = State(f'{state_domain}.test', STATE_ON)
    cap_on = get_exact_one_capability(hass, BASIC_CONFIG, state_on, CAPABILITIES_ONOFF)

    assert cap_on.type == CAPABILITIES_ONOFF
    assert cap_on.retrievable
    assert cap_on.get_value()
    assert cap_on.parameters() is None

    on_calls = async_mock_service(hass, service_domain, SERVICE_TURN_ON)
    await cap_on.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: f'{state_domain}.test'}

    off_calls = async_mock_service(hass, service_domain, SERVICE_TURN_OFF)
    await cap_on.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: f'{state_domain}.test'}

    state_off = State(f'{state_domain}.test', STATE_OFF)
    cap_off = get_exact_one_capability(hass, BASIC_CONFIG, state_off, CAPABILITIES_ONOFF)
    assert not cap_off.get_value()


@pytest.mark.parametrize('domain,initial_state', [(script.DOMAIN, STATE_OFF), (scene.DOMAIN, scene.STATE)])
async def test_capability_onoff_only_on(hass, domain, initial_state):
    state = State(f'{domain}.test', initial_state)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF)

    assert cap.type == CAPABILITIES_ONOFF
    assert not cap.retrievable
    assert cap.parameters() is None

    on_calls = async_mock_service(hass, domain, SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': True})
    await cap.set_state(BASIC_DATA, {'value': False})

    if domain == script.DOMAIN:
        await hass.async_block_till_done()

    assert len(on_calls) == 2
    assert on_calls[0].data == {ATTR_ENTITY_ID: f'{domain}.test'}
    assert on_calls[1].data == {ATTR_ENTITY_ID: f'{domain}.test'}


async def test_capability_onoff_cover(hass):
    state_open = State('cover.test', cover.STATE_OPEN,
                       attributes={ATTR_SUPPORTED_FEATURES: cover.SUPPORT_SET_POSITION})
    cap_open = get_exact_one_capability(hass, BASIC_CONFIG, state_open, CAPABILITIES_ONOFF)

    assert cap_open.type == CAPABILITIES_ONOFF
    assert cap_open.retrievable
    assert cap_open.get_value()
    assert cap_open.parameters() is None

    on_calls = async_mock_service(hass, cover.DOMAIN, cover.SERVICE_OPEN_COVER)
    await cap_open.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: 'cover.test'}

    off_calls = async_mock_service(hass, cover.DOMAIN, cover.SERVICE_CLOSE_COVER)
    await cap_open.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: 'cover.test'}

    for state in [cover.STATE_CLOSED, cover.STATE_CLOSING, cover.STATE_OPENING]:
        state_other = State('cover.test', state,
                            attributes={ATTR_SUPPORTED_FEATURES: cover.SUPPORT_SET_POSITION})
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state_other, CAPABILITIES_ONOFF)

        assert not cap.get_value()

    state_no_features = State('cover.test', cover.STATE_OPEN)
    cap_binary = get_exact_one_capability(hass, BASIC_CONFIG, state_no_features, CAPABILITIES_ONOFF)
    assert cap_binary.type == CAPABILITIES_ONOFF
    assert not cap_binary.retrievable
    assert cap_binary.parameters() == {'split': True}
