"""Regression coverage for climates with single and dual temperature targets."""

from typing import Any, cast

from homeassistant.components import climate
from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home.capability_range import ClimateTargetTemperatureCapability, RangeCapability
from custom_components.yandex_smart_home.device import Device
from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    RangeCapabilityInstance,
    RangeCapabilityInstanceAction,
    RangeCapabilityInstanceActionState,
    RangeCapabilityParameters,
    ResponseCode,
)

from . import MockConfigEntryData
from .test_capability import get_capabilities, get_exact_one_capability

DUAL_FEATURES = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE


def climate_state(mode: str = HVACMode.HEAT_COOL, **attributes: Any) -> State:
    return State(
        "climate.test",
        mode,
        {
            ATTR_SUPPORTED_FEATURES: DUAL_FEATURES,
            ATTR_TEMPERATURE: None,
            climate.ATTR_TARGET_TEMP_LOW: 19,
            climate.ATTR_TARGET_TEMP_HIGH: 27,
            climate.ATTR_MIN_TEMP: 7,
            climate.ATTR_MAX_TEMP: 35,
            climate.ATTR_TARGET_TEMP_STEP: 0.5,
            **attributes,
        },
    )


def temperature_capability(hass: HomeAssistant, entry_data: MockConfigEntryData, state: State) -> RangeCapability:
    hass.states.async_set(state.entity_id, state.state, state.attributes)
    return cast(
        RangeCapability,
        get_exact_one_capability(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.TEMPERATURE),
    )


@pytest.mark.parametrize("mode", [HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.OFF])
@pytest.mark.parametrize(
    "features", [ClimateEntityFeature.TARGET_TEMPERATURE, ClimateEntityFeature.TARGET_TEMPERATURE_RANGE, DUAL_FEATURES]
)
async def test_climate_temperature_feature_mode_matrix(
    hass: HomeAssistant, entry_data: MockConfigEntryData, mode: str, features: int
) -> None:
    state = climate_state(mode, supported_features=features, temperature=22)
    cap = temperature_capability(hass, entry_data, state)
    range_only = features == ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    expected = 27 if range_only else (23 if mode == HVACMode.HEAT_COOL and features == DUAL_FEATURES else 22)
    assert cap.get_value() == expected
    assert (
        len(get_capabilities(hass, entry_data, state, CapabilityType.RANGE, RangeCapabilityInstance.VOLUME))
        == range_only
    )


async def test_climate_dual_temperature_query(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = climate_state()
    device = Device(hass, entry_data, state.entity_id, state)
    temperature_states = [c.as_dict() for c in device.query().capabilities or [] if c.state.instance == "temperature"]
    assert temperature_states == [
        {"type": "devices.capabilities.range", "state": {"instance": "temperature", "value": 23}}
    ]
    cap = temperature_capability(hass, entry_data, state)
    assert isinstance(cap, ClimateTargetTemperatureCapability)
    assert cap.parameters.as_dict() == {
        "instance": "temperature",
        "random_access": True,
        "range": {"min": 11, "max": 31, "precision": 0.5},
        "unit": "unit.temperature.celsius",
    }


@pytest.mark.parametrize(
    ("value", "relative", "low", "high"),
    [
        (2, True, 21, 29),
        (-2, True, 17, 25),
        (0, True, 19, 27),
        (100, True, 27, 35),
        (-100, True, 7, 15),
        (24, False, 20, 28),
        (11, False, 7, 15),
        (31, False, 27, 35),
        (23.5, False, 19.5, 27.5),
    ],
)
async def test_climate_dual_temperature_action(
    hass: HomeAssistant, entry_data: MockConfigEntryData, value: float, relative: bool, low: float, high: float
) -> None:
    state = climate_state(temperature=5)  # A stale single target must not be used in heat_cool.
    hass.states.async_set(state.entity_id, state.state, state.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    context = Context()
    device = Device(hass, entry_data, state.entity_id, state)
    await device.execute(
        context,
        RangeCapabilityInstanceAction(
            type=CapabilityType.RANGE,
            state=RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
            ),
        ),
    )
    assert len(calls) == 1
    assert calls[0].context == context
    assert calls[0].data == {
        ATTR_ENTITY_ID: state.entity_id,
        climate.ATTR_TARGET_TEMP_LOW: low,
        climate.ATTR_TARGET_TEMP_HIGH: high,
    }
    assert high - low == 8
    updated = climate_state(target_temp_low=low, target_temp_high=high)
    assert temperature_capability(hass, entry_data, updated).get_value() == (low + high) / 2


@pytest.mark.parametrize(
    ("value", "relative"),
    [(7, False), (35, False), (-100, False), (100, False), (23.25, False), (0.25, True)]
    + [(value, relative) for value in [float("nan"), float("inf"), -float("inf")] for relative in [False, True]],
)
async def test_climate_dual_temperature_invalid_action(
    hass: HomeAssistant, entry_data: MockConfigEntryData, value: float, relative: bool
) -> None:
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    cap = temperature_capability(hass, entry_data, climate_state())
    with pytest.raises(APIError) as error:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
            ),
        )
    assert error.value.code == ResponseCode.INVALID_VALUE
    assert not calls


