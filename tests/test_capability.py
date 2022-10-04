from __future__ import annotations

from typing import Any, Optional

from homeassistant.components import button, climate, cover, fan, humidifier, light, lock, media_player, switch
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component

from custom_components.yandex_smart_home.capability import CAPABILITIES, AbstractCapability
from custom_components.yandex_smart_home.capability_mode import ModeCapability
from custom_components.yandex_smart_home.capability_range import RangeCapability
from custom_components.yandex_smart_home.entity import YandexEntity
from custom_components.yandex_smart_home.helpers import Config

from . import BASIC_CONFIG


def get_capabilities(hass: HomeAssistant, config: Config, state: State,
                     capability_type: str, instance: str) -> list[AbstractCapability]:
    caps = []

    for Capability in CAPABILITIES:
        capability = Capability(hass, config, state)

        if capability.type != capability_type or capability.instance != instance:
            continue

        if capability.supported():
            caps.append(capability)

    return caps


def get_exact_one_capability(hass: HomeAssistant, config: Config, state: State,
                             capability_type: str,
                             instance: str) -> AbstractCapability | RangeCapability | ModeCapability:

    caps = get_capabilities(hass, config, state, capability_type, instance)
    assert len(caps) == 1
    return caps[0]


def assert_exact_one_capability(hass: HomeAssistant, config: Config, state: State,
                                capability_type: str, instance: str):
    assert len(get_capabilities(hass, config, state, capability_type, instance)) == 1


def assert_no_capabilities(hass: HomeAssistant, config: Config, state: State,
                           capability_type: str, instance: str):
    assert len(get_capabilities(hass, config, state, capability_type, instance)) == 0


def test_capability(hass):
    class TestCapabilityWithParametersNoValue(AbstractCapability):
        type = 'test_type'
        instance = 'test_instance'

        def supported(self) -> bool:
            return True

        def parameters(self) -> Optional[dict[str, Any]]:
            return {'param': 'value'}

        def get_value(self):
            return None

        async def set_state(self, data, state):
            pass

    cap = TestCapabilityWithParametersNoValue(hass, BASIC_CONFIG, State('switch.test', STATE_ON))
    assert cap.description() == {
        'type': 'test_type',
        'retrievable': True,
        'reportable': True,
        'parameters': {
            'param': 'value',
        }
    }
    assert cap.get_state() is None

    class TestCapability(AbstractCapability):
        type = 'test_type'
        instance = 'test_instance'

        def supported(self) -> bool:
            return True

        def parameters(self) -> Optional[dict[str, Any]]:
            return None

        def get_value(self):
            return 'v'

        async def set_state(self, data, state):
            pass

    cap = TestCapability(hass, BASIC_CONFIG, State('switch.test', STATE_ON))
    assert cap.description() == {
        'type': 'test_type',
        'retrievable': True,
        'reportable': True,
    }
    assert cap.get_state() == {
        'type': 'test_type',
        'state': {
            'instance': 'test_instance',
            'value': 'v',
        }
    }


