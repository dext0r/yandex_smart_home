# pyright: reportOptionalMemberAccess=false
from typing import cast

from homeassistant.components import light
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.color import RGBColor
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_color import (
    ColorSceneCapability,
    ColorSceneStateCapability,
    ColorSettingCapability,
    ColorTemperatureCapability,
    RGBColorCapability,
)
from custom_components.yandex_smart_home.color import ColorConverter, ColorName, rgb_to_int
from custom_components.yandex_smart_home.entry_data import ConfigEntryData
from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    ColorScene,
    ColorSettingCapabilityInstance,
    ResponseCode,
    RGBInstanceActionState,
    SceneInstanceActionState,
    TemperatureKInstanceActionState,
)

from . import BASIC_ENTRY_DATA, MockConfigEntryData, generate_entity_filter
from .test_capability import assert_no_capabilities, get_exact_one_capability


def _get_color_setting_capability(
    hass: HomeAssistant, entry_data: ConfigEntryData, state: State
) -> ColorSettingCapability:
    return cast(
        ColorSettingCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
        ),
    )


def _get_color_profile_entry_data(entity_config: ConfigType) -> MockConfigEntryData:
    return MockConfigEntryData(
        yaml_config={const.CONF_COLOR_PROFILE: {"test": {"red": rgb_to_int(RGBColor(255, 191, 0)), "white": 4120}}},
        entity_config=entity_config,
        entity_filter=generate_entity_filter(include_entity_globs=["*"]),
    )


async def test_capability_color_setting(hass):
    state = State(
        "light.test",
        STATE_OFF,
        {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.RGB]},
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    assert cap_cs.get_value() is None
    with pytest.raises(APIError) as e:
        await cap_cs.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert e.value.code == ResponseCode.INTERNAL_ERROR


@pytest.mark.parametrize(
    "color_modes",
    [
        [light.ColorMode.RGB],
        [light.ColorMode.RGBW],
        [light.ColorMode.RGBWW],
        [light.ColorMode.HS],
        [light.ColorMode.XY],
        [],
    ],
)
@pytest.mark.parametrize("features", [light.SUPPORT_COLOR, 0])
async def test_capability_color_setting_rgb(hass, color_modes, features):
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
    )
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
    )

    state = State(
        "light.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: features, light.ATTR_SUPPORTED_COLOR_MODES: color_modes}
    )
    if not color_modes and not features:
        assert_no_capabilities(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        )
        assert_no_capabilities(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
        )
        return

    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)

    assert cap_cs.retrievable is True
    if light.ColorMode.RGBWW in color_modes or not color_modes:
        assert cap_cs.parameters.as_dict() == {"color_model": "rgb"}
    else:
        assert cap_cs.parameters.as_dict() == {
            "color_model": "rgb",
            "temperature_k": {"max": 4500 if light.ColorMode.RGBW not in color_modes else 6500, "min": 4500},
        }
    assert cap_rgb.get_value() is None
    assert cap_rgb.get_description() is None

    attributes = {ATTR_SUPPORTED_FEATURES: features, light.ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (240, 100)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.135, 0.039)
    else:
        attributes[light.ATTR_RGB_COLOR] = (0, 0, 255)

    state = State("light.test", STATE_OFF, attributes)
    cap_rgb = get_exact_one_capability(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
    )
    assert cap_rgb.get_value() == 255

    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: features,
            light.ATTR_SUPPORTED_COLOR_MODES: color_modes,
            light.ATTR_RGB_COLOR: (255, 255, 255),
        },
    )
    cap_rgb = get_exact_one_capability(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
    )
    assert cap_rgb.get_value() is None

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap_rgb.set_instance_state(Context(), RGBInstanceActionState(value=720711))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (10, 255, 71)}


@pytest.mark.parametrize(
    "color_modes",
    [
        [light.ColorMode.RGB],
        [light.ColorMode.RGBW],
        [light.ColorMode.RGBWW],
        [light.ColorMode.HS],
        [light.ColorMode.XY],
    ],
)
async def test_capability_color_setting_rgb_near_colors(hass, color_modes):
    attributes = {ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR, light.ATTR_SUPPORTED_COLOR_MODES: color_modes}
    moonlight_color = ColorConverter._palette[ColorName.MOONLIGHT]

    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (230.769, 10.196)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.303, 0.3055)
    else:
        attributes[light.ATTR_RGB_COLOR] = (229, 233, 255)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap.get_value() == moonlight_color

    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (226.154, 10.236)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.302, 0.3075)
    else:
        attributes[light.ATTR_RGB_COLOR] = (228, 234, 254)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap.get_value() == moonlight_color

    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (231.5, 9.1)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.301, 0.307)
    else:
        attributes[light.ATTR_RGB_COLOR] = (226, 230, 250)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap.get_value() != moonlight_color


