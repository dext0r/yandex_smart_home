from __future__ import annotations

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
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    PERCENTAGE,
    STATE_ON,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)
from homeassistant.core import State
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.const import DEVICE_CLASS_WATER
from custom_components.yandex_smart_home.error import SmartHomeError
from custom_components.yandex_smart_home.prop_event import PROPERTY_EVENT
from custom_components.yandex_smart_home.prop_float import PRESSURE_UNITS_TO_YANDEX_UNITS, PROPERTY_FLOAT, FloatProperty

from . import BASIC_CONFIG, MockConfig
from .test_prop import assert_no_properties, get_exact_one_property


class MockFloatProperty(FloatProperty):
    instance = 'humidity'

    def supported(self) -> bool:
        return True

    def get_value(self):
        pass


async def test_property_float(hass):
    prop = MockFloatProperty(hass, BASIC_CONFIG, State('binary_sensor.test', STATE_ON))
    assert prop.convert_value(1, 'foo') == 1


@pytest.mark.parametrize('domain,device_class,attribute,supported', [
    (sensor.DOMAIN, DEVICE_CLASS_HUMIDITY, None, True),
    (air_quality.DOMAIN, None, climate.ATTR_HUMIDITY, True),
    (air_quality.DOMAIN, None, None, False),
    (climate.DOMAIN, None, climate.ATTR_CURRENT_HUMIDITY, True),
    (climate.DOMAIN, None, None, False),
    (fan.DOMAIN, None, climate.ATTR_CURRENT_HUMIDITY, True),
    (fan.DOMAIN, None, None, False),
    (humidifier.DOMAIN, None, climate.ATTR_CURRENT_HUMIDITY, True),
    (humidifier.DOMAIN, None, None, False),
])
async def test_property_float_humidity(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 69
    else:
        attributes[attribute] = 69

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f'{domain}.test', value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_HUMIDITY)
    else:
        assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_HUMIDITY)
        return

    assert prop.retrievable
    assert prop.parameters() == {'instance': 'humidity', 'unit': 'unit.percent'}
    assert prop.get_value() == 69

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize('domain,device_class,attribute,unit_of_measurement,supported', [
    (sensor.DOMAIN, DEVICE_CLASS_TEMPERATURE, None, None, True),
    (sensor.DOMAIN, None, None, TEMP_CELSIUS, True),
    (air_quality.DOMAIN, None, climate.ATTR_TEMPERATURE, None, True),
    (air_quality.DOMAIN, None, None, None, False),
    (climate.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, None, True),
    (climate.DOMAIN, None, None, None, False),
    (fan.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, None, True),
    (fan.DOMAIN, None, None, None, False),
    (humidifier.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, None, True),
    (humidifier.DOMAIN, None, None, None, False),
    (water_heater.DOMAIN, None, climate.ATTR_CURRENT_TEMPERATURE, None, True),
    (water_heater.DOMAIN, None, None, None, False),
])
async def test_property_float_temperature(hass, domain, device_class, attribute, unit_of_measurement, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 34
    else:
        attributes[attribute] = 34

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class
    if unit_of_measurement:
        attributes[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    state = State(f'{domain}.test', value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_TEMPERATURE)
    else:
        assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_TEMPERATURE)
        return

    assert prop.retrievable
    assert prop.parameters() == {'instance': 'temperature', 'unit': 'unit.temperature.celsius'}
    assert prop.get_value() == 34

    if attribute is None:
        value = -50
    else:
        attributes[attribute] = -50
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() == -50

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize('device_class', ['pressure', 'atmospheric_pressure'])
@pytest.mark.parametrize('yandex_pressure_unit,v', [
    (const.PRESSURE_UNIT_PASCAL, 98658.28),
    (const.PRESSURE_UNIT_MMHG, 740),
    (const.PRESSURE_UNIT_ATM, 0.97),
    (const.PRESSURE_UNIT_BAR, 0.99),
])
def test_property_float_pressure(hass, device_class, yandex_pressure_unit, v):
    entry = MockConfigEntry(options={
        const.CONF_PRESSURE_UNIT: yandex_pressure_unit
    })
    config = MockConfig(entry=entry)
    state = State('sensor.test', '740', {
        ATTR_DEVICE_CLASS: device_class
    })
    assert_no_properties(hass, config, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_PRESSURE)

    state = State('sensor.test', '740', {
        ATTR_DEVICE_CLASS: device_class,
        ATTR_UNIT_OF_MEASUREMENT: const.PRESSURE_UNIT_MMHG
    })
    prop = get_exact_one_property(hass, config, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_PRESSURE)
    prop.state = State('sensor.test', '740', {
        ATTR_DEVICE_CLASS: device_class
    })
    with pytest.raises(SmartHomeError):
        prop.get_value()

    state = State('sensor.test', '740', {
        ATTR_DEVICE_CLASS: device_class,
        ATTR_UNIT_OF_MEASUREMENT: const.PRESSURE_UNIT_MMHG
    })
    prop = get_exact_one_property(hass, config, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_PRESSURE)
    assert prop.retrievable
    assert prop.parameters() == {
        'instance': 'pressure',
        'unit': PRESSURE_UNITS_TO_YANDEX_UNITS[yandex_pressure_unit]
    }
    assert prop.get_value() == v

    prop.state = State('sensor.test', '-5', {
        ATTR_DEVICE_CLASS: device_class,
        ATTR_UNIT_OF_MEASUREMENT: const.PRESSURE_UNIT_MMHG
    })
    assert prop.get_value() == 0


@pytest.mark.parametrize('domain,device_class,attribute,supported', [
    (sensor.DOMAIN, DEVICE_CLASS_ILLUMINANCE, None, True),
    (sensor.DOMAIN, None, None, False),
    (sensor.DOMAIN, None, 'illuminance', True),
    (light.DOMAIN, None, 'illuminance', True),
    (light.DOMAIN, None, None, False),
    (fan.DOMAIN, None, 'illuminance', True),
    (fan.DOMAIN, None, None, False),
])
async def test_property_float_illuminance(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 48
    else:
        attributes[attribute] = 48

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f'{domain}.test', value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_ILLUMINATION)
    else:
        assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_ILLUMINATION)
        return

    assert prop.retrievable
    assert prop.parameters() == {'instance': 'illumination', 'unit': 'unit.illumination.lux'}
    assert prop.get_value() == 48

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize('domain,attribute,supported', [
    (fan.DOMAIN, 'water_level', True),
    (humidifier.DOMAIN, 'water_level', True),
])
async def test_property_float_water_level(hass, domain, attribute, supported):
    state = State(f'{domain}.test', STATE_ON, {attribute: '90'})
    assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_EVENT, const.FLOAT_INSTANCE_WATER_LEVEL)
    if supported:
        prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_WATER_LEVEL)
    else:
        assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_WATER_LEVEL)
        return

    assert prop.retrievable
    assert prop.parameters() == {'instance': 'water_level', 'unit': 'unit.percent'}
    assert prop.get_value() == 90

    for v in [-5, 200]:
        prop.state = State(f'{domain}.test', STATE_ON, {attribute: v})
        assert prop.get_value() == 0

    prop.state = State(f'{domain}.test', STATE_ON, {attribute: None})
    assert prop.get_value() is None


