from typing import cast

from homeassistant.components import climate, fan, humidifier, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import Context, State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_mode import (
    FanSpeedCapabilityFanViaPercentage,
    FanSpeedCapabilityFanViaPreset,
    ModeCapability,
    StateModeCapability,
)
from custom_components.yandex_smart_home.error import SmartHomeError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    ModeCapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
)

from . import BASIC_ENTRY_DATA, MockConfigEntryData
from .test_capability import assert_exact_one_capability, assert_no_capabilities, get_exact_one_capability


class MockModeCapability(StateModeCapability):
    instance = ModeCapabilityInstance.SWING
    _modes_map_default = {
        ModeCapabilityMode.FOWL: ["mode_1"],
        ModeCapabilityMode.PIZZA: ["mode_2"],
        ModeCapabilityMode.PUERH_TEA: ["MODE_3"],
    }

    @property
    def supported_ha_modes(self) -> list[str]:
        return self.state.attributes.get("modes_list", [])

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        pass


class MockModeCapabilityA(MockModeCapability):
    @property
    def _ha_value(self) -> str | None:
        return self.state.attributes.get("current_mode")


class MockFallbackModeCapability(MockModeCapabilityA):
    _modes_map_index_fallback = {
        0: ModeCapabilityMode.ONE,
        1: ModeCapabilityMode.TWO,
        2: ModeCapabilityMode.THREE,
        3: ModeCapabilityMode.FOUR,
        4: ModeCapabilityMode.FIVE,
        5: ModeCapabilityMode.SIX,
        6: ModeCapabilityMode.SEVEN,
        7: ModeCapabilityMode.EIGHT,
        8: ModeCapabilityMode.NINE,
        9: ModeCapabilityMode.TEN,
    }


async def test_capability_mode_unsupported(hass):
    state = State("switch.test", STATE_OFF)
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is False

    state = State("switch.test", STATE_OFF, {"modes_list": ["foo", "bar"]})
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is False


async def test_capability_mode_auto_mapping(hass, caplog):
    state = State("switch.test", STATE_OFF, {"modes_list": ["mode_1", "mode_3", "mode_4"]})
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)

    assert cap.supported is True
    assert cap.supported_ha_modes == ["mode_1", "mode_3", "mode_4"]
    assert cap.supported_yandex_modes == [ModeCapabilityMode.FOWL, ModeCapabilityMode.PUERH_TEA]
    assert cap.parameters.dict() == {
        "instance": "swing",
        "modes": [{"value": "fowl"}, {"value": "puerh_tea"}],
    }

    assert cap.get_yandex_mode_by_ha_mode("invalid") is None
    assert len(caplog.records) == 0

    assert cap.get_yandex_mode_by_ha_mode("mode_4") is None
    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.message == (
            'Unable to get Yandex mode for "mode_4" for swing instance of switch.test. '
            'It may cause inconsistencies between Yandex and HA. Check "modes" setting for this entity'
        )
    caplog.clear()

    assert cap.get_yandex_mode_by_ha_mode(STATE_OFF) is None
    assert len(caplog.records) == 0

    assert cap.get_yandex_mode_by_ha_mode("mode_1") == ModeCapabilityMode.FOWL
    assert cap.get_yandex_mode_by_ha_mode("mode_3") == ModeCapabilityMode.PUERH_TEA
    with pytest.raises(SmartHomeError) as e:  # strange case o_O
        assert cap.get_yandex_mode_by_ha_mode("MODE_1")
    assert e.value.code == const.ERR_INVALID_VALUE
    assert e.value.message == (
        """Unsupported HA mode "MODE_1" for swing instance of switch.test (not in ['mode_1', 'mode_3', 'mode_4'])"""
    )

    with pytest.raises(SmartHomeError) as e:
        assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.DEEP_FRYER) == ""
    assert e.value.code == const.ERR_INVALID_VALUE
    assert e.value.message == (
        'Unsupported mode "deep_fryer" for swing instance of switch.test. Check "modes" setting for this entity'
    )

    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.FOWL) == "mode_1"
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.PUERH_TEA) == "mode_3"


async def test_capability_mode_custom_mapping(hass):
    state = State("switch.test", STATE_OFF, {"modes_list": ["mode_1", "mode_foo", "mode_bar"]})
    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    "swing": {
                        ModeCapabilityMode.ECO: ["mode_foo"],
                        ModeCapabilityMode.LATTE: ["Mode_Bar"],
                    }
                }
            }
        }
    )
    cap = MockModeCapabilityA(hass, entry_data, state)
    assert cap.supported is True
    assert cap.supported_ha_modes == ["mode_1", "mode_foo", "mode_bar"]  # yeap, strange too
    assert cap.supported_yandex_modes == [ModeCapabilityMode.ECO, ModeCapabilityMode.LATTE]


