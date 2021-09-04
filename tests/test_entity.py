from homeassistant.components.media_player import DEVICE_CLASS_TV
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import State
import pytest
from pytest_homeassistant_custom_component.common import mock_area_registry, mock_device_registry, mock_registry

from custom_components.yandex_smart_home.const import (
    TYPE_MEDIA_DEVICE,
    TYPE_MEDIA_DEVICE_TV,
    TYPE_OPENABLE,
    TYPE_SWITCH,
)
from custom_components.yandex_smart_home.entity import YandexEntity

from . import BASIC_CONFIG, MockConfig


@pytest.fixture
def registries(hass):
    from types import SimpleNamespace

    ns = SimpleNamespace()
    ns.entity = mock_registry(hass)
    ns.device = mock_device_registry(hass)
    ns.area = mock_area_registry(hass)
    return ns


async def test_yandex_entity_serialize_state(hass, registries):
    ent_reg, dev_reg, area_reg = registries.entity, registries.device, registries.area

    entity_unavailable = YandexEntity(hass, BASIC_CONFIG, State('switch.test', STATE_UNAVAILABLE))
    assert await entity_unavailable.devices_serialize(ent_reg, dev_reg, area_reg) is None

    entity_no_caps = YandexEntity(hass, BASIC_CONFIG, State('sensor.test', '13'))
    assert await entity_no_caps.devices_serialize(ent_reg, dev_reg, area_reg) is None

    entity = YandexEntity(hass, BASIC_CONFIG, State('switch.test_1', STATE_ON))
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_1'
    assert s['name'] == 'test 1'
    assert s['type'] == TYPE_SWITCH
    assert 'room' not in s
    assert s['device_info'] == {'model': 'switch.test_1'}

    config = MockConfig(entity_config={
        'switch.test_1': {
            'name': 'Тест',
            'type': TYPE_OPENABLE,
            'room': 'Кухня'
        }
    })
    entity = YandexEntity(hass, config, State('switch.test_1', STATE_ON))
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_1'
    assert s['name'] == 'Тест'
    assert s['room'] == 'Кухня'
    assert s['type'] == TYPE_OPENABLE


async def test_yandex_entity_serialize_device(hass, registries):
    ent_reg, dev_reg, area_reg = registries.entity, registries.device, registries.area
    area_kitchen = area_reg.async_get_or_create('Кухня')
    area_closet = area_reg.async_get_or_create('Кладовка')

    state = State('switch.test_1', STATE_ON)
    device = dev_reg.async_get_or_create(
        manufacturer='Acme Inc.',
        identifiers={'test_1'},
        config_entry_id='test_1',
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
        sw_version='0.1',
        identifiers={'test_2'},
        config_entry_id='test_2',
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
        'sw_version': '0.1'
    }

    config = MockConfig(entity_config={
        'switch.test_2': {
            'room': 'Комната'
        }
    })
    entity = YandexEntity(hass, config, state)
    s = await entity.devices_serialize(ent_reg, dev_reg, area_reg)
    assert s['id'] == 'switch.test_2'
    assert s['room'] == 'Комната'

    state = State('switch.test_3', STATE_ON)
    device = dev_reg.async_get_or_create(
        identifiers={'test_3'},
        config_entry_id='test_3',
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
        should_expose=lambda s: s != 'switch.not_expose'
    )
    entity = YandexEntity(hass, config, State('switch.test', STATE_ON))
    assert entity.should_expose

    entity = YandexEntity(hass, config, State('switch.not_expose', STATE_ON))
    assert not entity.should_expose


async def test_yandex_entity_device_type(hass):
    state = State('media_player.tv', STATE_ON)
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == TYPE_MEDIA_DEVICE

    state = State('media_player.tv', STATE_ON, attributes={
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TV
    })
    entity = YandexEntity(hass, BASIC_CONFIG, state)
    assert entity.yandex_device_type == TYPE_MEDIA_DEVICE_TV
