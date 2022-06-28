from homeassistant.components import light
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF
from homeassistant.core import State
from homeassistant.util.color import color_temperature_kelvin_to_mired
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_color import CAPABILITIES_COLOR_SETTING, ColorConverter
from custom_components.yandex_smart_home.const import (
    COLOR_SETTING_RGB,
    COLOR_SETTING_SCENE,
    COLOR_SETTING_TEMPERATURE_K,
)
from custom_components.yandex_smart_home.error import SmartHomeError

from . import BASIC_CONFIG, BASIC_DATA, MockConfig, generate_entity_filter
from .test_capability import assert_no_capabilities, get_exact_one_capability


class ColorProfileMockConfig(MockConfig):
    @property
    def color_profiles(self) -> dict[str, dict[str, int]]:
        return {
            'test': {
                'red': ColorConverter.rgb_to_int(255, 191, 0),
                'white': 4120
            }
        }


@pytest.mark.parametrize('color_modes', [
    [light.ColorMode.RGB], [light.ColorMode.RGBW], [light.ColorMode.RGBWW], [light.ColorMode.HS],
    [light.ColorMode.XY], []
])
@pytest.mark.parametrize('features', [
    light.SUPPORT_COLOR, 0
])
async def test_capability_color_setting_rgb(hass, color_modes, features):
    state = State('light.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)

    state = State('light.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes
    })
    if not color_modes and not features:
        assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
        return

    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.retrievable
    if light.ColorMode.RGBWW in color_modes or not color_modes:
        assert cap.parameters() == {'color_model': 'rgb'}
    else:
        assert cap.parameters() == {
            'color_model': 'rgb',
            'temperature_k': {
                'max': 4500 if light.ColorMode.RGBW not in color_modes else 6500,
                'min': 4500
            }
        }
    assert not cap.get_value()

    attributes = {
        ATTR_SUPPORTED_FEATURES: features,
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes
    }
    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (240, 100)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.135, 0.039)
    else:
        attributes[light.ATTR_RGB_COLOR] = (0, 0, 255)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() == 255

    state = State('light.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: features,
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes,
        light.ATTR_RGB_COLOR: (255, 255, 255)
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() is None

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 720711})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (10, 255, 71)}


@pytest.mark.parametrize('color_modes', [
    [light.ColorMode.RGB], [light.ColorMode.RGBW], [light.ColorMode.RGBWW], [light.ColorMode.HS], [light.ColorMode.XY]
])
async def test_capability_color_setting_rgb_near_colors(hass, color_modes):
    attributes = {
        ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR,
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes
    }
    moonlight_color = ColorConverter._palette[const.COLOR_NAME_MOONLIGHT]

    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (230.769, 10.196)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.303, 0.3055)
    else:
        attributes[light.ATTR_RGB_COLOR] = (229, 233, 255)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() == moonlight_color

    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (226.154, 10.236)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.302, 0.3075)
    else:
        attributes[light.ATTR_RGB_COLOR] = (228, 234, 254)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() == moonlight_color

    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (231.5, 9.1)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.301, 0.307)
    else:
        attributes[light.ATTR_RGB_COLOR] = (226, 230, 250)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() != moonlight_color