@pytest.mark.parametrize('domain,device_class,attribute,supported', [
    (sensor.DOMAIN, DEVICE_CLASS_CO2, None, True),
    (sensor.DOMAIN, None, None, False),
    (air_quality.DOMAIN, None, air_quality.ATTR_CO2, True),
    (air_quality.DOMAIN, None, None, False),
    (fan.DOMAIN, None, air_quality.ATTR_CO2, True),
    (fan.DOMAIN, None, None, False),
])
async def test_property_float_co2(hass, domain, device_class, attribute, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 643
    else:
        attributes[attribute] = 643

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f'{domain}.test', value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_CO2_LEVEL)
    else:
        assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_CO2_LEVEL)
        return

    assert prop.retrievable
    assert prop.parameters() == {'instance': 'co2_level', 'unit': 'unit.ppm'}
    assert prop.get_value() == 643

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize('attribute,instance', [
    (air_quality.ATTR_PM_0_1, const.FLOAT_INSTANCE_PM1_DENSITY),
    (air_quality.ATTR_PM_2_5, const.FLOAT_INSTANCE_PM2_5_DENSITY),
    (air_quality.ATTR_PM_10, const.FLOAT_INSTANCE_PM10_DENSITY),
])
async def test_property_float_pm(hass, attribute, instance):
    state = State('air_quality.test', STATE_ON, {attribute: 300})
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, instance)

    assert prop.retrievable
    assert prop.parameters() == {'instance': instance, 'unit': 'unit.density.mcg_m3'}
    assert prop.get_value() == 300

    prop.state = State('air_quality.test', STATE_ON, {attribute: -5})
    assert prop.get_value() == 0

    prop.state = State('air_quality.test', STATE_ON, {attribute: None})
    assert prop.get_value() is None


