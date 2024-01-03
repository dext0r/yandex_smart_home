from __future__ import annotations

from unittest.mock import patch

from homeassistant.components import media_player, switch
from homeassistant.components.binary_sensor import DEVICE_CLASS_DOOR
from homeassistant.components.demo.light import DemoLight
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    MAJOR_VERSION,
    MINOR_VERSION,
    PERCENTAGE,
    SERVICE_TURN_OFF,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    TEMP_CELSIUS,
)
from homeassistant.core import State
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
    mock_area_registry,
    mock_device_registry,
    mock_registry,
)

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.capability_color import RgbCapability, TemperatureKCapability
from custom_components.yandex_smart_home.capability_custom import (
    CustomModeCapability,
    CustomRangeCapability,
    CustomToggleCapability,
)
from custom_components.yandex_smart_home.capability_onoff import CAPABILITIES_ONOFF, OnOffCapabilityBasic
from custom_components.yandex_smart_home.capability_range import BrightnessCapability
from custom_components.yandex_smart_home.capability_toggle import CAPABILITIES_TOGGLE, ToggleCapability
from custom_components.yandex_smart_home.const import (
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_NAME,
    CONF_ROOM,
    CONF_TYPE,
    ERR_DEVICE_UNREACHABLE,
    ERR_INTERNAL_ERROR,
    ERR_INVALID_ACTION,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    TOGGLE_INSTANCE_PAUSE,
)
from custom_components.yandex_smart_home.entity import YandexEntity, YandexEntityCallbackState
from custom_components.yandex_smart_home.error import SmartHomeError
from custom_components.yandex_smart_home.prop_custom import (
    CustomEntityProperty,
    CustomEventEntityProperty,
    CustomFloatEntityProperty,
)
from custom_components.yandex_smart_home.prop_event import ContactProperty
from custom_components.yandex_smart_home.prop_float import TemperatureProperty, VoltageProperty

from . import BASIC_CONFIG, BASIC_DATA, MockConfig, generate_entity_filter


@pytest.fixture
def registries(hass):
    from types import SimpleNamespace

    ns = SimpleNamespace()
    ns.entity = mock_registry(hass)
    ns.device = mock_device_registry(hass)
    ns.area = mock_area_registry(hass)
    return ns


async def test_yandex_entity_duplicate_capabilities(hass):
    class MockCapability(OnOffCapabilityBasic):
        def supported(self) -> bool:
            return True

    state = State('switch.test', STATE_ON)
    entity = YandexEntity(hass, BASIC_CONFIG, state)

    with patch('custom_components.yandex_smart_home.capability.CAPABILITIES', [MockCapability, MockCapability]):
        assert len(entity.capabilities()) == 1
        assert isinstance(entity.capabilities()[0], MockCapability)


async def test_yandex_entity_capabilities(hass):
    if (MAJOR_VERSION == 2023 and MINOR_VERSION >= 7) or MAJOR_VERSION >= 2024:
        light = DemoLight(
            'test_light',
            'Light',
            available=True,
            state=True,
        )
        light._attr_name = 'Kitchen Light'
    else:
        light = DemoLight(
            unique_id='test_light',
            name='Light',
            available=True,
            state=True,
        )
    light.hass = hass
    light.entity_id = 'light.test'
    await light.async_update_ha_state()

    state = hass.states.get('light.test')
    state_sensor = State('sensor.test', '33')
    config = MockConfig(
        entity_config={
            light.entity_id: {
                const.CONF_ENTITY_MODE_MAP: {
                    const.MODE_INSTANCE_DISHWASHING: {
                        const.MODE_INSTANCE_MODE_ECO: ['']
                    }
                },
                const.CONF_ENTITY_CUSTOM_RANGES: {
                    const.RANGE_INSTANCE_HUMIDITY: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: state_sensor.entity_id,
                        const.CONF_ENTITY_CUSTOM_RANGE_SET_VALUE: {},
                    }
                },
                const.CONF_ENTITY_CUSTOM_TOGGLES: {
                    const.TOGGLE_INSTANCE_PAUSE: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: state_sensor.entity_id,
                        const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON: {},
                        const.CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF: {},
                    }
                },
                const.CONF_ENTITY_CUSTOM_MODES: {
                    const.MODE_INSTANCE_DISHWASHING: {
                        const.CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: state_sensor.entity_id,
                        const.CONF_ENTITY_CUSTOM_MODE_SET_MODE: {},
                    }
                }
            }
        }
    )
    entity = YandexEntity(hass, config, state)
    assert [type(c) for c in entity.capabilities()] == [
        CustomModeCapability, CustomToggleCapability, CustomRangeCapability,
        RgbCapability, TemperatureKCapability, BrightnessCapability, OnOffCapabilityBasic
    ]


