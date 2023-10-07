from homeassistant.components import (
    air_quality,
    binary_sensor,
    climate,
    cover,
    fan,
    humidifier,
    light,
    sensor,
    switch,
    water_heater,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_ON,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.property_float import PropertyType
from custom_components.yandex_smart_home.schema import FloatPropertyInstance
from custom_components.yandex_smart_home.unit_conversion import UnitOfPressure

from . import BASIC_ENTRY_DATA, MockConfigEntryData
from .test_property import assert_no_properties, get_exact_one_property


@pytest.mark.parametrize(
    "domain,device_class,attribute,supported",
    [
        (sensor.DOMAIN, SensorDeviceClass.HUMIDITY, None, True),
        (air_quality.DOMAIN, None, climate.ATTR_HUMIDITY, True),
        (air_quality.DOMAIN, None, None, False),
        (climate.DOMAIN, None, climate.ATTR_CURRENT_HUMIDITY, True),
        (climate.DOMAIN, None, None, False),
        (fan.DOMAIN, None, climate.ATTR_CURRENT_HUMIDITY, True),
        (fan.DOMAIN, None, None, False),
        (humidifier.DOMAIN, None, climate.ATTR_CURRENT_HUMIDITY, True),
        (humidifier.DOMAIN, None, None, False),
    ],
)
async def test_property_float_humidity(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 69
    else:
        attributes[attribute] = 69

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.HUMIDITY)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.HUMIDITY)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "humidity", "unit": "unit.percent"}
    assert prop.get_value() == 69

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "domain,device_class,attribute,supported",
    [
        (sensor.DOMAIN, SensorDeviceClass.TEMPERATURE, None, True),
        (air_quality.DOMAIN, None, climate.ATTR_TEMPERATURE, True),
        (air_quality.DOMAIN, None, None, False),
        (climate.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, True),
        (climate.DOMAIN, None, None, False),
        (fan.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, True),
        (fan.DOMAIN, None, None, False),
        (humidifier.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, True),
        (humidifier.DOMAIN, None, None, False),
        (water_heater.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, True),
        (water_heater.DOMAIN, None, None, False),
    ],
)
async def test_property_float_temperature(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 34
    else:
        attributes[attribute] = 34

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    assert prop.get_value() == 34

    if attribute is None:
        value = -50
    else:
        attributes[attribute] = -50
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() == -50

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() is None


async def test_property_float_temperature_convertion(hass):
    state = State(
        "sensor.test",
        "34.756",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
        },
    )
    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    assert prop.get_value() == 34.76

    state = State(
        "sensor.test",
        "50.10",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.FAHRENHEIT,
        },
    )
    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    assert prop.get_value() == 10.06


@pytest.mark.parametrize("device_class", [SensorDeviceClass.PRESSURE, SensorDeviceClass.ATMOSPHERIC_PRESSURE])
@pytest.mark.parametrize(
    "unit_of_measurement,property_unit,v",
    [
        (UnitOfPressure.PA, "unit.pressure.pascal", 98658.57),
        (UnitOfPressure.MMHG, "unit.pressure.mmhg", 740),
        (UnitOfPressure.ATM, "unit.pressure.atm", 0.97),
        (UnitOfPressure.BAR, "unit.pressure.bar", 0.99),
    ],
)
def test_property_float_pressure_from_mmhg(
    hass, config_entry_direct, device_class, unit_of_measurement, property_unit, v
):
    entry_data = MockConfigEntryData(
        entry=config_entry_direct, yaml_config={const.CONF_SETTINGS: {const.CONF_PRESSURE_UNIT: unit_of_measurement}}
    )
    state = State(
        "sensor.test",
        "740",
        {ATTR_DEVICE_CLASS: device_class, ATTR_UNIT_OF_MEASUREMENT: UnitOfPressure.MMHG},
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.PRESSURE)
    assert prop.retrievable is True
    assert prop.parameters == {"instance": "pressure", "unit": property_unit}
    assert prop.get_value() == v

    prop.state = State(
        "sensor.test",
        "-5",
        {ATTR_DEVICE_CLASS: device_class, ATTR_UNIT_OF_MEASUREMENT: UnitOfPressure.MMHG},
    )
    assert prop.get_value() == 0


