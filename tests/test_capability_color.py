from typing import Any, cast

from homeassistant.components import light
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    ATTR_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_WHITE,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.color import RGBColor
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home.capability_color import (
    ColorSceneCapability,
    ColorSceneStateCapability,
    ColorSettingCapability,
    ColorTemperatureCapability,
    RGBColorCapability,
)
from custom_components.yandex_smart_home.color import ColorConverter, ColorName, rgb_to_int
from custom_components.yandex_smart_home.const import CONF_COLOR_PROFILE, CONF_ENTITY_MODE_MAP
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

from . import MockConfigEntryData, generate_entity_filter
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


def _get_temperature_capability(
    hass: HomeAssistant, entry_data: MockConfigEntryData, state: State
) -> ColorTemperatureCapability:
    return cast(
        ColorTemperatureCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
        ),
    )


def _get_color_profile_entry_data(hass: HomeAssistant, entity_config: ConfigType) -> MockConfigEntryData:
    return MockConfigEntryData(
        hass,
        yaml_config={CONF_COLOR_PROFILE: {"test": {"red": rgb_to_int(RGBColor(255, 191, 0)), "white": 4120}}},
        entity_config=entity_config,
        entity_filter=generate_entity_filter(include_entity_globs=["*"]),
    )


async def test_capability_color_setting(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State(
        "light.test",
        STATE_OFF,
        {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGB]},
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    assert cap_cs.get_value() is None
    with pytest.raises(APIError) as e:
        await cap_cs.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert e.value.code == ResponseCode.INTERNAL_ERROR


@pytest.mark.parametrize(
    "color_modes",
    [
        [ColorMode.HS],
        [ColorMode.XY],
        [ColorMode.RGB],
        [ColorMode.RGBW],
        [ColorMode.RGBWW],
        [],
    ],
)
async def test_capability_color_setting_rgb(
    hass: HomeAssistant, entry_data: MockConfigEntryData, color_modes: list[ColorMode]
) -> None:
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB)
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE)

    state = State("light.test", STATE_OFF, {ATTR_SUPPORTED_COLOR_MODES: color_modes})
    if not color_modes:
        assert_no_capabilities(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        )
        assert_no_capabilities(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE
        )
        return

    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)

    assert cap_cs.retrievable is True
    if ColorMode.RGBWW in color_modes or not color_modes:
        assert cap_cs.parameters.as_dict() == {"color_model": "rgb"}
    else:
        assert cap_cs.parameters.as_dict() == {
            "color_model": "rgb",
            "temperature_k": {"max": 4500 if ColorMode.RGBW not in color_modes else 6500, "min": 4500},
        }
    assert cap_rgb.get_value() is None
    assert cap_rgb.get_description() is None

    attributes: dict[str, Any] = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (240, 100)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.135, 0.039)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (0, 0, 255)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (0, 0, 255, 0)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (0, 0, 255, 0, 0)

    state = State("light.test", STATE_OFF, attributes)
    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap_rgb.get_value() == 255

    for level in (0, 255):
        attributes = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
        if ColorMode.RGBWW in color_modes:
            attributes[ATTR_RGBWW_COLOR] = (level, level, level, 10, 10)
        elif ColorMode.RGBW in color_modes:
            attributes[ATTR_RGBW_COLOR] = (level, level, level, 10)
        else:
            attributes[ATTR_RGB_COLOR] = (level, level, level)

        state = State("light.test", STATE_OFF, attributes)
        cap_rgb = cast(
            RGBColorCapability,
            get_exact_one_capability(
                hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
            ),
        )
        assert cap_rgb.get_value() is None

    state = State("light.test", STATE_OFF, {ATTR_SUPPORTED_COLOR_MODES: color_modes})
    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap_rgb.get_value() is None
    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap_rgb.set_instance_state(Context(), RGBInstanceActionState(value=720711))
    assert len(calls) == 1
    if ColorMode.RGBWW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBWW_COLOR: (10, 255, 71, 0, 0)}
    elif ColorMode.RGBW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (10, 255, 71, 0)}
    else:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (10, 255, 71)}

    attributes = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (209.677, 62)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.186, 0.225)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (50, 100, 150)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (50, 100, 150, 12)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (50, 100, 150, 12, 15)

    state = State("light.test", STATE_ON, attributes)
    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    if ColorMode.HS in color_modes:
        assert cap_rgb.get_value() == 6336767
    elif ColorMode.XY in color_modes:
        assert cap_rgb.get_value() == 6927615
    else:
        assert cap_rgb.get_value() == 3302550

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap_rgb.set_instance_state(Context(), RGBInstanceActionState(value=720711))
    assert len(calls) == 1
    if ColorMode.RGBWW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBWW_COLOR: (10, 255, 71, 12, 15)}
    elif ColorMode.RGBW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (10, 255, 71, 12)}
    else:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (10, 255, 71)}