@pytest.mark.parametrize(
    "attributes",
    [
        {"target_temp_low": None},
        {"target_temp_high": None},
        {"target_temp_low": "unknown"},
        {"target_temp_high": "unavailable"},
        {"target_temp_low": "invalid"},
        {"target_temp_low": True},
        {"target_temp_low": float("nan")},
        {"target_temp_high": float("inf")},
        {"target_temp_low": 28, "target_temp_high": 27},
        {"target_temp_low": 6},
        {"target_temp_high": 36},
        {"min_temp": None},
        {"max_temp": float("inf")},
        {"min_temp": 36, "max_temp": 7},
        {"target_temp_step": 0},
        {"target_temp_step": None},
        {"target_temp_step": -0.5},
        {"target_temp_step": float("nan")},
        {"target_temp_step": float("inf")},
        {"target_temp_step": 5e-324},
        {"target_temp_low": 10**400},
        {"min_temp": -1e308, "max_temp": 1e308},
        {
            "min_temp": 1e16 - 10,
            "target_temp_low": 1e16,
            "target_temp_high": 1e16 + 4,
            "max_temp": 1e16 + 10,
            "target_temp_step": 0.5,
        },
        {"target_temp_step": 1e-15},
    ],
)
async def test_climate_dual_temperature_invalid_band(
    hass: HomeAssistant, entry_data: MockConfigEntryData, attributes: dict[str, Any]
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state(temperature=22, **attributes))
    assert cap.get_value() is None
    assert cap.get_description() is None
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    for relative, value in ((True, 1), (False, 24)):
        with pytest.raises(APIError) as error:
            await cap.set_instance_state(
                Context(),
                RangeCapabilityInstanceActionState(
                    instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
                ),
            )
        assert error.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert not calls


async def test_climate_dual_temperature_fractional_midpoint(
    hass: HomeAssistant, entry_data: MockConfigEntryData
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state(target_temp_low=23.5, target_temp_high=25))
    assert cap.get_value() == 24.25
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    with pytest.raises(APIError):
        await cap.set_instance_state(
            Context(), RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=24)
        )
    assert not calls
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=0.5, relative=True),
    )
    assert calls[0].data == {ATTR_ENTITY_ID: "climate.test", "target_temp_low": 24, "target_temp_high": 25.5}


@pytest.mark.parametrize("mode", [HVACMode.HEAT, HVACMode.HEAT_COOL, STATE_UNKNOWN, STATE_UNAVAILABLE])
async def test_climate_dual_temperature_refreshes_mode(
    hass: HomeAssistant, entry_data: MockConfigEntryData, mode: str
) -> None:
    # Simulate an earlier mode action in the same request, which retains the old Device snapshot.
    old = climate_state(HVACMode.HEAT if mode == HVACMode.HEAT_COOL else HVACMode.HEAT_COOL, temperature=22)
    device = Device(hass, entry_data, old.entity_id, old)
    current = climate_state(mode, temperature=22)
    hass.states.async_set(current.entity_id, current.state, current.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    action = RangeCapabilityInstanceAction(
        type=CapabilityType.RANGE,
        state=RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=24),
    )
    if mode in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        with pytest.raises(APIError):
            await device.execute(Context(), action)
        assert not calls
    else:
        await device.execute(Context(), action)
        expected = (
            {"target_temp_low": 20, "target_temp_high": 28} if mode == HVACMode.HEAT_COOL else {"temperature": 24}
        )
        assert calls[0].data == {ATTR_ENTITY_ID: current.entity_id, **expected}


