from typing import cast

from homeassistant.components import climate, fan, humidifier, media_player, vacuum
from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.components.fan import FanEntityFeature
from homeassistant.components.humidifier import HumidifierEntityFeature
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.vacuum import VacuumEntityFeature
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant, State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home.capability import STATE_CAPABILITIES_REGISTRY
from custom_components.yandex_smart_home.capability_mode import (
    FanSpeedCapabilityFanViaPercentage,
    FanSpeedCapabilityFanViaPreset,
    ModeCapability,
    StateModeCapability,
)
from custom_components.yandex_smart_home.const import CONF_ENTITY_MODE_MAP
from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    ModeCapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
    ResponseCode,
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
    def _ha_modes(self) -> list[str]:
        return self.state.attributes.get("modes_list", []) or []

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        pass


class MockModeCapabilityA(MockModeCapability):
    @property
    def _ha_value(self) -> str | None:
        return self.state.attributes.get("current_mode")


class MockModeCapabilityAShortIndexFallback(MockModeCapabilityA):
    _modes_map_index_fallback = {
        0: ModeCapabilityMode.ONE,
        1: ModeCapabilityMode.TWO,
        2: ModeCapabilityMode.THREE,
        3: ModeCapabilityMode.FOUR,
    }


async def test_capability_mode_unsupported(hass: HomeAssistant) -> None:
    state = State("switch.test", STATE_OFF)
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is False

    state = State("switch.test", STATE_OFF, {"modes_list": ["foo", "bar"]})
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is True


async def test_capability_mode_auto_mapping(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    state = State("switch.test", STATE_OFF, {"modes_list": ["mode_1", "mode_3", "mode_4", "eco", "mode_5"]})
    cap = MockModeCapabilityAShortIndexFallback(hass, BASIC_ENTRY_DATA, state)

    assert cap.supported is True
    assert cap.supported_ha_modes == ["mode_1", "mode_3", "mode_4", "eco", "mode_5"]
    assert cap.supported_yandex_modes == [
        ModeCapabilityMode.ECO,
        ModeCapabilityMode.FOWL,
        ModeCapabilityMode.PUERH_TEA,
        ModeCapabilityMode.THREE,
    ]
    assert cap.parameters.dict() == {
        "instance": "swing",
        "modes": [{"value": "eco"}, {"value": "fowl"}, {"value": "puerh_tea"}, {"value": "three"}],
    }

    assert cap.get_yandex_mode_by_ha_mode("invalid") is None
    assert len(caplog.records) == 0

    assert cap.get_yandex_mode_by_ha_mode("mode_5") is None
    assert len(caplog.records) == 1
    for record in caplog.records:
        assert record.message == (
            "Failed to get Yandex mode for mode 'mode_5' for instance swing of mode "
            "capability of switch.test. It may cause inconsistencies between Yandex and "
            "HA. See https://docs.yaha-cloud.ru/dev/config/modes/"
        )
    caplog.clear()

    assert cap.get_yandex_mode_by_ha_mode(STATE_OFF) is None
    assert len(caplog.records) == 0

    assert cap.get_yandex_mode_by_ha_mode("mode_1") == ModeCapabilityMode.FOWL
    assert cap.get_yandex_mode_by_ha_mode("mode_3") == ModeCapabilityMode.PUERH_TEA
    assert cap.get_yandex_mode_by_ha_mode("mode_4") == ModeCapabilityMode.THREE
    assert cap.get_yandex_mode_by_ha_mode("eco") == ModeCapabilityMode.ECO
    with pytest.raises(APIError) as e:  # strange case o_O
        assert cap.get_yandex_mode_by_ha_mode("MODE_1")
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert e.value.message == (
        "Unsupported HA mode 'MODE_1' for instance swing of mode capability of "
        "switch.test: not in ['mode_1', 'mode_3', 'mode_4', 'eco', 'mode_5']"
    )

    with pytest.raises(APIError) as e:
        assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.DEEP_FRYER) == ""
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert e.value.message == (
        "Unsupported mode 'deep_fryer' for instance swing of mode capability of switch.test, "
        "see https://docs.yaha-cloud.ru/dev/config/modes/"
    )

    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.FOWL) == "mode_1"
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.PUERH_TEA) == "mode_3"
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.ECO) == "eco"


