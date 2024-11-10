from typing import Any

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
from homeassistant.components.air_quality import ATTR_CO2, ATTR_PM_0_1, ATTR_PM_2_5, ATTR_PM_10
from homeassistant.components.climate import ATTR_CURRENT_HUMIDITY, ATTR_HUMIDITY
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.water_heater import ATTR_CURRENT_TEMPERATURE
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_ON,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, State
import pytest

from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.property_float import PropertyType
from custom_components.yandex_smart_home.schema import FloatPropertyInstance, ResponseCode
from custom_components.yandex_smart_home.unit_conversion import UnitOfPressure
from tests import MockConfigEntryData

from .test_property import assert_no_properties, get_exact_one_property


@pytest.mark.parametrize(
    "domain,device_class,attribute,supported",
    [
        (sensor.DOMAIN, SensorDeviceClass.HUMIDITY, None, True),
        (sensor.DOMAIN, SensorDeviceClass.MOISTURE, None, True),
        (air_quality.DOMAIN, None, ATTR_HUMIDITY, True),
        (air_quality.DOMAIN, None, None, False),
        (climate.DOMAIN, None, ATTR_CURRENT_HUMIDITY, True),
        (climate.DOMAIN, None, None, False),
        (fan.DOMAIN, None, ATTR_CURRENT_HUMIDITY, True),
        (fan.DOMAIN, None, None, False),
        (humidifier.DOMAIN, None, ATTR_CURRENT_HUMIDITY, True),
        (humidifier.DOMAIN, None, None, False),
    ],
)
async def test_property_float_humidity(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    device_class: str | None,
    attribute: str | None,
    supported: bool,
) -> None:
    attributes: dict[str, Any] = {}
    value = STATE_ON

    if attribute is None:
        value = "69"
    else:
        attributes[attribute] = 69

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.HUMIDITY)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.HUMIDITY)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "humidity", "unit": "unit.percent"}
    assert prop.get_value() == 69

    if attribute is None:
        value = "-5"
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
    "domain,device_class,attribute,unit_of_measurement,supported",
    [
        (sensor.DOMAIN, SensorDeviceClass.TEMPERATURE, None, None, True),
        (sensor.DOMAIN, None, None, UnitOfTemperature.CELSIUS, True),
        (sensor.DOMAIN, None, None, UnitOfTemperature.KELVIN, True),
        (sensor.DOMAIN, None, None, UnitOfTemperature.FAHRENHEIT, True),
        (air_quality.DOMAIN, None, ATTR_TEMPERATURE, None, True),
        (air_quality.DOMAIN, None, None, None, False),
        (climate.DOMAIN, None, ATTR_CURRENT_TEMPERATURE, None, True),
        (climate.DOMAIN, None, None, None, False),
        (fan.DOMAIN, None, ATTR_CURRENT_TEMPERATURE, None, True),
        (fan.DOMAIN, None, None, None, False),
        (humidifier.DOMAIN, None, ATTR_CURRENT_TEMPERATURE, None, True),
        (humidifier.DOMAIN, None, None, None, False),
        (water_heater.DOMAIN, None, ATTR_CURRENT_TEMPERATURE, None, True),
        (water_heater.DOMAIN, None, None, None, False),
    ],
)
async def test_property_float_temperature(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    device_class: str | None,
    attribute: str | None,
    unit_of_measurement: str | None,
    supported: bool,
) -> None:
    attributes: dict[str, Any] = {}
    value = STATE_ON

    if attribute is None:
        value = "34"
    else:
        attributes[attribute] = 34

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)
        return

    if unit_of_measurement in (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.KELVIN):
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    assert prop.get_value() == 34

    if attribute is None:
        value = "-50"
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


async def test_property_float_temperature_convertion(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    state = State(
        "sensor.test",
        "34.756",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
        },
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    assert prop.get_value() == 34.76

    state = State(
        "sensor.test",
        "34.756",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.KELVIN,
        },
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.kelvin"}
    assert prop.get_value() == 34.76

    state = State(
        "sensor.test",
        "50.10",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.FAHRENHEIT,
        },
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    assert prop.get_value() == 10.06

    state = State(
        "sensor.test",
        "50.10",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: "foo",
        },
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TEMPERATURE)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "temperature", "unit": "unit.temperature.celsius"}
    with pytest.raises(APIError) as e:
        prop.get_value()
    assert e.value.code == ResponseCode.INVALID_VALUE
    assert e.value.message == (
        "Failed to convert value from 'foo' to '°C' for instance temperature of float property of sensor.test: "
        "foo is not a recognized temperature unit."
    )


