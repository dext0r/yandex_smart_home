from homeassistant.const import ATTR_ENTITY_ID, CONF_SERVICE, CONF_SERVICE_DATA, STATE_OFF, STATE_ON
from homeassistant.core import Context, State
from homeassistant.helpers.config_validation import dynamic_template
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_custom import (
    CustomCapability,
    CustomModeCapability,
    CustomRangeCapability,
    CustomToggleCapability,
)
from custom_components.yandex_smart_home.error import SmartHomeError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    ModeCapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
    OnOffCapabilityInstance,
    RangeCapabilityInstance,
    RangeCapabilityInstanceActionState,
    ToggleCapabilityInstance,
    ToggleCapabilityInstanceActionState,
)

from . import BASIC_CONFIG, MockConfig


class MockCapability(CustomCapability):
    type = CapabilityType.ON_OFF

    @property
    def supported(self) -> bool:
        return True

    def parameters(self) -> None:
        return None

    async def set_instance_state(self, *_, **__) -> None:
        pass


async def test_capability_custom(hass):
    state = State("switch.test", STATE_ON)
    cap = MockCapability(hass, BASIC_CONFIG, state, OnOffCapabilityInstance.ON, {})
    assert cap.retrievable is False
    assert cap.get_value() is None


async def test_capability_custom_state_attr(hass):
    state = State("switch.test", STATE_ON, {"value": "foo"})
    cap = MockCapability(
        hass,
        BASIC_CONFIG,
        state,
        OnOffCapabilityInstance.ON,
        {const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE: "value"},
    )
    assert cap.retrievable is True
    assert cap.get_value() == "foo"

    cap.state = State("switch.test", STATE_ON)
    assert cap.get_value() is None


async def test_capability_custom_state_entity(hass):
    state = State("switch.test", STATE_ON, {"value": "foo"})
    cap = MockCapability(
        hass,
        BASIC_CONFIG,
        state,
        OnOffCapabilityInstance.ON,
        {const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "input_number.test"},
    )
    assert cap.retrievable is True

    with pytest.raises(SmartHomeError) as e:
        cap.get_value()
    assert e.value.code == const.ERR_DEVICE_UNREACHABLE

    hass.states.async_set("input_number.test", "bar")
    assert cap.get_value() == "bar"

    cap = MockCapability(
        hass,
        BASIC_CONFIG,
        state,
        OnOffCapabilityInstance.ON,
        {
            const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: "input_number.test",
            const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE: "value",
        },
    )
    assert cap.get_value() is None
    hass.states.async_set("input_number.test", "bar", {"value": "foo"})
    assert cap.get_value() == "foo"


async def test_capability_custom_mode(hass):
    state = State("switch.test", STATE_ON)
    cap = CustomModeCapability(
        hass, BASIC_CONFIG, state, ModeCapabilityInstance.CLEANUP_MODE, {const.CONF_ENTITY_CUSTOM_MODE_SET_MODE: None}
    )
    assert cap.supported is False

    state = State("switch.test", "mode_1", {})
    hass.states.async_set(state.entity_id, state.state)
    config = MockConfig(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    "cleanup_mode": {
                        ModeCapabilityMode.ONE: ["mode_1"],
                        ModeCapabilityMode.TWO: ["mode_2"],
                    }
                }
            }
        }
    )
    cap = CustomModeCapability(
        hass,
        config,
        state,
        ModeCapabilityInstance.CLEANUP_MODE,
        {
            const.CONF_ENTITY_CUSTOM_MODE_SET_MODE: {
                CONF_SERVICE: "test.set_mode",
                ATTR_ENTITY_ID: "switch.test",
                CONF_SERVICE_DATA: {"service_mode": dynamic_template("mode: {{ mode }}")},
            },
        },
    )
    assert cap.supported is True
    assert cap.retrievable is False
    assert cap.modes_list_attribute is None
    assert cap.get_value() is None

    cap = CustomModeCapability(
        hass,
        config,
        state,
        ModeCapabilityInstance.CLEANUP_MODE,
        {
            const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: state.entity_id,
            const.CONF_ENTITY_CUSTOM_MODE_SET_MODE: {
                CONF_SERVICE: "test.set_mode",
                ATTR_ENTITY_ID: "switch.test",
                CONF_SERVICE_DATA: {"service_mode": dynamic_template("mode: {{ mode }}")},
            },
        },
    )
    assert cap.supported is True
    assert cap.retrievable is True
    assert cap.modes_list_attribute is None
    assert cap.get_value() == "one"

    calls = async_mock_service(hass, "test", "set_mode")
    await cap.set_instance_state(
        Context(),
        ModeCapabilityInstanceActionState(instance=ModeCapabilityInstance.CLEANUP_MODE, value=ModeCapabilityMode.ONE),
    )
    assert len(calls) == 1
    assert calls[0].data == {"service_mode": "mode: mode_1", ATTR_ENTITY_ID: "switch.test"}