@pytest.mark.parametrize("device_class", [SensorDeviceClass.PRESSURE, SensorDeviceClass.ATMOSPHERIC_PRESSURE])
@pytest.mark.parametrize(
    "unit_of_measurement,property_unit,v",
    [
        (UnitOfPressure.PA, "unit.pressure.pascal", 106868.73),
        (UnitOfPressure.MMHG, "unit.pressure.mmhg", 801.58),
        (UnitOfPressure.ATM, "unit.pressure.atm", 1.05),
        (UnitOfPressure.BAR, "unit.pressure.bar", 1.07),
    ],
)
def test_property_float_pressure_from_psi(
    hass, config_entry_direct, device_class, unit_of_measurement, property_unit, v
):
    entry_data = MockConfigEntryData(
        entry=config_entry_direct, yaml_config={const.CONF_SETTINGS: {const.CONF_PRESSURE_UNIT: unit_of_measurement}}
    )
    state = State(
        "sensor.test",
        "15.5",
        {ATTR_DEVICE_CLASS: device_class, ATTR_UNIT_OF_MEASUREMENT: UnitOfPressure.PSI},
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.PRESSURE)
    assert prop.retrievable is True
    assert prop.parameters == {"instance": "pressure", "unit": property_unit}
    assert prop.get_value() == v


def test_property_float_pressure_unsupported_target(hass, config_entry_direct):
    entry_data = MockConfigEntryData(
        entry=config_entry_direct, yaml_config={const.CONF_SETTINGS: {const.CONF_PRESSURE_UNIT: "kPa"}}
    )
    state = State(
        "sensor.test",
        "15.5",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.PRESSURE, ATTR_UNIT_OF_MEASUREMENT: UnitOfPressure.PSI},
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.PRESSURE)
    assert prop.retrievable is True
    with pytest.raises(ValueError):
        assert prop.parameters

    with pytest.raises(ValueError):
        prop.get_value()