async def test_climate_dual_temperature_fahrenheit(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    cap = temperature_capability(
        hass,
        entry_data,
        climate_state(target_temp_low=68, target_temp_high=77, min_temp=50, max_temp=95, target_temp_step=0.5),
    )
    assert cap.get_value() == pytest.approx(22.5)
    assert cap.parameters.range is not None
    assert cap.parameters.range.min == 12.5
    assert cap.parameters.range.max == 32.5
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=2.5, relative=True),
    )
    assert calls[0].data == {ATTR_ENTITY_ID: "climate.test", "target_temp_low": 72.5, "target_temp_high": 81.5}


@pytest.mark.parametrize(
    "attribute",
    [climate.ATTR_TARGET_TEMP_LOW, climate.ATTR_TARGET_TEMP_HIGH, climate.ATTR_MIN_TEMP, climate.ATTR_MAX_TEMP],
)
async def test_climate_dual_temperature_missing_attribute(
    hass: HomeAssistant, entry_data: MockConfigEntryData, attribute: str
) -> None:
    attributes = dict(climate_state().attributes)
    attributes.pop(attribute)
    cap = temperature_capability(hass, entry_data, State("climate.test", HVACMode.HEAT_COOL, attributes))
    assert cap.get_value() is None
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    with pytest.raises(APIError):
        await cap.set_instance_state(
            Context(), RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=24)
        )
    assert not calls


@pytest.mark.parametrize(
    ("low", "high", "step", "value", "relative", "expected_low", "expected_high"),
    [
        (23, 23, 0.5, 24, False, 24, 24),
        (7, 35, 0.5, 10, True, 7, 35),
        (19.1, 27.1, 0.1, 0.3, True, 19.4, 27.4),
        (19.1, 27.1, 0.1, -0.3, True, 18.8, 26.8),
    ],
)
async def test_climate_dual_temperature_band_widths(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    low: float,
    high: float,
    step: float,
    value: float,
    relative: bool,
    expected_low: float,
    expected_high: float,
) -> None:
    cap = temperature_capability(
        hass, entry_data, climate_state(target_temp_low=low, target_temp_high=high, target_temp_step=step)
    )
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(
            instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
        ),
    )
    assert calls[0].data[climate.ATTR_TARGET_TEMP_LOW] == pytest.approx(expected_low)
    assert calls[0].data[climate.ATTR_TARGET_TEMP_HIGH] == pytest.approx(expected_high)
    assert calls[0].data[climate.ATTR_TARGET_TEMP_HIGH] - calls[0].data[climate.ATTR_TARGET_TEMP_LOW] == pytest.approx(
        high - low
    )


@pytest.mark.parametrize(
    "features",
    [0, ClimateEntityFeature.TARGET_TEMPERATURE, ClimateEntityFeature.TARGET_TEMPERATURE_RANGE, DUAL_FEATURES],
)
async def test_climate_dual_temperature_feature_transition(
    hass: HomeAssistant, entry_data: MockConfigEntryData, features: int
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state())
    current = climate_state(supported_features=features, temperature=22)
    hass.states.async_set(current.entity_id, current.state, current.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    action = RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=24)
    if features in (0, ClimateEntityFeature.TARGET_TEMPERATURE_RANGE):
        with pytest.raises(APIError) as error:
            await cap.set_instance_state(Context(), action)
        assert error.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
        assert not calls
    else:
        await cap.set_instance_state(Context(), action)
        expected = {"target_temp_low": 20, "target_temp_high": 28} if features == DUAL_FEATURES else {"temperature": 24}
        assert calls[0].data == {ATTR_ENTITY_ID: current.entity_id, **expected}


