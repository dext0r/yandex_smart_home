"""Helper classes for Yandex Smart Home integration."""
from asyncio import gather
from collections.abc import Mapping

from homeassistant.core import Context, callback
from homeassistant.const import (
    CONF_NAME, STATE_UNAVAILABLE, ATTR_SUPPORTED_FEATURES,
    ATTR_DEVICE_CLASS
)

from . import capability
from .const import (
    DEVICE_CLASS_TO_YANDEX_TYPES, DOMAIN_TO_YANDEX_TYPES,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE, ERR_DEVICE_UNREACHABLE,
    ERR_INVALID_VALUE, CONF_ROOM,
)
from .error import SmartHomeError


class Config:
    """Hold the configuration for Yandex Smart Home."""

    def __init__(self, should_expose, entity_config=None):
        """Initialize the configuration."""
        self.should_expose = should_expose
        self.entity_config = entity_config or {}


class RequestData:
    """Hold data associated with a particular request."""

    def __init__(self, config, user_id, request_id):
        """Initialize the request data."""
        self.config = config
        self.request_id = request_id
        self.context = Context(user_id=user_id)


def get_yandex_type(domain, device_class):
    """Yandex type based on domain and device class."""
    yandex_type = DEVICE_CLASS_TO_YANDEX_TYPES.get((domain, device_class))

    return yandex_type if yandex_type is not None else \
        DOMAIN_TO_YANDEX_TYPES[domain]


class YandexEntity:
    """Adaptation of Entity expressed in Yandex's terms."""

    def __init__(self, hass, config, state):
        """Initialize a Yandex Smart Home entity."""
        self.hass = hass
        self.config = config
        self.state = state
        self._capabilities = None

    @property
    def entity_id(self):
        """Return entity ID."""
        return self.state.entity_id

    @callback
    def capabilities(self):
        """Return capabilities for entity."""
        if self._capabilities is not None:
            return self._capabilities

        state = self.state
        domain = state.domain
        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        self._capabilities = [
            Capability(self.hass, state, self.config)
            for Capability in capability.CAPABILITIES
            if Capability.supported(domain, features)
        ]
        return self._capabilities

    async def devices_serialize(self):
        """Serialize entity for a devices response.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/get-devices-docpage/
        """
        state = self.state

        # When a state is unavailable, the attributes that describe
        # capabilities will be stripped. For example, a light entity will miss
        # the min/max mireds. Therefore they will be excluded from a sync.
        if state.state == STATE_UNAVAILABLE:
            return None

        entity_config = self.config.entity_config.get(state.entity_id, {})
        name = (entity_config.get(CONF_NAME) or state.name).strip()
        domain = state.domain
        device_class = state.attributes.get(ATTR_DEVICE_CLASS)

        # If an empty string
        if not name:
            return None

        capabilities = self.capabilities()

        # Found no supported traits for this entity
        if not capabilities:
            return None

        device_type = get_yandex_type(domain, device_class)

        device = {
            'id': state.entity_id,
            'name': name,
            'type': device_type,
            'capabilities': [],
        }

        for cpb in capabilities:
            description = cpb.description()
            if description not in device['capabilities']:
                device['capabilities'].append(description)

        room = entity_config.get(CONF_ROOM)
        if room:
            device['room'] = room
            return device

        dev_reg, ent_reg, area_reg = await gather(
            self.hass.helpers.device_registry.async_get_registry(),
            self.hass.helpers.entity_registry.async_get_registry(),
            self.hass.helpers.area_registry.async_get_registry(),
        )

        entity_entry = ent_reg.async_get(state.entity_id)
        if not (entity_entry and entity_entry.device_id):
            return device

        device_entry = dev_reg.devices.get(entity_entry.device_id)
        if not (device_entry and device_entry.area_id):
            return device

        area_entry = area_reg.areas.get(device_entry.area_id)
        if area_entry and area_entry.name:
            device['room'] = area_entry.name

        return device

    @callback
    def query_serialize(self):
        """Serialize entity for a query response.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-devices-query-docpage/
        """
        state = self.state

        if state.state == STATE_UNAVAILABLE:
            return {'error_code': ERR_DEVICE_UNREACHABLE}

        capabilities = []

        for cpb in self.capabilities():
            if cpb.retrievable:
                capabilities.append(cpb.get_state())

        return {
            'id': state.entity_id,
            'capabilities': capabilities,
        }

    async def execute(self, data, capability_type, state):
        """Execute action.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-action-docpage/
        """
        executed = False
        if state is None or 'instance' not in state:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                "Invalid request: no 'instance' field in state {} / {}"
                .format(capability_type, self.state.entity_id))

        instance = state['instance']
        for cpb in self.capabilities():
            if capability_type == cpb.type and instance == cpb.instance:
                await cpb.set_state(data, state)
                executed = True
                break

        if not executed:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                "Unable to execute {} / {} for {}".format(capability_type,
                                                          instance,
                                                          self.state.entity_id
                                                          ))

    @callback
    def async_update(self):
        """Update the entity with latest info from Home Assistant."""
        self.state = self.hass.states.get(self.entity_id)

        if self._capabilities is None:
            return

        for trt in self._capabilities:
            trt.state = self.state


def deep_update(target, source):
    """Update a nested dictionary with another nested dictionary."""
    for key, value in source.items():
        if isinstance(value, Mapping):
            target[key] = deep_update(target.get(key, {}), value)
        else:
            target[key] = value
    return target
