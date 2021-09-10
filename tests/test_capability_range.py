from unittest.mock import patch

from homeassistant.components import climate, cover, humidifier, light, media_player, water_heater
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_MODEL,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_range import CAPABILITIES_RANGE, RangeCapability
from custom_components.yandex_smart_home.const import (
    RANGE_INSTANCE_BRIGHTNESS,
    RANGE_INSTANCE_CHANNEL,
    RANGE_INSTANCE_HUMIDITY,
    RANGE_INSTANCE_OPEN,
    RANGE_INSTANCE_TEMPERATURE,
    RANGE_INSTANCE_VOLUME,
)
from custom_components.yandex_smart_home.error import SmartHomeError

from . import BASIC_CONFIG, BASIC_DATA, MockConfig
from .test_capability import assert_no_capabilities, get_exact_one_capability


async def test_capability_range(hass):
    class MockCapability(RangeCapability):
        type = 'test_type'
        instance = 'test_instance'

        @property
        def support_random_access(self) -> bool:
            return False

        @property
        def supported(self) -> bool:
            return True

        async def set_state(self, *args, **kwargs):
            pass

        def get_value(self):
            return None

    class MockCapabilityRandomAccess(MockCapability):
        @property
        def support_random_access(self) -> bool:
            return True

    cap = MockCapability(hass, BASIC_CONFIG, State('switch.test', STATE_ON))
    assert not cap.retrievable
    assert cap.parameters() == {'instance': 'test_instance', 'random_access': False}

    cap = MockCapabilityRandomAccess(hass, BASIC_CONFIG, State('switch.test', STATE_ON))
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.range == (0, 100, 1)

    for range_min in [0, 1, 5, None]:
        for range_max in [50, 100, None]:
            for range_prec in [0.3, 1, None]:
                entity_range_config = {}
                if range_min:
                    entity_range_config[const.CONF_ENTITY_RANGE_MIN] = range_min
                if range_max:
                    entity_range_config[const.CONF_ENTITY_RANGE_MAX] = range_max
                if range_prec:
                    entity_range_config[const.CONF_ENTITY_RANGE_PRECISION] = range_prec

                config = MockConfig(
                    entity_config={
                        'switch.test': {
                            const.CONF_ENTITY_RANGE: entity_range_config
                        }
                    }
                )
                cap = MockCapabilityRandomAccess(hass, config, State('switch.test', STATE_ON))
                assert cap.range == (
                    range_min or cap.default_range[0],
                    range_max or cap.default_range[1],
                    range_prec or cap.default_range[2]
                )
                assert cap.parameters() == {
                    'instance': 'test_instance',
                    'random_access': True,
                    'range': {
                        'min': range_min or cap.default_range[0],
                        'max': range_max or cap.default_range[1],
                        'precision': range_prec or cap.default_range[2],
                    }
                }

    for v in [STATE_UNAVAILABLE, STATE_UNKNOWN, 'None']:
        assert cap.float_value(v) is None

    for v in ['4', '5.5']:
        assert cap.float_value(v) == float(v)

    with pytest.raises(SmartHomeError) as e:
        assert cap.float_value('foo')
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE

    with patch.object(cap, 'get_value', return_value=20):
        assert cap.get_absolute_value(10) == 30
        assert cap.get_absolute_value(-5) == 15
        assert cap.get_absolute_value(99) == 100
        assert cap.get_absolute_value(-50) == 0

    with pytest.raises(SmartHomeError) as e:
        cap.get_absolute_value(0)
    assert e.value.code == const.ERR_INVALID_VALUE
    assert 'Unable' in e.value.message

    cap.state.state = STATE_OFF
    with pytest.raises(SmartHomeError) as e:
        cap.get_absolute_value(0)
    assert e.value.code == const.ERR_DEVICE_OFF
    assert 'turned off' in e.value.message