@pytest.mark.parametrize('unit,v', [
    ('ppb', 134.89),
    ('ppm', 134888.81),
    ('µg/m³', 30),
    ('mg/m³', 30000),
    ('μg/ft³', 1059.44),
    ('unsupported', 30),
])
async def test_property_float_tvoc(hass, unit, v):
    state = State('air_quality.test', STATE_ON,)
    assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_TVOC)

    state = State('air_quality.test', STATE_ON, {
        'total_volatile_organic_compounds': 30,
        ATTR_UNIT_OF_MEASUREMENT: unit
    })
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_TVOC)

    assert prop.retrievable
    assert prop.parameters() == {'instance': const.FLOAT_INSTANCE_TVOC, 'unit': 'unit.density.mcg_m3'}
    assert prop.get_value() == v

    prop.state = State('air_quality.test', STATE_ON, {'total_volatile_organic_compounds': -5})
    assert prop.get_value() == 0

    prop.state = State('air_quality.test', STATE_ON, {'total_volatile_organic_compounds': None})
    assert prop.get_value() is None


@pytest.mark.parametrize('unit,v', [
    ('A', 1245),
    ('mA', 1.245),
])
async def test_property_float_amperage_value(hass, unit, v):
    state = State('switch.test', STATE_ON, {
        'current': 1245,
        ATTR_UNIT_OF_MEASUREMENT: unit
    })
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_AMPERAGE)

    assert prop.retrievable
    assert prop.parameters() == {'instance': const.FLOAT_INSTANCE_AMPERAGE, 'unit': 'unit.ampere'}
    assert prop.get_value() == v


