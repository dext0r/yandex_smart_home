from homeassistant.components import (
    climate,
    cover,
    fan,
    group,
    input_boolean,
    light,
    lock,
    media_player,
    scene,
    script,
    switch,
    vacuum,
    water_heater,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITY_ID,
    CONF_SERVICE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_onoff import CAPABILITIES_ONOFF
from custom_components.yandex_smart_home.const import ON_OFF_INSTANCE_ON

from . import BASIC_CONFIG, BASIC_DATA, MockConfig
from .test_capability import assert_no_capabilities, get_capabilities, get_exact_one_capability


@pytest.mark.parametrize(
    'state_domain,service_domain', [
        (input_boolean.DOMAIN, input_boolean.DOMAIN),
        (group.DOMAIN, HA_DOMAIN),
        (fan.DOMAIN, fan.DOMAIN),
        (switch.DOMAIN, switch.DOMAIN),
        (light.DOMAIN, light.DOMAIN),
    ],
)
async def test_capability_onoff_simple(hass, state_domain, service_domain):
    state_on = State(f'{state_domain}.test', STATE_ON)
    cap_on = get_exact_one_capability(hass, BASIC_CONFIG, state_on, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

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
    cap_off = get_exact_one_capability(hass, BASIC_CONFIG, state_off, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap_off.get_value()


@pytest.mark.parametrize('domain,initial_state', [(script.DOMAIN, STATE_OFF), (scene.DOMAIN, scene.STATE)])
async def test_capability_onoff_only_on(hass, domain, initial_state):
    state = State(f'{domain}.test', initial_state)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

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
    cap_open = get_exact_one_capability(hass, BASIC_CONFIG, state_open, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

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
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state_other, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

        assert not cap.get_value()

    state_no_features = State('cover.test', cover.STATE_OPEN)
    cap_binary = get_exact_one_capability(hass, BASIC_CONFIG, state_no_features, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap_binary.retrievable
    assert cap_binary.parameters() == {'split': True}


async def test_capability_onoff_media_player(hass):
    state = State('media_player.simple', STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    state = State('media_player.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_TURN_ON | media_player.SUPPORT_TURN_OFF
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert cap.retrievable
    assert cap.get_value()
    assert cap.parameters() is None

    on_calls = async_mock_service(hass, media_player.DOMAIN, SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    off_calls = async_mock_service(hass, media_player.DOMAIN, SERVICE_TURN_OFF)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    state.state = STATE_OFF
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.get_value()


async def test_capability_onoff_lock(hass):
    state = State('lock.test', lock.STATE_UNLOCKED)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    assert cap.retrievable
    assert cap.get_value()
    assert cap.parameters() is None

    on_calls = async_mock_service(hass, lock.DOMAIN, lock.SERVICE_UNLOCK)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    off_calls = async_mock_service(hass, lock.DOMAIN, lock.SERVICE_LOCK)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    for s in [lock.STATE_UNLOCKING, lock.STATE_LOCKING]:
        state_other = State('lock.test', s)
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state_other, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

        assert not cap.get_value()

    state.state = lock.STATE_LOCKED
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.get_value()


async def test_capability_onoff_vacuum(hass):
    for s in [STATE_ON, vacuum.STATE_CLEANING]:
        state = State('vacuum.test', s, attributes={
            ATTR_SUPPORTED_FEATURES: vacuum.SUPPORT_START | vacuum.SUPPORT_STOP
        })
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
        assert cap.get_value()
        assert cap.retrievable
        assert cap.parameters() is None

    for s in vacuum.STATES + [STATE_OFF]:
        if s == vacuum.STATE_CLEANING:
            continue
        state = State('vacuum.test', s, attributes={
            ATTR_SUPPORTED_FEATURES: vacuum.SUPPORT_START | vacuum.SUPPORT_STOP
        })
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
        assert not cap.get_value()


@pytest.mark.parametrize(
    'features,supported', [
        (0, False),
        (vacuum.SUPPORT_START, False),
        (vacuum.SUPPORT_START | vacuum.SUPPORT_RETURN_HOME, True),
        (vacuum.SUPPORT_START | vacuum.SUPPORT_STOP, True),
        (vacuum.SUPPORT_TURN_ON, False),
        (vacuum.SUPPORT_TURN_ON | vacuum.SUPPORT_TURN_OFF, True),
    ]
)
async def test_capability_onoff_vacuum_supported(hass, features, supported):
    state = State('vacuum.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: features
    })
    assert bool(get_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)) == supported


@pytest.mark.parametrize(
    'features,service', [
        (vacuum.SUPPORT_START | vacuum.SUPPORT_RETURN_HOME, vacuum.SERVICE_START),
        (vacuum.SUPPORT_START | vacuum.SUPPORT_STOP | vacuum.SUPPORT_RETURN_HOME, vacuum.SERVICE_START),
        (vacuum.SUPPORT_START | vacuum.SUPPORT_STOP, vacuum.SERVICE_START),
        (vacuum.SUPPORT_TURN_ON | vacuum.SUPPORT_TURN_OFF, vacuum.SERVICE_TURN_ON),
    ]
)
async def test_capability_onoff_vacuum_turn_on(hass, features, service):
    state = State('vacuum.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: features
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    on_calls = async_mock_service(hass, vacuum.DOMAIN, service)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


@pytest.mark.parametrize(
    'features,service', [
        (vacuum.SUPPORT_START | vacuum.SUPPORT_RETURN_HOME, vacuum.SERVICE_RETURN_TO_BASE),
        (vacuum.SUPPORT_START | vacuum.SUPPORT_STOP | vacuum.SUPPORT_RETURN_HOME, vacuum.SERVICE_RETURN_TO_BASE),
        (vacuum.SUPPORT_START | vacuum.SUPPORT_STOP, vacuum.SERVICE_STOP),
        (vacuum.SUPPORT_TURN_ON | vacuum.SUPPORT_TURN_OFF, vacuum.SERVICE_TURN_OFF),
    ]
)
async def test_capability_onoff_vacuum_turn_off(hass, features, service):
    state = State('vacuum.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: features
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    off_calls = async_mock_service(hass, vacuum.DOMAIN, service)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_capability_onoff_climate(hass):
    for s in climate.const.HVAC_MODES:
        if s == climate.const.HVAC_MODE_OFF:
            continue

        state = State('climate.test', s)
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
        assert cap.get_value()
        assert cap.retrievable
        assert cap.parameters() is None

    state = State('climate.test', STATE_OFF)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.get_value()

    off_calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_TURN_OFF)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


@pytest.mark.parametrize(
    'hvac_modes,service,service_hvac_mode', [
        ([], SERVICE_TURN_ON, None),
        ([climate.const.HVAC_MODE_COOL], SERVICE_TURN_ON, None),
        ([climate.const.HVAC_MODE_AUTO, climate.const.HVAC_MODE_COOL],
         climate.SERVICE_SET_HVAC_MODE, climate.const.HVAC_MODE_AUTO),
        ([climate.const.HVAC_MODE_HEAT_COOL, climate.const.HVAC_MODE_COOL],
         climate.SERVICE_SET_HVAC_MODE, climate.const.HVAC_MODE_HEAT_COOL),
        ([climate.const.HVAC_MODE_HEAT_COOL, climate.const.HVAC_MODE_AUTO, climate.const.HVAC_MODE_COOL],
         climate.SERVICE_SET_HVAC_MODE, climate.const.HVAC_MODE_HEAT_COOL),
    ]
)
async def test_capability_onoff_climate_turn_on(hass, hvac_modes, service, service_hvac_mode):
    state = State('climate.test', climate.HVAC_MODE_COOL, {
        climate.const.ATTR_HVAC_MODES: hvac_modes
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    on_calls = async_mock_service(hass, climate.DOMAIN, service)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    if service_hvac_mode:
        assert on_calls[0].data[climate.const.ATTR_HVAC_MODE] == service_hvac_mode


async def test_capability_onoff_custom_service(hass):
    state = State('media_player.test', STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    turn_on_service = 'test.turn_on'
    turn_off_service = 'test.turn_off'
    turn_on_off_entity_id = 'switch.test'

    config = MockConfig(
        entity_config={
            state.entity_id: {
                const.CONF_TURN_ON: {
                    CONF_SERVICE: turn_on_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                },
                const.CONF_TURN_OFF: {
                    CONF_SERVICE: turn_off_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                }
            }
        }
    )
    state = State('media_player.test', STATE_ON)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    on_calls = async_mock_service(hass, *turn_on_service.split('.'))
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: [turn_on_off_entity_id]}

    off_calls = async_mock_service(hass, *turn_off_service.split('.'))
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: [turn_on_off_entity_id]}


@pytest.mark.parametrize('op_on', ['On', 'ON', 'electric', 'gas', 'performance', None])
@pytest.mark.parametrize('op_off', ['Off', 'OFF', None])
@pytest.mark.parametrize('op,value', [
    ('On', True), ('ON', True), ('electric', True), ('gas', None), ('performance', None),
    ('Off', False), ('OFF', False)
])
async def test_capability_onoff_water_heater(hass, op_on, op_off, op, value):
    operation_list = []
    if op_on:
        operation_list.append(op_on)

    if op_off:
        operation_list.append(op_off)

    if op not in operation_list:
        return

    state = State('water_heater.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: water_heater.SUPPORT_OPERATION_MODE,
        water_heater.ATTR_OPERATION_LIST: operation_list,
        water_heater.ATTR_OPERATION_MODE: op,
    })
    if value is None or op_on in ['gas', 'performance', None] or op_off in [None]:
        return assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert cap.retrievable
    assert cap.parameters() is None
    assert bool(cap.get_value()) == value

    on_calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_SET_OPERATION_MODE)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert on_calls[0].data[water_heater.ATTR_OPERATION_MODE] in ['On', 'ON', 'electric']

    off_calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_SET_OPERATION_MODE)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert off_calls[0].data[water_heater.ATTR_OPERATION_MODE] in ['Off', 'OFF']