async def test_yandex_entity_duplicate_properties(hass):
    class MockProperty(TemperatureProperty):
        def supported(self) -> bool:
            return True

    state = State('sensor.test', '33')
    entity = YandexEntity(hass, BASIC_CONFIG, state)

    with patch('custom_components.yandex_smart_home.prop.PROPERTIES', [MockProperty, MockProperty]):
        assert len(entity.properties()) == 1
        assert isinstance(entity.properties()[0], MockProperty)


async def test_yandex_entity_properties(hass):
    state = State('sensor.temp', '5', attributes={
        ATTR_UNIT_OF_MEASUREMENT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
    })
    config = MockConfig(
        entity_config={
            state.entity_id: {
                const.CONF_ENTITY_PROPERTIES: [{
                    const.CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_VOLTAGE
                }, {
                    const.CONF_ENTITY_PROPERTY_TYPE: const.EVENT_INSTANCE_BUTTON
                }]
            }
        }
    )
    entity = YandexEntity(hass, config, state)
    assert [type(c) for c in entity.properties()] == [
        CustomFloatEntityProperty, CustomEventEntityProperty, TemperatureProperty
    ]

    state = State('binary_sensor.door', STATE_ON, attributes={
        ATTR_DEVICE_CLASS: DEVICE_CLASS_DOOR,
    })
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert [type(c) for c in entity.properties()] == [
        ContactProperty
    ]


async def test_yandex_entity_devices_serialize_state(hass, registries):
    ent_reg, dev_reg, area_reg = registries.entity, registries.device, registries.area

    entity_unavailable = YandexEntity(hass, BASIC_CONFIG, State('switch.test', STATE_UNAVAILABLE))
    assert await entity_unavailable.devices_serialize(ent_reg, dev_reg, area_reg) is None

    entity_no_caps = YandexEntity(hass, BASIC_CONFIG, State('sensor.test', '13'))
    assert await entity_no_caps.devices_serialize(ent_reg, dev_reg, area_reg) is None

    entity = YandexEntity(hass, BASIC_CONFIG, State('switch.test_1', STATE_ON))
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_1'
    assert s['name'] == 'test 1'
    assert s['type'] == const.TYPE_SWITCH
    assert 'room' not in s
    assert s['device_info'] == {'model': 'switch.test_1'}

    config = MockConfig(entity_config={
        'switch.test_1': {
            CONF_NAME: 'Тест',
            CONF_TYPE: const.TYPE_OPENABLE,
            CONF_ROOM: 'Кухня'
        }
    })
    entity = YandexEntity(hass, config, State('switch.test_1', STATE_ON))
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_1'
    assert s['name'] == 'Тест'
    assert s['room'] == 'Кухня'
    assert s['type'] == const.TYPE_OPENABLE


