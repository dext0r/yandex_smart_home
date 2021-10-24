from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Event

from custom_components.yandex_smart_home.logbook import EVENT_EXECUTE_ACTION, async_describe_events


def test_async_describe_events(hass):
    def _test_describe(_, __, f):
        event = Event(event_type=EVENT_EXECUTE_ACTION, data={ATTR_ENTITY_ID: 'sensor.test'})
        assert f(event) == {
            'name': 'Умный дом Яндекса',
            'message': 'отправил команду на изменения состояния',
            'entity_id': 'sensor.test'
        }

    async_describe_events(hass, _test_describe)