async def test_capability_range_cover(hass):
    state = State('cover.test', cover.STATE_OPEN)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_OPEN)

    state = State('cover.test', cover.STATE_OPEN, {
        ATTR_SUPPORTED_FEATURES: cover.SUPPORT_SET_POSITION
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_OPEN)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'open',
        'random_access': True,
        'range': {
            'max': 100,
            'min': 0,
            'precision': 1
         },
        'unit': 'unit.percent',
    }
    assert cap.get_value() is None

    state = State('cover.test', cover.STATE_OPEN, {
        ATTR_SUPPORTED_FEATURES: cover.SUPPORT_SET_POSITION,
        cover.ATTR_CURRENT_POSITION: '30',
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_OPEN)
    assert cap.get_value() == 30

    calls = async_mock_service(hass, cover.DOMAIN, cover.SERVICE_SET_COVER_POSITION)
    await cap.set_state(BASIC_DATA, {'value': 0})
    await cap.set_state(BASIC_DATA, {'value': 20})
    await cap.set_state(BASIC_DATA, {'value': -15, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -40, 'relative': True})

    assert len(calls) == 4
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[cover.ATTR_POSITION] == 0
    assert calls[1].data[cover.ATTR_POSITION] == 20
    assert calls[2].data[cover.ATTR_POSITION] == 15
    assert calls[3].data[cover.ATTR_POSITION] == 0


async def test_capability_range_temperature_climate(hass):
    state = State('climate.test', climate.STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_TEMPERATURE)

    state = State('climate.test', climate.STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: climate.SUPPORT_TARGET_TEMPERATURE,
        climate.ATTR_MIN_TEMP: 10,
        climate.ATTR_MAX_TEMP: 25,
        climate.ATTR_TARGET_TEMP_STEP: 1,
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_TEMPERATURE)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'temperature',
        'random_access': True,
        'range': {
            'max': 25,
            'min': 10,
            'precision': 1
        },
        'unit': 'unit.temperature.celsius',
    }
    assert not cap.get_value()

    state = State('climate.test', climate.HVAC_MODE_HEAT_COOL, {
        ATTR_SUPPORTED_FEATURES: climate.SUPPORT_TARGET_TEMPERATURE,
        climate.ATTR_MIN_TEMP: 12,
        climate.ATTR_MAX_TEMP: 27,
        climate.ATTR_TEMPERATURE: 23.5

    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_TEMPERATURE)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'temperature',
        'random_access': True,
        'range': {
            'max': 27,
            'min': 12,
            'precision': 0.5
        },
        'unit': 'unit.temperature.celsius',
    }
    assert cap.get_value() == 23.5

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_state(BASIC_DATA, {'value': 11})
    await cap.set_state(BASIC_DATA, {'value': 15})
    await cap.set_state(BASIC_DATA, {'value': 28})
    await cap.set_state(BASIC_DATA, {'value': 10, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -3, 'relative': True})

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[climate.ATTR_TEMPERATURE] == 11
    assert calls[1].data[climate.ATTR_TEMPERATURE] == 15
    assert calls[2].data[climate.ATTR_TEMPERATURE] == 28
    assert calls[3].data[climate.ATTR_TEMPERATURE] == 27
    assert calls[4].data[climate.ATTR_TEMPERATURE] == 20.5


async def test_capability_range_temperature_water_heater(hass):
    state = State('water_heater.test', water_heater.STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_TEMPERATURE)

    state = State('water_heater.test', water_heater.STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: water_heater.SUPPORT_TARGET_TEMPERATURE,
        water_heater.ATTR_MIN_TEMP: 30,
        water_heater.ATTR_MAX_TEMP: 90,
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_TEMPERATURE)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'temperature',
        'random_access': True,
        'range': {
            'max': 90,
            'min': 30,
            'precision': 0.5
        },
        'unit': 'unit.temperature.celsius',
    }
    assert not cap.get_value()

    state = State('water_heater.test', water_heater.STATE_ELECTRIC, {
        ATTR_SUPPORTED_FEATURES: water_heater.SUPPORT_TARGET_TEMPERATURE,
        water_heater.ATTR_MIN_TEMP: 30,
        water_heater.ATTR_MAX_TEMP: 90,
        water_heater.ATTR_TEMPERATURE: 50

    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_TEMPERATURE)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.get_value() == 50

    calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_SET_TEMPERATURE)
    await cap.set_state(BASIC_DATA, {'value': 20})
    await cap.set_state(BASIC_DATA, {'value': 100})
    await cap.set_state(BASIC_DATA, {'value': 50})
    await cap.set_state(BASIC_DATA, {'value': 15, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -20, 'relative': True})

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[water_heater.ATTR_TEMPERATURE] == 20
    assert calls[1].data[water_heater.ATTR_TEMPERATURE] == 100
    assert calls[2].data[water_heater.ATTR_TEMPERATURE] == 50
    assert calls[3].data[water_heater.ATTR_TEMPERATURE] == 65
    assert calls[4].data[water_heater.ATTR_TEMPERATURE] == 30


