from unittest.mock import PropertyMock, patch

from homeassistant.components import climate, fan, humidifier, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF
from homeassistant.core import State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_mode import (
    CAPABILITIES_MODE,
    FanSpeedCapabilityFanLegacy,
    FanSpeedCapabilityFanViaPercentage,
    FanSpeedCapabilityFanViaPreset,
    ModeCapability,
)
from custom_components.yandex_smart_home.const import (
    MODE_INSTANCE_CLEANUP_MODE,
    MODE_INSTANCE_FAN_SPEED,
    MODE_INSTANCE_INPUT_SOURCE,
    MODE_INSTANCE_PROGRAM,
    MODE_INSTANCE_SWING,
    MODE_INSTANCE_THERMOSTAT,
)
from custom_components.yandex_smart_home.error import SmartHomeError

from . import BASIC_CONFIG, BASIC_DATA, MockConfig
from .test_capability import assert_no_capabilities, get_exact_one_capability


class MockModeCapability(ModeCapability):
    instance = 'test_instance'
    modes_map_default = {
        const.MODE_INSTANCE_MODE_FOWL: ['mode_1'],
        const.MODE_INSTANCE_MODE_PIZZA: ['mode_2'],
        const.MODE_INSTANCE_MODE_PUERH_TEA: ['MODE_3'],
    }

    @property
    def modes_list_attribute(self):
        return 'modes_list'

    @property
    def state_value_attribute(self):
        return 'current_mode'

    async def set_state(self, *args, **kwarsg):
        pass


class MockFallbackModeCapability(MockModeCapability):
    modes_map_index_fallback = {
        0: const.MODE_INSTANCE_MODE_ONE,
        1: const.MODE_INSTANCE_MODE_TWO,
        2: const.MODE_INSTANCE_MODE_THREE,
        3: const.MODE_INSTANCE_MODE_FOUR,
        4: const.MODE_INSTANCE_MODE_FIVE,
        5: const.MODE_INSTANCE_MODE_SIX,
        6: const.MODE_INSTANCE_MODE_SEVEN,
        7: const.MODE_INSTANCE_MODE_EIGHT,
        8: const.MODE_INSTANCE_MODE_NINE,
        9: const.MODE_INSTANCE_MODE_TEN,
    }


async def test_capability_mode_unsupported(hass):
    state = State('switch.test', STATE_OFF)
    cap = MockModeCapability(hass, BASIC_CONFIG, state)
    assert not cap.supported()

    state = State('switch.test', STATE_OFF, {
        'modes_list': ['foo', 'bar']
    })
    cap = MockModeCapability(hass, BASIC_CONFIG, state)
    assert not cap.supported()


async def test_capability_mode_auto_mapping(hass, caplog):
    state = State('switch.test', STATE_OFF, {
        'modes_list': ['mode_1', 'mode_3']
    })
    cap = MockModeCapability(hass, BASIC_CONFIG, state)

    assert cap.supported()
    assert cap.parameters() == {
        'instance': 'test_instance',
        'modes': [{'value': 'fowl'}, {'value': 'puerh_tea'}],
    }
    assert cap.supported_ha_modes == ['mode_1', 'mode_3']
    assert cap.supported_yandex_modes == [const.MODE_INSTANCE_MODE_FOWL, const.MODE_INSTANCE_MODE_PUERH_TEA]

    assert cap.get_yandex_mode_by_ha_mode('invalid') is None
    for record in caplog.records:
        assert 'Unable to get Yandex mode' in record.message
    caplog.clear()

    assert cap.get_yandex_mode_by_ha_mode(STATE_OFF) is None
    assert len(caplog.records) == 0

    assert cap.get_yandex_mode_by_ha_mode('mode_1') == const.MODE_INSTANCE_MODE_FOWL
    assert cap.get_yandex_mode_by_ha_mode('mode_3') == const.MODE_INSTANCE_MODE_PUERH_TEA
    with pytest.raises(SmartHomeError):  # strange case o_O
        assert cap.get_yandex_mode_by_ha_mode('MODE_1')

    with pytest.raises(SmartHomeError) as e:
        assert cap.get_ha_mode_by_yandex_mode(const.MODE_INSTANCE_MODE_DEEP_FRYER) == ''
    assert e.value.code == const.ERR_INVALID_VALUE
    assert e.value.message.startswith('Unsupported mode')

    assert cap.get_ha_mode_by_yandex_mode(const.MODE_INSTANCE_MODE_FOWL) == 'mode_1'
    assert cap.get_ha_mode_by_yandex_mode(const.MODE_INSTANCE_MODE_PUERH_TEA) == 'mode_3'