async def test_climate_dual_temperature_missing_entity(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    cap = temperature_capability(hass, entry_data, climate_state())
    hass.states.async_remove("climate.test")
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    with pytest.raises(APIError) as error:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=1, relative=True),
        )
    assert error.value.code == ResponseCode.DEVICE_UNREACHABLE
    assert not calls


@pytest.mark.parametrize("mode", [HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.OFF])
@pytest.mark.parametrize(
    "features", [ClimateEntityFeature.TARGET_TEMPERATURE, ClimateEntityFeature.TARGET_TEMPERATURE_RANGE, DUAL_FEATURES]
)
async def test_climate_temperature_command_compatibility(
    hass: HomeAssistant, entry_data: MockConfigEntryData, mode: str, features: int
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state(mode, supported_features=features, temperature=22))
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    for value, relative in ((24, False), (1, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(
                instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
            ),
        )
    if features == ClimateEntityFeature.TARGET_TEMPERATURE_RANGE:
        expected = [{"target_temp_low": 19, "target_temp_high": 24}, {"target_temp_low": 19, "target_temp_high": 28}]
    elif features == DUAL_FEATURES and mode == HVACMode.HEAT_COOL:
        expected = [{"target_temp_low": 20, "target_temp_high": 28}] * 2
    else:
        expected = [{"temperature": 24}, {"temperature": 23}]
    assert [call.data for call in calls] == [{ATTR_ENTITY_ID: "climate.test", **data} for data in expected]


@pytest.mark.parametrize("mode", [STATE_UNKNOWN, STATE_UNAVAILABLE])
async def test_climate_dual_temperature_unknown_query(
    hass: HomeAssistant, entry_data: MockConfigEntryData, mode: str
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state(mode, temperature=22))
    assert cap.get_value() is None
    assert cap.get_description() is None


async def test_climate_dual_temperature_unknown_discovery(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = climate_state(STATE_UNKNOWN, temperature=22, hvac_modes=[HVACMode.HEAT_COOL, HVACMode.OFF])
    description = await Device(hass, entry_data, state.entity_id, state).describe()
    assert description is not None  # Other capabilities remain discoverable.
    assert all(
        not isinstance(c.parameters, RangeCapabilityParameters) or c.parameters.instance != "temperature"
        for c in description.capabilities or []
    )


async def test_climate_dual_temperature_becomes_range_capable(
    hass: HomeAssistant, entry_data: MockConfigEntryData
) -> None:
    cap = temperature_capability(
        hass,
        entry_data,
        climate_state(HVACMode.HEAT, supported_features=ClimateEntityFeature.TARGET_TEMPERATURE, temperature=22),
    )
    current = climate_state()
    hass.states.async_set(current.entity_id, current.state, current.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=1, relative=True),
    )
    assert calls[0].data == {ATTR_ENTITY_ID: "climate.test", "target_temp_low": 20, "target_temp_high": 28}


@pytest.mark.parametrize(
    ("low", "high", "step", "expected_min", "expected_max"),
    [
        (19, 27, 0.5, 11, 31),
        (23.5, 25, 0.5, 7.75, 34.25),
        (19.1, 27.1, 0.5, 11.1, 30.6),
        (19.1, 27.1, 0.1, 11, 31),
        (7.1, 7.2, 0.1, 7.05, 34.95),
        (7.4, 7.5, 0.1, 7.05, 34.95),
        (7, 35, 0.5, 21, 21),
        (23, 23, 0.5, 7, 35),
        (19, 27, 50, 23, 23),
    ],
)
async def test_climate_dual_discovery_matches_accepted_midpoints(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    low: float,
    high: float,
    step: float,
    expected_min: float,
    expected_max: float,
) -> None:
    state = climate_state(target_temp_low=low, target_temp_high=high, target_temp_step=step)
    cap = temperature_capability(hass, entry_data, state)
    description = await Device(hass, entry_data, state.entity_id, state).describe()
    assert description is not None
    discovered = [
        c.parameters
        for c in description.capabilities or []
        if isinstance(c.parameters, RangeCapabilityParameters) and c.parameters.instance == "temperature"
    ]
    assert discovered == [cap.parameters]
    assert cap.parameters.range is not None
    value_range = cap.parameters.range
    assert value_range.min == pytest.approx(expected_min)
    assert value_range.max == pytest.approx(expected_max)
    assert value_range.precision == step

    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    # Every advertised step, including both endpoints, must be an accepted absolute command.
    for offset in range(round((value_range.max - value_range.min) / step) + 1):
        value = min(value_range.max, value_range.min + offset * step)
        await cap.set_instance_state(
            Context(), RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=value)
        )
        actual = calls[-1].data
        new_low, new_high = actual[climate.ATTR_TARGET_TEMP_LOW], actual[climate.ATTR_TARGET_TEMP_HIGH]
        assert 7 <= new_low <= new_high <= 35
        assert new_high - new_low == pytest.approx(high - low)
        updated = climate_state(target_temp_low=new_low, target_temp_high=new_high, target_temp_step=step)
        assert temperature_capability(hass, entry_data, updated).get_value() == pytest.approx(value)
        # Restore the input band: each command in this loop is independent.
        hass.states.async_set(state.entity_id, state.state, state.attributes)