@pytest.mark.parametrize('color_modes', [
    [light.ColorMode.RGB], [light.ColorMode.RGBW], [light.ColorMode.RGBWW], [light.ColorMode.HS], [light.ColorMode.XY]
])
@pytest.mark.parametrize('features', [
    light.SUPPORT_COLOR
])
async def test_capability_color_setting_rgb_with_profile(hass, color_modes, features):
    config = ColorProfileMockConfig(
        entity_config={
            'light.test': {
                const.CONF_COLOR_PROFILE: 'test'
            },
            'light.invalid': {
                const.CONF_COLOR_PROFILE: 'invalid'
            }
        },
        entity_filter=generate_entity_filter(include_entity_globs=['*'])
    )

    attributes = {
        ATTR_SUPPORTED_FEATURES: features,
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes
    }
    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (45, 100)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.527, 0.447)
    else:
        attributes[light.ATTR_RGB_COLOR] = (255, 191, 0)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() == 16714250  # red

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 16714250})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 191, 0)}

    state = State('light.invalid', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    with pytest.raises(SmartHomeError) as e:
        assert cap.get_value() == 16714250
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message.startswith('Color profile')

    with pytest.raises(SmartHomeError) as e:
        await cap.set_state(BASIC_DATA, {'value': 16714250})
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message.startswith('Color profile')


@pytest.mark.parametrize('color_modes', [
    [light.ColorMode.RGB], [light.ColorMode.RGBW], [light.ColorMode.RGBWW], [light.ColorMode.HS], [light.ColorMode.XY]
])
@pytest.mark.parametrize('features', [
    light.SUPPORT_COLOR
])
async def test_capability_color_setting_rgb_with_internal_profile(hass, color_modes, features):
    config = ColorProfileMockConfig(
        entity_config={
            'light.test': {
                const.CONF_COLOR_PROFILE: 'natural'
            }
        },
        entity_filter=generate_entity_filter(include_entity_globs=['*'])
    )

    attributes = {
        ATTR_SUPPORTED_FEATURES: features,
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes
    }
    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (0, 100)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.701, 0.299)
    else:
        attributes[light.ATTR_RGB_COLOR] = (255, 0, 0)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() == 16714250  # red

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 16714250})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 0, 0)}


@pytest.mark.parametrize('attributes,temp_range', [
    ({ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR_TEMP}, (1500, 6500)),
    ({
         light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP]
     }, (1500, 6500)),
    ({
         light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.RGB]
     }, (1500, 6500)),
    ({
         light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.XY]
     }, (1500, 6500)),
    ({
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
        light.ATTR_MIN_MIREDS: 200,
        light.ATTR_MAX_MIREDS: 500,
     }, (1500, 5600)),
])
async def test_capability_color_setting_temperature_k(hass, attributes, temp_range):
    state = State('light.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.retrievable
    assert cap.parameters()['temperature_k'] == {
        'min': temp_range[0],
        'max': temp_range[1]
    }
    assert cap.get_value() is None

    state = State('light.test', STATE_OFF, dict({light.ATTR_COLOR_TEMP: 370}, **attributes))
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 2700

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 6500})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 6500}

    state = State('light.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: 0,
        light.ATTR_COLOR_MODE: light.ColorMode.UNKNOWN,
    })
    cap.state = state
    with pytest.raises(SmartHomeError) as e:
        await cap.set_state(BASIC_DATA, {'value': 6500})
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE


async def test_capability_color_setting_temprature_k_extend(hass):
    # 1:1
    state = State('light.test', STATE_OFF, {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
        light.ATTR_MIN_MIREDS: color_temperature_kelvin_to_mired(6500),
        light.ATTR_MAX_MIREDS: color_temperature_kelvin_to_mired(2700),
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.parameters()['temperature_k'] == {
        'min': 2700,
        'max': 6500
    }

    # beyond range
    state = State('light.test', STATE_OFF, {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
        light.ATTR_MIN_MIREDS: color_temperature_kelvin_to_mired(12000),
        light.ATTR_MAX_MIREDS: color_temperature_kelvin_to_mired(700),
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.parameters()['temperature_k'] == {
        'min': 1500,
        'max': 9000
    }

    # no extend
    state = State('light.test', STATE_OFF, {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
        light.ATTR_MIN_MIREDS: color_temperature_kelvin_to_mired(6700),
        light.ATTR_MAX_MIREDS: color_temperature_kelvin_to_mired(2500),
    })
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.parameters()['temperature_k'] == {
        'min': 2700,
        'max': 6500
    }

    # extend
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
        light.ATTR_MIN_MIREDS: color_temperature_kelvin_to_mired(6800),
        light.ATTR_MAX_MIREDS: color_temperature_kelvin_to_mired(2300),
    }
    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.parameters()['temperature_k'] == {
        'min': 1500,
        'max': 7500
    }

    state = State('light.test', STATE_OFF, dict({
        light.ATTR_COLOR_TEMP: color_temperature_kelvin_to_mired(2300)
    }, **attributes))
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 1500

    state = State('light.test', STATE_OFF, dict({
        light.ATTR_COLOR_TEMP: color_temperature_kelvin_to_mired(6800)
    }, **attributes))
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 7500

    state = State('light.test', STATE_OFF, dict({
        light.ATTR_COLOR_TEMP: color_temperature_kelvin_to_mired(6700)
    }, **attributes))
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 6700

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 1500})
    await cap.set_state(BASIC_DATA, {'value': 6700})
    await cap.set_state(BASIC_DATA, {'value': 7500})
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 2300}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 6700}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 6800}