async def test_yandex_entity_devices_serialize_device(hass, registries):
    ent_reg, dev_reg, area_reg = registries.entity, registries.device, registries.area
    area_kitchen = area_reg.async_get_or_create('Кухня')
    area_closet = area_reg.async_get_or_create('Кладовка')

    config_entry = MockConfigEntry(domain='test', data={})
    config_entry.add_to_hass(hass)

    state = State('switch.test_1', STATE_ON)
    device = dev_reg.async_get_or_create(
        manufacturer='Acme Inc.',
        identifiers={'test_1'},
        config_entry_id=config_entry.entry_id,
    )
    ent_reg.async_get_or_create(
        'switch',
        'test',
        '1',
        device_id=device.id,
    )
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_1'
    assert s['device_info'] == {'model': 'switch.test_1', 'manufacturer': 'Acme Inc.'}

    state = State('switch.test_2', STATE_ON)
    device = dev_reg.async_get_or_create(
        manufacturer='Acme Inc.',
        model='Ultra Switch',
        sw_version=57,
        identifiers={'test_2'},
        config_entry_id=config_entry.entry_id,
    )
    dev_reg.async_update_device(device.id, area_id=area_closet.id)
    ent_reg.async_get_or_create(
        'switch',
        'test',
        '2',
        device_id=device.id,
    )
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_2'
    assert s['room'] == 'Кладовка'
    assert s['device_info'] == {
        'manufacturer': 'Acme Inc.',
        'model': 'Ultra Switch | switch.test_2',
        'sw_version': '57'
    }

    config = MockConfig(entity_config={
        'switch.test_2': {
            CONF_ROOM: 'Комната'
        }
    })
    entity = YandexEntity(hass, config, state)
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_2'
    assert s['room'] == 'Комната'

    state = State('switch.test_3', STATE_ON)
    device = dev_reg.async_get_or_create(
        identifiers={'test_3'},
        config_entry_id=config_entry.entry_id,
    )
    entry = ent_reg.async_get_or_create(
        'switch',
        'test',
        '3',
        device_id=device.id,
    )
    ent_reg.async_update_entity(entry.entity_id, area_id=area_kitchen.id)

    entity = YandexEntity(hass, BASIC_CONFIG, state)
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_3'
    assert s['room'] == 'Кухня'
    assert s['device_info'] == {'model': 'switch.test_3'}


async def test_yandex_entity_should_expose(hass):
    entity = YandexEntity(hass, BASIC_CONFIG, State('group.all_locks', STATE_ON))
    assert not entity.should_expose

    entity = YandexEntity(hass, BASIC_CONFIG, State('fake.unsupported', STATE_ON))
    assert not entity.should_expose

    config = MockConfig(
        entity_filter=generate_entity_filter(exclude_entities=['switch.not_expose'])
    )
    entity = YandexEntity(hass, config, State('switch.test', STATE_ON))
    assert entity.should_expose

    entity = YandexEntity(hass, config, State('switch.not_expose', STATE_ON))
    assert not entity.should_expose


async def test_yandex_entity_should_expose_empty_filters(hass):
    config = MockConfig(entity_filter=generate_entity_filter())

    entity = YandexEntity(hass, config, State('switch.test', STATE_ON))
    assert not entity.should_expose


async def test_yandex_entity_device_type_media_player(hass):
    state = State('media_player.tv', STATE_ON)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == const.TYPE_MEDIA_DEVICE

    state = State('media_player.tv', STATE_ON, attributes={
        ATTR_DEVICE_CLASS: media_player.DEVICE_CLASS_TV
    })
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == const.TYPE_MEDIA_DEVICE_TV

    state = State('media_player.tv', STATE_ON, attributes={
        ATTR_DEVICE_CLASS: media_player.DEVICE_CLASS_RECEIVER
    })
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == const.TYPE_MEDIA_DEVICE_RECIEVER

    state = State('media_player.tv', STATE_ON, attributes={
        ATTR_DEVICE_CLASS: media_player.DEVICE_CLASS_SPEAKER
    })
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == const.TYPE_MEDIA_DEVICE


async def test_yandex_entity_device_type_switch(hass):
    state = State('switch.test', STATE_ON)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == const.TYPE_SWITCH

    state = State('switch.test', STATE_ON, attributes={
        ATTR_DEVICE_CLASS: switch.DEVICE_CLASS_OUTLET
    })
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == const.TYPE_SOCKET


async def test_yandex_entity_device_type(hass):
    state = State('input_number.test', '40')
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type is None

    config = MockConfig(
        entity_config={
            state.entity_id: {
                CONF_TYPE: 'other'
            }
        }
    )
    entity = YandexEntity(hass, config, state)
    assert entity.yandex_device_type == 'other'


