from homeassistant.components import input_text, sensor
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.event import ATTR_EVENT_TYPE, EventDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, CONF_DEVICE_CLASS, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.yandex_smart_home.const import CONF_ENTITY_EVENT_MAP
from custom_components.yandex_smart_home.schema import EventPropertyInstance, PropertyType

from . import MockConfigEntryData
from .test_property import assert_no_properties, get_exact_one_property


async def test_property_event_custom_mapping(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State("sensor.button", "click", {ATTR_DEVICE_CLASS: "button"})
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() == "click"
    prop.state.state = "click_foo"
    assert prop.get_value() is None

    entry_data = MockConfigEntryData(
        hass,
        entity_config={
            state.entity_id: {
                CONF_ENTITY_EVENT_MAP: {
                    "button": {
                        "double_click": ["click_foo"],
                    }
                }
            }
        },
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() == "double_click"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.DOOR, True),
        (BinarySensorDeviceClass.GARAGE_DOOR, True),
        (BinarySensorDeviceClass.WINDOW, True),
        (BinarySensorDeviceClass.OPENING, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_open(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"events": [{"value": "opened"}, {"value": "closed"}], "instance": "open"}
    assert prop.get_value() == "opened"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "closed"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.MOTION, True),
        (BinarySensorDeviceClass.OCCUPANCY, True),
        (BinarySensorDeviceClass.PRESENCE, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_motion_sensor(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.MOTION)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.MOTION)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"events": [{"value": "detected"}, {"value": "not_detected"}], "instance": "motion"}
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (EventDeviceClass.MOTION, True),
        (EventDeviceClass.BUTTON, False),
    ],
)
async def test_state_property_event_motion_event(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("event.test", STATE_UNKNOWN, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.MOTION)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.MOTION)
        return

    assert prop.retrievable is False
    assert prop.parameters == {"events": [{"value": "detected"}], "instance": "motion"}
    assert prop.get_value() is None
    prop.state = State("event.test", STATE_UNKNOWN, {ATTR_DEVICE_CLASS: device_class, ATTR_EVENT_TYPE: "motion"})
    assert prop.get_value() == "detected"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.GAS, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_gas(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.GAS)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.GAS)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "detected"}, {"value": "not_detected"}, {"value": "high"}],
        "instance": "gas",
    }
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"
    prop.state.state = "high"
    assert prop.get_value() == "high"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.SMOKE, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_smoke(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.SMOKE)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.SMOKE)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "detected"}, {"value": "not_detected"}, {"value": "high"}],
        "instance": "smoke",
    }
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"
    prop.state.state = "high"
    assert prop.get_value() == "high"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.BATTERY, True),
        (BinarySensorDeviceClass.SMOKE, False),
    ],
)
async def test_state_property_event_battery(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BATTERY_LEVEL)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BATTERY_LEVEL)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "low"}, {"value": "normal"}, {"value": "high"}],
        "instance": "battery_level",
    }
    assert prop.get_value() == "low"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "normal"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.MOISTURE, True),
        (BinarySensorDeviceClass.SMOKE, False),
    ],
)
async def test_state_property_event_water_leak(
    hass: HomeAssistant, entry_data: MockConfigEntryData, device_class: str, supported: bool
) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEAK)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEAK)
        return

    assert prop.retrievable
    assert prop.parameters == {"events": [{"value": "dry"}, {"value": "leak"}], "instance": "water_leak"}
    assert prop.get_value() == "leak"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "dry"


@pytest.mark.parametrize("domain", [sensor.DOMAIN, input_text.DOMAIN])
@pytest.mark.parametrize(
    "device_class,mock_entry_data,supported",
    [
        (None, False, False),
        (None, True, True),
        ("button", False, True),
    ],
)
async def test_state_property_event_button_sensor(
    hass: HomeAssistant,
    domain: str,
    device_class: str | None,
    entry_data: MockConfigEntryData,
    mock_entry_data: bool,
    supported: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entity_id = f"{domain}.test"
    if mock_entry_data:
        entry_data = MockConfigEntryData(hass, entity_config={entity_id: {CONF_DEVICE_CLASS: EventDeviceClass.BUTTON}})

    state = State(entity_id, "click", {ATTR_DEVICE_CLASS: device_class})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
        return

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() == "click"

    prop.state.state = "double"
    assert prop.get_value() == "double_click"

    prop.state.state = "hold"
    assert prop.get_value() == "long_press"

    caplog.clear()
    prop.state.state = "invalid"
    assert prop.get_value() is None
    assert caplog.messages == [f"Unknown event invalid for instance button of {entity_id}"]


async def test_state_property_event_button_gw3(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action"})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "foo"})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "click"})
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() is None

    prop.state.state = "double"
    assert prop.get_value() == "double_click"


@pytest.mark.parametrize(
    "device_class,mock_entry_data,supported",
    [
        (EventDeviceClass.BUTTON, False, True),
        (EventDeviceClass.DOORBELL, False, True),
        (EventDeviceClass.MOTION, False, False),
        (None, False, False),
        (None, True, True),
    ],
)
async def test_state_property_event_button_event(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    device_class: str | None,
    mock_entry_data: bool,
    supported: bool,
) -> None:
    entity_id = "event.test"
    if mock_entry_data:
        entry_data = MockConfigEntryData(hass, entity_config={entity_id: {CONF_DEVICE_CLASS: EventDeviceClass.BUTTON}})

    state = State(entity_id, STATE_UNKNOWN, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
        return

    assert prop.retrievable is False
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() is None
    prop.state = State(entity_id, STATE_UNKNOWN, {ATTR_DEVICE_CLASS: device_class, ATTR_EVENT_TYPE: "press"})
    assert prop.get_value() == "click"
    prop.state = State(entity_id, STATE_UNKNOWN, {ATTR_DEVICE_CLASS: device_class, ATTR_EVENT_TYPE: "double"})
    assert prop.get_value() == "double_click"


async def test_state_property_event_vibration(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.VIBRATION})

    prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "tilt"}, {"value": "fall"}, {"value": "vibration"}],
        "instance": "vibration",
    }
    assert prop.get_value() == "vibration"

    prop.state.state = STATE_OFF
    assert prop.get_value() is None


async def test_state_property_event_vibration_gw3(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action"})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "foo"})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "vibrate"})
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "tilt"}, {"value": "fall"}, {"value": "vibration"}],
        "instance": "vibration",
    }
    assert prop.get_value() is None

    prop.state = State("sensor.vibration", "vibrate")
    assert prop.get_value() == "vibration"

    prop.state = State("sensor.vibration", "fall")
    assert prop.get_value() == "fall"
