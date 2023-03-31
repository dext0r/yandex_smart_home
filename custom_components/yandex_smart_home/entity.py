from __future__ import annotations

import re
from typing import Any

from homeassistant.const import ATTR_DEVICE_CLASS, CLOUD_NEVER_EXPOSED_ENTITIES, CONF_NAME, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.area_registry import AreaEntry, AreaRegistry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers.template import Template

from . import capability as caps, const, prop
from .capability import AbstractCapability
from .capability_custom import CustomModeCapability, CustomRangeCapability, CustomToggleCapability
from .const import (
    CONF_ENTITY_PROPERTIES,
    CONF_ROOM,
    CONF_TYPE,
    DEVICE_CLASS_TO_YANDEX_TYPES,
    DOMAIN_TO_YANDEX_TYPES,
    ERR_DEVICE_UNREACHABLE,
    ERR_INTERNAL_ERROR,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
)
from .error import SmartHomeError, SmartHomeUserError
from .helpers import Config, DeviceActionCapability, RequestData
from .prop import AbstractProperty
from .prop_custom import CustomEntityProperty
from .prop_event import EventProperty


def _alias_priority(text: str) -> (int, str):
    if re.search('[а-яё]', text, flags=re.IGNORECASE):
        return 0, text
    return 1, text