async def test_capability_mode_custom_mapping(hass):
    state = State('switch.test', STATE_OFF, {
        'modes_list': ['mode_1', 'mode_foo', 'mode_bar']
    })
    config = MockConfig(entity_config={
        state.entity_id: {
            const.CONF_ENTITY_MODE_MAP: {
                'test_instance': {
                    const.MODE_INSTANCE_MODE_ECO: ['mode_foo'],
                    const.MODE_INSTANCE_MODE_LATTE: ['Mode_Bar'],
                }
            }
        }
    })
    cap = MockModeCapability(hass, config, state)
    assert cap.supported()
    assert cap.supported_ha_modes == ['mode_1', 'mode_foo', 'mode_bar']  # yeap, strange too
    assert cap.supported_yandex_modes == [const.MODE_INSTANCE_MODE_ECO,
                                          const.MODE_INSTANCE_MODE_LATTE]


async def test_capability_mode_fallback_index(hass):
    state = State('switch.test', STATE_OFF, {
        'modes_list': ['some', 'mode_1', 'foo']
    })
    cap = MockFallbackModeCapability(hass, BASIC_CONFIG, state)
    assert cap.supported()
    assert cap.supported_ha_modes == ['some', 'mode_1', 'foo']
    assert cap.supported_yandex_modes == [const.MODE_INSTANCE_MODE_ONE, const.MODE_INSTANCE_MODE_FOWL,
                                          const.MODE_INSTANCE_MODE_THREE]
    assert cap.get_ha_mode_by_yandex_mode(const.MODE_INSTANCE_MODE_FOWL) == 'mode_1'
    assert cap.get_ha_mode_by_yandex_mode(const.MODE_INSTANCE_MODE_ONE) == 'some'
    assert cap.get_yandex_mode_by_ha_mode('foo') == const.MODE_INSTANCE_MODE_THREE
    assert cap.get_yandex_mode_by_ha_mode('mode_1') == const.MODE_INSTANCE_MODE_FOWL

    state = State('switch.test', STATE_OFF, {
        'modes_list': [f'mode_{v}' for v in range(0, 11)]
    })
    cap = MockFallbackModeCapability(hass, BASIC_CONFIG, state)
    assert cap.supported()
    assert cap.get_yandex_mode_by_ha_mode('mode_9') == 'ten'
    assert cap.get_yandex_mode_by_ha_mode('mode_11') is None


async def test_capability_mode_get_value(hass, caplog):
    state = State('switch.test', STATE_OFF, {
        'modes_list': ['mode_1', 'mode_3'],
        'current_mode': 'mode_1'
    })
    cap = MockModeCapability(hass, BASIC_CONFIG, state)
    assert cap.get_value() == const.MODE_INSTANCE_MODE_FOWL

    with patch.object(MockModeCapability, 'state_value_attribute', new_callable=PropertyMock(return_value=None)):
        assert cap.get_value() is None

        cap.state.state = 'mode_3'
        assert cap.get_value() == const.MODE_INSTANCE_MODE_PUERH_TEA