async def test_capability_mode_fallback_index(hass):
    state = State("switch.test", STATE_OFF, {"modes_list": ["some", "mode_1", "foo"]})
    cap = MockFallbackModeCapability(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is True
    assert cap.supported_ha_modes == ["some", "mode_1", "foo"]
    assert cap.supported_yandex_modes == [
        ModeCapabilityMode.ONE,
        ModeCapabilityMode.FOWL,
        ModeCapabilityMode.THREE,
    ]
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.FOWL) == "mode_1"
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.ONE) == "some"
    assert cap.get_yandex_mode_by_ha_mode("foo") == ModeCapabilityMode.THREE
    assert cap.get_yandex_mode_by_ha_mode("mode_1") == ModeCapabilityMode.FOWL

    state = State("switch.test", STATE_OFF, {"modes_list": [f"mode_{v}" for v in range(0, 11)]})
    cap = MockFallbackModeCapability(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is True
    assert cap.get_yandex_mode_by_ha_mode("mode_9") == "ten"
    assert cap.get_yandex_mode_by_ha_mode("mode_11") is None

    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    "swing": {
                        ModeCapabilityMode.BABY_FOOD: ["mode_1"],
                        ModeCapabilityMode.AMERICANO: ["mode_3"],
                    }
                }
            }
        }
    )
    cap = MockFallbackModeCapability(hass, entry_data, state)
    assert cap.supported is True
    assert cap.supported_yandex_modes == ["baby_food", "americano"]


async def test_capability_mode_get_value(hass, caplog):
    state = State("switch.test", STATE_OFF, {"modes_list": ["mode_1", "mode_3"], "current_mode": "mode_1"})
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.get_value() == ModeCapabilityMode.FOWL

    cap = MockModeCapability(hass, BASIC_ENTRY_DATA, state)
    assert cap.get_value() is None
    cap.state.state = "mode_3"
    assert cap.get_value() == ModeCapabilityMode.PUERH_TEA


async def test_capability_mode_thermostat(hass):
    state = State("climate.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.THERMOSTAT)

    state = State("climate.test", STATE_OFF, {climate.ATTR_HVAC_MODES: None})
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.THERMOSTAT)

    state = State(
        "climate.test",
        STATE_OFF,
        {climate.ATTR_HVAC_MODES: [climate.HVAC_MODE_HEAT_COOL, climate.HVACMode.FAN_ONLY, climate.HVAC_MODE_OFF]},
    )
    cap = cast(
        StateModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.THERMOSTAT),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "thermostat", "modes": [{"value": "auto"}, {"value": "fan_only"}]}
    assert cap.get_value() is None

    cap.state.state = climate.HVACMode.FAN_ONLY
    assert cap.get_value() == ModeCapabilityMode.FAN_ONLY

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_HVAC_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.THERMOSTAT, value=ModeCapabilityMode.AUTO),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_HVAC_MODE: "heat_cool"}


async def test_capability_mode_swing(hass):
    state = State("climate.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.SWING)

    state = State(
        "climate.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.SWING_MODE, climate.ATTR_SWING_MODES: ["lr", "ud"]},
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.SWING),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "swing", "modes": [{"value": "horizontal"}, {"value": "vertical"}]}
    assert cap.get_value() is None

    state = State(
        "climate.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.SWING_MODE,
            climate.ATTR_SWING_MODES: ["lr", "ud"],
            climate.ATTR_SWING_MODE: "ud",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.SWING),
    )
    assert cap.get_value() == ModeCapabilityMode.VERTICAL

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_SWING_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.SWING, value=ModeCapabilityMode.HORIZONTAL),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_SWING_MODE: "lr"}


async def test_capability_mode_program_humidifier(hass):
    state = State("humidifier.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM)

    state = State(
        "humidifier.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: humidifier.HumidifierEntityFeature.MODES,
            humidifier.ATTR_AVAILABLE_MODES: ["Idle", "Middle"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "program", "modes": [{"value": "eco"}, {"value": "medium"}]}
    assert cap.get_value() is None

    state = State(
        "humidifier.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: humidifier.HumidifierEntityFeature.MODES,
            humidifier.ATTR_AVAILABLE_MODES: ["Idle", "Middle"],
            humidifier.ATTR_MODE: "Idle",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM),
    )
    assert cap.get_value() == ModeCapabilityMode.ECO

    calls = async_mock_service(hass, humidifier.DOMAIN, humidifier.SERVICE_SET_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.PROGRAM, value=ModeCapabilityMode.MEDIUM),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, humidifier.ATTR_MODE: "Middle"}


