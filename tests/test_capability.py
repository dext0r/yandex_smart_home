from unittest.mock import patch

from homeassistant import core
from homeassistant.components import button, climate, cover, fan, humidifier, light, lock, media_player, switch
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component

from custom_components.yandex_smart_home.capability import STATE_CAPABILITIES_REGISTRY, StateCapability
from custom_components.yandex_smart_home.device import Device
from custom_components.yandex_smart_home.helpers import Config
from custom_components.yandex_smart_home.schema import CapabilityInstance, CapabilityType

from . import BASIC_CONFIG


def get_capabilities(
    hass: HomeAssistant, config: Config, state: State, capability_type: CapabilityType, instance: CapabilityInstance
) -> list[StateCapability]:
    caps = []

    for CapabilityT in STATE_CAPABILITIES_REGISTRY:
        capability = CapabilityT(hass, config, state)

        if capability.type != capability_type or capability.instance != instance:
            continue

        if capability.supported:
            caps.append(capability)

    return caps


def get_exact_one_capability(
    hass: HomeAssistant, config: Config, state: State, capability_type: CapabilityType, instance: CapabilityInstance
) -> StateCapability:
    caps = get_capabilities(hass, config, state, capability_type, instance)
    assert len(caps) == 1
    return caps[0]


def assert_exact_one_capability(
    hass: HomeAssistant, config: Config, state: State, capability_type: CapabilityType, instance: CapabilityInstance
):
    assert len(get_capabilities(hass, config, state, capability_type, instance)) == 1


def assert_no_capabilities(
    hass: HomeAssistant, config: Config, state: State, capability_type: CapabilityType, instance: CapabilityInstance
):
    assert len(get_capabilities(hass, config, state, capability_type, instance)) == 0


async def test_capability_demo_platform(hass):
    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [
            Platform.BUTTON,
            Platform.SWITCH,
            Platform.LIGHT,
            Platform.COVER,
            Platform.MEDIA_PLAYER,
            Platform.FAN,
            Platform.CLIMATE,
            Platform.HUMIDIFIER,
            Platform.LOCK,
        ],
    ):
        await async_setup_component(hass, core.DOMAIN, {})
        for component in [button, switch, light, cover, media_player, fan, climate, humidifier, lock]:
            await async_setup_component(hass, component.DOMAIN, {component.DOMAIN: [{"platform": "demo"}]})
        await hass.async_block_till_done()

    # for x in sorted(hass.states.async_all(), key=lambda e: e.entity_id):
    #     d = Device(hass, BASIC_CONFIG, x.entity_id, x)
    #     l = list((c.type.value, c.instance.value) for c in d.get_capabilities())
    #     print(f"state = hass.states.get('{x.entity_id}')")
    #     print(f"device = Device(hass, BASIC_CONFIG, state.entity_id, state)")
    #     if d.type is None:
    #         print(f"assert device.type is None")
    #     else:
    #         print(f"assert device.type == '{d.type.value}'")
    #     print(f"capabilities = list((c.type, c.instance) for c in device.get_capabilities())")
    #     print(f"assert capabilities == {l}")
    #     print()

    state = hass.states.get("button.push")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.other"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("climate.ecobee")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.thermostat"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "thermostat"),
        ("devices.capabilities.mode", "swing"),
        ("devices.capabilities.mode", "fan_speed"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("climate.heatpump")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.thermostat"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "thermostat"),
        ("devices.capabilities.range", "temperature"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("climate.hvac")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.thermostat"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "thermostat"),
        ("devices.capabilities.mode", "swing"),
        ("devices.capabilities.mode", "fan_speed"),
        ("devices.capabilities.range", "temperature"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("cover.garage_door")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable.curtain"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("cover.hall_window")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable.curtain"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "open"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("cover.kitchen_window")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable.curtain"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.toggle", "pause"), ("devices.capabilities.on_off", "on")]

    state = hass.states.get("cover.living_room_window")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable.curtain"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "open"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("cover.pergola_roof")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable.curtain"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("fan.ceiling_fan")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.fan"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.mode", "fan_speed"), ("devices.capabilities.on_off", "on")]

    state = hass.states.get("fan.living_room_fan")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.fan"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "fan_speed"),
        ("devices.capabilities.toggle", "oscillation"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("fan.percentage_full_fan")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.fan"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "fan_speed"),
        ("devices.capabilities.toggle", "oscillation"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("fan.percentage_limited_fan")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.fan"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.mode", "fan_speed"), ("devices.capabilities.on_off", "on")]

    state = hass.states.get("fan.preset_only_limited_fan")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.fan"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.mode", "fan_speed"), ("devices.capabilities.on_off", "on")]

    state = hass.states.get("humidifier.dehumidifier")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.humidifier"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.range", "humidity"), ("devices.capabilities.on_off", "on")]

    state = hass.states.get("humidifier.humidifier")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.humidifier"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.range", "humidity"), ("devices.capabilities.on_off", "on")]

    state = hass.states.get("humidifier.hygrostat")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.humidifier"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "program"),
        ("devices.capabilities.range", "humidity"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("light.bed_light")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.light"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.color_setting", "base"),
        ("devices.capabilities.color_setting", "rgb"),
        ("devices.capabilities.color_setting", "temperature_k"),
        ("devices.capabilities.color_setting", "scene"),
        ("devices.capabilities.range", "brightness"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("light.ceiling_lights")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.light"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.color_setting", "base"),
        ("devices.capabilities.color_setting", "rgb"),
        ("devices.capabilities.color_setting", "temperature_k"),
        ("devices.capabilities.range", "brightness"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("light.entrance_color_white_lights")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.light"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.color_setting", "base"),
        ("devices.capabilities.color_setting", "rgb"),
        ("devices.capabilities.color_setting", "temperature_k"),
        ("devices.capabilities.range", "brightness"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("light.kitchen_lights")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.light"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.color_setting", "base"),
        ("devices.capabilities.color_setting", "rgb"),
        ("devices.capabilities.color_setting", "temperature_k"),
        ("devices.capabilities.range", "brightness"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("light.living_room_rgbww_lights")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.light"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.color_setting", "base"),
        ("devices.capabilities.color_setting", "rgb"),
        ("devices.capabilities.range", "brightness"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("light.office_rgbw_lights")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.light"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.color_setting", "base"),
        ("devices.capabilities.color_setting", "rgb"),
        ("devices.capabilities.color_setting", "temperature_k"),
        ("devices.capabilities.range", "brightness"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("lock.front_door")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("lock.kitchen_door")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("lock.openable_lock")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("lock.poorly_installed_door")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.openable"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("media_player.bedroom")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.bedroom_2")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.kitchen")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.kitchen_2")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.living_room")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.living_room_2")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.lounge_room")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device.tv"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "input_source"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.lounge_room_2")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device.tv"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.mode", "input_source"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.walkman")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("media_player.walkman_2")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.media_device"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [
        ("devices.capabilities.range", "volume"),
        ("devices.capabilities.range", "channel"),
        ("devices.capabilities.toggle", "mute"),
        ("devices.capabilities.toggle", "pause"),
        ("devices.capabilities.on_off", "on"),
    ]

    state = hass.states.get("switch.ac")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.socket"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("switch.decorative_lights")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type == "devices.types.switch"
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == [("devices.capabilities.on_off", "on")]

    state = hass.states.get("zone.home")
    device = Device(hass, BASIC_CONFIG, state.entity_id, state)
    assert device.type is None
    capabilities = list((c.type, c.instance) for c in device.get_capabilities())
    assert capabilities == []