@pytest.mark.parametrize(
    "domain,device_class,attribute,supported",
    [
        (sensor.DOMAIN, SensorDeviceClass.ILLUMINANCE, None, True),
        (sensor.DOMAIN, None, None, False),
        (sensor.DOMAIN, None, "illuminance", True),
        (light.DOMAIN, None, "illuminance", True),
        (light.DOMAIN, None, None, False),
        (fan.DOMAIN, None, "illuminance", True),
        (fan.DOMAIN, None, None, False),
    ],
)
async def test_property_float_illumination(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 48
    else:
        attributes[attribute] = 48

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.ILLUMINATION
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.ILLUMINATION)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "illumination", "unit": "unit.illumination.lux"}
    assert prop.get_value() == 48

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "domain,attribute,supported",
    [
        (fan.DOMAIN, "water_level", True),
        (humidifier.DOMAIN, "water_level", True),
    ],
)
async def test_property_float_water_level(hass, domain, attribute, supported):
    state = State(f"{domain}.test", STATE_ON, {attribute: "90"})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, FloatPropertyInstance.WATER_LEVEL)
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.WATER_LEVEL
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.WATER_LEVEL)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "water_level", "unit": "unit.percent"}
    assert prop.get_value() == 90

    for a, b in ((-5, 0), (200, 100)):
        prop.state = State(f"{domain}.test", STATE_ON, {attribute: a})
        assert prop.get_value() == b

    prop.state = State(f"{domain}.test", STATE_ON, {attribute: None})
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "domain,device_class,attribute,supported",
    [
        (sensor.DOMAIN, SensorDeviceClass.CO2, None, True),
        (sensor.DOMAIN, None, None, False),
        (air_quality.DOMAIN, None, air_quality.ATTR_CO2, True),
        (air_quality.DOMAIN, None, None, False),
        (fan.DOMAIN, None, air_quality.ATTR_CO2, True),
        (fan.DOMAIN, None, None, False),
    ],
)
async def test_property_float_co2_level(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 643
    else:
        attributes[attribute] = 643

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.CO2_LEVEL
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.CO2_LEVEL)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "co2_level", "unit": "unit.ppm"}
    assert prop.get_value() == 643

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "attribute,instance",
    [
        (air_quality.ATTR_PM_0_1, "pm1_density"),
        (air_quality.ATTR_PM_2_5, "pm2.5_density"),
        (air_quality.ATTR_PM_10, "pm10_density"),
    ],
)
async def test_property_float_pm_density(hass, attribute, instance):
    state = State("air_quality.test", STATE_ON, {attribute: 300})
    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance(instance))

    assert prop.retrievable is True
    assert prop.parameters == {"instance": instance, "unit": "unit.density.mcg_m3"}
    assert prop.get_value() == 300

    prop.state = State("air_quality.test", STATE_ON, {attribute: -5})
    assert prop.get_value() == 0

    prop.state = State("air_quality.test", STATE_ON, {attribute: None})
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "unit,v",
    [
        ("ppb", 134.89),
        ("ppm", 134888.81),
        ("µg/m³", 30),
        ("mg/m³", 30000),
        ("μg/ft³", 1059.44),
        ("unsupported", 30),
        (None, 30),
    ],
)
async def test_property_float_tvoc_concentration(hass, unit, v):
    state = State(
        "air_quality.test",
        STATE_ON,
    )
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.TVOC)

    attributes = {"total_volatile_organic_compounds": 30}
    if unit:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit

    state = State("air_quality.test", STATE_ON, attributes)
    prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.TVOC)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "tvoc", "unit": "unit.density.mcg_m3"}
    if unit == "unsupported":
        with pytest.raises(HomeAssistantError):
            prop.get_value()
        return

    assert prop.get_value() == v

    prop.state = State("air_quality.test", STATE_ON, {"total_volatile_organic_compounds": -5})
    assert prop.get_value() == 0

    prop.state = State("air_quality.test", STATE_ON, {"total_volatile_organic_compounds": None})
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "domain,device_class,instance,unit,unit_of_measurement,supported,v",
    [
        (binary_sensor.DOMAIN, SensorDeviceClass.VOLTAGE, "voltage", "unit.volt", None, False, None),
        (sensor.DOMAIN, SensorDeviceClass.VOLTAGE, "voltage", "unit.volt", None, True, 220.57),
        (sensor.DOMAIN, SensorDeviceClass.VOLTAGE, "voltage", "unit.volt", "V", True, 220.57),
        (sensor.DOMAIN, SensorDeviceClass.VOLTAGE, "voltage", "unit.volt", "mV", True, 0.22),
        (binary_sensor.DOMAIN, SensorDeviceClass.CURRENT, "amperage", "unit.ampere", None, False, None),
        (sensor.DOMAIN, SensorDeviceClass.CURRENT, "amperage", "unit.ampere", None, True, 220.57),
        (sensor.DOMAIN, SensorDeviceClass.CURRENT, "amperage", "unit.ampere", "A", True, 220.57),
        (sensor.DOMAIN, SensorDeviceClass.CURRENT, "amperage", "unit.ampere", "mA", True, 0.22),
        (binary_sensor.DOMAIN, SensorDeviceClass.POWER, "power", "unit.watt", None, False, None),
        (sensor.DOMAIN, SensorDeviceClass.POWER, "power", "unit.watt", None, True, 220.57),
        (sensor.DOMAIN, SensorDeviceClass.POWER, "power", "unit.watt", "W", True, 220.57),
        (sensor.DOMAIN, SensorDeviceClass.POWER, "power", "unit.watt", "kW", True, 220566),
    ],
)
async def test_property_electricity_sensor(
    hass, domain, device_class, instance, unit, unit_of_measurement, supported, v
):
    attributes = {ATTR_DEVICE_CLASS: device_class}
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement
    state = State(f"{domain}.test", "220.566", attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, instance)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, instance)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": instance, "unit": unit}
    assert prop.get_value() == v

    prop.state = State(f"{domain}.test", "-5", attributes)
    assert prop.get_value() == 0

    prop.state = State(f"{domain}.test", STATE_UNKNOWN, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "domain,value_attribute,instance,unit,supported",
    [
        (sensor.DOMAIN, None, "voltage", "unit.volt", False),
        (switch.DOMAIN, "voltage", "voltage", "unit.volt", True),
        (switch.DOMAIN, None, "voltage", "unit.volt", False),
        (light.DOMAIN, "voltage", "voltage", "unit.volt", True),
        (light.DOMAIN, None, "voltage", "unit.volt", False),
        (sensor.DOMAIN, None, "amperage", "unit.ampere", False),
        (switch.DOMAIN, "current", "amperage", "unit.ampere", True),
        (switch.DOMAIN, None, "amperage", "unit.ampere", False),
        (light.DOMAIN, "current", "amperage", "unit.ampere", True),
        (light.DOMAIN, None, "amperage", "unit.ampere", False),
        (sensor.DOMAIN, None, "power", "unit.watt", False),
        (switch.DOMAIN, "power", "power", "unit.watt", True),
        (switch.DOMAIN, "load_power", "power", "unit.watt", True),
        (switch.DOMAIN, None, "power", "unit.watt", False),
    ],
)
@pytest.mark.parametrize("unit_of_measurement", [None, "foo"])
async def test_property_electricity_attributes(
    hass, domain, value_attribute, instance, unit, supported, unit_of_measurement
):
    attributes = {}
    value = STATE_ON

    if value_attribute:
        attributes[value_attribute] = 220
    else:
        value = 220

    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, instance)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, instance)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": instance, "unit": unit}
    assert prop.get_value() == 220

    if value_attribute:
        attributes[value_attribute] = -5
    else:
        value = -5
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() == 0

    if value_attribute:
        attributes[value_attribute] = None
    else:
        value = STATE_UNKNOWN

    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize("domain", [switch.DOMAIN, sensor.DOMAIN, light.DOMAIN, cover.DOMAIN])
