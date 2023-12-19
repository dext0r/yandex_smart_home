from __future__ import annotations

from homeassistant.components import binary_sensor, climate, sensor
from homeassistant.const import MINOR_VERSION
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component

from custom_components.yandex_smart_home.entity import YandexEntity
from custom_components.yandex_smart_home.helpers import Config
from custom_components.yandex_smart_home.prop import PROPERTIES, AbstractProperty
from custom_components.yandex_smart_home.prop_event import EventProperty
from custom_components.yandex_smart_home.prop_float import FloatProperty

from . import BASIC_CONFIG


def get_properties(hass: HomeAssistant, config: Config, state: State,
                   property_type: str, instance: str) -> list[AbstractProperty]:
    props = []

    for Property in PROPERTIES:
        prop = Property(hass, config, state)

        if prop.type != property_type or prop.instance != instance:
            continue

        if prop.supported():
            props.append(prop)

    return props


def get_exact_one_property(hass: HomeAssistant, config: Config, state: State,
                           property_type: str, instance: str) -> AbstractProperty | EventProperty | FloatProperty:
    props = get_properties(hass, config, state, property_type, instance)
    assert len(props) == 1
    return props[0]


def assert_exact_one_property(hass: HomeAssistant, config: Config, state: State,
                              property_type: str, instance: str):
    assert len(get_properties(hass, config, state, property_type, instance)) == 1


def assert_no_properties(hass: HomeAssistant, config: Config, state: State,
                         property_type: str, instance: str):
    assert len(get_properties(hass, config, state, property_type, instance)) == 0


async def test_property_demo_platform(hass):
    for component in climate, sensor, binary_sensor:
        await async_setup_component(
            hass, component.DOMAIN, {component.DOMAIN: [{'platform': 'demo'}]}
        )
    await hass.async_block_till_done()

    # for x in hass.states.async_all():
    #     e = YandexEntity(hass, BASIC_CONFIG, x)
    #     l = list((c.type, c.instance) for c in e.properties())
    #     print(f'state = hass.states.get(\'{x.entity_id}\')')
    #     print(f'entity = YandexEntity(hass, BASIC_CONFIG, state)')
    #     print(f'props = list((p.type, p.instance) for p in entity.properties())')
    #     print(f'assert props == {l}')
    #     print()

    state = hass.states.get('climate.heatpump')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.float', 'temperature')]

    state = hass.states.get('climate.hvac')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.float', 'temperature'), ('devices.properties.float', 'humidity')]

    state = hass.states.get('climate.ecobee')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.float', 'temperature')]

    state = hass.states.get('sensor.outside_temperature')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.float', 'temperature'), ('devices.properties.float', 'battery_level')]

    state = hass.states.get('sensor.outside_humidity')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.float', 'humidity')]

    state = hass.states.get('sensor.carbon_monoxide')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == []

    state = hass.states.get('sensor.carbon_dioxide')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.float', 'co2_level'), ('devices.properties.float', 'battery_level')]

    if MINOR_VERSION > 7:
        state = hass.states.get('sensor.power_consumption')
        entity = YandexEntity(hass, BASIC_CONFIG, state)
        props = list((p.type, p.instance) for p in entity.properties())
        assert props == [('devices.properties.float', 'power')]

        if MINOR_VERSION < 9:
            state = hass.states.get('sensor.today_energy')
            entity = YandexEntity(hass, BASIC_CONFIG, state)
            props = list((p.type, p.instance) for p in entity.properties())
            assert props == [('devices.properties.float', 'electricity_meter')]

    state = hass.states.get('binary_sensor.basement_floor_wet')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.event', 'water_leak')]

    state = hass.states.get('binary_sensor.movement_backyard')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [('devices.properties.event', 'motion')]