class YandexEntity:
    """Adaptation of Entity expressed in Yandex's terms."""

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a Yandex Smart Home entity."""
        self.hass = hass
        self.state = state

        self._component_config = config
        self._config = config.get_entity_config(self.entity_id)
        self._capabilities: list[AbstractCapability] | None = None
        self._properties: list[AbstractProperty] | None = None

    @property
    def entity_id(self) -> str:
        """Return entity ID."""
        return self.state.entity_id

    @callback
    def capabilities(self) -> list[AbstractCapability]:
        """Return capabilities for entity."""
        if self._capabilities is not None:
            return self._capabilities

        self._capabilities = []
        state = self.state

        for capability_class, config_key in (
                (CustomModeCapability, const.CONF_ENTITY_CUSTOM_MODES),
                (CustomToggleCapability, const.CONF_ENTITY_CUSTOM_TOGGLES),
                (CustomRangeCapability, const.CONF_ENTITY_CUSTOM_RANGES)):
            if config_key in self._config:
                for instance in self._config[config_key]:
                    capability = capability_class(
                        self.hass, self._component_config, state, instance, self._config[config_key][instance]
                    )

                    if capability.supported():
                        self._capabilities.append(capability)

        for Capability in caps.CAPABILITIES:
            capability = Capability(self.hass, self._component_config, state)
            if capability.supported() and capability.instance not in [c.instance for c in self._capabilities]:
                self._capabilities.append(capability)

        return self._capabilities

    @callback
    def properties(self) -> list[AbstractProperty]:
        """Return properties for entity."""
        if self._properties is not None:
            return self._properties

        self._properties = []
        state = self.state

        for property_config in self._config.get(CONF_ENTITY_PROPERTIES, []):
            self._properties.append(
                CustomEntityProperty.get(self.hass, self._component_config, state, property_config)
            )

        for Property in prop.PROPERTIES:
            entity_property = Property(self.hass, self._component_config, state)
            if entity_property.supported():
                if entity_property.instance not in [p.instance for p in self._properties]:
                    self._properties.append(entity_property)

        return self._properties

    @property
    def should_expose(self) -> bool:
        """If device should be exposed."""
        if self.entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        if not self.yandex_device_type:
            return False

        return self._component_config.should_expose(self.entity_id)

    @property
    def yandex_device_type(self) -> str | None:
        """Yandex type based on domain and device class."""
        if CONF_TYPE in self._config:
            return self._config[CONF_TYPE]

        device_class = self.state.attributes.get(ATTR_DEVICE_CLASS)
        domain = self.state.domain
        return DEVICE_CLASS_TO_YANDEX_TYPES.get((domain, device_class), DOMAIN_TO_YANDEX_TYPES.get(domain))

    async def devices_serialize(self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry,
                                area_reg: AreaRegistry) -> dict[str, Any] | None:
        """Serialize entity for a devices response.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/get-devices-docpage/
        """
        if self.state.state == STATE_UNAVAILABLE:
            return None

        if not self.capabilities() and not self.properties():
            return None

        entity_entry, device_entry = await self._get_entity_and_device(ent_reg, dev_reg)
        device = {
            'id': self.entity_id,
            'name': self._get_name(entity_entry).strip(),
            'type': self.yandex_device_type,
            'capabilities': [],
            'properties': [],
            'device_info': {
                'model': self.entity_id,
            },
        }

        if room := self._get_room(entity_entry, device_entry, area_reg):
            device['room'] = room.strip()

        if device_entry:
            if device_entry.manufacturer:
                device['device_info']['manufacturer'] = device_entry.manufacturer
            if device_entry.model:
                device['device_info']['model'] = f'{device_entry.model} | {self.entity_id}'
            if device_entry.sw_version:
                device['device_info']['sw_version'] = str(device_entry.sw_version)

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

    async def execute(self, data: RequestData, capability: DeviceActionCapability) -> dict[str, Any] | None:
        """Execute action.

        https://yandex.ru/dev/dialogs/alice/doc/smart-home/reference/post-action-docpage/
        """
        capability_type = capability['type']
        instance = capability['state']['instance']

        target_capabilities = [c for c in self.capabilities() if c.type == capability_type and c.instance == instance]
        if not target_capabilities:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Capability not found for instance {instance} ({capability_type}) of {self.state.entity_id}'
            )

        for target_capability in target_capabilities:
            if error_code_template := self._error_code_template:
                if error_code := error_code_template.async_render(capability=capability, parse_result=False):
                    if error_code not in const.ERROR_CODES:
                        raise SmartHomeError(
                            ERR_INTERNAL_ERROR,
                            f'Invalid error code for {self.state.entity_id}: {error_code!r}'
                        )

                    raise SmartHomeUserError(error_code)

            try:
                return await target_capability.set_state(data, capability['state'])
            except SmartHomeError:
                raise
            except Exception as e:
                raise SmartHomeError(
                    ERR_INTERNAL_ERROR,
                    f'Failed to execute action for instance {instance} ({capability_type}) of {self.state.entity_id}: '
                    f'{e!r}'
                )

    async def _get_entity_and_device(self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry) -> \
            tuple[RegistryEntry, DeviceEntry] | tuple[None, None]:
        """Fetch the entity and device entries."""
        entity_entry = ent_reg.async_get(self.entity_id)
        if not entity_entry:
            return None, None

        device_entry = dev_reg.devices.get(entity_entry.device_id)
        return entity_entry, device_entry

    def _get_name(self, entity_entry: RegistryEntry | None) -> str:
        if CONF_NAME in self._config:
            return self._config[CONF_NAME]

        if entity_entry and entity_entry.aliases:
            return sorted(entity_entry.aliases, key=_alias_priority)[0]

        return self.state.name or self.entity_id

    def _get_room(self, entity_entry: RegistryEntry | None, device_entry: DeviceEntry | None,
                  area_reg: AreaRegistry) -> str | None:
        if CONF_ROOM in self._config:
            return self._config[CONF_ROOM]

        area = self._get_area(entity_entry, device_entry, area_reg)
        if area:
            if area.aliases:
                return sorted(area.aliases, key=_alias_priority)[0]

            return area.name

    @staticmethod
    def _get_area(entity_entry: RegistryEntry | None, device_entry: DeviceEntry | None,
                  area_reg: AreaRegistry) -> AreaEntry | None:
        """Calculate the area for an entity."""
        if entity_entry and entity_entry.area_id:
            area_id = entity_entry.area_id
        elif device_entry and device_entry.area_id:
            area_id = device_entry.area_id
        else:
            return None

        return area_reg.areas.get(area_id)

    @property
    def _error_code_template(self) -> Template | None:
        template = self._config.get(const.CONF_ERROR_CODE_TEMPLATE)
        if template:
            template.hass = self.hass

        return template


class YandexEntityCallbackState:
    def __init__(self, entity: YandexEntity, event_entity_id: str, initial_report: bool = False):
        self.device_id: str = entity.entity_id
        self.old_state: YandexEntityCallbackState | None = None

        self.capabilities: list[dict] = []
        self.properties: list[dict] = []
        self.should_report_immediately = False

        if entity.state.state == STATE_UNAVAILABLE:
            return

        for item in [c for c in entity.capabilities() if c.reportable]:
            state = item.get_state()
            if state is not None:
                self.capabilities.append(state)

        for item in [c for c in entity.properties() if c.reportable]:
            if isinstance(item, CustomEntityProperty):
                if item.property_entity_id != event_entity_id:
                    continue
            elif item.state.entity_id != event_entity_id:
                continue

            if initial_report:
                if isinstance(item, EventProperty):
                    continue

            if item.report_immediately:
                self.should_report_immediately = True

            state = item.get_state()
            if state is not None:
                self.properties.append(state)

    @property
    def should_report(self) -> bool:
        if not self.capabilities and not self.properties:
            return False

        if self.old_state:
            if self.properties == self.old_state.properties and self.capabilities == self.old_state.capabilities:
                return False

        return True
