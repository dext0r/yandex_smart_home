from abc import ABC
from typing import cast
from unittest.mock import patch

from homeassistant.components import climate, cover, humidifier, light, media_player, water_heater
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_MODEL,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, State
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_range import RangeCapability, StateRangeCapability
from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    RangeCapabilityInstance,
    RangeCapabilityInstanceActionState,
    RangeCapabilityParameters,
    RangeCapabilityRange,
    ResponseCode,
)

from . import BASIC_ENTRY_DATA, MockConfigEntryData
from .test_capability import assert_no_capabilities, get_exact_one_capability


async def test_capability_range(hass, caplog):
    class MockCapability(StateRangeCapability):
        instance = RangeCapabilityInstance.VOLUME

        @property
        def support_random_access(self) -> bool:
            return False

        @property
        def supported(self) -> bool:
            return True

        async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
            pass

        def _get_value(self) -> float | None:
            return None

    class MockCapabilityRandomAccess(MockCapability):
        @property
        def support_random_access(self) -> bool:
            return True

    cap = MockCapability(hass, BASIC_ENTRY_DATA, State("switch.test", STATE_ON))
    assert cap.retrievable is False
    assert cap.parameters == RangeCapabilityParameters(instance=RangeCapabilityInstance.VOLUME, random_access=False)

    cap = MockCapabilityRandomAccess(hass, BASIC_ENTRY_DATA, State("switch.test", STATE_ON))
    assert cap.retrievable
    assert cap.support_random_access
    assert cap._range == RangeCapabilityRange(min=0.0, max=100.0, precision=1.0)

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

                entry_data = MockConfigEntryData(
                    entity_config={"switch.test": {const.CONF_ENTITY_RANGE: entity_range_config}}
                )
                cap = MockCapabilityRandomAccess(hass, entry_data, State("switch.test", STATE_ON))
                assert cap._range == RangeCapabilityRange(
                    min=range_min or cap._default_range.min,
                    max=range_max or cap._default_range.max,
                    precision=range_prec or cap._default_range.precision,
                )
                assert cap.parameters.as_dict() == {
                    "instance": "volume",
                    "random_access": True,
                    "range": {
                        "min": range_min or cap._default_range.min,
                        "max": range_max or cap._default_range.max,
                        "precision": range_prec or cap._default_range.precision,
                    },
                }

    for v in [STATE_UNAVAILABLE, STATE_UNKNOWN, "None"]:
        assert cap._convert_to_float(v) is None

    for v in ["4", "5.5"]:
        assert cap._convert_to_float(v) == float(v)

    with pytest.raises(APIError) as e:
        assert cap._convert_to_float("foo")
        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE

    with patch.object(MockCapability, "_get_value", return_value=20):
        assert cap._get_absolute_value(10) == 30
        assert cap._get_absolute_value(-5) == 15
        assert cap._get_absolute_value(99) == 100
        assert cap._get_absolute_value(-50) == 0

    for v in [-1, 101]:
        with patch.object(MockCapability, "_get_value", return_value=v):
            assert cap.get_value() is None

    assert caplog.messages == [
        "Value -1 is not in range [0.0, 100.0] for instance volume of switch.test",
        "Value 101 is not in range [0.0, 100.0] for instance volume of switch.test",
    ]

    with pytest.raises(APIError) as e:
        cap._get_absolute_value(0)
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert e.value.message == "Unable to get current value or volume instance of switch.test"

    cap.state.state = STATE_OFF
    with pytest.raises(APIError) as e:
        cap._get_absolute_value(0)
    assert e.value.code == ResponseCode.DEVICE_OFF
    assert e.value.message == "Device switch.test probably turned off"


