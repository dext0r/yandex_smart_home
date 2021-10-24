"""Describe logbook events."""
import logging

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import callback

from .const import DOMAIN, EVENT_EXECUTE_ACTION

_LOGGER = logging.getLogger(__name__)


@callback
def async_describe_events(_, async_describe_event):
    """Describe logbook events."""

    @callback
    def async_describe_logbook_event(event):
        """Describe a logbook event."""
        return {
            'name': 'Умный дом Яндекса',
            'message': 'отправил команду на изменения состояния',
            'entity_id': event.data.get(ATTR_ENTITY_ID),
        }

    async_describe_event(DOMAIN, EVENT_EXECUTE_ACTION, async_describe_logbook_event)