@pytest.mark.parametrize("device_class", [SensorDeviceClass.PRESSURE, SensorDeviceClass.ATMOSPHERIC_PRESSURE])
@pytest.mark.parametrize(
    "unit_of_measurement,property_unit,assert_value",
    [
        (None, "unit.pressure.mmhg", None),
        (UnitOfPressure.PA, "unit.pressure.pascal", None),
        (UnitOfPressure.MMHG, "unit.pressure.mmhg", None),
        (UnitOfPressure.ATM, "unit.pressure.atm", None),
        (UnitOfPressure.BAR, "unit.pressure.bar", None),
        (UnitOfPressure.PSI, "unit.pressure.mmhg", 38294.9),
    ],
)
def test_property_float_pressure(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    device_class: str,
    unit_of_measurement: str | None,
    property_unit: str,
    assert_value: Any,
) -> None:
    value = 740.5
    attributes = {ATTR_DEVICE_CLASS: device_class}
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State("sensor.test", str(value), attributes)
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.PRESSURE)
    assert prop.retrievable is True
    assert prop.parameters == {"instance": "pressure", "unit": property_unit}

    if assert_value:
        assert prop.get_value() == assert_value
    else:
        assert prop.get_value() == value

    prop.state = State("sensor.test", "-5", attributes)
    assert prop.get_value() == 0


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
async def test_property_float_illumination(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    device_class: str | None,
    attribute: str | None,
    supported: bool,
) -> None:
    attributes: dict[str, Any] = {}
    value = STATE_ON

    if attribute is None:
        value = "48"
    else:
        attributes[attribute] = 48

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.ILLUMINATION)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.ILLUMINATION)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "illumination", "unit": "unit.illumination.lux"}
    assert prop.get_value() == 48

    if attribute is None:
        value = "-5"
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
async def test_property_float_water_level(
    hass: HomeAssistant, entry_data: MockConfigEntryData, domain: str, attribute: str, supported: bool
) -> None:
    state = State(f"{domain}.test", STATE_ON, {attribute: "90"})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, FloatPropertyInstance.WATER_LEVEL)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.WATER_LEVEL)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.WATER_LEVEL)
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
        (air_quality.DOMAIN, None, ATTR_CO2, True),
        (air_quality.DOMAIN, None, None, False),
        (fan.DOMAIN, None, ATTR_CO2, True),
        (fan.DOMAIN, None, None, False),
    ],
)
async def test_property_float_co2_level(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    device_class: str | None,
    attribute: str | None,
    supported: bool,
) -> None:
    attributes: dict[str, Any] = {}
    value = STATE_ON

    if attribute is None:
        value = "643"
    else:
        attributes[attribute] = 643

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.CO2_LEVEL)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.CO2_LEVEL)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "co2_level", "unit": "unit.ppm"}
    assert prop.get_value() == 643

    if attribute is None:
        value = "-5"
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
    "device_class,unit_of_measurement,instance,unit,assert_value",
    [
        (SensorDeviceClass.ENERGY, None, "electricity_meter", "unit.kilowatt_hour", None),
        (SensorDeviceClass.ENERGY, UnitOfEnergy.WATT_HOUR, "electricity_meter", "unit.kilowatt_hour", 3.42),
        (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "electricity_meter", "unit.kilowatt_hour", None),
        (SensorDeviceClass.ENERGY, UnitOfEnergy.MEGA_WATT_HOUR, "electricity_meter", "unit.kilowatt_hour", 3420500.0),
        (SensorDeviceClass.GAS, None, "gas_meter", "unit.cubic_meter", None),
        (SensorDeviceClass.GAS, UnitOfVolume.CUBIC_METERS, "gas_meter", "unit.cubic_meter", None),
        (SensorDeviceClass.GAS, UnitOfVolume.LITERS, "gas_meter", "unit.cubic_meter", 3.42),
        (SensorDeviceClass.WATER, None, "water_meter", "unit.cubic_meter", None),
        (SensorDeviceClass.WATER, UnitOfVolume.CUBIC_METERS, "water_meter", "unit.cubic_meter", None),
        (SensorDeviceClass.WATER, UnitOfVolume.LITERS, "water_meter", "unit.cubic_meter", 3.42),
    ],
)
def test_property_float_meter(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    device_class: str,
    instance: str,
    unit: str,
    unit_of_measurement: str | None,
    assert_value: Any,
) -> None:
    value = 3420.5
    attributes = {ATTR_DEVICE_CLASS: device_class}
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State("sensor.test", str(value), attributes)
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance(instance))
    assert prop.retrievable is True
    assert prop.parameters == {"instance": instance, "unit": unit}

    if assert_value:
        assert prop.get_value() == assert_value
    else:
        assert prop.get_value() == value

    prop.state = State("sensor.test", "-5", attributes)
    assert prop.get_value() == 0