async def test_capability_mode_program_fan(hass):
    state = State("fan.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM)

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: fan.FanEntityFeature.PRESET_MODE | fan.FanEntityFeature.SET_SPEED,
            fan.ATTR_PRESET_MODES: ["Nature", "Normal"],
        },
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM)

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: fan.FanEntityFeature.PRESET_MODE | fan.FanEntityFeature.SET_SPEED,
            fan.ATTR_PERCENTAGE_STEP: 50,
            fan.ATTR_PRESET_MODES: ["Nature", "Normal"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "program", "modes": [{"value": "quiet"}, {"value": "normal"}]}
    assert cap.get_value() is None

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: fan.FanEntityFeature.PRESET_MODE | fan.FanEntityFeature.SET_SPEED,
            fan.ATTR_PERCENTAGE_STEP: 50,
            fan.ATTR_PRESET_MODES: ["Nature", "Normal"],
            fan.ATTR_PRESET_MODE: "Nature",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM),
    )
    assert cap.get_value() == ModeCapabilityMode.QUIET

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PRESET_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.PROGRAM, value=ModeCapabilityMode.NORMAL),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PRESET_MODE: "Normal"}


async def test_capability_mode_input_source(hass, caplog):
    state = State("media_player.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    state = State("media_player.test", STATE_ON)
    entry_data = MockConfigEntryData(entity_config={state.entity_id: {"features": ["select_source"]}})
    assert_exact_one_capability(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: [f"s{i}" for i in range(1, 15)],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert len(cap.supported_yandex_modes) == 10

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: ["s1", "s2", "s3"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {
        "instance": "input_source",
        "modes": [{"value": "one"}, {"value": "two"}, {"value": "three"}],
    }
    assert cap.get_value() is None

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: ["s1", "s2", "s3"],
            media_player.ATTR_INPUT_SOURCE: "test",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.get_value() is None
    assert len(caplog.records) == 0

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: ["s1", "s2", "s3"],
            media_player.ATTR_INPUT_SOURCE: "s2",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.get_value() == ModeCapabilityMode.TWO

    calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_SELECT_SOURCE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.INPUT_SOURCE, value=ModeCapabilityMode.THREE),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, media_player.ATTR_INPUT_SOURCE: "s3"}


@pytest.mark.parametrize("off_state", [STATE_OFF, STATE_UNKNOWN])
async def test_capability_mode_input_source_cache(hass, off_state):
    state = State(
        "media_player.test",
        off_state,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: ["s1", "s2", "s3"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.supported_ha_modes == ["s1", "s2", "s3"]

    state = State(
        "media_player.test",
        off_state,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: [],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.supported_ha_modes == ["s1", "s2", "s3"]

    state = State(
        "media_player.test",
        off_state,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
            media_player.ATTR_INPUT_SOURCE_LIST: ["Live TV"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.supported_ha_modes == ["s1", "s2", "s3"]

    state = State(
        "media_player.test",
        off_state,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE
        ),
    )
    assert cap.supported_ha_modes == ["s1", "s2", "s3"]

    state = State(
        "media_player.test",
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
        },
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.SELECT_SOURCE,
        },
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)


@pytest.mark.parametrize(
    "features", [fan.FanEntityFeature.SET_SPEED | fan.FanEntityFeature.PRESET_MODE, fan.FanEntityFeature.SET_SPEED]
)
async def test_capability_mode_fan_speed_fan_via_percentage(hass, features):
    state = State("fan.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 100})
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED)

    state = State("fan.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 100})
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED)

    state = State("fan.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 25})
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )

    assert isinstance(cap, FanSpeedCapabilityFanViaPercentage)
    assert cap.retrievable is True
    assert cap.parameters.dict() == {
        "instance": "fan_speed",
        "modes": [{"value": "low"}, {"value": "normal"}, {"value": "medium"}, {"value": "high"}],
    }
    assert cap.get_value() is None

    state = State(
        "fan.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 25, fan.ATTR_PERCENTAGE: 50},
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert cap.get_value() == ModeCapabilityMode.NORMAL

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PERCENTAGE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.MEDIUM),
    )
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
        state = State(
            "fan.test",
            STATE_OFF,
            {
                ATTR_SUPPORTED_FEATURES: features,
                fan.ATTR_PERCENTAGE_STEP: 100 / float(speed_count),
            },
        )
        if not mode_count:
            assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED)
        else:
            cap = cast(
                ModeCapability,
                get_exact_one_capability(
                    hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED
                ),
            )
            assert len(cap.supported_ha_modes) == mode_count
            assert len(cap.supported_yandex_modes) == mode_count


@pytest.mark.parametrize(
    "features", [fan.FanEntityFeature.SET_SPEED | fan.FanEntityFeature.PRESET_MODE, fan.FanEntityFeature.SET_SPEED]
)
async def test_capability_mode_fan_speed_fan_via_percentage_custom(hass, features):
    state = State(
        "fan.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 25, fan.ATTR_PERCENTAGE: 50},
    )
    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    "fan_speed": {
                        ModeCapabilityMode.FOWL: ["50%"],
                        ModeCapabilityMode.HORIZONTAL: ["100%"],
                    }
                }
            }
        }
    )
    cap = cast(
        ModeCapabilityMode,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )

    assert isinstance(cap, FanSpeedCapabilityFanViaPercentage)
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "fan_speed", "modes": [{"value": "fowl"}, {"value": "horizontal"}]}
    assert cap.get_value() == ModeCapabilityMode.FOWL

    state = State(
        "fan.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 25, fan.ATTR_PERCENTAGE: 25},
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert cap.get_value() is None

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PERCENTAGE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.FOWL),
    )
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(
            instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.HORIZONTAL
        ),
    )
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PERCENTAGE: 50}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PERCENTAGE: 100}

    with pytest.raises(SmartHomeError) as e:
        await cap.set_instance_state(
            Context(),
            ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.LOW),
        )
    assert e.value.code == const.ERR_INVALID_VALUE
    assert e.value.message == (
        'Unsupported mode "low" for fan_speed instance of fan.test. Check "modes" setting for this entity'
    )

    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    "fan_speed": {
                        ModeCapabilityMode.FOWL: ["not-int"],
                    }
                }
            }
        }
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    with pytest.raises(SmartHomeError) as e:
        cap.get_value()
    assert e.value.code == const.ERR_INVALID_VALUE
    assert e.value.message == "Unsupported speed value 'not-int' for fan_speed instance of fan.test."