async def test_property_float_battery_class(hass, domain):
    state = State(f"{domain}.test", "50", {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, FloatPropertyInstance.BATTERY_LEVEL)
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.BATTERY_LEVEL)

    state = State(
        f"{domain}.test", "50", {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY, ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    prop = get_exact_one_property(
        hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.BATTERY_LEVEL
    )
    assert prop.retrievable is True
    assert prop.parameters == {"instance": "battery_level", "unit": "unit.percent"}
    assert prop.get_value() == 50

    prop.state = State(
        f"{domain}.test",
        STATE_UNKNOWN,
        {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY, ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE},
    )
    assert prop.get_value() is None

    for s in ["low", "charging", "-5"]:
        prop.state = State(
            f"{domain}.test", s, {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY, ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
        )
        assert prop.get_value() == 0

    prop.state = State(
        f"{domain}.test", "200", {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY, ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    assert prop.get_value() == 100


@pytest.mark.parametrize("domain", [switch.DOMAIN, sensor.DOMAIN, light.DOMAIN, cover.DOMAIN])
async def test_property_float_battery_attr(hass, domain):
    state = State(f"{domain}.test", STATE_ON, {ATTR_BATTERY_LEVEL: 50})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, FloatPropertyInstance.BATTERY_LEVEL)
    prop = get_exact_one_property(
        hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, FloatPropertyInstance.BATTERY_LEVEL
    )
    assert prop.retrievable is True
    assert prop.parameters == {"instance": "battery_level", "unit": "unit.percent"}
    assert prop.get_value() == 50

    prop.state = State(f"{domain}.test", STATE_ON, {ATTR_BATTERY_LEVEL: None})
    assert prop.get_value() is None

    for s in ["low", "charging", "-5"]:
        prop.state = State(f"{domain}.test", STATE_ON, {ATTR_BATTERY_LEVEL: s})
        assert prop.get_value() == 0

    prop.state = State(f"{domain}.test", STATE_ON, {ATTR_BATTERY_LEVEL: "200"})
    assert prop.get_value() == 100
