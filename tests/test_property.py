import typing
from unittest.mock import patch

from homeassistant import core
from homeassistant.components import demo
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component

from custom_components.yandex_smart_home.device import Device
from custom_components.yandex_smart_home.entry_data import ConfigEntryData
from custom_components.yandex_smart_home.property import STATE_PROPERTIES_REGISTRY, StateProperty
from custom_components.yandex_smart_home.property_event import StateEventProperty
from custom_components.yandex_smart_home.property_float import StateFloatProperty
from custom_components.yandex_smart_home.schema import (
    EventPropertyInstance,
    FloatPropertyInstance,
    PropertyInstance,
    PropertyType,
)
from tests import MockConfigEntryData


@typing.overload
def get_properties(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: FloatPropertyInstance,
) -> list[StateFloatProperty]: ...


@typing.overload
def get_properties(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: EventPropertyInstance,
) -> list[StateEventProperty]: ...


def get_properties(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: PropertyInstance,
) -> list[StateFloatProperty] | list[StateEventProperty]:
    props: list[StateProperty] = []

    for PropertyT in STATE_PROPERTIES_REGISTRY:
        prop = PropertyT(hass, entry_data, state)

        if prop.type != property_type or prop.instance != instance:
            continue

        if prop.supported:
            props.append(prop)

    match instance:
        case FloatPropertyInstance():
            return typing.cast(list[StateFloatProperty], props)
        case EventPropertyInstance():
            return typing.cast(list[StateEventProperty], props)

    raise ValueError(f"Invalid type: {instance.__class__}")


@typing.overload
def get_exact_one_property(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: FloatPropertyInstance,
) -> StateFloatProperty: ...


@typing.overload
def get_exact_one_property(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: EventPropertyInstance,
) -> StateEventProperty: ...


def get_exact_one_property(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: PropertyInstance,
) -> StateFloatProperty | StateEventProperty:
    props = get_properties(hass, entry_data, state, property_type, instance)
    assert len(props) == 1
    return props[0]


def assert_exact_one_property(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: PropertyInstance,
) -> None:
    assert len(get_properties(hass, entry_data, state, property_type, instance)) == 1


def assert_no_properties(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    state: State,
    property_type: PropertyType,
    instance: PropertyInstance,
) -> None:
    assert len(get_properties(hass, entry_data, state, property_type, instance)) == 0


async def test_property_demo_platform(hass: HomeAssistant, entry_data: MockConfigEntryData) -> None:
    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR],
    ):
        await async_setup_component(hass, core.DOMAIN, {})
        await async_setup_component(hass, demo.DOMAIN, {})
        await hass.async_block_till_done()

    # for x in hass.states.async_all():
    #     d = Device(hass, entry_data, x.entity_id, x)
    #     l = list((c.type.value, c.instance.value) for c in d.get_properties())
    #     print(f"state = hass.states.get('{x.entity_id}')")
    #     print(f"assert state is not None")
    #     print(f"device = Device(hass, entry_data, state.entity_id, state)")
    #     if d.type is None:
    #         print(f"assert device.type is None")
    #     else:
    #         print(f"assert device.type == '{d.type.value}'")
    #     print(f"props = list((p.type, p.instance) for p in device.get_properties())")
    #     print(f"assert props == {l}")
    #     print()

    state = hass.states.get("zone.home")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type is None
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == []

    state = hass.states.get("climate.heatpump")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.thermostat"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "temperature")]

    state = hass.states.get("climate.hvac")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.thermostat"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "temperature"), ("devices.properties.float", "humidity")]

    state = hass.states.get("climate.ecobee")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.thermostat"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "temperature")]

    state = hass.states.get("sensor.outside_temperature")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor.climate"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "temperature"), ("devices.properties.float", "battery_level")]

    state = hass.states.get("sensor.outside_humidity")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor.climate"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "humidity")]

    state = hass.states.get("sensor.carbon_monoxide")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor.climate"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == []

    state = hass.states.get("sensor.carbon_dioxide")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor.climate"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "co2_level"), ("devices.properties.float", "battery_level")]

    state = hass.states.get("sensor.power_consumption")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "power")]

    state = hass.states.get("sensor.total_energy_kwh")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.smart_meter.electricity"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "electricity_meter")]

    state = hass.states.get("sensor.total_energy_mwh")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.smart_meter.electricity"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "electricity_meter")]

    state = hass.states.get("sensor.total_gas_m3")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.smart_meter.gas"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "gas_meter")]

    state = hass.states.get("sensor.total_gas_ft3")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.smart_meter.gas"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.float", "gas_meter")]

    state = hass.states.get("sensor.thermostat")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == []

    state = hass.states.get("binary_sensor.basement_floor_wet")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor.water_leak"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.event", "water_leak")]

    state = hass.states.get("binary_sensor.movement_backyard")
    assert state is not None
    device = Device(hass, entry_data, state.entity_id, state)
    assert device.type == "devices.types.sensor.motion"
    props = list((p.type, p.instance) for p in device.get_properties())
    assert props == [("devices.properties.event", "motion")]