async def test_capability_custom_toggle(hass):
    state = State("switch.test", STATE_ON)
    cap = CustomToggleCapability(
        hass,
        BASIC_CONFIG,
        state,
        ToggleCapabilityInstance.IONIZATION,
        {const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON: None, const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF: None},
    )
    assert cap.supported is True
    assert cap.retrievable is False
    assert cap.get_value() is None

    state = State("switch.test", STATE_ON, {})
    hass.states.async_set(state.entity_id, state.state)
    cap = CustomToggleCapability(
        hass,
        BASIC_CONFIG,
        state,
        ToggleCapabilityInstance.IONIZATION,
        {
            const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: state.entity_id,
            const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON: {
                CONF_SERVICE: "test.turn_on",
                ATTR_ENTITY_ID: "switch.test1",
            },
            const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF: {
                CONF_SERVICE: "test.turn_off",
                ATTR_ENTITY_ID: "switch.test2",
            },
        },
    )
    assert cap.supported is True
    assert cap.retrievable is True
    assert cap.get_value() is True

    hass.states.async_set(state.entity_id, STATE_OFF)
    assert cap.get_value() is False

    calls_on = async_mock_service(hass, "test", "turn_on")
    await cap.set_instance_state(
        Context(),
        ToggleCapabilityInstanceActionState(instance=ToggleCapabilityInstance.IONIZATION, value=True),
    )
    assert len(calls_on) == 1
    assert calls_on[0].data == {ATTR_ENTITY_ID: "switch.test1"}

    calls_off = async_mock_service(hass, "test", "turn_off")
    await cap.set_instance_state(
        Context(),
        ToggleCapabilityInstanceActionState(instance=ToggleCapabilityInstance.IONIZATION, value=False),
    )
    assert len(calls_off) == 1
    assert calls_off[0].data == {ATTR_ENTITY_ID: "switch.test2"}


async def test_capability_custom_range_random_access(hass):
    state = State("switch.test", "30", {})
    hass.states.async_set(state.entity_id, state.state)
    cap = CustomRangeCapability(
        hass,
        BASIC_CONFIG,
        state,
        RangeCapabilityInstance.OPEN,
        {
            const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: state.entity_id,
            const.CONF_ENTITY_RANGE: {
                const.CONF_ENTITY_RANGE_MIN: 10,
                const.CONF_ENTITY_RANGE_MAX: 50,
                const.CONF_ENTITY_RANGE_PRECISION: 3,
            },
            const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE: {
                CONF_SERVICE: "test.set_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
        },
    )
    assert cap.supported is True
    assert cap.retrievable is True
    assert cap.support_random_access is True
    assert cap.get_value() == 30

    for v in ["55", "5"]:
        hass.states.async_set(state.entity_id, v)
        assert cap.get_value() is None

    hass.states.async_set(state.entity_id, "30")

    calls = async_mock_service(hass, "test", "set_value")
    for value, relative in ((40, False), (100, False), (10, True), (-3, True), (-50, True)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=value, relative=relative),
        )

    assert len(calls) == 5
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == "input_number.test"

    assert calls[0].data["value"] == "value: 40"
    assert calls[1].data["value"] == "value: 100"
    assert calls[2].data["value"] == "value: 40"
    assert calls[3].data["value"] == "value: 27"
    assert calls[4].data["value"] == "value: 10"