@pytest.mark.parametrize('attributes', [
    {ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR_TEMP},
    {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP]},
    {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.RGB]},
    {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS]},
    {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.XY]},
])
async def test_capability_color_setting_temperature_k_with_profile(hass, attributes):
    config = ColorProfileMockConfig(
        entity_config={
            'light.test': {
                const.CONF_COLOR_PROFILE: 'test'
            },
            'light.invalid': {
                const.CONF_COLOR_PROFILE: 'invalid'
            }
        },
        entity_filter=generate_entity_filter(include_entity_globs=['*'])
    )
    attributes.update({
        light.ATTR_MIN_MIREDS: 170,
        light.ATTR_MAX_MIREDS: 500,
    })

    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.retrievable
    assert cap.parameters()['temperature_k'] == {
        'min': 1500,
        'max': 6500,
    }
    assert cap.get_value() is None

    state = State('light.test', STATE_OFF, dict({light.ATTR_COLOR_TEMP: 370}, **attributes))
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 2700

    state = State('light.test', STATE_OFF, dict({light.ATTR_COLOR_TEMP: 238}, **attributes))
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 4200

    state = State('light.test', STATE_OFF, dict({light.ATTR_COLOR_TEMP: 243}, **attributes))  # k: 4150
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 4500})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 4100}

    state = State('light.test', STATE_OFF, dict({light.ATTR_COLOR_TEMP: 243}, **attributes))  # k: 4150
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 4100

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 4100})
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 4100}

    state = State('light.invalid', STATE_OFF, dict({light.ATTR_COLOR_TEMP: 243}, **attributes))
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    with pytest.raises(SmartHomeError) as e:
        cap.get_value()
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message.startswith('Color profile')

    with pytest.raises(SmartHomeError) as e:
        await cap.set_state(BASIC_DATA, {'value': 4100})
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message.startswith('Color profile')


@pytest.mark.parametrize('color_modes', [
    [light.ColorMode.RGB], [light.ColorMode.HS], [light.ColorMode.XY]
])
async def test_capability_color_setting_temperature_k_rgb(hass, color_modes):
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes
    }
    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.retrievable
    assert cap.parameters() == {'color_model': 'rgb', 'temperature_k': {'max': 4500, 'min': 4500}}
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGB_COLOR: (0, 0, 0),
        light.ATTR_COLOR_MODE: color_modes[0]
    }, **attributes))
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGB_COLOR: (255, 255, 255),
        light.ATTR_COLOR_MODE: color_modes[0]
    }, **attributes))
    assert cap.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 4500})
    await cap.set_state(BASIC_DATA, {'value': 4300})
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}


@pytest.mark.parametrize('color_modes', [
    [light.ColorMode.RGB], [light.ColorMode.HS], [light.ColorMode.XY]
])
async def test_capability_color_setting_temperature_k_rgb_white(hass, color_modes):
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: color_modes + [light.ColorMode.WHITE]
    }
    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.retrievable
    assert cap.parameters() == {'color_model': 'rgb', 'temperature_k': {'max': 6500, 'min': 4500}}
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGB_COLOR: (0, 0, 0),
        light.ATTR_COLOR_MODE: color_modes[0]
    }, **attributes))
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGB_COLOR: (255, 255, 255),
        light.ATTR_COLOR_MODE: color_modes[0]
    }, **attributes))
    assert cap.get_value() == 6500

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGB_COLOR: (255, 255, 255),
        light.ATTR_COLOR_MODE: light.ColorMode.WHITE,
        light.ATTR_BRIGHTNESS: 56
    }, **attributes))
    assert cap.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 6500})
    await cap.set_state(BASIC_DATA, {'value': 4500})
    await cap.set_state(BASIC_DATA, {'value': 4300})
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_WHITE: 56}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}


