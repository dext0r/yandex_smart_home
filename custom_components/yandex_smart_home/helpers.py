"""Helper classes for Yandex Smart Home integration."""
from __future__ import annotations
from asyncio import gather
from collections.abc import Mapping
from typing import Optional, Any, Callable

from homeassistant.core import HomeAssistant, Context, callback, State
from homeassistant.const import (
    CONF_NAME, STATE_UNAVAILABLE, ATTR_SUPPORTED_FEATURES,
    ATTR_DEVICE_CLASS, CLOUD_NEVER_EXPOSED_ENTITIES
)
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.device_registry import DeviceRegistry

from . import prop, const
from .capability import CustomModeCapability, CustomToggleCapability, CustomRangeCapability, CAPABILITIES, _Capability
from .const import (
    DEVICE_CLASS_TO_YANDEX_TYPES, DOMAIN_TO_YANDEX_TYPES,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE, ERR_DEVICE_UNREACHABLE,
    ERR_INVALID_VALUE, CONF_ROOM, CONF_TYPE, CONF_ENTITY_PROPERTIES,
    CONF_ENTITY_PROPERTY_ENTITY
)
from .error import SmartHomeError


class Config:
    """Hold the configuration for Yandex Smart Home."""

    def __init__(self, settings: dict[str, Any], notifier: list[dict[str, Any]],
                 should_expose: Callable[[str], bool], entity_config: Optional[dict[str, Any]] = None):
        """Initialize the configuration."""
        self.settings = settings
        self.notifier = notifier
        self.should_expose = should_expose
        self.entity_config = entity_config or {}


class RequestData:
    """Hold data associated with a particular request."""

    def __init__(self, config: Config, user_id: Optional[str], request_id: str):
        """Initialize the request data."""
        self.config = config
        self.request_id = request_id
        self.context = Context(user_id=user_id)