async def test_capability_custom_range_random_access_no_state(hass):
    state = State("switch.test", "30", {})
    hass.states.async_set(state.entity_id, state.state)
    cap = CustomRangeCapability(
        hass,
        BASIC_CONFIG,
        state,
        RangeCapabilityInstance.OPEN,
        {
            const.CONF_ENTITY_RANGE: {
                const.CONF_ENTITY_RANGE_MIN: 10,
                const.CONF_ENTITY_RANGE_MAX: 50,
                const.CONF_ENTITY_RANGE_PRECISION: 3,
            },
            const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE: {
                CONF_SERVICE: "test.set_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
        },
    )
    assert cap.supported is True
    assert cap.retrievable is False
    assert cap.support_random_access is True
    assert cap.get_value() is None

    calls = async_mock_service(hass, "test", "set_value")
    for value, relative in ((40, False), (100, False)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=value, relative=relative),
        )

    assert len(calls) == 2
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == "input_number.test"

    assert calls[0].data["value"] == "value: 40"
    assert calls[1].data["value"] == "value: 100"

    for v in [10, -3, 50]:
        with pytest.raises(SmartHomeError) as e:
            await cap.set_instance_state(
                Context(),
                RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=v, relative=True),
            )
        assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
        assert e.value.message == (
            "Failed to set relative value for open instance of switch.test. " "No state or service found."
        )


async def test_capability_custom_range_relative_override_no_state(hass):
    state = State("switch.test", STATE_ON, {})
    cap = CustomRangeCapability(
        hass,
        BASIC_CONFIG,
        state,
        RangeCapabilityInstance.OPEN,
        {
            const.CONF_ENTITY_RANGE: {
                const.CONF_ENTITY_RANGE_MIN: 10,
                const.CONF_ENTITY_RANGE_MAX: 99,
                const.CONF_ENTITY_RANGE_PRECISION: 3,
            },
            const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE: {
                CONF_SERVICE: "test.set_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
            const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE: {
                CONF_SERVICE: "test.increase_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
            const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE: {
                CONF_SERVICE: "test.decrease_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
        },
    )
    assert cap.supported is True
    assert cap.support_random_access is True
    assert cap.retrievable is False
    assert cap.get_value() is None

    calls = async_mock_service(hass, "test", "set_value")
    for value, relative in ((40, False), (100, False)):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=value, relative=relative),
        )

    assert len(calls) == 2
    for i in range(0, len(calls)):
        assert calls[i].data[ATTR_ENTITY_ID] == "input_number.test"

    assert calls[0].data["value"] == "value: 40"
    assert calls[1].data["value"] == "value: 100"

    calls = async_mock_service(hass, "test", "increase_value")
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=10, relative=True),
    )
    assert len(calls) == 1
    assert calls[0].data == {"entity_id": "input_number.test", "value": "value: 10"}

    calls = async_mock_service(hass, "test", "decrease_value")
    for value in (-3, -50):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=value, relative=True),
        )
    assert len(calls) == 2
    assert calls[0].data == {"entity_id": "input_number.test", "value": "value: -3"}
    assert calls[1].data == {"entity_id": "input_number.test", "value": "value: -50"}


async def test_capability_custom_range_only_relative(hass):
    state = State("switch.test", STATE_ON, {})
    cap = CustomRangeCapability(
        hass,
        BASIC_CONFIG,
        state,
        RangeCapabilityInstance.OPEN,
        {
            const.CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE: {
                CONF_SERVICE: "test.increase_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
            const.CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE: {
                CONF_SERVICE: "test.decrease_value",
                ATTR_ENTITY_ID: "input_number.test",
                CONF_SERVICE_DATA: {"value": dynamic_template("value: {{ value|int }}")},
            },
        },
    )
    assert cap.supported is True
    assert cap.support_random_access is False
    assert cap.retrievable is False
    assert cap.get_value() is None

    calls = async_mock_service(hass, "test", "increase_value")
    await cap.set_instance_state(
        Context(),
        RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=10, relative=True),
    )
    assert len(calls) == 1
    assert calls[0].data == {"entity_id": "input_number.test", "value": "value: 10"}

    calls = async_mock_service(hass, "test", "decrease_value")
    for value in (-3, -50):
        await cap.set_instance_state(
            Context(),
            RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=value, relative=True),
        )
    assert len(calls) == 2
    assert calls[0].data == {"entity_id": "input_number.test", "value": "value: -3"}
    assert calls[1].data == {"entity_id": "input_number.test", "value": "value: -50"}