@pytest.mark.parametrize('domain,device_class,attribute,instance,unit,supported', [
    (binary_sensor.DOMAIN, DEVICE_CLASS_VOLTAGE, None, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', False),
    (sensor.DOMAIN, DEVICE_CLASS_VOLTAGE, None, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', True),
    (sensor.DOMAIN, None, None, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', False),
    (switch.DOMAIN, None, ATTR_VOLTAGE, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', True),
    (switch.DOMAIN, None, None, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', False),
    (light.DOMAIN, None, ATTR_VOLTAGE, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', True),
    (light.DOMAIN, None, None, const.FLOAT_INSTANCE_VOLTAGE, 'unit.volt', False),

    (binary_sensor.DOMAIN, DEVICE_CLASS_CURRENT, None, const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', False),
    (sensor.DOMAIN, DEVICE_CLASS_CURRENT, None, const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', True),
    (sensor.DOMAIN, None, None, const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', False),
    (switch.DOMAIN, None, 'current', const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', True),
    (switch.DOMAIN, None, None, const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', False),
    (light.DOMAIN, None, 'current', const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', True),
    (light.DOMAIN, None, None, const.FLOAT_INSTANCE_AMPERAGE, 'unit.ampere', False),

    (sensor.DOMAIN, DEVICE_CLASS_POWER, None, const.FLOAT_INSTANCE_POWER, 'unit.watt', True),
    (sensor.DOMAIN, None, None, const.FLOAT_INSTANCE_POWER, 'unit.watt', False),
    (switch.DOMAIN, None, 'power', const.FLOAT_INSTANCE_POWER, 'unit.watt', True),
    (switch.DOMAIN, None, 'load_power', const.FLOAT_INSTANCE_POWER, 'unit.watt', True),
    (switch.DOMAIN, None, None, const.FLOAT_INSTANCE_POWER, 'unit.watt', False),

    (sensor.DOMAIN, DEVICE_CLASS_ENERGY, None, const.FLOAT_INSTANCE_ELECTRICITY_METER, 'unit.kilowatt_hour', True),
    (sensor.DOMAIN, DEVICE_CLASS_GAS, None, const.FLOAT_INSTANCE_GAS_METER, 'unit.cubic_meter', True),
    (sensor.DOMAIN, DEVICE_CLASS_WATER, None, const.FLOAT_INSTANCE_WATER_METER, 'unit.cubic_meter', True),
])
async def test_property_float_simple(hass, domain, device_class, attribute, instance: str, unit, supported):
    attributes = {}
    value = STATE_ON

    if attribute is None:
        value = 220
    else:
        attributes[attribute] = 220

    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f'{domain}.test', value, attributes)
    if supported:
        prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, instance)
    else:
        assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, instance)
        return

    assert prop.retrievable
    assert prop.parameters() == {'instance': instance, 'unit': unit}
    assert prop.get_value() == 220

    if attribute is None:
        value = -5
    else:
        attributes[attribute] = -5
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() == 0

    if attribute is None:
        value = STATE_UNKNOWN
    else:
        attributes[attribute] = None
    prop.state = State(f'{domain}.test', value, attributes)
    assert prop.get_value() is None


@pytest.mark.parametrize('domain', [switch.DOMAIN, sensor.DOMAIN, light.DOMAIN, cover.DOMAIN])
async def test_property_float_battery_class(hass, domain):
    state = State(f'{domain}.test', '50', {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_BATTERY
    })
    assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_EVENT, const.FLOAT_INSTANCE_BATTERY_LEVEL)
    assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_BATTERY_LEVEL)

    state = State(f'{domain}.test', '50', {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_BATTERY,
        ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE
    })
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_BATTERY_LEVEL)
    assert prop.retrievable
    assert prop.parameters() == {'instance': 'battery_level', 'unit': 'unit.percent'}
    assert prop.get_value() == 50

    prop.state = State(f'{domain}.test', STATE_UNKNOWN, {
        ATTR_DEVICE_CLASS: DEVICE_CLASS_BATTERY,
        ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE
    })
    assert prop.get_value() is None

    for s in ['low', 'charging', -5, 200]:
        prop.state = State(f'{domain}.test', s, {
            ATTR_DEVICE_CLASS: DEVICE_CLASS_BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE
        })
        assert prop.get_value() == 0


@pytest.mark.parametrize('domain', [switch.DOMAIN, sensor.DOMAIN, light.DOMAIN, cover.DOMAIN])
async def test_property_float_battery_attr(hass, domain):
    state = State(f'{domain}.test', STATE_ON, {
        ATTR_BATTERY_LEVEL: 50
    })
    assert_no_properties(hass, BASIC_CONFIG, state, PROPERTY_EVENT, const.FLOAT_INSTANCE_BATTERY_LEVEL)
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_BATTERY_LEVEL)
    assert prop.retrievable
    assert prop.parameters() == {'instance': 'battery_level', 'unit': 'unit.percent'}
    assert prop.get_value() == 50

    prop.state = State(f'{domain}.test', STATE_ON, {
        ATTR_BATTERY_LEVEL: None
    })
    assert prop.get_value() is None

    for s in ['low', 'charging', -5, 200]:
        prop.state = State(f'{domain}.test', STATE_ON, {
            ATTR_BATTERY_LEVEL: s
        })
        assert prop.get_value() == 0


@pytest.mark.parametrize('unit,v', [
    ('Wh', 0.001),
    ('kWh', 1.245),
])
async def test_property_float_energy_meter_value(hass, unit, v):
    state = State('sensor.test', '1.245', {
        ATTR_UNIT_OF_MEASUREMENT: unit,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_ENERGY
    })
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_ELECTRICITY_METER)

    assert prop.retrievable
    assert prop.parameters() == {'instance': const.FLOAT_INSTANCE_ELECTRICITY_METER, 'unit': 'unit.kilowatt_hour'}
    assert prop.get_value() == v


@pytest.mark.parametrize('unit,v', [
    ('L', 1.245),
    ('m³', 1245),
])
async def test_property_float_water_meter_value(hass, unit, v):
    state = State('sensor.test', '1245', {
        ATTR_UNIT_OF_MEASUREMENT: unit,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_WATER
    })
    prop = get_exact_one_property(hass, BASIC_CONFIG, state, PROPERTY_FLOAT, const.FLOAT_INSTANCE_WATER_METER)

    assert prop.retrievable
    assert prop.parameters() == {'instance': const.FLOAT_INSTANCE_WATER_METER, 'unit': 'unit.cubic_meter'}
    assert prop.get_value() == v