@pytest.mark.parametrize(
    "color_modes",
    [
        [ColorMode.HS],
        [ColorMode.XY],
        [ColorMode.RGB],
        [ColorMode.RGBW],
        [ColorMode.RGBWW],
    ],
)
async def test_capability_color_setting_rgb_near_colors(
    hass: HomeAssistant, entry_data: MockConfigEntryData, color_modes: list[ColorMode]
) -> None:
    attributes: dict[str, Any] = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
    moonlight_color = ColorConverter._palette[ColorName.MOONLIGHT]

    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (230.769, 10.196)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.303, 0.3055)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (229, 233, 255)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (229, 233, 255, 10)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (229, 233, 255, 10, 15)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap.get_value() == moonlight_color

    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (226.154, 10.236)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.302, 0.3075)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (228, 234, 254)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (228, 234, 254, 10)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (228, 234, 254, 10, 15)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap.get_value() == moonlight_color

    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (231.5, 9.1)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.301, 0.307)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (226, 230, 250)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (226, 230, 250, 10)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (226, 230, 250, 10, 10)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap.get_value() != moonlight_color


@pytest.mark.parametrize(
    "color_modes",
    [
        [ColorMode.HS],
        [ColorMode.XY],
        [ColorMode.RGB],
        [ColorMode.RGBW],
        [ColorMode.RGBWW],
    ],
)
async def test_capability_color_setting_rgb_with_profile(hass: HomeAssistant, color_modes: list[ColorMode]) -> None:
    config = _get_color_profile_entry_data(
        hass,
        {
            "light.test": {CONF_COLOR_PROFILE: "test"},
            "light.invalid": {CONF_COLOR_PROFILE: "invalid"},
        },
    )

    attributes: dict[str, Any] = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (45, 100)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.527, 0.447)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (255, 191, 0)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (255, 191, 0, 10)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (255, 191, 0, 10, 15)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB),
    )
    assert cap.get_value() == 16714250  # red

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert len(calls) == 1
    if ColorMode.RGBW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (255, 191, 0, 10)}
    elif ColorMode.RGBWW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBWW_COLOR: (255, 191, 0, 10, 15)}
    else:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (255, 191, 0)}

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
        [ColorMode.HS],
        [ColorMode.XY],
        [ColorMode.RGB],
        [ColorMode.RGBW],
        [ColorMode.RGBWW],
    ],
)
async def test_capability_color_setting_rgb_with_internal_profile(
    hass: HomeAssistant, color_modes: list[ColorMode]
) -> None:
    config = _get_color_profile_entry_data(hass, {"light.test": {CONF_COLOR_PROFILE: "natural"}})

    attributes: dict[str, Any] = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
    if ColorMode.HS in color_modes:
        attributes[ATTR_HS_COLOR] = (0, 100)
    elif ColorMode.XY in color_modes:
        attributes[ATTR_XY_COLOR] = (0.701, 0.299)
    elif ColorMode.RGB in color_modes:
        attributes[ATTR_RGB_COLOR] = (255, 0, 0)
    elif ColorMode.RGBW in color_modes:
        attributes[ATTR_RGBW_COLOR] = (255, 0, 0, 10)
    elif ColorMode.RGBWW in color_modes:
        attributes[ATTR_RGBWW_COLOR] = (255, 0, 0, 10, 15)

    state = State("light.test", STATE_OFF, attributes)
    cap = cast(
        RGBColorCapability,
        get_exact_one_capability(hass, config, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB),
    )
    assert cap.get_value() == 16714250  # red

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap.set_instance_state(Context(), RGBInstanceActionState(value=16714250))
    assert len(calls) == 1
    if ColorMode.RGBW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (255, 0, 0, 10)}
    elif ColorMode.RGBWW in color_modes:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBWW_COLOR: (255, 0, 0, 10, 15)}
    else:
        assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (255, 0, 0)}