async def test_capability_mode_custom_mapping(hass: HomeAssistant) -> None:
    state = State("switch.test", STATE_OFF, {"modes_list": ["mode_1", "mode_foo", "mode_bar", "americano"]})
    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                CONF_ENTITY_MODE_MAP: {
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
    assert cap.supported_ha_modes == ["mode_1", "mode_foo", "mode_bar", "americano"]  # yeap, strange too
    assert cap.supported_yandex_modes == [ModeCapabilityMode.ECO, ModeCapabilityMode.LATTE]


async def test_capability_mode_fallback_index(hass: HomeAssistant) -> None:
    state = State("switch.test", STATE_OFF, {"modes_list": ["some", "mode_1", "foo", "off"]})
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is True
    assert cap.supported_ha_modes == ["some", "mode_1", "foo", "off"]
    assert cap.supported_yandex_modes == [
        ModeCapabilityMode.FOWL,
        ModeCapabilityMode.ONE,
        ModeCapabilityMode.THREE,
    ]
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.FOWL) == "mode_1"
    assert cap.get_ha_mode_by_yandex_mode(ModeCapabilityMode.ONE) == "some"
    assert cap.get_yandex_mode_by_ha_mode("foo") == ModeCapabilityMode.THREE
    assert cap.get_yandex_mode_by_ha_mode("mode_1") == ModeCapabilityMode.FOWL

    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                CONF_ENTITY_MODE_MAP: {
                    "thermostat": {
                        ModeCapabilityMode.BABY_FOOD: ["mode_1"],
                        ModeCapabilityMode.AMERICANO: ["mode_3"],
                    }
                }
            }
        }
    )
    cap = MockModeCapabilityA(hass, entry_data, state)
    assert cap.supported is True
    assert cap.supported_yandex_modes == [
        ModeCapabilityMode.FOWL,
        ModeCapabilityMode.ONE,
        ModeCapabilityMode.THREE,
    ]

    state = State("switch.test", STATE_OFF, {"modes_list": [f"mode_{v}" for v in range(0, 11)]})
    cap = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap.supported is True
    assert cap.get_yandex_mode_by_ha_mode("mode_9") == "ten"
    assert cap.get_yandex_mode_by_ha_mode("mode_11") is None

    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                CONF_ENTITY_MODE_MAP: {
                    "swing": {
                        ModeCapabilityMode.BABY_FOOD: ["mode_1"],
                        ModeCapabilityMode.AMERICANO: ["mode_3"],
                    }
                }
            }
        }
    )
    cap = MockModeCapabilityA(hass, entry_data, state)
    assert cap.supported is True
    assert cap.supported_yandex_modes == ["americano", "baby_food"]


async def test_capability_mode_get_value(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    state = State("switch.test", STATE_OFF, {"modes_list": ["mode_1", "mode_3"], "current_mode": "mode_1"})
    cap_a = MockModeCapabilityA(hass, BASIC_ENTRY_DATA, state)
    assert cap_a.get_value() == ModeCapabilityMode.FOWL

    cap = MockModeCapability(hass, BASIC_ENTRY_DATA, state)
    assert cap.get_value() is None
    cap.state.state = "mode_3"
    assert cap.get_value() == ModeCapabilityMode.PUERH_TEA


async def test_capability_mode_thermostat(hass: HomeAssistant) -> None:
    state = State("climate.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.THERMOSTAT)

    state = State("climate.test", STATE_OFF, {climate.ATTR_HVAC_MODES: None})
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.THERMOSTAT)

    state = State(
        "climate.test",
        STATE_OFF,
        {climate.ATTR_HVAC_MODES: [HVACMode.HEAT_COOL, HVACMode.FAN_ONLY, HVACMode.OFF]},
    )
    cap = cast(
        StateModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.THERMOSTAT),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {
        "instance": "thermostat",
        "modes": [{"value": "auto"}, {"value": "fan_only"}],
    }
    assert cap.get_value() is None

    cap.state.state = HVACMode.FAN_ONLY
    assert cap.get_value() == ModeCapabilityMode.FAN_ONLY

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_HVAC_MODE)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.THERMOSTAT, value=ModeCapabilityMode.AUTO),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, climate.ATTR_HVAC_MODE: "heat_cool"}


