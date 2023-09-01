import typing
from unittest.mock import patch

from homeassistant import core
from homeassistant.components import binary_sensor, climate, sensor
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component

from custom_components.yandex_smart_home.entity import YandexEntity
from custom_components.yandex_smart_home.helpers import Config
from custom_components.yandex_smart_home.property import STATE_PROPERTIES_REGISTRY, Property
from custom_components.yandex_smart_home.property_event import StateEventProperty
from custom_components.yandex_smart_home.property_float import FloatProperty
from custom_components.yandex_smart_home.schema import (
    EventPropertyInstance,
    FloatPropertyInstance,
    PropertyInstance,
    PropertyType,
)

from . import BASIC_CONFIG


@typing.overload
def get_properties(
    hass: HomeAssistant,
    config: Config,
    state: State,
    property_type: PropertyType.FLOAT,
    instance: FloatPropertyInstance,
) -> list[FloatProperty]:
    ...


@typing.overload
def get_properties(
    hass: HomeAssistant,
    config: Config,
    state: State,
    property_type: PropertyType.EVENT,
    instance: EventPropertyInstance,
) -> list[StateEventProperty]:
    ...


def get_properties(
    hass: HomeAssistant,
    config: Config,
    state: State,
    property_type: PropertyType,
    instance: PropertyInstance,
) -> list[Property]:
    props = []

    for PropertyT in STATE_PROPERTIES_REGISTRY:
        prop = PropertyT(hass, config, state)

        if prop.type != property_type or prop.instance != instance:
            continue

        if prop.supported:
            props.append(prop)

    return props


@typing.overload
def get_exact_one_property(
    hass: HomeAssistant,
    config: Config,
    state: State,
    property_type: PropertyType.FLOAT,
    instance: FloatPropertyInstance,
) -> FloatProperty:
    ...


@typing.overload
def get_exact_one_property(
    hass: HomeAssistant,
    config: Config,
    state: State,
    property_type: PropertyType.EVENT,
    instance: EventPropertyInstance,
) -> StateEventProperty:
    ...


def get_exact_one_property(
    hass: HomeAssistant, config: Config, state: State, property_type: PropertyType, instance: PropertyInstance
) -> Property:
    props = get_properties(hass, config, state, property_type, instance)
    assert len(props) == 1
    return props[0]


def assert_exact_one_property(
    hass: HomeAssistant, config: Config, state: State, property_type: PropertyType, instance: PropertyInstance
):
    assert len(get_properties(hass, config, state, property_type, instance)) == 1


def assert_no_properties(
    hass: HomeAssistant, config: Config, state: State, property_type: PropertyType, instance: PropertyInstance
):
    assert len(get_properties(hass, config, state, property_type, instance)) == 0


async def test_property_demo_platform(hass):
    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR],
    ):
        await async_setup_component(hass, core.DOMAIN, {})
        for component in climate, sensor, binary_sensor:
            await async_setup_component(hass, component.DOMAIN, {component.DOMAIN: [{"platform": "demo"}]})
        await hass.async_block_till_done()

    # for x in hass.states.async_all():
    #     e = YandexEntity(hass, BASIC_CONFIG, x)
    #     l = list((c.type, c.instance) for c in e.properties())
    #     print(f'state = hass.states.get(\'{x.entity_id}\')')
    #     print(f'entity = YandexEntity(hass, BASIC_CONFIG, state)')
    #     print(f'props = list((p.type, p.instance) for p in entity.properties())')
    #     print(f'assert props == {l}')
    #     print()

    state = hass.states.get("climate.heatpump")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "temperature")]

    state = hass.states.get("climate.hvac")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "temperature"), ("devices.properties.float", "humidity")]

    state = hass.states.get("climate.ecobee")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "temperature")]

    state = hass.states.get("sensor.outside_temperature")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "temperature"), ("devices.properties.float", "battery_level")]

    state = hass.states.get("sensor.outside_humidity")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "humidity")]

    state = hass.states.get("sensor.carbon_monoxide")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == []

    state = hass.states.get("sensor.carbon_dioxide")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "co2_level"), ("devices.properties.float", "battery_level")]

    state = hass.states.get("sensor.power_consumption")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.float", "power")]

    state = hass.states.get("binary_sensor.basement_floor_wet")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.event", "water_leak")]

    state = hass.states.get("binary_sensor.movement_backyard")
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    props = list((p.type, p.instance) for p in entity.properties())
    assert props == [("devices.properties.event", "motion")]