@pytest.mark.parametrize(
    "attributes,temp_range",
    [
        ({ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP]}, (1500, 6500)),
        ({ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.RGB]}, (1500, 6500)),
        ({ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.XY]}, (1500, 6500)),
        (
            {
                ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS],
                ATTR_MIN_COLOR_TEMP_KELVIN: 2000,
                ATTR_MAX_COLOR_TEMP_KELVIN: 5000,
            },
            (1500, 5600),
        ),
    ],
)
async def test_capability_color_setting_temperature_k(
    hass: HomeAssistant, entry_data: MockConfigEntryData, attributes: dict[str, Any], temp_range: tuple[int, int]
) -> None:
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(
        hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.TEMPERATURE_K
    )
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE)

    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": temp_range[0], "max": temp_range[1]}
    assert cap_temp.get_value() is None
    assert cap_temp.get_description() is None

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 2700}, **attributes))
    cap = _get_temperature_capability(hass, entry_data, state)
    assert cap.get_value() == 2700

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap.set_instance_state(Context(), TemperatureKInstanceActionState(value=6500))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 6500}


async def test_capability_color_setting_temprature_k_extend(
    hass: HomeAssistant, entry_data: MockConfigEntryData
) -> None:
    # 1:1
    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS],
            ATTR_MIN_COLOR_TEMP_KELVIN: 2700,
            ATTR_MAX_COLOR_TEMP_KELVIN: 6500,
        },
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 2700, "max": 6500}

    # beyond range
    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS],
            ATTR_MIN_COLOR_TEMP_KELVIN: 700,
            ATTR_MAX_COLOR_TEMP_KELVIN: 12000,
        },
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 1500, "max": 9000}

    # no extend
    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS],
            ATTR_MIN_COLOR_TEMP_KELVIN: 2500,
            ATTR_MAX_COLOR_TEMP_KELVIN: 6700,
        },
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 2700, "max": 6500}

    # narrow range
    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS],
            ATTR_COLOR_TEMP_KELVIN: 2000,
            ATTR_MIN_COLOR_TEMP_KELVIN: 2000,
            ATTR_MAX_COLOR_TEMP_KELVIN: 2008,
        },
    )
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 4500, "max": 4500}
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=4500))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 2000}

    # extend
    attributes = {
        ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS],
        ATTR_MIN_COLOR_TEMP_KELVIN: 2300,
        ATTR_MAX_COLOR_TEMP_KELVIN: 6800,
    }
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    assert cap_cs.parameters.dict()["temperature_k"] == {"min": 1500, "max": 7500}

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 2300}, **attributes))
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 1500

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 6800}, **attributes))
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 7500

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 6700}, **attributes))
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 6700

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    for v in (1500, 6700, 7500):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 2300}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 6700}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 6800}