async def test_capability_range_cover(hass):
    state = State("cover.test", cover.STATE_OPEN)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.OPEN)

    state = State("cover.test", cover.STATE_OPEN, {ATTR_SUPPORTED_FEATURES: cover.CoverEntityFeature.SET_POSITION})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.OPEN),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.dict() == {
        "instance": "open",
        "random_access": True,
        "range": {"max": 100, "min": 0, "precision": 1},
        "unit": "unit.percent",
    }
    assert cap.get_value() is None

    state = State(
        "cover.test",
        cover.STATE_OPEN,
        {
            ATTR_SUPPORTED_FEATURES: cover.CoverEntityFeature.SET_POSITION,
            cover.ATTR_CURRENT_POSITION: "30",
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.OPEN),
    )
    assert cap.get_value() == 30

    calls = async_mock_service(hass, cover.DOMAIN, cover.SERVICE_SET_COVER_POSITION)
    for value, relative in ((0, False), (20, False), (-15, True), (-40, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=value, relative=relative),
        )

    assert len(calls) == 4
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[cover.ATTR_POSITION] == 0
    assert calls[1].data[cover.ATTR_POSITION] == 20
    assert calls[2].data[cover.ATTR_POSITION] == 15
    assert calls[3].data[cover.ATTR_POSITION] == 0


async def test_capability_range_temperature_climate(hass):
    state = State("climate.test", climate.STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE)

    state = State(
        "climate.test",
        climate.STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.TARGET_TEMPERATURE,
            climate.ATTR_MIN_TEMP: 10,
            climate.ATTR_MAX_TEMP: 25,
            climate.ATTR_TARGET_TEMP_STEP: 1,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE
        ),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "temperature",
        "random_access": True,
        "range": {"max": 25, "min": 10, "precision": 1},
        "unit": "unit.temperature.celsius",
    }
    assert cap.get_value() is None

    state = State(
        "climate.test",
        climate.HVAC_MODE_HEAT_COOL,
        {
            ATTR_SUPPORTED_FEATURES: climate.ClimateEntityFeature.TARGET_TEMPERATURE,
            climate.ATTR_MIN_TEMP: 12,
            climate.ATTR_MAX_TEMP: 27,
            climate.ATTR_TEMPERATURE: 23.5,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE
        ),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "temperature",
        "random_access": True,
        "range": {"max": 27, "min": 12, "precision": 0.5},
        "unit": "unit.temperature.celsius",
    }
    assert cap.get_value() == 23.5

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    for value, relative in ((11, False), (15, False), (28, False), (10, True), (-3, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
            ),
        )

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[climate.ATTR_TEMPERATURE] == 11
    assert calls[1].data[climate.ATTR_TEMPERATURE] == 15
    assert calls[2].data[climate.ATTR_TEMPERATURE] == 28
    assert calls[3].data[climate.ATTR_TEMPERATURE] == 27
    assert calls[4].data[climate.ATTR_TEMPERATURE] == 20.5