async def test_yandex_entity_serialize(hass):
    class PauseCapability(ToggleCapability):
        instance = TOGGLE_INSTANCE_PAUSE

        def supported(self) -> bool:
            return True

        def get_value(self):
            if self.state.state == STATE_UNAVAILABLE:
                return None

            return self.state.state == STATE_ON

        async def set_state(self, *args, **kwargs):
            pass

    state = State('switch.unavailable', STATE_UNAVAILABLE)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.query_serialize() == {'id': state.entity_id, 'error_code': ERR_DEVICE_UNREACHABLE}

    state = State('switch.test', STATE_ON)
    state_pause = State('input_boolean.pause', STATE_OFF)
    cap_onoff = OnOffCapabilityBasic(hass, BASIC_CONFIG, state)
    cap_pause = PauseCapability(hass, BASIC_CONFIG, state_pause)

    state_temp = State('sensor.temp', '5', attributes={
        ATTR_UNIT_OF_MEASUREMENT: TEMP_CELSIUS,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
    })
    state_humidity = State('sensor.humidity', '95', attributes={
        ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_HUMIDITY,
    })
    hass.states.async_set(state_humidity.entity_id, state_humidity.state, state_humidity.attributes)

    state_voltage = State('sensor.voltage', '220', attributes={
        ATTR_UNIT_OF_MEASUREMENT: 'V',
        ATTR_DEVICE_CLASS: DEVICE_CLASS_VOLTAGE,
    })

    prop_temp = TemperatureProperty(hass, BASIC_CONFIG, state_temp)
    prop_humidity_custom = CustomEntityProperty.get(hass, BASIC_CONFIG, state, {
        CONF_ENTITY_PROPERTY_ENTITY: state_humidity.entity_id,
        CONF_ENTITY_PROPERTY_TYPE: const.FLOAT_INSTANCE_HUMIDITY,
    })
    prop_voltage = VoltageProperty(hass, BASIC_CONFIG, state_voltage)

    state_button = State('binary_sensor.button', '', attributes={
        'action': 'click'
    })
    prop_button = CustomEventEntityProperty(hass, BASIC_CONFIG, state, state_button, {
        CONF_ENTITY_PROPERTY_ATTRIBUTE: 'action',
        CONF_ENTITY_PROPERTY_TYPE: const.EVENT_INSTANCE_BUTTON
    })

    entity = YandexEntity(hass, BASIC_CONFIG, state)

    with patch.object(entity, 'capabilities', return_value=[cap_onoff, cap_pause]), patch.object(
        entity, 'properties', return_value=[prop_temp, prop_voltage, prop_humidity_custom, prop_button]
    ):
        assert entity.query_serialize() == {
            'id': 'switch.test',
            'capabilities': [{
                'type': 'devices.capabilities.on_off',
                'state': {'instance': 'on', 'value': True}
            }, {
                'type': 'devices.capabilities.toggle',
                'state': {'instance': 'pause', 'value': False}
            }],
            'properties': [{
                'type': 'devices.properties.float',
                'state': {'instance': 'temperature', 'value': 5.0}
            }, {
                'type': 'devices.properties.float',
                'state': {'instance': 'voltage', 'value': 220.0}
            }, {
                'type': 'devices.properties.float',
                'state': {'instance': 'humidity', 'value': 95.0}
            }]
        }

        # TODO: move to dedicated test
        callback_state = YandexEntityCallbackState(entity, 'switch.test')
        assert callback_state.properties == []
        assert callback_state.capabilities == [{
            'type': 'devices.capabilities.on_off',
            'state': {'instance': 'on', 'value': True}
        }, {
            'type': 'devices.capabilities.toggle',
            'state': {'instance': 'pause', 'value': False}
        }]

        callback_state = YandexEntityCallbackState(entity, 'sensor.voltage')
        assert callback_state.properties == [{
            'type': 'devices.properties.float',
            'state': {'instance': 'voltage', 'value': 220.0}
        }]
        assert callback_state.capabilities == [{
            'type': 'devices.capabilities.on_off',
            'state': {'instance': 'on', 'value': True}
        }, {
            'type': 'devices.capabilities.toggle',
            'state': {'instance': 'pause', 'value': False}
        }]

        callback_state = YandexEntityCallbackState(entity, 'sensor.humidity')
        assert callback_state.properties == [{
            'type': 'devices.properties.float',
            'state': {'instance': 'humidity', 'value': 95.0}
        }]
        assert callback_state.capabilities == [{
            'type': 'devices.capabilities.on_off',
            'state': {'instance': 'on', 'value': True}
        }, {
            'type': 'devices.capabilities.toggle',
            'state': {'instance': 'pause', 'value': False}
        }]

        prop_voltage.reportable = False
        callback_state = YandexEntityCallbackState(entity, 'sensor.voltage')
        assert callback_state.properties == []
        assert callback_state.capabilities == [{
            'type': 'devices.capabilities.on_off',
            'state': {'instance': 'on', 'value': True}
        }, {
            'type': 'devices.capabilities.toggle',
            'state': {'instance': 'pause', 'value': False}
        }]

        prop_voltage.reportable = True

        callback_state = YandexEntityCallbackState(entity, 'binary_sensor.button')
        assert callback_state.properties == [{
            'type': 'devices.properties.event',
            'state': {'instance': 'button', 'value': 'click'}
        }]
        assert callback_state.capabilities == [{
            'type': 'devices.capabilities.on_off',
            'state': {'instance': 'on', 'value': True}
        }, {
            'type': 'devices.capabilities.toggle',
            'state': {'instance': 'pause', 'value': False}
        }]

        cap_pause.retrievable = False
        prop_temp.retrievable = False
        assert entity.query_serialize() == {
            'id': 'switch.test',
            'capabilities': [{
                'type': 'devices.capabilities.on_off',
                'state': {'instance': 'on', 'value': True}
            }],
            'properties': [{
                'type': 'devices.properties.float',
                'state': {'instance': 'voltage', 'value': 220.0}
            }, {
                'type': 'devices.properties.float',
                'state': {'instance': 'humidity', 'value': 95.0}
            }]
        }
        cap_pause.retrievable = True
        prop_temp.retrievable = True

        state_pause.state = STATE_UNAVAILABLE
        state_voltage.state = STATE_UNAVAILABLE
        prop_humidity_custom.property_state.state = STATE_UNAVAILABLE
        assert entity.query_serialize() == {
            'id': 'switch.test',
            'capabilities': [{
                'type': 'devices.capabilities.on_off',
                'state': {'instance': 'on', 'value': True}
            }],
            'properties': [{
                'type': 'devices.properties.float',
                'state': {'instance': 'temperature', 'value': 5.0}
            }]
        }