@pytest.mark.parametrize(
    "attributes",
    [
        {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP]},
        {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.RGB]},
        {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.HS]},
        {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.XY]},
    ],
)
async def test_capability_color_setting_temperature_k_with_profile(
    hass: HomeAssistant, entry_data: MockConfigEntryData, attributes: dict[str, Any]
) -> None:
    config = _get_color_profile_entry_data(
        hass,
        {
            "light.test": {CONF_COLOR_PROFILE: "test"},
            "light.invalid": {CONF_COLOR_PROFILE: "invalid"},
        },
    )
    attributes.update(
        {
            ATTR_MIN_COLOR_TEMP_KELVIN: 2000,
            ATTR_MAX_COLOR_TEMP_KELVIN: 5882,
        }
    )

    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, config, state)
    cap_temp = _get_temperature_capability(hass, config, state)
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.dict()["temperature_k"] == {
        "min": 1500,
        "max": 6500,
    }
    assert cap_temp.get_value() is None

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 2702}, **attributes))
    cap_temp = _get_temperature_capability(hass, config, state)
    assert cap_temp.get_value() == 2700

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 4201}, **attributes))
    cap_temp = _get_temperature_capability(hass, config, state)
    assert cap_temp.get_value() == 4200

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 4115}, **attributes))
    cap_temp = _get_temperature_capability(hass, config, state)
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=4500))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 4100}

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 4115}, **attributes))
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 4100

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=4100))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_KELVIN: 4100}

    state = State("light.invalid", STATE_OFF, dict({ATTR_COLOR_TEMP_KELVIN: 4115}, **attributes))
    cap_temp = _get_temperature_capability(hass, config, state)
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


@pytest.mark.parametrize("color_mode", [ColorMode.RGB, ColorMode.HS, ColorMode.XY])
async def test_capability_color_setting_temperature_k_rgb(
    hass: HomeAssistant, entry_data: MockConfigEntryData, color_mode: ColorMode
) -> None:
    attributes = {ATTR_SUPPORTED_COLOR_MODES: [color_mode]}
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {
        "color_model": "rgb",
        "temperature_k": {"max": 4500, "min": 4500},
    }
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGB_COLOR: (0, 0, 0), ATTR_COLOR_MODE: color_mode}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGB_COLOR: (255, 255, 255), ATTR_COLOR_MODE: color_mode}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    for v in (4500, 4300):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (255, 255, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (255, 255, 255)}


@pytest.mark.parametrize("color_modes", [[ColorMode.RGB], [ColorMode.HS], [ColorMode.XY]])
async def test_capability_color_setting_temperature_k_rgb_white(
    hass: HomeAssistant, entry_data: MockConfigEntryData, color_modes: list[ColorMode]
) -> None:
    attributes = {ATTR_SUPPORTED_COLOR_MODES: color_modes}
    attributes = {ATTR_SUPPORTED_COLOR_MODES: color_modes + [ColorMode.WHITE]}
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {
        "color_model": "rgb",
        "temperature_k": {"max": 6500, "min": 4500},
    }
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGB_COLOR: (0, 0, 0), ATTR_COLOR_MODE: color_modes[0]}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGB_COLOR: (255, 255, 255), ATTR_COLOR_MODE: color_modes[0]}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 6500

    state = State(
        "light.test",
        STATE_OFF,
        dict(
            {
                ATTR_RGB_COLOR: (255, 255, 255),
                ATTR_COLOR_MODE: ColorMode.WHITE,
                ATTR_BRIGHTNESS: 56,
            },
            **attributes
        ),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    for v in (6500, 4500, 4300):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (255, 255, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_WHITE: 56}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGB_COLOR: (255, 255, 255)}