@pytest.mark.parametrize(
    "color_modes",
    [
        [light.ColorMode.RGB],
        [light.ColorMode.RGBW],
        [light.ColorMode.RGBWW],
        [light.ColorMode.HS],
        [light.ColorMode.XY],
    ],
)
@pytest.mark.parametrize("features", [light.SUPPORT_COLOR])
async def test_capability_color_setting_rgb_with_profile(hass, color_modes, features):
    config = _get_color_profile_entry_data(
        {
            "light.test": {const.CONF_COLOR_PROFILE: "test"},
            "light.invalid": {const.CONF_COLOR_PROFILE: "invalid"},
        }
    )

    attributes = {ATTR_SUPPORTED_FEATURES: features, light.ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (45, 100)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.527, 0.447)
    else:
        attributes[light.ATTR_RGB_COLOR] = (255, 191, 0)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB),
    )
    assert cap.get_value() == 16714250  # red

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 191, 0)}

    state = State("light.invalid", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB),
    )
    with pytest.raises(APIError) as e:
        assert cap.get_value() == 16714250
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert (
        e.value.message
        == "Color profile 'invalid' not found for instance rgb of color_setting capability of light.invalid"
    )

    with pytest.raises(APIError) as e:
        await cap.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert (
        e.value.message
        == "Color profile 'invalid' not found for instance rgb of color_setting capability of light.invalid"
    )


@pytest.mark.parametrize(
    "color_modes",
    [
        [light.ColorMode.RGB],
        [light.ColorMode.RGBW],
        [light.ColorMode.RGBWW],
        [light.ColorMode.HS],
        [light.ColorMode.XY],
    ],
)
@pytest.mark.parametrize("features", [light.SUPPORT_COLOR])
async def test_capability_color_setting_rgb_with_internal_profile(hass, color_modes, features):
    config = _get_color_profile_entry_data({"light.test": {const.CONF_COLOR_PROFILE: "natural"}})

    attributes = {ATTR_SUPPORTED_FEATURES: features, light.ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if light.ColorMode.HS in color_modes:
        attributes[light.ATTR_HS_COLOR] = (0, 100)
    elif light.ColorMode.XY in color_modes:
        attributes[light.ATTR_XY_COLOR] = (0.701, 0.299)
    else:
        attributes[light.ATTR_RGB_COLOR] = (255, 0, 0)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB),
    )
    assert cap.get_value() == 16714250  # red

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 0, 0)}


@pytest.mark.parametrize(
    "attributes,temp_range",
    [
        ({ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR_TEMP}, (1500, 6500)),
        ({light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP]}, (1500, 6500)),
        ({light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.RGB]}, (1500, 6500)),
        ({light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.XY]}, (1500, 6500)),
        (
            {
                light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
                light.ATTR_MIN_COLOR_TEMP_KELVIN: 2000,
                light.ATTR_MAX_COLOR_TEMP_KELVIN: 5000,
            },
            (1500, 5600),
        ),
    ],
)
async def test_capability_color_setting_temperature_k(hass, attributes, temp_range):
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
    )
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
    )

    state = State("light.test", STATE_OFF, attributes)
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": temp_range[0], "max": temp_range[1]}
    assert cap_temp.get_value() is None
    assert cap_temp.get_description() is None

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 2700}, **attributes))
    cap = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap.get_value() == 2700

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap.set_instance_state(Context(), TemperatureKInstanceActionState(value=6500))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 6500}

    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: 0,
            light.ATTR_COLOR_MODE: light.ColorMode.UNKNOWN,
        },
    )
    cap.state = state
    with pytest.raises(APIError) as e:
        await cap.set_instance_state(
            Context(),
            TemperatureKInstanceActionState(value=6500),
        )
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert (
        e.value.message
        == "Unsupported value '6500' for instance temperature_k of color_setting capability of light.test"
    )