class YandexEntity:
    """Adaptation of Entity expressed in Yandex's terms."""

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a Yandex Smart Home entity."""
        self.hass = hass
        self.config = config
        self.state = state
        self._capabilities: Optional[list[_Capability]] = None
        self._properties = None

    @property
    def entity_id(self):
        """Return entity ID."""
        return self.state.entity_id

    @callback
    def capabilities(self):
        """Return capabilities for entity."""
        if self._capabilities is not None:
            return self._capabilities

        self._capabilities = []
        state = self.state
        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        entity_config = self.config.entity_config.get(state.entity_id, {})

        for capability_class, config_key in (
                (CustomModeCapability, const.CONF_ENTITY_CUSTOM_MODES),
                (CustomToggleCapability, const.CONF_ENTITY_CUSTOM_TOGGLES),
                (CustomRangeCapability, const.CONF_ENTITY_CUSTOM_RANGES)):
            if config_key in entity_config:
                for instance in entity_config[config_key]:
                    capability = capability_class(
                        self.hass, state, entity_config, instance, entity_config[config_key][instance]
                    )

                    if capability.supported(state.domain, features, entity_config, state.attributes):
                        self._capabilities.append(capability)

        for Capability in CAPABILITIES:
            capability = Capability(self.hass, state, entity_config)
            if capability.supported(state.domain, features, entity_config, state.attributes) and \
                    capability.instance not in [c.instance for c in self._capabilities]:
                self._capabilities.append(capability)

        return self._capabilities

    @callback
    def properties(self):
        """Return properties for entity."""
        if self._properties is not None:
            return self._properties

        self._properties = []
        state = self.state
        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        entity_config = self.config.entity_config.get(state.entity_id, {})

        for property_config in entity_config.get(CONF_ENTITY_PROPERTIES, []):
            self._properties.append(
                prop.CustomEntityProperty(self.hass, state, entity_config, property_config)
            )

        for Property in prop.PROPERTIES:
            entity_property = Property(self.hass, state, entity_config)
            if entity_property.supported(state.domain, features, entity_config, state.attributes) and \
                    entity_property.instance not in [p.instance for p in self._properties]:
                self._properties.append(entity_property)

        return self._properties

    @property
    def supported(self) -> bool:
        """Test if device is supported."""
        return bool(self.yandex_device_type)

    @property
    def should_expose(self) -> bool:
        """If device should be exposed."""
        if self.entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        return self.config.should_expose(self.entity_id)

    @property
    def yandex_device_type(self) -> Optional[str]:
        """Yandex type based on domain and device class."""
        device_class = self.state.attributes.get(ATTR_DEVICE_CLASS)
        domain = self.state.domain
        return DEVICE_CLASS_TO_YANDEX_TYPES.get((domain, device_class), DOMAIN_TO_YANDEX_TYPES.get(domain))

    async def devices_serialize(self, entity_reg: EntityRegistry, dev_reg: DeviceRegistry):
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

        # If an empty string
        if not name:
            return None

        capabilities = self.capabilities()
        properties = self.properties()

        # Found no supported capabilities for this entity
        if not capabilities and not properties:
            return None

        entry = entity_reg.async_get(state.entity_id)
        device = dev_reg.async_get(getattr(entry, 'device_id', ''))

        manufacturer = state.entity_id
        model = ''
        if device is DeviceRegistry:
            if device.manufacturer is not None:
                manufacturer += ' | ' + device.manufacturer
            if device.model is not None:
                model = device.model

        device_info = {
            'manufacturer': manufacturer,
            'model': model
        }

        device = {
            'id': state.entity_id,
            'name': name,
            'type': self.yandex_device_type,
            'capabilities': [],
            'properties': [],
            'device_info': device_info,
        }

        for cpb in capabilities:
            description = cpb.description()
            if description not in device['capabilities']:
                device['capabilities'].append(description)

        for ppt in properties:
            description = ppt.description()
            if description not in device['properties']:
                device['properties'].append(description)

        override_type = entity_config.get(CONF_TYPE)
        if override_type:
            device['type'] = override_type

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

        if state is None:
            return {'error_code': ERR_DEVICE_UNREACHABLE}

        if state.state == STATE_UNAVAILABLE:
            return {'id': state.entity_id, 'error_code': ERR_DEVICE_UNREACHABLE}

        capabilities = []
        for cpb in self.capabilities():
            cpb_state = cpb.get_state()
            if cpb.retrievable and cpb_state is not None:
                capabilities.append(cpb_state)

        properties = []
        for ppt in self.properties():
            if ppt.retrievable:
                properties.append(ppt.get_state())

        return {
            'id': state.entity_id,
            'capabilities': capabilities,
            'properties': properties,
        }

    @callback
    def notification_serialize(self, event_entity_id=None):
        """Serialize entity for a notification."""
        state = self.state

        if state is None:
            return {'error_code': ERR_DEVICE_UNREACHABLE}

        if state.state == STATE_UNAVAILABLE:
            return {'id': state.entity_id, 'error_code': ERR_DEVICE_UNREACHABLE}

        capabilities = []
        for cpb in self.capabilities():
            cpb_state = cpb.get_state()
            if cpb.reportable and cpb_state is not None:
                capabilities.append(cpb_state)

        properties = []
        for ppt in self.properties():
            entity_id = ppt.property_config.get(CONF_ENTITY_PROPERTY_ENTITY, None) \
                if hasattr(ppt, 'property_config') and CONF_ENTITY_PROPERTY_ENTITY in ppt.property_config \
                else ppt.state.entity_id
            ppt_state = ppt.get_state()
            if ppt.reportable and ppt_state is not None and event_entity_id == entity_id:
                properties.append(ppt_state)

        return {
            'id': state.entity_id,
            'capabilities': capabilities,
            'properties': properties,
        }

    async def execute(self, data, capability_type, state):
        """Execute action.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-action-docpage/
        """
        executed = False
        if state is None or 'instance' not in state:
            raise SmartHomeError(
                ERR_INVALID_VALUE,
                f'Invalid request: no instance field in state {capability_type} of {self.state.entity_id}'
            )

        instance = state['instance']
        for cpb in self.capabilities():
            if capability_type == cpb.type and instance == cpb.instance:
                await cpb.set_state(data, state)
                executed = True
                break

        if not executed:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unable to execute request for instance {capability_type}.{instance} of {self.state.entity_id}'
            )

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