@pytest.mark.parametrize(("delta", "low", "high"), [(100, 26.6, 34.6), (-100, 7.1, 15.1)])
async def test_climate_dual_saturation_respects_step_lattice(
    hass: HomeAssistant, entry_data: MockConfigEntryData, delta: float, low: float, high: float
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state(target_temp_low=19.1, target_temp_high=27.1))
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=delta, relative=True),
    )
    assert calls[0].data[climate.ATTR_TARGET_TEMP_LOW] == pytest.approx(low)
    assert calls[0].data[climate.ATTR_TARGET_TEMP_HIGH] == pytest.approx(high)


async def test_climate_dual_discovery_missing_band(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = climate_state(target_temp_low=None, hvac_modes=[HVACMode.HEAT_COOL, HVACMode.OFF])
    description = await Device(hass, entry_data, state.entity_id, state).describe()
    assert description is not None  # Other capabilities remain discoverable.
    assert all(
        not isinstance(c.parameters, RangeCapabilityParameters) or c.parameters.instance != "temperature"
        for c in description.capabilities or []
    )


async def test_climate_dual_temperature_default_step(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    attributes = dict(climate_state().attributes)
    attributes.pop(climate.ATTR_TARGET_TEMP_STEP)
    cap = temperature_capability(hass, entry_data, State("climate.test", HVACMode.HEAT_COOL, attributes))
    assert cap.parameters.range is not None
    assert cap.parameters.range.precision == 0.5
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=0.5, relative=True),
    )
    assert calls[0].data == {ATTR_ENTITY_ID: "climate.test", "target_temp_low": 19.5, "target_temp_high": 27.5}


async def test_climate_dual_fahrenheit_absolute_limits(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    state = climate_state(target_temp_low=68, target_temp_high=77, min_temp=50, max_temp=95, target_temp_step=0.5)
    cap = temperature_capability(hass, entry_data, state)
    assert cap.parameters.range is not None
    assert cap.parameters.range.precision == pytest.approx(0.5 / 1.8)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    for value in (cap.parameters.range.min, cap.parameters.range.max, 25):
        await cap.set_instance_state(
            Context(), RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=value)
        )
        data = calls[-1].data
        updated = climate_state(**{**state.attributes, **data})
        assert temperature_capability(hass, entry_data, updated).get_value() == pytest.approx(value)
        assert data[climate.ATTR_TARGET_TEMP_HIGH] - data[climate.ATTR_TARGET_TEMP_LOW] == pytest.approx(9)
        hass.states.async_set(state.entity_id, state.state, state.attributes)
    for value, relative in ((10, False), (35, False), (1, True), (1e308, True), (1e308, False)):
        before = len(calls)
        with pytest.raises(APIError) as error:
            await cap.set_instance_state(
                Context(),
                RangeCapabilityInstanceActionState(
                    instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
                ),
            )
        assert error.value.code == ResponseCode.INVALID_VALUE
        assert len(calls) == before