async def test_capability_range_temperature_water_heater(hass):
    state = State("water_heater.test", water_heater.STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE)

    state = State(
        "water_heater.test",
        water_heater.STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: water_heater.WaterHeaterEntityFeature.TARGET_TEMPERATURE,
            water_heater.ATTR_MIN_TEMP: 30,
            water_heater.ATTR_MAX_TEMP: 90,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE
        ),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "temperature",
        "random_access": True,
        "range": {"max": 90, "min": 30, "precision": 0.5},
        "unit": "unit.temperature.celsius",
    }
    assert cap.get_value() is None

    state = State(
        "water_heater.test",
        water_heater.STATE_ELECTRIC,
        {
            ATTR_SUPPORTED_FEATURES: water_heater.WaterHeaterEntityFeature.TARGET_TEMPERATURE,
            water_heater.ATTR_MIN_TEMP: 30,
            water_heater.ATTR_MAX_TEMP: 90,
            water_heater.ATTR_TEMPERATURE: 50,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE
        ),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.get_value() == 50

    calls = async_mock_service(hass, water_heater.DOMAIN, water_heater.SERVICE_SET_TEMPERATURE)
    for value, relative in ((20, False), (100, False), (50, False), (15, True), (-20, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
            ),
        )

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[water_heater.ATTR_TEMPERATURE] == 20
    assert calls[1].data[water_heater.ATTR_TEMPERATURE] == 100
    assert calls[2].data[water_heater.ATTR_TEMPERATURE] == 50
    assert calls[3].data[water_heater.ATTR_TEMPERATURE] == 65
    assert calls[4].data[water_heater.ATTR_TEMPERATURE] == 30


async def test_capability_range_humidity_humidifier(hass):
    state = State(
        "humidifier.test",
        STATE_OFF,
        {
            humidifier.ATTR_MIN_HUMIDITY: 10,
            humidifier.ATTR_MAX_HUMIDITY: 80,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.HUMIDITY),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "humidity",
        "random_access": True,
        "range": {"max": 80, "min": 10, "precision": 1},
        "unit": "unit.percent",
    }
    assert cap.get_value() is None

    state = State(
        "humidifier.test",
        STATE_OFF,
        {humidifier.ATTR_MIN_HUMIDITY: 10, humidifier.ATTR_MAX_HUMIDITY: 80, humidifier.ATTR_HUMIDITY: 30},
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.HUMIDITY),
    )
    assert cap.get_value() == 30

    calls = async_mock_service(hass, humidifier.DOMAIN, humidifier.SERVICE_SET_HUMIDITY)
    for value, relative in ((20, False), (100, False), (50, False), (15, True), (-5, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.HUMIDITY, value=value, relative=relative
            ),
        )

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[humidifier.ATTR_HUMIDITY] == 20
    assert calls[1].data[humidifier.ATTR_HUMIDITY] == 100
    assert calls[2].data[humidifier.ATTR_HUMIDITY] == 50
    assert calls[3].data[humidifier.ATTR_HUMIDITY] == 45
    assert calls[4].data[humidifier.ATTR_HUMIDITY] == 25


async def test_capability_range_humidity_fan(hass):
    state = State("fan.test", water_heater.STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.HUMIDITY)

    state = State("fan.test", STATE_OFF, {const.ATTR_TARGET_HUMIDITY: 50, ATTR_MODEL: "zhimi.test.a"})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.HUMIDITY),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "humidity",
        "random_access": True,
        "range": {"max": 100, "min": 0, "precision": 1},
        "unit": "unit.percent",
    }
    assert cap.get_value() == 50

    calls = async_mock_service(hass, const.DOMAIN_XIAOMI_AIRPURIFIER, const.SERVICE_FAN_SET_TARGET_HUMIDITY)
    for value, relative in ((20, False), (100, False), (50, False), (15, True), (-5, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.HUMIDITY, value=value, relative=relative
            ),
        )

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[humidifier.ATTR_HUMIDITY] == 20
    assert calls[1].data[humidifier.ATTR_HUMIDITY] == 100
    assert calls[2].data[humidifier.ATTR_HUMIDITY] == 50
    assert calls[3].data[humidifier.ATTR_HUMIDITY] == 65
    assert calls[4].data[humidifier.ATTR_HUMIDITY] == 45


async def test_capability_range_brightness_legacy(hass):
    state = State("light.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.BRIGHTNESS)

    state = State("light.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: light.SUPPORT_BRIGHTNESS})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.BRIGHTNESS
        ),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "brightness",
        "random_access": True,
        "range": {"max": 100, "min": 1, "precision": 1},
        "unit": "unit.percent",
    }
    assert cap.get_value() is None

    state = State(
        "light.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: light.SUPPORT_BRIGHTNESS, light.ATTR_BRIGHTNESS: 128}
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.BRIGHTNESS
        ),
    )
    assert cap.get_value() == 50


