from homeassistant.components import binary_sensor, input_text, sensor
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from homeassistant.core import State
import pytest

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.schema import EventPropertyInstance, PropertyType

from . import BASIC_ENTRY_DATA, MockConfigEntryData
from .test_property import assert_no_properties, get_exact_one_property


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
async def test_state_property_event_open(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
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
async def test_state_property_event_motion(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.MOTION)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"events": [{"value": "detected"}, {"value": "not_detected"}], "instance": "motion"}
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.GAS, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_gas(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.GAS)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.GAS)
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
async def test_state_property_event_smoke(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.SMOKE)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.SMOKE)
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
async def test_state_property_event_battery(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BATTERY_LEVEL
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BATTERY_LEVEL)
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
async def test_state_property_event_water_leak(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEAK
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEAK)
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
async def test_state_property_event_button(hass, domain, device_class, mock_entry_data, supported, caplog):
    entity_id = f"{domain}.test"
    entry_data = BASIC_ENTRY_DATA
    if mock_entry_data:
        entry_data = MockConfigEntryData(
            entity_config={entity_id: {const.CONF_DEVICE_CLASS: const.DEVICE_CLASS_BUTTON}}
        )

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


async def test_state_property_event_button_gw3(hass):
    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action"})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "foo"})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "click"})
    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() is None

    prop.state.state = "double"
    assert prop.get_value() == "double_click"


async def test_state_property_event_vibration(hass):
    state = State("binary_sensor.test", STATE_ON, {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.VIBRATION})

    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "tilt"}, {"value": "fall"}, {"value": "vibration"}],
        "instance": "vibration",
    }
    assert prop.get_value() == "vibration"

    prop.state.state = STATE_OFF
    assert prop.get_value() is None


async def test_state_property_event_vibration_gw3(hass):
    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action"})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "foo"})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

    state = State("sensor.button", "", {ATTR_DEVICE_CLASS: "action", "action": "vibrate"})
    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)

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