async def test_capability_color_setting_temprature_k_extend(hass):
    # 1:1
    state = State(
        "light.test",
        STATE_OFF,
        {
            light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
            light.ATTR_MIN_COLOR_TEMP_KELVIN: 2700,
            light.ATTR_MAX_COLOR_TEMP_KELVIN: 6500,
        },
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 2700, "max": 6500}

    # beyond range
    state = State(
        "light.test",
        STATE_OFF,
        {
            light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
            light.ATTR_MIN_COLOR_TEMP_KELVIN: 700,
            light.ATTR_MAX_COLOR_TEMP_KELVIN: 12000,
        },
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 1500, "max": 9000}

    # no extend
    state = State(
        "light.test",
        STATE_OFF,
        {
            light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
            light.ATTR_MIN_COLOR_TEMP_KELVIN: 2500,
            light.ATTR_MAX_COLOR_TEMP_KELVIN: 6700,
        },
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 2700, "max": 6500}

    # narrow range
    state = State(
        "light.test",
        STATE_OFF,
        {
            light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
            light.ATTR_COLOR_TEMP_KELVIN: 2000,
            light.ATTR_MIN_COLOR_TEMP_KELVIN: 2000,
            light.ATTR_MAX_COLOR_TEMP_KELVIN: 2008,
        },
    )
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 4500, "max": 4500}
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=4500))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 2000}

    # extend
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS],
        light.ATTR_MIN_COLOR_TEMP_KELVIN: 2300,
        light.ATTR_MAX_COLOR_TEMP_KELVIN: 6800,
    }
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 1500, "max": 7500}

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 2300}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 1500

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 6800}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 7500

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 6700}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 6700

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    for v in (1500, 6700, 7500):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 2300}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 6700}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 6800}


@pytest.mark.parametrize(
    "attributes",
    [
        {ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR_TEMP},
        {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP]},
        {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.RGB]},
        {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.HS]},
        {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.XY]},
    ],
)
async def test_capability_color_setting_temperature_k_with_profile(hass, attributes):
    config = _get_color_profile_entry_data(
        {
            "light.test": {const.CONF_COLOR_PROFILE: "test"},
            "light.invalid": {const.CONF_COLOR_PROFILE: "invalid"},
        }
    )
    attributes.update(
        {
            light.ATTR_MIN_COLOR_TEMP_KELVIN: 2000,
            light.ATTR_MAX_COLOR_TEMP_KELVIN: 5882,
        }
    )

    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, config, state)
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.dict()["temperature_k"] == {
        "min": 1500,
        "max": 6500,
    }
    assert cap_temp.get_value() is None

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 2702}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 2700

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 4201}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 4200

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 4115}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=4500))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 4100}

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 4115}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_temp.get_value() == 4100

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=4100))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_KELVIN: 4100}

    state = State("light.invalid", STATE_OFF, dict({light.ATTR_COLOR_TEMP_KELVIN: 4115}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    with pytest.raises(APIError) as e:
        cap_temp.get_value()
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message == (
        "Color profile 'invalid' not found for instance temperature_k of color_setting capability of light.invalid"
    )

    with pytest.raises(APIError) as e:
        await cap_temp.set_instance_state(
            Context(),
            TemperatureKInstanceActionState(value=4100),
        )
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message == (
        "Color profile 'invalid' not found for instance temperature_k of color_setting capability of light.invalid"
    )


@pytest.mark.parametrize("color_modes", [[light.ColorMode.RGB], [light.ColorMode.HS], [light.ColorMode.XY]])
async def test_capability_color_setting_temperature_k_rgb(hass, color_modes):
    attributes = {light.ATTR_SUPPORTED_COLOR_MODES: color_modes}
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {
        "color_model": "rgb",
        "temperature_k": {"max": 4500, "min": 4500},
    }
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGB_COLOR: (0, 0, 0), light.ATTR_COLOR_MODE: color_modes[0]}, **attributes),
    )
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGB_COLOR: (255, 255, 255), light.ATTR_COLOR_MODE: color_modes[0]}, **attributes),
    )
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    for v in (4500, 4300):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}


@pytest.mark.parametrize("color_modes", [[light.ColorMode.RGB], [light.ColorMode.HS], [light.ColorMode.XY]])
async def test_capability_color_setting_temperature_k_rgb_white(hass, color_modes):
    attributes = {light.ATTR_SUPPORTED_COLOR_MODES: color_modes + [light.ColorMode.WHITE]}
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {
        "color_model": "rgb",
        "temperature_k": {"max": 6500, "min": 4500},
    }
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGB_COLOR: (0, 0, 0), light.ATTR_COLOR_MODE: color_modes[0]}, **attributes),
    )
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGB_COLOR: (255, 255, 255), light.ATTR_COLOR_MODE: color_modes[0]}, **attributes),
    )
    assert cap_temp.get_value() == 6500

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict(
            {
                light.ATTR_RGB_COLOR: (255, 255, 255),
                light.ATTR_COLOR_MODE: light.ColorMode.WHITE,
                light.ATTR_BRIGHTNESS: 56,
            },
            **attributes
        ),
    )
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    for v in (6500, 4500, 4300):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_WHITE: 56}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGB_COLOR: (255, 255, 255)}