@pytest.mark.parametrize("color_mode", sorted(light.COLOR_MODES_BRIGHTNESS))
async def test_capability_range_brightness(hass, color_mode):
    state = State(
        "light.test",
        STATE_ON,
        {ATTR_SUPPORTED_FEATURES: light.SUPPORT_BRIGHTNESS, light.ATTR_SUPPORTED_COLOR_MODES: [color_mode]},
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.BRIGHTNESS
        ),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "brightness",
        "random_access": True,
        "range": {"max": 100, "min": 1, "precision": 1},
        "unit": "unit.percent",
    }
    assert cap.get_value() is None

    state = State("light.test", STATE_ON, {light.ATTR_SUPPORTED_COLOR_MODES: [color_mode], light.ATTR_BRIGHTNESS: 128})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.BRIGHTNESS
        ),
    )
    assert cap.get_value() == 50

    calls = async_mock_service(hass, light.DOMAIN, light.SERVICE_TURN_ON)
    for value, relative in ((0, False), (30, False), (126, False), (30, True), (-60, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.BRIGHTNESS, value=value, relative=relative
            ),
        )

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[light.ATTR_BRIGHTNESS_PCT] == 0
    assert calls[1].data[light.ATTR_BRIGHTNESS_PCT] == 30
    assert calls[2].data[light.ATTR_BRIGHTNESS_PCT] == 126
    assert calls[3].data[light.ATTR_BRIGHTNESS_STEP_PCT] == 30
    assert calls[4].data[light.ATTR_BRIGHTNESS_STEP_PCT] == -60


async def test_capability_range_volume(hass):
    state = State("media_player.test", STATE_ON)
    entry_data = MockConfigEntryData(entity_config={state.entity_id: {"features": ["volume_set"]}})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME),
    )
    assert cap.support_random_access is True


@pytest.mark.parametrize(
    "features",
    [
        media_player.MediaPlayerEntityFeature.VOLUME_SET,
        media_player.MediaPlayerEntityFeature.VOLUME_SET | media_player.MediaPlayerEntityFeature.VOLUME_STEP,
    ],
)
async def test_capability_range_volume_support_random(hass, features):
    state = State("media_player.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME)

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: features,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "volume",
        "random_access": True,
        "range": {"max": 100, "min": 0, "precision": 1},
    }
    assert cap.get_value() is None

    state = State(
        "media_player.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: features, media_player.ATTR_MEDIA_VOLUME_LEVEL: 0.56}
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME),
    )
    assert cap.get_value() == 56

    calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_SET)
    for value, relative in ((0, False), (34, False), (126, False), (30, True), (-10, True), (-60, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=value, relative=relative),
        )

    assert len(calls) == 6
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == state.entity_id

    assert calls[0].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0
    assert calls[1].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0.34
    assert calls[2].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 1.26
    assert calls[3].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0.86
    assert calls[4].data[media_player.ATTR_MEDIA_VOLUME_LEVEL] == 0.46


@pytest.mark.parametrize("precision", [2, 10, None])
async def test_capability_range_volume_only_relative(hass, precision):
    state = State(
        "media_player.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.VOLUME_STEP}
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME),
    )
    assert cap.support_random_access is False

    entity_config = {}
    if precision:
        entity_config = {const.CONF_ENTITY_RANGE: {const.CONF_ENTITY_RANGE_PRECISION: precision}}

    entry_data = MockConfigEntryData(entity_config={state.entity_id: entity_config})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME),
    )

    calls_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_UP)
    with pytest.raises(APIError) as e:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=15, relative=False),
        )
    assert e.value.code == ResponseCode.INVALID_VALUE

    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=3, relative=True),
    )
    assert len(calls_up) == 3
    for i in range(0, len(calls_up)):
        assert calls_up[i].data[ATTR_ENTITY_ID] == state.entity_id

    calls_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_DOWN)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=-2, relative=True),
    )
    assert len(calls_down) == 2
    for i in range(0, len(calls_down)):
        assert calls_down[i].data[ATTR_ENTITY_ID] == state.entity_id

    calls_one_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_UP)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=1, relative=True),
    )
    assert len(calls_one_up) == (precision or 1)
    for i in range(0, precision or 1):
        assert calls_one_up[i].data[ATTR_ENTITY_ID] == state.entity_id

    calls_one_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_DOWN)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=-1, relative=True),
    )
    assert len(calls_one_down) == (precision or 1)
    for i in range(0, precision or 1):
        assert calls_one_down[i].data[ATTR_ENTITY_ID] == state.entity_id