async def test_capability_demo_platform(hass):
    components = [button, switch, light, cover, media_player, fan, climate, humidifier, lock]

    for component in components:
        await async_setup_component(
            hass, component.DOMAIN, {component.DOMAIN: [{'platform': 'demo'}]}
        )
    await hass.async_block_till_done()

    # for x in sorted(hass.states.async_all(), key=lambda e: e.entity_id):
    #     e = YandexEntity(hass, BASIC_CONFIG, x)
    #     l = list((c.type, c.instance) for c in e.capabilities())
    #     print(f'state = hass.states.get(\'{x.entity_id}\')')
    #     print(f'entity = YandexEntity(hass, BASIC_CONFIG, state)')
    #     print(f'assert entity.yandex_device_type == \'{e.yandex_device_type}\'')
    #     print(f'capabilities = list((c.type, c.instance) for c in entity.capabilities())')
    #     print(f'assert capabilities == {l}')
    #     print()

    state = hass.states.get('button.push')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.other'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('climate.ecobee')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.thermostat'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'thermostat'), ('devices.capabilities.mode', 'swing'),
                            ('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('climate.heatpump')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.thermostat'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'thermostat'), ('devices.capabilities.range', 'temperature'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('climate.hvac')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.thermostat'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'thermostat'), ('devices.capabilities.mode', 'swing'),
                            ('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.range', 'temperature'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('cover.garage_door')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable.curtain'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('cover.hall_window')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable.curtain'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'open'), ('devices.capabilities.toggle', 'pause'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('cover.kitchen_window')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable.curtain'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.toggle', 'pause'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('cover.living_room_window')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable.curtain'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'open'), ('devices.capabilities.toggle', 'pause'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('cover.pergola_roof')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable.curtain'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('fan.ceiling_fan')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.fan'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('fan.living_room_fan')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.fan'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.toggle', 'oscillation'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('fan.percentage_full_fan')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.fan'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.toggle', 'oscillation'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('fan.percentage_limited_fan')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.fan'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('fan.preset_only_limited_fan')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.fan'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'fan_speed'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('humidifier.dehumidifier')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.humidifier'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'humidity'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('humidifier.humidifier')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.humidifier'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'humidity'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('humidifier.hygrostat')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.humidifier'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'program'), ('devices.capabilities.range', 'humidity'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('light.bed_light')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.light'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.color_setting', 'rgb'),
                            ('devices.capabilities.color_setting', 'temperature_k'),
                            ('devices.capabilities.range', 'brightness'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('light.ceiling_lights')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.light'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.color_setting', 'rgb'),
                            ('devices.capabilities.color_setting', 'temperature_k'),
                            ('devices.capabilities.range', 'brightness'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('light.entrance_color_white_lights')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.light'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.color_setting', 'rgb'),
                            ('devices.capabilities.color_setting', 'temperature_k'),
                            ('devices.capabilities.range', 'brightness'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('light.kitchen_lights')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.light'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.color_setting', 'rgb'),
                            ('devices.capabilities.color_setting', 'temperature_k'),
                            ('devices.capabilities.range', 'brightness'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('light.living_room_rgbww_lights')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.light'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.color_setting', 'rgb'), ('devices.capabilities.range', 'brightness'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('light.office_rgbw_lights')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.light'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.color_setting', 'rgb'),
                            ('devices.capabilities.color_setting', 'temperature_k'),
                            ('devices.capabilities.range', 'brightness'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('lock.front_door')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('lock.kitchen_door')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('lock.openable_lock')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('lock.poorly_installed_door')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.openable'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('media_player.bedroom')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.media_device'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'volume'), ('devices.capabilities.range', 'channel'),
                            ('devices.capabilities.toggle', 'mute'), ('devices.capabilities.toggle', 'pause'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('media_player.kitchen')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.media_device'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'volume'), ('devices.capabilities.range', 'channel'),
                            ('devices.capabilities.toggle', 'mute'), ('devices.capabilities.toggle', 'pause'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('media_player.living_room')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.media_device'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'volume'), ('devices.capabilities.range', 'channel'),
                            ('devices.capabilities.toggle', 'mute'), ('devices.capabilities.toggle', 'pause'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('media_player.lounge_room')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    if MAJOR_VERSION == 2022 and MINOR_VERSION >= 10:
        assert entity.yandex_device_type == 'devices.types.media_device.tv'
    else:
        assert entity.yandex_device_type == 'devices.types.media_device'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.mode', 'input_source'), ('devices.capabilities.range', 'channel'),
                            ('devices.capabilities.toggle', 'pause'), ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('media_player.walkman')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.media_device'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.range', 'volume'), ('devices.capabilities.range', 'channel'),
                            ('devices.capabilities.toggle', 'mute'), ('devices.capabilities.toggle', 'pause'),
                            ('devices.capabilities.on_off', 'on')]

    state = hass.states.get('switch.ac')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.socket'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]

    state = hass.states.get('switch.decorative_lights')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == 'devices.types.switch'
    capabilities = list((c.type, c.instance) for c in entity.capabilities())
    assert capabilities == [('devices.capabilities.on_off', 'on')]