async def test_capability_range_humidity_humidifier(hass):
    state = State('humidifier.test', STATE_OFF, {
        humidifier.ATTR_MIN_HUMIDITY: 10,
        humidifier.ATTR_MAX_HUMIDITY: 80,
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_HUMIDITY)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'humidity',
        'random_access': True,
        'range': {
            'max': 80,
            'min': 10,
            'precision': 1
        },
        'unit': 'unit.percent',
    }
    assert not cap.get_value()

    state = State('humidifier.test', STATE_OFF, {
        humidifier.ATTR_MIN_HUMIDITY: 10,
        humidifier.ATTR_MAX_HUMIDITY: 80,
        humidifier.ATTR_HUMIDITY: 30
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_HUMIDITY)
    assert cap.get_value() == 30

    calls = async_mock_service(hass, humidifier.DOMAIN, humidifier.SERVICE_SET_HUMIDITY)
    await cap.set_state(BASIC_DATA, {'value': 20})
    await cap.set_state(BASIC_DATA, {'value': 100})
    await cap.set_state(BASIC_DATA, {'value': 50})
    await cap.set_state(BASIC_DATA, {'value': 15, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -5, 'relative': True})

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[humidifier.ATTR_HUMIDITY] == 20
    assert calls[1].data[humidifier.ATTR_HUMIDITY] == 100
    assert calls[2].data[humidifier.ATTR_HUMIDITY] == 50
    assert calls[3].data[humidifier.ATTR_HUMIDITY] == 45
    assert calls[4].data[humidifier.ATTR_HUMIDITY] == 25


async def test_capability_range_humidity_fan(hass):
    state = State('fan.test', water_heater.STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_HUMIDITY)

    state = State('fan.test', STATE_OFF, {
        const.ATTR_TARGET_HUMIDITY: 50,
        ATTR_MODEL: 'zhimi.test.a'
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_HUMIDITY)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'humidity',
        'random_access': True,
        'range': {
            'max': 100,
            'min': 0,
            'precision': 1
        },
        'unit': 'unit.percent',
    }
    assert cap.get_value() == 50

    calls = async_mock_service(hass, const.DOMAIN_XIAOMI_AIRPURIFIER, const.SERVICE_FAN_SET_TARGET_HUMIDITY)
    await cap.set_state(BASIC_DATA, {'value': 20})
    await cap.set_state(BASIC_DATA, {'value': 100})
    await cap.set_state(BASIC_DATA, {'value': 50})
    await cap.set_state(BASIC_DATA, {'value': 15, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -5, 'relative': True})

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[humidifier.ATTR_HUMIDITY] == 20
    assert calls[1].data[humidifier.ATTR_HUMIDITY] == 100
    assert calls[2].data[humidifier.ATTR_HUMIDITY] == 50
    assert calls[3].data[humidifier.ATTR_HUMIDITY] == 65
    assert calls[4].data[humidifier.ATTR_HUMIDITY] == 45


async def test_capability_range_brightness_legacy(hass):
    state = State('light.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_BRIGHTNESS)

    state = State('light.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: light.SUPPORT_BRIGHTNESS
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_BRIGHTNESS)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'brightness',
        'random_access': True,
        'range': {
            'max': 100,
            'min': 1,
            'precision': 1
        },
        'unit': 'unit.percent',
    }
    assert cap.get_value() is None

    state = State('light.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: light.SUPPORT_BRIGHTNESS,
        light.ATTR_BRIGHTNESS: 128
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_BRIGHTNESS)
    assert cap.get_value() == 50


@pytest.mark.parametrize('color_mode', sorted(light.COLOR_MODES_BRIGHTNESS))
async def test_capability_range_brightness(hass, color_mode):
    state = State('light.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: light.SUPPORT_BRIGHTNESS,
        light.ATTR_SUPPORTED_COLOR_MODES: [color_mode]
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_BRIGHTNESS)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'brightness',
        'random_access': True,
        'range': {
            'max': 100,
            'min': 1,
            'precision': 1
        },
        'unit': 'unit.percent',
    }
    assert cap.get_value() is None

    state = State('light.test', STATE_ON, {
        light.ATTR_SUPPORTED_COLOR_MODES: [color_mode],
        light.ATTR_BRIGHTNESS: 128
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_BRIGHTNESS)
    assert cap.get_value() == 50

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 0})
    await cap.set_state(BASIC_DATA, {'value': 30})
    await cap.set_state(BASIC_DATA, {'value': 126})
    await cap.set_state(BASIC_DATA, {'value': 30, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -60, 'relative': True})

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[light.ATTR_BRIGHTNESS_PCT] == 0
    assert calls[1].data[light.ATTR_BRIGHTNESS_PCT] == 30
    assert calls[2].data[light.ATTR_BRIGHTNESS_PCT] == 126
    assert calls[3].data[light.ATTR_BRIGHTNESS_STEP_PCT] == 30
    assert calls[4].data[light.ATTR_BRIGHTNESS_STEP_PCT] == -60