async def test_capability_range_channel_via_features(hass):
    state = State("media_player.test", STATE_OFF)
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL)

    state = State("media_player.test", STATE_ON)
    entry_data = MockConfigEntryData(entity_config={state.entity_id: {"features": ["next_previous_track"]}})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.support_random_access is False


async def test_capability_range_channel_set_via_config(hass):
    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            ATTR_DEVICE_CLASS: media_player.MediaPlayerDeviceClass.TV,
        },
    )
    entry_data = MockConfigEntryData(entity_config={state.entity_id: {const.CONF_SUPPORT_SET_CHANNEL: False}})
    assert_no_capabilities(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL)

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA
            | media_player.MediaPlayerEntityFeature.PREVIOUS_TRACK
            | media_player.MediaPlayerEntityFeature.NEXT_TRACK,
            ATTR_DEVICE_CLASS: media_player.MediaPlayerDeviceClass.TV,
        },
    )

    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.retrievable is False
    assert cap.support_random_access is False


async def test_capability_range_channel_set_random(hass):
    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.retrievable is False
    assert cap.support_random_access is False

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            ATTR_DEVICE_CLASS: media_player.MediaPlayerDeviceClass.RECEIVER,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.retrievable is False
    assert cap.support_random_access is False

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            ATTR_DEVICE_CLASS: media_player.MediaPlayerDeviceClass.TV,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "channel",
        "random_access": True,
        "range": {"max": 999, "min": 0, "precision": 1},
    }
    assert cap.get_value() is None

    calls_set = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_PLAY_MEDIA)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=15),
    )
    await hass.async_block_till_done()
    assert len(calls_set) == 1
    assert calls_set[0].data == {
        ATTR_ENTITY_ID: state.entity_id,
        media_player.ATTR_MEDIA_CONTENT_ID: 15,
        media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
    }

    with pytest.raises(APIError) as e:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=1, relative=True),
        )
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE

    with pytest.raises(APIError) as e:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=-1, relative=True),
        )
        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE


async def test_capability_range_channel_set_not_supported(hass):
    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            ATTR_DEVICE_CLASS: media_player.MediaPlayerDeviceClass.TV,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True

    with patch.object(cap._hass.services, "async_call", side_effect=ValueError("nope")):
        with pytest.raises(APIError) as e:
            await cap.set_instance_state(
                Context(),
                RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=15),
            )
        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
        assert e.value.message == (
            'Failed to set channel for media_player.test. Please change setting "support_set_channel" to "false" in '
            "entity_config if the device does not support channel selection. Error: ValueError('nope')"
        )


async def test_capability_range_channel_set_random_with_value(hass):
    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            ATTR_DEVICE_CLASS: media_player.MediaPlayerDeviceClass.TV,
            media_player.ATTR_MEDIA_CONTENT_ID: 15,
            media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.parameters.as_dict() == {
        "instance": "channel",
        "random_access": True,
        "range": {"max": 999, "min": 0, "precision": 1},
    }
    assert cap.get_value() == 15

    calls_set = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_PLAY_MEDIA)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=5, relative=True),
    )
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=-3, relative=True),
    )
    await hass.async_block_till_done()
    assert len(calls_set) == 2
    assert calls_set[0].data == {
        ATTR_ENTITY_ID: state.entity_id,
        media_player.ATTR_MEDIA_CONTENT_ID: 20,
        media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
    }
    assert calls_set[1].data == {
        ATTR_ENTITY_ID: state.entity_id,
        media_player.ATTR_MEDIA_CONTENT_ID: 12,
        media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
    }