@pytest.mark.parametrize(
    "features", [fan.FanEntityFeature.SET_SPEED | fan.FanEntityFeature.PRESET_MODE, fan.FanEntityFeature.PRESET_MODE]
)
async def test_capability_mode_fan_speed_fan_via_preset(hass, features):
    state = State("fan.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: features})
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED)

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: features,
            fan.ATTR_PRESET_MODES: ["Level 4", "Level 5"],
        },
    )
    cap = cast(
        ModeCapabilityMode,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert isinstance(cap, FanSpeedCapabilityFanViaPreset)
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "fan_speed", "modes": [{"value": "high"}, {"value": "turbo"}]}
    assert cap.get_value() is None

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: features,
            fan.ATTR_PRESET_MODES: ["Level 4", "Level 5"],
            fan.ATTR_PRESET_MODE: "Level 5",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert cap.get_value() == ModeCapabilityMode.TURBO

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_SET_PRESET_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.HIGH),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, fan.ATTR_PRESET_MODE: "Level 4"}


async def test_capability_mode_fan_speed_climate(hass, caplog):
    state = State("climate.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED)

    state = State(
        "climate.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.FAN_MODE,
            climate.ATTR_FAN_MODES: ["3", "2"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "fan_speed", "modes": [{"value": "medium"}, {"value": "low"}]}
    assert cap.get_value() is None

    state = State(
        "climate.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.FAN_MODE,
            climate.ATTR_FAN_MODES: ["3", "2"],
            climate.ATTR_FAN_MODE: "3",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert cap.get_value() == ModeCapabilityMode.MEDIUM

    state = State(
        "climate.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.FAN_MODE,
            climate.ATTR_FAN_MODES: ["3", "2"],
            climate.ATTR_FAN_MODE: "on",
        },
    )

    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    caplog.clear()
    assert cap.get_value() == ModeCapabilityMode.AUTO
    assert len(caplog.records) == 0

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_FAN_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.LOW),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_FAN_MODE: "2"}


async def test_capability_mode_cleanup_mode(hass):
    state = State("vacuum.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.CLEANUP_MODE)

    state = State(
        "vacuum.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.FAN_SPEED,
            vacuum.ATTR_FAN_SPEED_LIST: ["gentle", "mop"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.CLEANUP_MODE
        ),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "cleanup_mode", "modes": [{"value": "low"}, {"value": "min"}]}
    assert cap.get_value() is None

    state = State(
        "vacuum.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.FAN_SPEED,
            vacuum.ATTR_FAN_SPEED_LIST: ["gentle", "mop"],
            vacuum.ATTR_FAN_SPEED: "mop",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.CLEANUP_MODE
        ),
    )
    assert cap.get_value() == ModeCapabilityMode.MIN

    calls = async_mock_service(hass, vacuum.DOMAIN, vacuum.SERVICE_SET_FAN_SPEED)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.CLEANUP_MODE, value=ModeCapabilityMode.LOW),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, vacuum.ATTR_FAN_SPEED: "gentle"}
