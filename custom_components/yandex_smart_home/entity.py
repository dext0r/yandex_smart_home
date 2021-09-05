from __future__ import annotations
from typing import Optional
from typing import Any

from homeassistant.core import HomeAssistant, callback, State
from homeassistant.const import (
    CONF_NAME, STATE_UNAVAILABLE, ATTR_SUPPORTED_FEATURES,
    ATTR_DEVICE_CLASS, CLOUD_NEVER_EXPOSED_ENTITIES
)
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers.device_registry import DeviceRegistry, DeviceEntry
from homeassistant.helpers.area_registry import AreaRegistry, AreaEntry

from . import prop, const
from .helpers import Config, RequestData
from .capability import CustomModeCapability, CustomToggleCapability, CustomRangeCapability, CAPABILITIES, _Capability
from .prop import _Property, CustomEntityProperty
from .const import (
    DEVICE_CLASS_TO_YANDEX_TYPES, DOMAIN_TO_YANDEX_TYPES,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE, ERR_DEVICE_UNREACHABLE,
    ERR_INVALID_VALUE, CONF_ROOM, CONF_TYPE, CONF_ENTITY_PROPERTIES
)
from .error import SmartHomeError


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
        entity_config = self.config.get_entity_config(state.entity_id)

        for capability_class, config_key in (
                (CustomModeCapability, const.CONF_ENTITY_CUSTOM_MODES),
                (CustomToggleCapability, const.CONF_ENTITY_CUSTOM_TOGGLES),
                (CustomRangeCapability, const.CONF_ENTITY_CUSTOM_RANGES)):
            if config_key in entity_config:
                for instance in entity_config[config_key]:
                    capability = capability_class(
                        self.hass, self.config, state, instance, entity_config[config_key][instance]
                    )

                    if capability.supported(state.domain, features, entity_config, state.attributes):
                        self._capabilities.append(capability)

        for Capability in CAPABILITIES:
            capability = Capability(self.hass, self.config, state)
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
                prop.CustomEntityProperty(self.hass, self.config, state, property_config)
            )

        for Property in prop.PROPERTIES:
            entity_property = Property(self.hass, self.config, state)
            if entity_property.supported(state.domain, features, entity_config, state.attributes) and \
                    entity_property.instance not in [p.instance for p in self._properties]:
                self._properties.append(entity_property)

        return self._properties

    @property
    def should_expose(self) -> bool:
        """If device should be exposed."""
        if self.entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        if not self.yandex_device_type:
            return False

        return self.config.should_expose(self.entity_id)

    @property
    def yandex_device_type(self) -> str | None:
        """Yandex type based on domain and device class."""
        device_class = self.state.attributes.get(ATTR_DEVICE_CLASS)
        domain = self.state.domain
        return DEVICE_CLASS_TO_YANDEX_TYPES.get((domain, device_class), DOMAIN_TO_YANDEX_TYPES.get(domain))

    async def devices_serialize(self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry,
                                area_reg: AreaRegistry):
        """Serialize entity for a devices response.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/get-devices-docpage/
        """
        if self.state.state == STATE_UNAVAILABLE:
            return None

        if not self.capabilities() and not self.properties():
            return None

        entity_config = self.config.get_entity_config(self.entity_id)
        name = (entity_config.get(CONF_NAME) or self.state.name).strip() or self.entity_id
        entity_entry, device_entry = await self._get_entity_and_device(ent_reg, dev_reg)

        device = {
            'id': self.entity_id,
            'name': name,
            'type': entity_config.get(CONF_TYPE, self.yandex_device_type),
            'capabilities': [],
            'properties': [],
            'device_info': {
                'model': self.entity_id,
            },
        }

        room = entity_config.get(CONF_ROOM)
        if room:
            device['room'] = room
        else:
            area = await self._get_area(entity_entry, device_entry, area_reg)
            if area and area.name:
                device['room'] = area.name

        if device_entry:
            if device_entry.manufacturer:
                device['device_info']['manufacturer'] = device_entry.manufacturer
            if device_entry.model:
                device['device_info']['model'] = f'{device_entry.model} | {self.entity_id}'
            if device_entry.sw_version:
                device['device_info']['sw_version'] = device_entry.sw_version

        for item in [c.description() for c in self.capabilities()]:
            if item not in device['capabilities']:
                device['capabilities'].append(item)

        for item in [p.description() for p in self.properties()]:
            if item not in device['properties']:
                device['properties'].append(item)

        return device

    @callback
    def query_serialize(self) -> dict[str, Any]:
        """Serialize entity for a query response.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-devices-query-docpage/
        """
        if self.state.state == STATE_UNAVAILABLE:
            return {
                'id': self.entity_id, 'error_code': ERR_DEVICE_UNREACHABLE
            }

        device = {
            'id': self.entity_id,
            'capabilities': [],
            'properties': [],
        }

        for item in [c for c in self.capabilities() if c.retrievable]:
            state = item.get_state()
            if state is not None:
                device['capabilities'].append(state)

        for item in [p for p in self.properties() if p.retrievable]:
            state = item.get_state()
            if state is not None:
                device['properties'].append(state)

        return device

    @callback
    def notification_serialize(self, event_entity_id: str) -> dict[str, Any]:
        """Serialize entity for a notification."""
        if self.state.state == STATE_UNAVAILABLE:
            return {'id': self.state.entity_id, 'error_code': ERR_DEVICE_UNREACHABLE}

        device = {
            'id': self.entity_id,
            'capabilities': [],
            'properties': [],
        }

        for item in [c for c in self.capabilities() if c.reportable]:
            state = item.get_state()
            if state is not None:
                device['capabilities'].append(state)

        for item in [c for c in self.properties() if c.reportable]:
            if isinstance(item, CustomEntityProperty):
                if item.property_entity_id != event_entity_id:
                    continue
            elif item.state.entity_id != event_entity_id:
                continue

            state = item.get_state()
            if state is not None:
                device['properties'].append(state)

        return device

    async def execute(self,
                      data: RequestData,
                      capability_type: str,
                      instance: str,
                      state: dict[str, str | int | bool]) -> None:
        """Execute action.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-action-docpage/
        """
        target_capabilities = [c for c in self.capabilities() if c.type == capability_type and c.instance == instance]
        if not target_capabilities:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unable to execute request for instance {capability_type}.{instance} of {self.state.entity_id}'
            )

        for capability in target_capabilities:
            await capability.set_state(data, state)

    async def _get_entity_and_device(self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry) -> \
            tuple[RegistryEntry, DeviceEntry] | tuple[None, None]:
        """Fetch the entity and device entries."""
        entity_entry = ent_reg.async_get(self.entity_id)
        if not entity_entry:
            return None, None

        device_entry = dev_reg.devices.get(entity_entry.device_id)
        return entity_entry, device_entry

    @staticmethod
    async def _get_area(entity_entry: RegistryEntry | None, device_entry: DeviceEntry | None,
                        area_reg: AreaRegistry) -> AreaEntry | None:
        """Calculate the area for an entity."""
        if entity_entry and entity_entry.area_id:
            area_id = entity_entry.area_id
        elif device_entry and device_entry.area_id:
            area_id = device_entry.area_id
        else:
            return None

        return area_reg.areas.get(area_id)