async def test_capability_range_channel_value(hass, caplog):
    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
            media_player.ATTR_MEDIA_CONTENT_ID: "5",
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.get_value() == 5

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_CLASS_ALBUM,
            media_player.ATTR_MEDIA_CONTENT_ID: "5",
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.get_value() is None

    state = State(
        "media_player.test",
        STATE_OFF,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
            media_player.ATTR_MEDIA_CONTENT_TYPE: media_player.const.MEDIA_TYPE_CHANNEL,
            media_player.ATTR_MEDIA_CONTENT_ID: "foo",
        },
    )
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    assert cap.get_value() is None
    assert len(caplog.records) == 0


@pytest.mark.parametrize(
    "features",
    [
        media_player.MediaPlayerEntityFeature.PREVIOUS_TRACK | media_player.MediaPlayerEntityFeature.NEXT_TRACK,
        media_player.MediaPlayerEntityFeature.PREVIOUS_TRACK
        | media_player.MediaPlayerEntityFeature.NEXT_TRACK
        | media_player.MediaPlayerEntityFeature.PLAY_MEDIA,
    ],
)
@pytest.mark.parametrize(
    "device_class", [media_player.MediaPlayerDeviceClass.TV, media_player.MediaPlayerDeviceClass.RECEIVER]
)
async def test_capability_range_channel_set_relative(hass, features, device_class):
    state = State(
        "media_player.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PREVIOUS_TRACK}
    )
    assert_no_capabilities(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL)

    state = State("media_player.test", STATE_OFF, {ATTR_SUPPORTED_FEATURES: features, ATTR_DEVICE_CLASS: device_class})
    cap = cast(
        RangeCapability,
        get_exact_one_capability(hass, BASIC_ENTRY_DATA, state, CapabilityType.RANGE, RangeCapabilityInstance.CHANNEL),
    )
    if device_class == media_player.MediaPlayerDeviceClass.TV:
        assert cap.retrievable is bool(features & media_player.MediaPlayerEntityFeature.PLAY_MEDIA)
        assert cap.support_random_access is bool(features & media_player.MediaPlayerEntityFeature.PLAY_MEDIA)
    else:
        assert cap.retrievable is False
        assert cap.support_random_access is False
        assert cap.parameters.as_dict() == {"instance": "channel", "random_access": False}
        assert cap.get_value() is None

    calls_up = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_NEXT_TRACK)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=1, relative=True),
    )
    assert len(calls_up) == 1
    assert calls_up[0].data == {ATTR_ENTITY_ID: state.entity_id}

    calls_down = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_PREVIOUS_TRACK)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.CHANNEL, value=-1, relative=True),
    )
    assert len(calls_down) == 1
    assert calls_down[0].data == {ATTR_ENTITY_ID: state.entity_id}


@pytest.mark.parametrize(
    "instance,range_required",
    [
        (RangeCapabilityInstance.BRIGHTNESS, True),
        (RangeCapabilityInstance.CHANNEL, False),
        (RangeCapabilityInstance.HUMIDITY, True),
        (RangeCapabilityInstance.OPEN, True),
        (RangeCapabilityInstance.TEMPERATURE, True),
        (RangeCapabilityInstance.VOLUME, False),
    ],
)
async def test_capability_range_relative_only_parameters(hass, instance, range_required):
    class MockCapability(StateRangeCapability, ABC):
        @property
        def supported(self) -> bool:
            return True

        async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
            pass

        def _get_value(self) -> float | None:
            return None

    class MockCapabilityRandom(MockCapability):
        @property
        def support_random_access(self) -> bool:
            return True

    class MockCapabilityRelative(MockCapability):
        @property
        def support_random_access(self) -> bool:
            return False

    cap_random = MockCapabilityRandom(hass, BASIC_ENTRY_DATA, State("switch.foo", STATE_OFF))
    cap_relative = MockCapabilityRelative(hass, BASIC_ENTRY_DATA, State("switch.foo", STATE_OFF))
    cap_random.instance = cap_relative.instance = instance

    assert cap_random.parameters.range is not None
    if range_required:
        assert cap_relative.parameters.range is not None
    else:
        assert cap_relative.parameters.range is None