async def test_capability_color_setting_temperature_k_rgbw(hass):
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.RGBW]
    }
    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.retrievable
    assert cap.parameters() == {'color_model': 'rgb', 'temperature_k': {'max': 6500, 'min': 4500}}
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGBW_COLOR: (0, 0, 0, 0),
        light.ATTR_COLOR_MODE: light.ColorMode.RGBW
    }, **attributes))
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGBW_COLOR: (100, 100, 100, 255),
        light.ATTR_COLOR_MODE: light.ColorMode.RGBW
    }, **attributes))
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGBW_COLOR: (255, 255, 255, 0),
        light.ATTR_COLOR_MODE: light.ColorMode.RGBW
    }, **attributes))
    assert cap.get_value() == 6500

    cap.state = State('light.test', STATE_OFF, dict({
        light.ATTR_RGBW_COLOR: (0, 0, 0, 255),
        light.ATTR_COLOR_MODE: light.ColorMode.RGBW
    }, **attributes))
    assert cap.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 4500})
    await cap.set_state(BASIC_DATA, {'value': 6500})
    await cap.set_state(BASIC_DATA, {'value': 5000})
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGBW_COLOR: (0, 0, 0, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGBW_COLOR: (255, 255, 255, 0)}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGBW_COLOR: (255, 255, 255, 0)}


async def test_capability_color_mode_color_temp(hass):
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.RGB],
        light.ATTR_MIN_MIREDS: color_temperature_kelvin_to_mired(6500),
        light.ATTR_MAX_MIREDS: color_temperature_kelvin_to_mired(2700),
        light.ATTR_COLOR_TEMP: color_temperature_kelvin_to_mired(3200),
        light.ATTR_RGB_COLOR: [255, 0, 0]
    }

    state = State('light.test', STATE_OFF, dict({
        light.ATTR_COLOR_MODE: light.ColorMode.RGB
    }, **attributes))
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 3200
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() == 16711680

    state = State('light.test', STATE_OFF, dict({
        light.ATTR_COLOR_MODE: light.ColorMode.COLOR_TEMP
    }, **attributes))
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_TEMPERATURE_K)
    assert cap.get_value() == 3200
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_RGB)
    assert cap.get_value() is None


async def test_capability_color_setting_scene(hass):
    state = State('light.test', STATE_OFF)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_SCENE)

    state = State('light.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: light.LightEntityFeature.EFFECT,
        light.ATTR_EFFECT_LIST: ['foo', 'bar']
    })
    assert_no_capabilities(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_SCENE)

    state = State('light.test', STATE_OFF, {
        ATTR_SUPPORTED_FEATURES: light.LightEntityFeature.EFFECT,
        light.ATTR_EFFECT_LIST: ['foo', 'bar', 'Alice'],
        light.ATTR_EFFECT: 'foo',
    })
    config = MockConfig(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    const.COLOR_SETTING_SCENE: {
                        const.COLOR_SCENE_GARLAND: ['foo']
                    }
                }
            }
        }
    )
    cap = get_exact_one_capability(hass, config, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_SCENE)
    assert cap.parameters() == {'color_scene': {'scenes': [{'id': 'alice'}, {'id': 'garland'}]}}
    assert cap.get_value() == 'garland'

    attributes = {
        ATTR_SUPPORTED_FEATURES: light.LightEntityFeature.EFFECT,
        light.ATTR_EFFECT_LIST: ['Leasure', 'Rainbow']
    }
    state = State('light.test', STATE_OFF, attributes)
    cap = get_exact_one_capability(hass, BASIC_CONFIG, state, CAPABILITIES_COLOR_SETTING, COLOR_SETTING_SCENE)
    assert cap.retrievable
    assert cap.parameters() == {'color_scene': {'scenes': [{'id': 'romance'}, {'id': 'siren'}]}}
    assert cap.get_value() is None

    cap.state = State('light.test', STATE_OFF, dict({light.ATTR_EFFECT: 'Rainbow'}, **attributes))
    assert cap.get_value() == 'siren'

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_state(BASIC_DATA, {'value': 'romance'})
    await cap.set_state(BASIC_DATA, {'value': 'invalid'})
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_EFFECT: 'Leasure'}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_EFFECT: None}