async def test_capability_range_volume(hass):
    state = State('media_player.test', STATE_ON)
    config = MockConfig(entity_config={
        state.entity_id: {
            'features': [
                'volume_set'
            ]
        }
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_RANGE, RANGE_INSTANCE_VOLUME)
    assert cap.support_random_access


@pytest.mark.parametrize('features', [
    media_player.SUPPORT_VOLUME_SET,
    media_player.SUPPORT_VOLUME_SET | media_player.SUPPORT_VOLUME_STEP,
])
async def test_capability_range_volume_support_random(hass, features):
    state = State('media_player.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_VOLUME)

    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_VOLUME)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'volume',
        'random_access': True,
        'range': {
            'max': 100,
            'min': 0,
            'precision': 1
        },
    }
    assert cap.get_value() is None

    state = State('media_player.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: features,
        media_player.ATTR_MEDIA_VOLUME_LEVEL: 0.56
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_VOLUME)
    assert cap.get_value() == 56

    calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_SET)
    await cap.set_state(BASIC_DATA, {'value': 0})
    await cap.set_state(BASIC_DATA, {'value': 34})
    await cap.set_state(BASIC_DATA, {'value': 126})
    await cap.set_state(BASIC_DATA, {'value': 30, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -10, 'relative': True})
    await cap.set_state(BASIC_DATA, {'value': -60, 'relative': True})

    assert len(calls) == 6
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0
    assert calls[1].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0.34
    assert calls[2].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 1.26
    assert calls[3].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0.86
    assert calls[4].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0.46


@pytest.mark.parametrize('precision', [2, 10, None])
async def test_capability_range_volume_only_relative(hass, precision):
    state = State('media_player.test', STATE_ON, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_VOLUME_STEP
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_VOLUME)
    assert not cap.support_random_access

    entity_config = {}
    if precision:
        entity_config = {
            const.CONF_ENTITY_RANGE: {
                const.CONF_ENTITY_RANGE_PRECISION: precision
            }
        }

    config = MockConfig(
        entity_config={
            state.entity_id: entity_config
        }
    )
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_RANGE, RANGE_INSTANCE_VOLUME)

    calls_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_UP)
    with pytest.raises(SmartHomeError) as e:
        await cap.set_state(BASIC_DATA, {'value': 15})
    assert e.value.code == const.ERR_INVALID_VALUE

    await cap.set_state(BASIC_DATA, {'value': 3, 'relative': True})
    assert len(calls_up) == 3
    for i in range(0, len(calls_up)):
        assert calls_up[i].data[ATTR_ENTITY_ID] == state.entity_id

    calls_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_DOWN)
    await cap.set_state(BASIC_DATA, {'value': -2, 'relative': True})
    assert len(calls_down) == 2
    for i in range(0, len(calls_down)):
        assert calls_down[i].data[ATTR_ENTITY_ID] == state.entity_id

    calls_one_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_UP)
    await cap.set_state(BASIC_DATA, {'value': 1, 'relative': True})
    assert len(calls_one_up) == (precision or 1)
    for i in range(0, precision or 1):
        assert calls_one_up[i].data[ATTR_ENTITY_ID] == state.entity_id

    calls_one_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_DOWN)
    await cap.set_state(BASIC_DATA, {'value': -1, 'relative': True})
    assert len(calls_one_down) == (precision or 1)
    for i in range(0, precision or 1):
        assert calls_one_down[i].data[ATTR_ENTITY_ID] == state.entity_id