async def test_capability_mode_swing(hass: HomeAssistant) -> None:
    state = State("climate.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.SWING)

    state = State(
        "climate.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.SWING_MODE, climate.ATTR_SWING_MODES: ["lr", "ud"]},
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
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.SWING_MODE,
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


async def test_capability_mode_program_humidifier(hass: HomeAssistant) -> None:
    state = State("humidifier.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM)

    state = State(
        "humidifier.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: HumidifierEntityFeature.MODES,
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
            ATTR_SUPPORTED_FEATURES: HumidifierEntityFeature.MODES,
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


async def test_capability_mode_program_fan(hass: HomeAssistant) -> None:
    state = State("fan.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM)

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED,
            fan.ATTR_PRESET_MODES: ["Nature", "Normal"],
        },
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM)

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED,
            fan.ATTR_PERCENTAGE_STEP: 50,
            fan.ATTR_PRESET_MODES: ["Nature", "Normal"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.PROGRAM),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "program", "modes": [{"value": "normal"}, {"value": "quiet"}]}
    assert cap.get_value() is None

    state = State(
        "fan.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED,
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


async def test_capability_mode_input_source(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    state = State("media_player.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    state = State("media_player.test", STATE_OFF)
    entry_data = MockConfigEntryData(entity_config={state.entity_id: {"features": ["select_source"]}})
    assert_no_capabilities(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    entry_data.cache.save_attr_value(state.entity_id, media_player.ATTR_INPUT_SOURCE_LIST, ["foo"])
    assert_exact_one_capability(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
        "modes": [{"value": "one"}, {"value": "three"}, {"value": "two"}],
    }
    assert cap.get_value() is None

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
async def test_capability_mode_input_source_cache(hass: HomeAssistant, off_state: str) -> None:
    state = State(
        "media_player.test",
        off_state,
        {
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
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
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
        },
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: MediaPlayerEntityFeature.SELECT_SOURCE,
        },
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.INPUT_SOURCE)


@pytest.mark.parametrize(
    "features", [FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE, FanEntityFeature.SET_SPEED]
)
async def test_capability_mode_fan_speed_fan_via_percentage(hass: HomeAssistant, features: list[int]) -> None:
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
    "features", [FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE, FanEntityFeature.SET_SPEED]
)
async def test_capability_mode_fan_speed_fan_via_percentage_custom(hass: HomeAssistant, features: list[int]) -> None:
    state = State(
        "fan.test",
        STATE_OFF,
        {ATTR_SUPPORTED_FEATURES: features, fan.ATTR_PERCENTAGE_STEP: 25, fan.ATTR_PERCENTAGE: 50},
    )
    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                CONF_ENTITY_MODE_MAP: {
                    "fan_speed": {
                        ModeCapabilityMode.FOWL: ["50%"],
                        ModeCapabilityMode.HORIZONTAL: ["100%"],
                    }
                }
            }
        }
    )
    cap_mode = cast(
        ModeCapabilityMode,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )

    assert isinstance(cap_mode, FanSpeedCapabilityFanViaPercentage)
    assert cap_mode.retrievable is True
    assert cap_mode.parameters.dict() == {
        "instance": "fan_speed",
        "modes": [{"value": "fowl"}, {"value": "horizontal"}],
    }
    assert cap_mode.get_value() == ModeCapabilityMode.FOWL

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

    with pytest.raises(APIError) as e:
        await cap.set_instance_state(
            Context(),
            ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.FAN_SPEED, value=ModeCapabilityMode.LOW),
        )
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert e.value.message == (
        "Unsupported mode 'low' for instance fan_speed of mode capability of "
        "fan.test, see https://docs.yaha-cloud.ru/dev/config/modes/"
    )

    entry_data = MockConfigEntryData(
        entity_config={
            state.entity_id: {
                CONF_ENTITY_MODE_MAP: {
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
    with pytest.raises(APIError) as e:
        cap.get_value()
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert e.value.message == "Unsupported speed value 'not-int' for instance fan_speed of mode capability of fan.test"


@pytest.mark.parametrize(
    "features", [FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE, FanEntityFeature.PRESET_MODE]
)
async def test_capability_mode_fan_speed_fan_via_preset(hass: HomeAssistant, features: list[int]) -> None:
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
    cap_mode = cast(
        ModeCapabilityMode,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert isinstance(cap_mode, FanSpeedCapabilityFanViaPreset)
    assert cap_mode.retrievable is True
    assert cap_mode.parameters.dict() == {"instance": "fan_speed", "modes": [{"value": "high"}, {"value": "turbo"}]}
    assert cap_mode.get_value() is None

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


async def test_capability_mode_fan_speed_climate(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    state = State("climate.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED)

    state = State(
        "climate.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.FAN_MODE,
            climate.ATTR_FAN_MODES: ["3", "2"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.FAN_SPEED),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {
        "instance": "fan_speed",
        "modes": [
            {"value": "low"},
            {"value": "medium"},
        ],
    }
    assert cap.get_value() is None

    state = State(
        "climate.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.FAN_MODE,
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
            ATTR_SUPPORTED_FEATURES: ClimateEntityFeature.FAN_MODE,
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


async def test_capability_mode_cleanup_mode(hass: HomeAssistant) -> None:
    state = State("vacuum.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.CLEANUP_MODE)

    state = State(
        "vacuum.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: VacuumEntityFeature.FAN_SPEED,
            vacuum.ATTR_FAN_SPEED_LIST: ["gentle", "performance"],
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.CLEANUP_MODE
        ),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "cleanup_mode", "modes": [{"value": "low"}, {"value": "turbo"}]}
    assert cap.get_value() is None

    state = State(
        "vacuum.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: VacuumEntityFeature.FAN_SPEED,
            vacuum.ATTR_FAN_SPEED_LIST: ["gentle", "performance"],
            vacuum.ATTR_FAN_SPEED: "performance",
        },
    )
    cap = cast(
        ModeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.MODE, ModeCapabilityInstance.CLEANUP_MODE
        ),
    )
    assert cap.get_value() == ModeCapabilityMode.TURBO

    calls = async_mock_service(hass, vacuum.DOMAIN, vacuum.SERVICE_SET_FAN_SPEED)
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.CLEANUP_MODE, value=ModeCapabilityMode.LOW),
    )
    assert len(calls) == 1
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id, vacuum.ATTR_FAN_SPEED: "gentle"}


async def test_capability_mode_unique_modes() -> None:
    for capability in STATE_CAPABILITIES_REGISTRY:
        if capability.type != CapabilityType.MODE:
            continue

        capability = cast(type[StateModeCapability], capability)
        seen: dict[str, ModeCapabilityMode] = {}
        for ya_mode, ha_modes in capability._modes_map_default.items():
            for ha_mode in ha_modes:
                ha_mode = ha_mode.lower()
                if ha_mode in seen and ha_mode != ya_mode:
                    pytest.fail(f"mode {ya_mode}:{ha_mode} already used for {seen[ha_mode]} of {capability.__name__}")

                seen[ha_mode] = ya_mode
