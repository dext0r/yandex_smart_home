from homeassistant.components import (
    automation,
    button,
    climate,
    cover,
    fan,
    group,
    input_boolean,
    input_button,
    light,
    lock,
    media_player,
    remote,
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
    MAJOR_VERSION,
    MINOR_VERSION,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_onoff import CAPABILITIES_ONOFF
from custom_components.yandex_smart_home.const import ON_OFF_INSTANCE_ON
from custom_components.yandex_smart_home.error import SmartHomeError

from . import BASIC_CONFIG, BASIC_DATA, MockConfig
from .test_capability import (
    assert_exact_one_capability,
    assert_no_capabilities,
    get_capabilities,
    get_exact_one_capability,
)


@pytest.mark.parametrize(
    'state_domain,service_domain', [
        (automation.DOMAIN, automation.DOMAIN),
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

    config = MockConfig(
        entity_config={
            f'{state_domain}.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state = State(f'{state_domain}.test', STATE_ON)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.retrievable
    assert cap.parameters() == {'split': True}


@pytest.mark.parametrize('domain,initial_state,service', [
    (script.DOMAIN, STATE_OFF, SERVICE_TURN_ON),
    (scene.DOMAIN, STATE_UNKNOWN, SERVICE_TURN_ON),
    (button.DOMAIN, STATE_UNKNOWN, button.SERVICE_PRESS),
    (input_button.DOMAIN, STATE_UNKNOWN, input_button.SERVICE_PRESS),
])
async def test_capability_onoff_only_on(hass, domain, initial_state, service):
    state = State(f'{domain}.test', initial_state)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    assert not cap.retrievable
    assert cap.parameters() is None
    assert cap.get_value() is None

    on_calls = async_mock_service(hass, domain, service)
    await cap.set_state(BASIC_DATA, {'value': True})
    await cap.set_state(BASIC_DATA, {'value': False})

    if domain == script.DOMAIN:
        await hass.async_block_till_done()

    assert len(on_calls) == 2
    assert on_calls[0].data == {ATTR_ENTITY_ID: f'{domain}.test'}
    assert on_calls[1].data == {ATTR_ENTITY_ID: f'{domain}.test'}


async def test_capability_onoff_cover(hass):
    state_open = State('cover.test', cover.STATE_OPEN,
                       attributes={ATTR_SUPPORTED_FEATURES: cover.CoverEntityFeature.SET_POSITION})
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
                            attributes={ATTR_SUPPORTED_FEATURES: cover.CoverEntityFeature.SET_POSITION})
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state_other, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

        assert not cap.get_value()

    state_no_features = State('cover.test', cover.STATE_OPEN)
    cap_no_features = get_exact_one_capability(hass, BASIC_CONFIG, state_no_features,
                                               CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert cap_no_features.retrievable
    assert cap_no_features.get_value()
    assert cap_no_features.parameters() is None

    config = MockConfig(
        entity_config={
            'cover.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state_binary = State('cover.test', cover.STATE_OPEN)
    cap_binary = get_exact_one_capability(hass, config, state_binary, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap_binary.retrievable
    assert cap_binary.parameters() == {'split': True}


if MAJOR_VERSION >= 2024:
    from homeassistant.components import valve

    async def test_capability_onoff_valve(hass):
        state_open = State('valve.test', valve.STATE_OPEN,
                        attributes={ATTR_SUPPORTED_FEATURES: valve.ValveEntityFeature.SET_POSITION})
        cap_open = get_exact_one_capability(hass, BASIC_CONFIG, state_open, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

        assert cap_open.retrievable
        assert cap_open.get_value()
        assert cap_open.parameters() is None

        on_calls = async_mock_service(hass, valve.DOMAIN, valve.SERVICE_OPEN_VALVE)
        await cap_open.set_state(BASIC_DATA, {'value': True})
        assert len(on_calls) == 1
        assert on_calls[0].data == {ATTR_ENTITY_ID: 'valve.test'}

        off_calls = async_mock_service(hass, valve.DOMAIN, valve.SERVICE_CLOSE_VALVE)
        await cap_open.set_state(BASIC_DATA, {'value': False})
        assert len(off_calls) == 1
        assert off_calls[0].data == {ATTR_ENTITY_ID: 'valve.test'}

        for state in [valve.STATE_CLOSED, valve.STATE_CLOSING, valve.STATE_OPENING]:
            state_other = State('valve.test', state,
                                attributes={ATTR_SUPPORTED_FEATURES: valve.ValveEntityFeature.SET_POSITION})
            cap = get_exact_one_capability(hass, BASIC_CONFIG, state_other, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

            assert not cap.get_value()

        state_no_features = State('valve.test', cover.STATE_OPEN)
        cap_no_features = get_exact_one_capability(hass, BASIC_CONFIG, state_no_features,
                                                CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
        assert cap_no_features.retrievable
        assert cap_no_features.get_value()
        assert cap_no_features.parameters() is None


async def test_capability_onoff_remote(hass):
    state = State('remote.test', STATE_ON)
    cap_open = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    assert cap_open.retrievable is False
    assert cap_open.get_value() is None
    assert cap_open.parameters() == {'split': True}

    on_calls = async_mock_service(hass, remote.DOMAIN, SERVICE_TURN_ON)
    await cap_open.set_state(BASIC_DATA, {'value': True})
    await hass.async_block_till_done()
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    off_calls = async_mock_service(hass, remote.DOMAIN, SERVICE_TURN_OFF)
    await cap_open.set_state(BASIC_DATA, {'value': False})
    await hass.async_block_till_done()
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_capability_onoff_media_player(hass):
    state = State('media_player.simple', STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    state = State('media_player.test', STATE_ON)
    config = MockConfig(entity_config={
        state.entity_id: {
            'features': [
                'turn_on_off'
            ]
        }
    })
    assert_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    state = State('media_player.only_on', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.TURN_OFF
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert cap.retrievable
    assert cap.parameters() is None

    config = MockConfig(
        entity_config={
            'media_player.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state_binary = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.TURN_OFF
    })
    cap_binary = get_exact_one_capability(hass, config, state_binary, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap_binary.retrievable
    assert cap_binary.parameters() == {'split': True}

    state = State('media_player.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES:
            media_player.MediaPlayerEntityFeature.TURN_ON | media_player.MediaPlayerEntityFeature.TURN_OFF
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
    if (MAJOR_VERSION == 2024 and MINOR_VERSION >= 10) or MAJOR_VERSION >= 2025:
        state = State('lock.test', lock.LockState.UNLOCKED)
    else:
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

    if (MAJOR_VERSION == 2024 and MINOR_VERSION >= 10) or MAJOR_VERSION >= 2025:
        states = [lock.LockState.UNLOCKING, lock.LockState.LOCKING]
    else:
        states = [lock.STATE_UNLOCKING, lock.STATE_LOCKING]

    for s in states:
        state_other = State('lock.test', s)
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state_other, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

        assert not cap.get_value()

    state.state = lock.STATE_LOCKED
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.get_value()

    config = MockConfig(
        entity_config={
            'lock.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state = State('lock.test', STATE_ON)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.retrievable
    assert cap.parameters() == {'split': True}


async def test_capability_onoff_vacuum(hass):
    for s in [STATE_ON, vacuum.STATE_CLEANING]:
        state = State('vacuum.test', s, attributes={
            ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.STOP
        })
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
        assert cap.get_value()
        assert cap.retrievable
        assert cap.parameters() is None

    for s in vacuum.STATES + [STATE_OFF]:
        if s == vacuum.STATE_CLEANING:
            continue
        state = State('vacuum.test', s, attributes={
            ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.STOP
        })
        cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
        assert not cap.get_value()

    config = MockConfig(
        entity_config={
            'vacuum.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state = State('vacuum.test', STATE_ON, attributes={
        ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.STOP
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.retrievable
    assert cap.parameters() == {'split': True}


@pytest.mark.parametrize(
    'features,supported', [
        (0, False),
        (vacuum.VacuumEntityFeature.START, False),
        (vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.RETURN_HOME, True),
        (vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.STOP, True),
        (vacuum.VacuumEntityFeature.TURN_ON, False),
        (vacuum.VacuumEntityFeature.TURN_ON | vacuum.VacuumEntityFeature.TURN_OFF, True),
    ]
)
async def test_capability_onoff_vacuum_supported(hass, features, supported):
    state = State('vacuum.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: features
    })
    assert bool(get_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)) == supported


@pytest.mark.parametrize(
    'features,service', [
        (vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.RETURN_HOME, vacuum.SERVICE_START),
        (vacuum.VacuumEntityFeature.START |
         vacuum.VacuumEntityFeature.STOP |
         vacuum.VacuumEntityFeature.RETURN_HOME, vacuum.SERVICE_START),
        (vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.STOP, vacuum.SERVICE_START),
        (vacuum.VacuumEntityFeature.TURN_ON | vacuum.VacuumEntityFeature.TURN_OFF, vacuum.SERVICE_TURN_ON),
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
        (vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.RETURN_HOME, vacuum.SERVICE_RETURN_TO_BASE),
        (vacuum.VacuumEntityFeature.START |
         vacuum.VacuumEntityFeature.STOP |
         vacuum.VacuumEntityFeature.RETURN_HOME, vacuum.SERVICE_RETURN_TO_BASE),
        (vacuum.VacuumEntityFeature.START | vacuum.VacuumEntityFeature.STOP, vacuum.SERVICE_STOP),
        (vacuum.VacuumEntityFeature.TURN_ON | vacuum.VacuumEntityFeature.TURN_OFF, vacuum.SERVICE_TURN_OFF),
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
        if s == climate.HVACMode.OFF:
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

    config = MockConfig(
        entity_config={
            'climate.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state = State('climate.test', STATE_ON)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.retrievable
    assert cap.parameters() == {'split': True}


@pytest.mark.parametrize(
    'hvac_modes,service,service_hvac_mode', [
        ([], SERVICE_TURN_ON, None),
        ([climate.HVACMode.COOL], SERVICE_TURN_ON, None),
        ([climate.HVACMode.AUTO, climate.HVACMode.COOL],
         climate.SERVICE_SET_HVAC_MODE, climate.HVACMode.AUTO),
        ([climate.HVACMode.HEAT_COOL, climate.HVACMode.COOL],
         climate.SERVICE_SET_HVAC_MODE, climate.HVACMode.HEAT_COOL),
        ([climate.HVACMode.HEAT_COOL, climate.HVACMode.AUTO, climate.HVACMode.COOL],
         climate.SERVICE_SET_HVAC_MODE, climate.HVACMode.HEAT_COOL),
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
    state_media = State('media_player.test', STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state_media, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    state_switch = State('switch.test', STATE_ON)
    cap_switch = get_exact_one_capability(hass, BASIC_CONFIG, state_switch, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    on_calls = async_mock_service(hass, switch.DOMAIN, switch.SERVICE_TURN_ON)
    await cap_switch.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state_switch.entity_id}

    off_calls = async_mock_service(hass, switch.DOMAIN, switch.SERVICE_TURN_OFF)
    await cap_switch.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state_switch.entity_id}

    turn_on_service = 'test.turn_on'
    turn_off_service = 'test.turn_off'
    turn_on_off_entity_id = 'switch.test'

    state_switch = State('switch.test', STATE_ON)
    state_media = State('media_player.test', STATE_ON)
    state_vacuum = State('vacuum.test', STATE_ON)
    config = MockConfig(
        entity_config={
            state_media.entity_id: {
                const.CONF_TURN_ON: {
                    CONF_SERVICE: turn_on_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                },
                const.CONF_TURN_OFF: {
                    CONF_SERVICE: turn_off_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                }
            },
            state_switch.entity_id: {
                const.CONF_TURN_ON: {
                    CONF_SERVICE: turn_on_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                },
                const.CONF_TURN_OFF: {
                    CONF_SERVICE: turn_off_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                }
            },
            state_vacuum.entity_id: {
                const.CONF_TURN_ON: {
                    CONF_SERVICE: turn_on_service,
                    CONF_ENTITY_ID: turn_on_off_entity_id
                }
            }
        }
    )
    cap_media = get_exact_one_capability(hass, config, state_media, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    cap_switch = get_exact_one_capability(hass, config, state_switch, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert_exact_one_capability(hass, config, state_vacuum, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)

    on_calls = async_mock_service(hass, *turn_on_service.split('.'))
    await cap_media.set_state(BASIC_DATA, {'value': True})
    await cap_switch.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 2
    assert on_calls[0].data == {ATTR_ENTITY_ID: [turn_on_off_entity_id]}
    assert on_calls[1].data == {ATTR_ENTITY_ID: [turn_on_off_entity_id]}

    off_calls = async_mock_service(hass, *turn_off_service.split('.'))
    await cap_media.set_state(BASIC_DATA, {'value': False})
    await cap_switch.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 2
    assert off_calls[0].data == {ATTR_ENTITY_ID: [turn_on_off_entity_id]}
    assert off_calls[1].data == {ATTR_ENTITY_ID: [turn_on_off_entity_id]}


async def test_capability_onoff_water_heater(hass):
    state = State('water_heater.test', STATE_ON)

    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert cap.retrievable
    assert cap.parameters() is None
    assert bool(cap.get_value())

    state = State('water_heater.test', STATE_OFF)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not bool(cap.get_value())

    on_calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(on_calls) == 1
    assert on_calls[0].data[ATTR_ENTITY_ID] == state.entity_id

    off_calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_TURN_OFF)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data[ATTR_ENTITY_ID] == state.entity_id

    config = MockConfig(
        entity_config={
            'water_heater.test': {
                const.CONF_STATE_UNKNOWN: True
            }
        }
    )
    state = State('water_heater.test', STATE_ON)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not cap.retrievable
    assert cap.parameters() == {'split': True}


@pytest.mark.parametrize('op_on', ['on', 'On', 'ON', 'electric', 'Boil'])
@pytest.mark.parametrize('op_off', ['off', 'Off', 'OFF'])
async def test_capability_onoff_water_heater_set_op_mode(hass, op_on, op_off):
    state = State('water_heater.test', op_on, {
        ATTR_SUPPORTED_FEATURES: water_heater.WaterHeaterEntityFeature.OPERATION_MODE,
        water_heater.ATTR_OPERATION_LIST: [op_on, op_off],
        water_heater.ATTR_OPERATION_MODE: op_on,
    })

    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert cap.retrievable
    assert cap.parameters() is None
    assert bool(cap.get_value())

    state = State('water_heater.test', op_off, {
        ATTR_SUPPORTED_FEATURES: water_heater.WaterHeaterEntityFeature.OPERATION_MODE,
        water_heater.ATTR_OPERATION_LIST: [op_on, op_off],
        water_heater.ATTR_OPERATION_MODE: op_off,
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert not bool(cap.get_value())

    set_mode_calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_SET_OPERATION_MODE)
    await cap.set_state(BASIC_DATA, {'value': True})
    assert len(set_mode_calls) == 1
    assert set_mode_calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert set_mode_calls[0].data[water_heater.ATTR_OPERATION_MODE] == op_on

    set_mode_calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_SET_OPERATION_MODE)
    await cap.set_state(BASIC_DATA, {'value': False})
    assert len(set_mode_calls) == 1
    assert set_mode_calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert set_mode_calls[0].data[water_heater.ATTR_OPERATION_MODE] == op_off


async def test_capability_onoff_water_heater_set_unsupported_op_mode(hass):
    state = State('water_heater.test', 'foo', {
        ATTR_SUPPORTED_FEATURES: water_heater.WaterHeaterEntityFeature.OPERATION_MODE,
        water_heater.ATTR_OPERATION_LIST: ['foo', 'bar'],
        water_heater.ATTR_OPERATION_MODE: 'foo'
    })

    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_ONOFF, ON_OFF_INSTANCE_ON)
    assert bool(cap.get_value())

    for v in [True, False]:
        with pytest.raises(SmartHomeError) as e:
            await cap.set_state(BASIC_DATA, {'value': v})

        assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
        assert 'Unable to determine operation mode ' in e.value.message