async def test_yandex_entity_execute(hass):
    state = State('switch.test', STATE_ON)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    with pytest.raises(SmartHomeError) as e:
        await entity.execute(BASIC_DATA, CAPABILITIES_TOGGLE, TOGGLE_INSTANCE_PAUSE, {'value': True})

    assert e.value.code == ERR_NOT_SUPPORTED_IN_CURRENT_MODE

    off_calls = async_mock_service(hass, state.domain, SERVICE_TURN_OFF)
    await entity.execute(BASIC_DATA, CAPABILITIES_ONOFF, 'on', {'value': False})
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_yandex_entity_execute_exception(hass):
    class MockOnOffCapability(OnOffCapabilityBasic):
        async def set_state(self, *args, **kwargs):
            raise Exception('fail set_state')

    class MockBrightnessCapability(BrightnessCapability):
        def supported(self) -> bool:
            return True

        async def set_state(self, *args, **kwargs):
            raise SmartHomeError(ERR_INVALID_ACTION, '')

    state = State('switch.test', STATE_ON)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    with patch('custom_components.yandex_smart_home.capability.CAPABILITIES', [MockOnOffCapability]):
        with pytest.raises(SmartHomeError) as e:
            await entity.execute(BASIC_DATA, MockOnOffCapability.type, MockOnOffCapability.instance, {'value': True})

    assert e.value.code == ERR_INTERNAL_ERROR

    entity = YandexEntity(hass, BASIC_CONFIG, state)
    with patch('custom_components.yandex_smart_home.capability.CAPABILITIES', [MockBrightnessCapability]):
        with pytest.raises(SmartHomeError) as e:
            await entity.execute(BASIC_DATA, MockBrightnessCapability.type,
                                 MockBrightnessCapability.instance, {'value': True})

    assert e.value.code == ERR_INVALID_ACTION


async def test_yandex_entity_callback_state_unavailable(hass):
    state = State('switch.unavailable', STATE_UNAVAILABLE)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    callback_state = YandexEntityCallbackState(entity, state.entity_id)
    assert callback_state.capabilities == []
    assert callback_state.properties == []
    assert not callback_state.should_report