async def test_capability_color_setting_temperature_k_rgbw(
    hass: HomeAssistant, entry_data: MockConfigEntryData
) -> None:
    attributes = {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.RGBW]}
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {
        "color_model": "rgb",
        "temperature_k": {"max": 6500, "min": 4500},
    }
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGBW_COLOR: (0, 0, 0, 0), ATTR_COLOR_MODE: ColorMode.RGBW}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGBW_COLOR: (100, 100, 100, 255), ATTR_COLOR_MODE: ColorMode.RGBW}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() is None

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGBW_COLOR: (255, 255, 255, 0), ATTR_COLOR_MODE: ColorMode.RGBW}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 6500

    state = State(
        "light.test",
        STATE_OFF,
        dict({ATTR_RGBW_COLOR: (0, 0, 0, 255), ATTR_COLOR_MODE: ColorMode.RGBW}, **attributes),
    )
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    assert cap_temp.get_value() == 4500

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    for v in (4500, 6500, 5000):
        await cap_temp.set_instance_state(Context(), TemperatureKInstanceActionState(value=v))
    assert len(calls) == 3
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (0, 0, 0, 255)}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (255, 255, 255, 0)}
    assert calls[2].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_RGBW_COLOR: (255, 255, 255, 0)}


async def test_capability_color_mode_color_temp(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    attributes = {
        ATTR_SUPPORTED_COLOR_MODES: [ColorMode.COLOR_TEMP, ColorMode.RGB],
        ATTR_COLOR_TEMP_KELVIN: 3200,
        ATTR_MIN_COLOR_TEMP_KELVIN: 2700,
        ATTR_MAX_COLOR_TEMP_KELVIN: 6500,
        ATTR_RGB_COLOR: [255, 0, 0],
    }

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_MODE: ColorMode.RGB}, **attributes))
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap_temp.get_value() == 3200
    assert cap_rgb.get_value() == 16711680

    state = State("light.test", STATE_OFF, dict({ATTR_COLOR_MODE: ColorMode.COLOR_TEMP}, **attributes))
    cap_temp = _get_temperature_capability(hass, entry_data, state)
    cap_rgb = cast(
        RGBColorCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.RGB
        ),
    )
    assert cap_temp.get_value() == 3200
    assert cap_rgb.get_value() is None


async def test_capability_color_setting_scene(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE)
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE)

    state = State(
        "light.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: LightEntityFeature.EFFECT, ATTR_EFFECT_LIST: ["foo", "bar"]},
    )
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE)
    assert_no_capabilities(hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.BASE)

    state = State(
        "light.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: LightEntityFeature.EFFECT,
            ATTR_EFFECT_LIST: ["foo", "bar", "Alice"],
            ATTR_EFFECT: "foo",
        },
    )
    entry_data = MockConfigEntryData(
        hass, entity_config={state.entity_id: {CONF_ENTITY_MODE_MAP: {"scene": {"garland": ["foo"]}}}}
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
        ATTR_SUPPORTED_FEATURES: LightEntityFeature.EFFECT,
        ATTR_EFFECT_LIST: ["Leasure", "Rainbow"],
    }
    state = State("light.test", STATE_OFF, attributes)
    cap_cs = _get_color_setting_capability(hass, entry_data, state)
    cap_scene = cast(
        ColorSceneStateCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.COLOR_SETTING, ColorSettingCapabilityInstance.SCENE
        ),
    )
    assert cap_cs.retrievable is True
    assert cap_cs.parameters.as_dict() == {"color_scene": {"scenes": [{"id": "romance"}, {"id": "siren"}]}}
    assert cap_scene.get_value() is None

    cap_scene.state = State("light.test", STATE_OFF, dict({ATTR_EFFECT: "Rainbow"}, **attributes))
    assert cap_scene.get_value() == "siren"

    calls = async_mock_service(hass, light.DOMAIN, SERVICE_TURN_ON)
    await cap_scene.set_instance_state(Context(), SceneInstanceActionState(value=ColorScene("romance")))
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, ATTR_EFFECT: "Leasure"}

    with pytest.raises(APIError) as e:
        await cap_scene.set_instance_state(Context(), SceneInstanceActionState(value=ColorScene("sunset")))
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert (
        e.value.message == "Unsupported scene 'sunset' for instance scene of color_setting capability of light.test, "
        "see https://docs.yaha-cloud.ru/dev/config/modes/"
    )