@pytest.mark.parametrize("instance", [RangeCapabilityInstance.TEMPERATURE, RangeCapabilityInstance.VOLUME])
@pytest.mark.parametrize("features", [ClimateEntityFeature.TARGET_TEMPERATURE, DUAL_FEATURES])
@pytest.mark.parametrize("relative", [False, True])
async def test_climate_legacy_range_rejects_changed_target_semantics(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    instance: RangeCapabilityInstance,
    features: int,
    relative: bool,
) -> None:
    old = climate_state(supported_features=ClimateEntityFeature.TARGET_TEMPERATURE_RANGE)
    cap = get_exact_one_capability(hass, entry_data, old, CapabilityType.RANGE, instance)
    current = climate_state(supported_features=features, temperature=22)
    hass.states.async_set(current.entity_id, current.state, current.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    with pytest.raises(APIError) as error:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=instance, value=1 if relative else 24, relative=relative),
        )
    assert error.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert not calls  # In particular, never narrow a band using a stale upper-target command.
    # A new request sees the current semantics instead of reusing the old capability snapshot.
    assert temperature_capability(hass, entry_data, current).get_value() == (23 if features == DUAL_FEATURES else 22)


@pytest.mark.parametrize("instance", [RangeCapabilityInstance.TEMPERATURE, RangeCapabilityInstance.VOLUME])
@pytest.mark.parametrize("mode", [HVACMode.HEAT_COOL, STATE_UNKNOWN, STATE_UNAVAILABLE, None])
@pytest.mark.parametrize("relative", [False, True])
async def test_climate_legacy_range_rejects_missing_support_or_state(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    instance: RangeCapabilityInstance,
    mode: str | None,
    relative: bool,
) -> None:
    old = climate_state(supported_features=ClimateEntityFeature.TARGET_TEMPERATURE_RANGE)
    cap = get_exact_one_capability(hass, entry_data, old, CapabilityType.RANGE, instance)
    if mode is not None:
        current = climate_state(
            mode,
            supported_features=0 if mode == HVACMode.HEAT_COOL else ClimateEntityFeature.TARGET_TEMPERATURE_RANGE,
        )
        hass.states.async_set(current.entity_id, current.state, current.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    with pytest.raises(APIError) as error:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=instance, value=1 if relative else 24, relative=relative),
        )
    expected_error = (
        ResponseCode.DEVICE_UNREACHABLE
        if mode in (None, STATE_UNAVAILABLE)
        else ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    )
    assert error.value.code == expected_error
    assert not calls


@pytest.mark.parametrize(
    ("value", "relative", "expected_low", "expected_high"),
    [(1, True, 21, 25), (100, True, 26, 30), (24, False, 22, 26)],
)
async def test_climate_dual_action_refreshes_targets_limits_and_step(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    value: float,
    relative: bool,
    expected_low: float,
    expected_high: float,
) -> None:
    cap = temperature_capability(hass, entry_data, climate_state())
    assert cap.parameters.range is not None  # Materialize the old discovery snapshot/cache.
    current = climate_state(target_temp_low=20, target_temp_high=24, min_temp=8, max_temp=30, target_temp_step=1)
    hass.states.async_set(current.entity_id, current.state, current.attributes)
    calls = async_mock_service(hass, climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE)
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(
            instance=RangeCapabilityInstance.TEMPERATURE, value=value, relative=relative
        ),
    )
    assert calls[0].data == {
        ATTR_ENTITY_ID: current.entity_id,
        climate.ATTR_TARGET_TEMP_LOW: expected_low,
        climate.ATTR_TARGET_TEMP_HIGH: expected_high,
    }
    with pytest.raises(APIError) as error:
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.TEMPERATURE, value=0.5, relative=True),
        )
    assert error.value.code == ResponseCode.INVALID_VALUE
    assert len(calls) == 1
