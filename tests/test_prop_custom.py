from __future__ import annotations

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import State
import pytest

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.error import SmartHomeError
from custom_components.yandex_smart_home.prop_custom import CustomEntityProperty
from custom_components.yandex_smart_home.prop_event import PROPERTY_EVENT
from custom_components.yandex_smart_home.prop_float import PROPERTY_FLOAT

from . import MockConfig

config = MockConfig(
    settings={
        const.CONF_PRESSURE_UNIT: const.PRESSURE_UNIT_MMHG
    }
)


@pytest.mark.parametrize('domain', [sensor.DOMAIN, binary_sensor.DOMAIN])
@pytest.mark.parametrize('instance', [
    'humidity',
    'temperature',
    'pressure',
    'water_level',
    'co2_level',
    'power',
    'voltage',
    'battery_level',
    'amperage',
    'illumination',
    'tvoc',
    'pm1_density',
    'pm2.5_density',
    'pm10_density',
    'vibration',
    'open',
    'button',
    'motion',
    'smoke',
    'gas',
    'water_leak'
])
async def test_property_custom(hass, domain, instance):
    state = State(f'{domain}.test', '10')
    if domain == binary_sensor.DOMAIN and instance in [
        'humidity', 'temperature', 'pressure', 'co2_level', 'power', 'voltage',
        'amperage', 'illumination', 'tvoc', 'pm1_density', 'pm2.5_density', 'pm10_density'
    ]:
        with pytest.raises(SmartHomeError) as e:
            CustomEntityProperty.get(hass, config, state, {
                const.CONF_ENTITY_PROPERTY_TYPE: instance
            })

        assert e.value.code == const.ERR_DEVICE_UNREACHABLE
        assert 'Unsupported' in e.value.message
        return

    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: instance
    })
    if instance in ['vibration', 'open', 'button', 'motion', 'smoke', 'gas', 'water_leak']:
        assert prop.type == PROPERTY_EVENT
    else:
        if domain == binary_sensor.DOMAIN and instance in ['water_level', 'battery_level']:
            assert prop.type == PROPERTY_EVENT
        else:
            assert prop.type == PROPERTY_FLOAT

    assert prop.parameters()['instance'] == instance

    if prop.type == PROPERTY_FLOAT:
        instance_unit = prop.parameters()['unit']
        if instance == 'pressure':
            assert 'pressure' in instance_unit

    if prop.type == PROPERTY_EVENT:
        assert len(prop.parameters()['events']) != 0

    if instance in ['button', 'vibration']:
        assert not prop.retrievable
    else:
        assert prop.retrievable


async def test_property_custom_get_value_event(hass):
    state = State('binary_sensor.test', STATE_ON)
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: const.EVENT_INSTANCE_BUTTON,
    })
    assert prop.supported(state.domain, 0, {}, {})
    assert prop.get_value() is None

    state = State('binary_sensor.test', STATE_UNAVAILABLE)
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: const.EVENT_INSTANCE_GAS,
    })
    assert prop.get_value() is None

    state = State('binary_sensor.test', STATE_ON)
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: const.EVENT_INSTANCE_GAS,
    })
    assert prop.get_value() == 'detected'


async def test_property_custom_get_value_float(hass):
    state = State('sensor.test', '3.36')
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
    })
    assert prop.supported(state.domain, 0, {}, {})
    assert prop.get_value() == 3.36
    for s in ['', '-', 'none', 'unknown']:
        prop.state.state = s.upper()
        assert prop.get_value() is None

    prop.state.state = 'not-a-number'
    with pytest.raises(SmartHomeError) as e:
        prop.get_value()
    assert e.value.code == const.ERR_NOT_SUPPORTED_IN_CURRENT_MODE
    assert 'Unsupported' in e.value.message

    with pytest.raises(SmartHomeError) as e:
        prop = CustomEntityProperty.get(hass, config, state, {
            const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
            const.CONF_ENTITY_PROPERTY_ATTRIBUTE: 'value'
        })
        prop.get_value()
    assert e.value.code == const.ERR_DEVICE_UNREACHABLE
    assert 'not found' in e.value.message

    state = State('sensor.test', '3')
    with pytest.raises(SmartHomeError) as e:
        CustomEntityProperty.get(hass, config, state, {
            const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
            const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.test_2'
        })
    assert e.value.code == const.ERR_DEVICE_UNREACHABLE
    assert 'not found' in e.value.message

    hass.states.async_set('sensor.test_2', '4.52')
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
        const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.test_2'
    })
    assert prop.get_value() == 4.52

    hass.states.async_set('sensor.test_2', '4.52', {
        'value': 9.99
    })
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_TEMPERATURE,
        const.CONF_ENTITY_PROPERTY_ENTITY: 'sensor.test_2',
        const.CONF_ENTITY_PROPERTY_ATTRIBUTE: 'value'
    })
    assert prop.get_value() == 9.99


@pytest.mark.parametrize('instance,unit,value', [
    (const.FLOAT_INSTANCE_PRESSURE, 'mmHg', 100),
    (const.FLOAT_INSTANCE_TVOC, 'ppb', 449.63)
])
async def test_property_custom_get_value_float_conversion(hass, instance: str, unit, value):
    state = State('sensor.test', '100')
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: instance,
        const.CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT: unit
    })
    assert prop.get_value() == value
    prop.state.state = STATE_UNAVAILABLE
    assert prop.get_value() is None

    state = State('sensor.test', '100', {
        ATTR_UNIT_OF_MEASUREMENT: unit
    })
    prop = CustomEntityProperty.get(hass, config, state, {
        const.CONF_ENTITY_PROPERTY_TYPE: instance
    })
    assert prop.get_value() == value