async def test_capability_mode_thermostat(hass):
    state = State('climate.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_THERMOSTAT)

    state = State('climate.test', STATE_OFF, {
        climate.ATTR_HVAC_MODES: [climate.HVAC_MODE_HEAT_COOL, climate.const.HVAC_MODE_FAN_ONLY, climate.HVAC_MODE_OFF]
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_THERMOSTAT)
    assert cap.retrievable
    assert cap.parameters() == {'instance': 'thermostat', 'modes': [{'value': 'auto'}, {'value': 'fan_only'}]}
    assert not cap.get_value()

    cap.state.state = climate.const.HVAC_MODE_FAN_ONLY
    assert cap.get_value() == 'fan_only'

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_HVAC_MODE)
    await cap.set_state(BASIC_DATA, {'value': 'auto'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_HVAC_MODE: 'heat_cool'}


async def test_capability_mode_swing(hass):
    state = State('climate.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_SWING)

    state = State('climate.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: climate.SUPPORT_SWING_MODE,
        climate.ATTR_SWING_MODES: ['lr', 'ud']
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_SWING)
    assert cap.retrievable
    assert cap.parameters() == {'instance': 'swing', 'modes': [{'value': 'horizontal'}, {'value': 'vertical'}]}
    assert not cap.get_value()

    state = State('climate.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: climate.SUPPORT_SWING_MODE,
        climate.ATTR_SWING_MODES: ['lr', 'ud'],
        climate.ATTR_SWING_MODE: 'ud'
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_SWING)
    assert cap.get_value() == 'vertical'

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_SWING_MODE)
    await cap.set_state(BASIC_DATA, {'value': 'horizontal'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_SWING_MODE: 'lr'}


async def test_capability_mode_program(hass):
    state = State('humidifier.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_PROGRAM)

    state = State('humidifier.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: humidifier.SUPPORT_MODES,
        humidifier.ATTR_AVAILABLE_MODES: ['Idle', 'Middle']
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_PROGRAM)
    assert cap.retrievable
    assert cap.parameters() == {'instance': 'program', 'modes': [{'value': 'eco'}, {'value': 'medium'}]}
    assert not cap.get_value()

    state = State('humidifier.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: humidifier.SUPPORT_MODES,
        humidifier.ATTR_AVAILABLE_MODES: ['Idle', 'Middle'],
        humidifier.ATTR_MODE: 'Idle'
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_PROGRAM)
    assert cap.get_value() == 'eco'

    calls = async_mock_service(hass, humidifier.DOMAIN, humidifier.SERVICE_SET_MODE)
    await cap.set_state(BASIC_DATA, {'value': 'medium'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, humidifier.ATTR_MODE: 'Middle'}


async def test_capability_mode_input_source(hass):
    state = State('media_player.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_INPUT_SOURCE)

    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_SELECT_SOURCE,
        media_player.ATTR_INPUT_SOURCE_LIST: [f's{i}' for i in range(1, 15)]
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_INPUT_SOURCE)

    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_SELECT_SOURCE,
        media_player.ATTR_INPUT_SOURCE_LIST: ['s1', 's2', 's3']
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_INPUT_SOURCE)
    assert cap.retrievable
    assert cap.parameters() == {
        'instance': 'input_source',
        'modes': [{'value': 'one'}, {'value': 'two'}, {'value': 'three'}]
    }
    assert not cap.get_value()

    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_SELECT_SOURCE,
        media_player.ATTR_INPUT_SOURCE_LIST: ['s1', 's2', 's3'],
        media_player.ATTR_INPUT_SOURCE: 's2'
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_INPUT_SOURCE)
    assert cap.get_value() == 'two'

    calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_SELECT_SOURCE)
    await cap.set_state(BASIC_DATA, {'value': 'three'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, media_player.ATTR_INPUT_SOURCE: 's3'}


async def test_capability_mode_fan_speed_fan_legacy(hass):
    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: fan.SUPPORT_SET_SPEED
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: fan.SUPPORT_SET_SPEED,
        fan.ATTR_PERCENTAGE_STEP: 1
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert isinstance(cap, FanSpeedCapabilityFanViaPercentage)

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: fan.SUPPORT_SET_SPEED,
        fan.ATTR_SPEED_LIST: ['low', 'high']
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert isinstance(cap, FanSpeedCapabilityFanLegacy)
    assert cap.retrievable
    assert cap.parameters() == {
        'instance': 'fan_speed',
        'modes': [{'value': 'low'}, {'value': 'high'}]
    }
    assert not cap.get_value()

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: fan.SUPPORT_SET_SPEED,
        fan.ATTR_SPEED_LIST: ['low', 'medium'],
        fan.ATTR_SPEED: 'medium'
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert cap.get_value() == 'medium'

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_SPEED)
    await cap.set_state(BASIC_DATA, {'value': 'low'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_SPEED: 'low'}


@pytest.mark.parametrize('features', [
    fan.SUPPORT_SET_SPEED | fan.SUPPORT_PRESET_MODE,
    fan.SUPPORT_SET_SPEED
])
async def test_capability_mode_fan_speed_fan_via_percentage(hass, features):
    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PERCENTAGE_STEP: 100
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PERCENTAGE_STEP: 100
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PERCENTAGE_STEP: 25
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    assert isinstance(cap, FanSpeedCapabilityFanViaPercentage)
    assert cap.retrievable
    assert cap.modes_list_attribute is None
    assert cap.parameters() == {
        'instance': 'fan_speed',
        'modes': [{'value': 'low'}, {'value': 'normal'}, {'value': 'medium'}, {'value': 'high'}]
    }
    assert not cap.get_value()

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PERCENTAGE_STEP: 25,
        fan.ATTR_PERCENTAGE: 50
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert cap.get_value() == 'normal'

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PERCENTAGE)
    await cap.set_state(BASIC_DATA, {'value': 'medium'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PERCENTAGE: 75}

    for speed_count, mode_count in (
        (1, 0),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
        (7, 7),
        (8, 7),
        (10, 7),
    ):
        state = State('fan.test', STATE_OFF, {
            ATTR_SUPPORTED_FEATURES: features,
            fan.ATTR_PERCENTAGE_STEP: 100/float(speed_count),
        })
        if not mode_count:
            assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
        else:
            cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
            assert len(cap.supported_ha_modes) == mode_count
            assert len(cap.supported_yandex_modes) == mode_count


@pytest.mark.parametrize('features', [
    fan.SUPPORT_SET_SPEED | fan.SUPPORT_PRESET_MODE,
    fan.SUPPORT_SET_SPEED
])
async def test_capability_mode_fan_speed_fan_via_percentage_custom(hass, features):
    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PERCENTAGE_STEP: 25,
        fan.ATTR_PERCENTAGE: 50
    })
    config = MockConfig(entity_config={
        state.entity_id: {
            const.CONF_ENTITY_MODE_MAP: {
                const.MODE_INSTANCE_FAN_SPEED: {
                    const.MODE_INSTANCE_MODE_FOWL: ['50%'],
                    const.MODE_INSTANCE_MODE_HORIZONTAL: ['100%'],
                }
            }
        }
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    assert isinstance(cap, FanSpeedCapabilityFanViaPercentage)
    assert cap.retrievable
    assert cap.parameters() == {
        'instance': 'fan_speed',
        'modes': [{'value': 'fowl'}, {'value': 'horizontal'}]
    }
    assert cap.get_value() == 'fowl'

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PERCENTAGE_STEP: 25,
        fan.ATTR_PERCENTAGE: 25
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert cap.get_value() is None

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PERCENTAGE)
    await cap.set_state(BASIC_DATA, {'value': 'fowl'})
    await cap.set_state(BASIC_DATA, {'value': 'horizontal'})
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PERCENTAGE: 50}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PERCENTAGE: 100}

    with pytest.raises(SmartHomeError) as e:
        await cap.set_state(BASIC_DATA, {'value': 'low'})
    assert e.value.code == const.ERR_INVALID_VALUE
    assert 'Unsupported' in e.value.message

    config = MockConfig(entity_config={
        state.entity_id: {
            const.CONF_ENTITY_MODE_MAP: {
                const.MODE_INSTANCE_FAN_SPEED: {
                    const.MODE_INSTANCE_MODE_FOWL: ['not-int'],
                }
            }
        }
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    with pytest.raises(SmartHomeError) as e:
        cap.get_value()
    assert e.value.code == const.ERR_INVALID_VALUE
    assert 'Unsupported' in e.value.message


@pytest.mark.parametrize('features', [
    fan.SUPPORT_SET_SPEED | fan.SUPPORT_PRESET_MODE,
    fan.SUPPORT_PRESET_MODE
])
async def test_capability_mode_fan_speed_fan_via_preset(hass, features):
    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PRESET_MODES: ['Level 4', 'Level 5'],
        fan.ATTR_SPEED_LIST: ['1', '2']
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert isinstance(cap, FanSpeedCapabilityFanViaPreset)
    assert cap.retrievable
    assert cap.parameters() == {
        'instance': 'fan_speed',
        'modes': [{'value': 'high'}, {'value': 'turbo'}]
    }
    assert not cap.get_value()

    state = State('fan.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        fan.ATTR_PRESET_MODES: ['Level 4', 'Level 5'],
        fan.ATTR_SPEED_LIST: ['1', '2'],
        fan.ATTR_SPEED: '2',
        fan.ATTR_PRESET_MODE: 'Level 5',
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert cap.get_value() == 'turbo'

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PRESET_MODE)
    await cap.set_state(BASIC_DATA, {'value': 'high'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PRESET_MODE: 'Level 4'}


async def test_capability_mode_fan_speed_climate(hass):
    state = State('climate.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)

    state = State('climate.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: climate.SUPPORT_FAN_MODE,
        climate.ATTR_FAN_MODES: ['3', '2'],
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert cap.retrievable
    assert cap.parameters() == {
        'instance': 'fan_speed',
        'modes': [{'value': 'medium'}, {'value': 'low'}]
    }
    assert not cap.get_value()

    state = State('climate.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: climate.SUPPORT_FAN_MODE,
        climate.ATTR_FAN_MODES: ['3', '2'],
        climate.ATTR_FAN_MODE:  '3',
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_FAN_SPEED)
    assert cap.get_value() == 'medium'

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_FAN_MODE)
    await cap.set_state(BASIC_DATA, {'value': 'low'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_FAN_MODE: '2'}


async def test_capability_mode_cleanup_mode(hass):
    state = State('vacuum.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_CLEANUP_MODE)

    state = State('vacuum.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: vacuum.SUPPORT_FAN_SPEED,
        vacuum.ATTR_FAN_SPEED_LIST: ['gentle', 'mop'],
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_CLEANUP_MODE)
    assert cap.retrievable
    assert cap.parameters() == {
        'instance': 'cleanup_mode',
        'modes': [{'value': 'low'}, {'value': 'min'}]
    }
    assert not cap.get_value()

    state = State('vacuum.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: vacuum.SUPPORT_FAN_SPEED,
        vacuum.ATTR_FAN_SPEED_LIST: ['gentle', 'mop'],
        vacuum.ATTR_FAN_SPEED: 'mop'
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_MODE, MODE_INSTANCE_CLEANUP_MODE)
    assert cap.get_value() == 'min'

    calls = async_mock_service(hass, vacuum.DOMAIN, vacuum.SERVICE_SET_FAN_SPEED)
    await cap.set_state(BASIC_DATA, {'value': 'low'})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, vacuum.ATTR_FAN_SPEED: 'gentle'}