async def test_capability_color_setting_temperature_k_rgbw(hass):
    attributes = {light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.RGBW]}
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {
        "color_model": "rgb",
        "temperature_k": {"max": 6500, "min": 4500},
    }
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGBW_COLOR: (0, 0, 0, 0), light.ATTR_COLOR_MODE: light.ColorMode.RGBW}, **attributes),
    )
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGBW_COLOR: (100, 100, 100, 255), light.ATTR_COLOR_MODE: light.ColorMode.RGBW}, **attributes),
    )
    assert cap_temp.get_value() is None

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGBW_COLOR: (255, 255, 255, 0), light.ATTR_COLOR_MODE: light.ColorMode.RGBW}, **attributes),
    )
    assert cap_temp.get_value() == 6500

    cap_temp.state = State(
        "light.test",
        STATE_OFF,
        dict({light.ATTR_RGBW_COLOR: (0, 0, 0, 255), light.ATTR_COLOR_MODE: light.ColorMode.RGBW}, **attributes),
    )
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    for v in (4500, 6500, 5000):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGBW_COLOR: (0, 0, 0, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGBW_COLOR: (255, 255, 255, 0)}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_RGBW_COLOR: (255, 255, 255, 0)}


async def test_capability_color_mode_color_temp(hass):
    attributes = {
        light.ATTR_SUPPORTED_COLOR_MODES: [light.ColorMode.COLOR_TEMP, light.ColorMode.RGB],
        light.ATTR_COLOR_TEMP_KELVIN: 3200,
        light.ATTR_MIN_COLOR_TEMP_KELVIN: 2700,
        light.ATTR_MAX_COLOR_TEMP_KELVIN: 6500,
        light.ATTR_RGB_COLOR: [255, 0, 0],
    }

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_MODE: light.ColorMode.RGB}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    cap_rgb = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap_temp.get_value() == 3200
    assert cap_rgb.get_value() == 16711680

    state = State("light.test", STATE_OFF, dict({light.ATTR_COLOR_MODE: light.ColorMode.COLOR_TEMP}, **attributes))
    cap_temp = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )
    cap_rgb = cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap_temp.get_value() == 3200
    assert cap_rgb.get_value() is None


async def test_capability_color_setting_scene(hass):
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE
    )
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
    )

    state = State(
        "light.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: light.LightEntityFeature.EFFECT, light.ATTR_EFFECT_LIST: ["foo", "bar"]},
    )
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE
    )
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
    )

    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: light.LightEntityFeature.EFFECT,
            light.ATTR_EFFECT_LIST: ["foo", "bar", "Alice"],
            light.ATTR_EFFECT: "foo",
        },
    )
    entry_data = MockConfigEntryData(
        entity_config={state.entity_id: {const.CONF_ENTITY_MODE_MAP: {"scene": {"garland": ["foo"]}}}}
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_scene = cast(
        ColorSceneCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE
        ),
    )
    assert cap_cs.parameters.as_dict() == {"color_scene": {"scenes": [{"id": "alice"}, {"id": "garland"}]}}
    assert cap_scene.get_value() == "garland"
    assert cap_scene.get_description() is None

    attributes = {
        ATTR_SUPPORTED_FEATURES: light.LightEntityFeature.EFFECT,
        light.ATTR_EFFECT_LIST: ["Leasure", "Rainbow"],
    }
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, BASIC_ENTRY_DATA, state)
    cap_scene = cast(
        ColorSceneStateCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE
        ),
    )
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {"color_scene": {"scenes": [{"id": "romance"}, {"id": "siren"}]}}
    assert cap_scene.get_value() is None

    cap_scene.state = State("light.test", STATE_OFF, dict({light.ATTR_EFFECT: "Rainbow"}, **attributes))
    assert cap_scene.get_value() == "siren"

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    await cap_scene.set_instance_state(Context(), SceneInstanceActionState(value=ColorScene("romance")))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, light.ATTR_EFFECT: "Leasure"}

    with pytest.raises(APIError) as e:
        await cap_scene.set_instance_state(Context(), SceneInstanceActionState(value=ColorScene("sunset")))
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert (
        e.value.message == "Unsupported scene 'sunset' for instance scene of color_setting capability of light.test, "
        "see https://docs.yaha-cloud.ru/dev/config/modes/"
    )