async def test_capability_range_channel(hass):
    state = State('media_player.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)

    state = State('media_player.test', STATE_ON)
    config = MockConfig(entity_config={
        state.entity_id: {
            'features': [
                'next_previous_track'
            ]
        }
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)
    assert cap.support_random_access is False


async def test_capability_range_channel_media_content_id(hass):
    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_PLAY_MEDIA,
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)

    config = MockConfig(
        entity_config={
            state.entity_id: {
                const.CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID: True
            }
        }
    )
    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_PLAY_MEDIA,
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'channel',
        'random_access': True,
        'range': {
            'max': 999,
            'min': 0,
            'precision': 1
        },
    }
    assert cap.get_value() is None

    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_PLAY_MEDIA,
        media_player.ATTR_MEDIA_CONTENT_ID: 43,
    })
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)
    assert cap.get_value() == 43

    calls_set = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_PLAY_MEDIA)
    await cap.set_state(BASIC_DATA, {'value': 15})
    assert len(calls_set) == 1
    assert calls_set[0].data == {
        ATTR_ENTITY_ID: state.entity_id,
        media_player.ATTR_MEDIA_CONTENT_ID: 15,
        media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL
    }

    calls_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_NEXT_TRACK)
    await cap.set_state(BASIC_DATA, {'value': 1, 'relative': True})
    assert len(calls_up) == 1
    assert calls_up[0].data == {ATTR_ENTITY_ID: state.entity_id}

    calls_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_PREVIOUS_TRACK)
    await cap.set_state(BASIC_DATA, {'value': -1, 'relative': True})
    assert len(calls_down) == 1
    assert calls_down[0].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_capability_range_channel_yandex_intents(hass):
    state = State('media_player.yandex_intents', STATE_OFF)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)
    assert cap.retrievable
    assert cap.support_random_access
    assert cap.parameters() == {
        'instance': 'channel',
        'random_access': True,
        'range': {
            'max': 999,
            'min': 0,
            'precision': 1
        },
    }
    assert cap.get_value() is None

    calls_set = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_PLAY_MEDIA)
    await cap.set_state(BASIC_DATA, {'value': 15})
    assert len(calls_set) == 1
    assert calls_set[0].data == {
        ATTR_ENTITY_ID: state.entity_id,
        media_player.ATTR_MEDIA_CONTENT_ID: 15,
        media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL
    }


async def test_capability_range_channel_nav(hass):
    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_PREVIOUS_TRACK
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)

    state = State('media_player.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: media_player.SUPPORT_PREVIOUS_TRACK | media_player.SUPPORT_NEXT_TRACK
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_RANGE, RANGE_INSTANCE_CHANNEL)
    assert not cap.retrievable
    assert not cap.support_random_access
    assert cap.parameters() == {
        'instance': 'channel',
        'random_access': False
    }
    assert cap.get_value() is None

    calls_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_NEXT_TRACK)
    await cap.set_state(BASIC_DATA, {'value': 1, 'relative': True})
    assert len(calls_up) == 1
    assert calls_up[0].data == {ATTR_ENTITY_ID: state.entity_id}

    calls_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_PREVIOUS_TRACK)
    await cap.set_state(BASIC_DATA, {'value': -1, 'relative': True})
    assert len(calls_down) == 1
    assert calls_down[0].data == {ATTR_ENTITY_ID: state.entity_id}