@pytest.mark.parametrize("v,assert_v", [("300", 300), ("-5", 0), ("None", None)])
@pytest.mark.parametrize(
    "domain,device_class,attribute,instance",
    [
        (sensor.DOMAIN, SensorDeviceClass.PM1, None, "pm1_density"),
        (sensor.DOMAIN, SensorDeviceClass.PM25, None, "pm2.5_density"),
        (sensor.DOMAIN, SensorDeviceClass.PM10, None, "pm10_density"),
        (air_quality.DOMAIN, None, ATTR_PM_0_1, "pm1_density"),
        (air_quality.DOMAIN, None, ATTR_PM_2_5, "pm2.5_density"),
        (air_quality.DOMAIN, None, ATTR_PM_10, "pm10_density"),
    ],
)
async def test_property_float_pm_density(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    v: str,
    assert_v: Any,
    device_class: str | None,
    attribute: str | None,
    instance: str,
) -> None:
    state_v = STATE_ON
    attributes: dict[str, Any] = {}
    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    if attribute:
        attributes[attribute] = v
    else:
        state_v = v

    state = State(f"{domain}.test", state_v, attributes)
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance(instance))

    assert prop.retrievable is True
    assert prop.parameters == {"instance": instance, "unit": "unit.density.mcg_m3"}
    assert prop.get_value() == assert_v


@pytest.mark.parametrize(
    "domain,device_class,attribute",
    [
        (sensor.DOMAIN, SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, None),
        (sensor.DOMAIN, "tvoc", None),
        (air_quality.DOMAIN, None, "total_volatile_organic_compounds"),
    ],
)
@pytest.mark.parametrize(
    "unit_of_measurement,v,assert_v",
    [
        ("ppb", "30", 134.89),
        ("ppm", "30", 134888.81),
        ("µg/m³", "30", 30),
        ("mg/m³", "30", 30000),
        ("μg/ft³", "30", 1059.44),
        (None, "30", 30),
        (None, "-5", 0),
        (None, "None", None),
    ],
)
async def test_property_float_tvoc_concentration(
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    device_class: str | None,
    attribute: str | None,
    unit_of_measurement: str | None,
    v: str,
    assert_v: Any,
) -> None:
    state_v = STATE_ON
    attributes: dict[str, Any] = {}
    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    if attribute:
        attributes[attribute] = v
    else:
        state_v = v
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State(f"{domain}.test", state_v, attributes)
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TVOC)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "tvoc", "unit": "unit.density.mcg_m3"}
    if attribute and unit_of_measurement:
        assert prop.get_value() == float(v)
    else:
        assert prop.get_value() == assert_v


async def test_property_float_tvoc_concentration_voc(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    attributes = {ATTR_DEVICE_CLASS: SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS, ATTR_UNIT_OF_MEASUREMENT: "foo"}
    state = State("sensor.test", "30", attributes)
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.TVOC)

    assert prop.retrievable is True
    assert prop.parameters == {"instance": "tvoc", "unit": "unit.density.mcg_m3"}
    assert prop.get_value() == 30

    prop.state = State("sensor.test", "-5", attributes)
    assert prop.get_value() == 0


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
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    device_class: str | None,
    instance: str,
    unit: str,
    unit_of_measurement: str | None,
    supported: bool,
    v: Any,
) -> None:
    attributes = {ATTR_DEVICE_CLASS: device_class}
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement
    state = State(f"{domain}.test", "220.566", attributes)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance(instance))
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance(instance))
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
    hass: HomeAssistant,
    entry_data: MockConfigEntryData,
    domain: str,
    value_attribute: str | None,
    instance: str,
    unit: str,
    supported: bool,
    unit_of_measurement: str | None,
) -> None:
    attributes: dict[str, Any] = {}
    value = STATE_ON

    if value_attribute:
        attributes[value_attribute] = 220
    else:
        value = "220"

    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State(f"{domain}.test", value, attributes)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance(instance))
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance(instance))
        return

    assert prop.retrievable is True
    assert prop.parameters == {"instance": instance, "unit": unit}
    assert prop.get_value() == 220

    if value_attribute:
        attributes[value_attribute] = -5
    else:
        value = "-5"
    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() == 0

    if value_attribute:
        attributes[value_attribute] = None
    else:
        value = STATE_UNKNOWN

    prop.state = State(f"{domain}.test", value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize("domain", [switch.DOMAIN, sensor.DOMAIN, light.DOMAIN, cover.DOMAIN])
async def test_property_float_battery_class(hass: HomeAssistant, entry_data: MockConfigEntryData, domain: str) -> None:
    state = State(f"{domain}.test", "50", {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, FloatPropertyInstance.BATTERY_LEVEL)
    assert_no_properties(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.BATTERY_LEVEL)

    state = State(
        f"{domain}.test", "50", {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY, ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.BATTERY_LEVEL)
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
async def test_property_float_battery_attr(hass: HomeAssistant, entry_data: MockConfigEntryData, domain: str) -> None:
    state = State(f"{domain}.test", STATE_ON, {ATTR_BATTERY_LEVEL: 50})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, FloatPropertyInstance.BATTERY_LEVEL)
    prop = get_exact_one_property(hass, entry_data, state, PropertyType.FLOAT, FloatPropertyInstance.BATTERY_LEVEL)
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
