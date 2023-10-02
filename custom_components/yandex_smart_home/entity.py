from __future__ import annotations

import re
from typing import Any

from homeassistant.const import ATTR_DEVICE_CLASS, CLOUD_NEVER_EXPOSED_ENTITIES, CONF_NAME, STATE_UNAVAILABLE
from homeassistant.core import Context, HomeAssistant, State, callback
from homeassistant.helpers.area_registry import AreaEntry, AreaRegistry
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.helpers.template import Template

from . import const
from .capability import STATE_CAPABILITIES_REGISTRY, Capability
from .capability_custom import get_custom_capability
from .const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITY_PROPERTIES,
    CONF_ROOM,
    CONF_TYPE,
    DEVICE_CLASS_TO_YANDEX_TYPES,
    DOMAIN_TO_YANDEX_TYPES,
    ERR_INTERNAL_ERROR,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
)
from .error import SmartHomeError, SmartHomeUserError
from .helpers import Config
from .property import STATE_PROPERTIES_REGISTRY, Property
from .property_custom import get_custom_property
from .schema import (
    CapabilityDescription,
    CapabilityInstanceAction,
    CapabilityInstanceActionResultValue,
    CapabilityInstanceState,
    CapabilityType,
    DeviceDescription,
    DeviceInfo,
    DeviceState,
    DeviceType,
    PropertyDescription,
    PropertyInstanceState,
    ResponseCode,
)


def _alias_priority(text: str) -> (int, str):
    if re.search("[а-яё]", text, flags=re.IGNORECASE):
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
        self._capabilities: list[Capability] | None = None
        self._properties: list[Property] | None = None

    @property
    def entity_id(self) -> str:
        """Return entity ID."""
        return self.state.entity_id

    @callback
    def capabilities(self) -> list[Capability]:
        """Return capabilities for entity."""
        if self._capabilities is not None:
            return self._capabilities

        self._capabilities = []
        state = self.state

        for capability_type, config_key in (
            (CapabilityType.MODE, const.CONF_ENTITY_CUSTOM_MODES),
            (CapabilityType.TOGGLE, const.CONF_ENTITY_CUSTOM_TOGGLES),
            (CapabilityType.RANGE, const.CONF_ENTITY_CUSTOM_RANGES),
        ):
            if config_key in self._config:
                for instance in self._config[config_key]:
                    capability = get_custom_capability(
                        self.hass,
                        self._component_config,
                        self._config[config_key][instance],
                        capability_type,
                        instance,
                        self.entity_id,
                    )

                    if capability.supported:
                        self._capabilities.append(capability)

        for CapabilityT in STATE_CAPABILITIES_REGISTRY:
            capability = CapabilityT(self.hass, self._component_config, state)
            if capability.supported and capability.instance not in [c.instance for c in self._capabilities]:
                self._capabilities.append(capability)

        return self._capabilities

    @callback
    def properties(self) -> list[Property]:
        """Return properties for entity."""
        if self._properties is not None:
            return self._properties

        self._properties = []
        state = self.state

        for property_config in self._config.get(CONF_ENTITY_PROPERTIES, []):
            if (
                device_property := get_custom_property(
                    self.hass, self._component_config, property_config, self.entity_id
                )
            ).supported:
                self._properties.append(device_property)

        for PropertyT in STATE_PROPERTIES_REGISTRY:
            device_property = PropertyT(self.hass, self._component_config, state)
            if device_property.supported:
                if device_property.instance not in [p.instance for p in self._properties]:
                    self._properties.append(device_property)

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

        domain = self.state.domain
        device_class = self._config.get(CONF_DEVICE_CLASS, self.state.attributes.get(ATTR_DEVICE_CLASS))
        return DEVICE_CLASS_TO_YANDEX_TYPES.get((domain, device_class), DOMAIN_TO_YANDEX_TYPES.get(domain))

    async def describe(
        self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry, area_reg: AreaRegistry
    ) -> DeviceDescription | None:
        """Return description of the device."""
        if self.state.state == STATE_UNAVAILABLE or not self.yandex_device_type:
            return None

        capabilities: list[CapabilityDescription] = []
        for c in self.capabilities():
            if description := c.get_description():
                capabilities.append(description)

        properties: list[PropertyDescription] = []
        for p in self.properties():
            if description := p.get_description():
                properties.append(description)

        if not capabilities and not properties:
            return None

        entity_entry, device_entry = await self._get_entity_and_device(ent_reg, dev_reg)
        device_info = DeviceInfo(model=self.entity_id)
        if device_entry is not None:
            if device_entry.model:
                device_model = f"{device_entry.model} | {self.entity_id}"
            else:
                device_model = self.entity_id

            device_info = DeviceInfo(
                manufacturer=device_entry.manufacturer,
                model=device_model,
                sw_version=device_entry.sw_version,
            )

        if (room := self._get_room(entity_entry, device_entry, area_reg)) is not None:
            room = room.strip()

        return DeviceDescription(
            id=self.entity_id,
            name=self._get_name(entity_entry).strip(),
            room=room,
            type=DeviceType(self.yandex_device_type),
            capabilities=capabilities,
            properties=properties,
            device_info=device_info,
        )

    @callback
    def query(self) -> DeviceState:
        """Return state of the device."""
        if self.state.state == STATE_UNAVAILABLE:
            return DeviceState(id=self.entity_id, error_code=ResponseCode.DEVICE_UNREACHABLE)

        capabilities: list[CapabilityInstanceState] = []
        for c in [c for c in self.capabilities() if c.retrievable]:
            if (state := c.get_instance_state()) is not None:
                capabilities.append(state)

        properties: list[PropertyInstanceState] = []
        for p in [p for p in self.properties() if p.retrievable]:
            if (state := p.get_instance_state()) is not None:
                properties.append(state)

        return DeviceState(id=self.entity_id, capabilities=capabilities, properties=properties)

    async def execute(
        self, context: Context, action: CapabilityInstanceAction
    ) -> CapabilityInstanceActionResultValue | None:
        """Execute an action to change capability state."""
        target_capability: Capability[Any] | None = None

        for capability in self.capabilities():
            if capability.type == action.type and capability.instance == action.state.instance:
                target_capability = capability
                break

        if not target_capability:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f"Capability not found for instance {action.state.instance.value} ({action.type.value}) of "
                f"{self.state.entity_id}",
            )

        if error_code_template := self._error_code_template:
            if error_code := error_code_template.async_render(capability=action.dict(), parse_result=False):
                if error_code not in const.ERROR_CODES:
                    raise SmartHomeError(
                        ERR_INTERNAL_ERROR, f"Invalid error code for {self.state.entity_id}: {error_code!r}"
                    )

                raise SmartHomeUserError(error_code)

        try:
            return await target_capability.set_instance_state(context, action.state)
        except SmartHomeError:
            raise
        except Exception as e:
            raise SmartHomeError(
                ERR_INTERNAL_ERROR,
                f"Failed to execute action for instance {action.state.instance.value} ({action.type.value}) of "
                f"{self.state.entity_id}: {e!r}",
            )

    async def _get_entity_and_device(
        self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry
    ) -> tuple[RegistryEntry | None, DeviceEntry | None]:
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

    def _get_room(
        self, entity_entry: RegistryEntry | None, device_entry: DeviceEntry | None, area_reg: AreaRegistry
    ) -> str | None:
        if CONF_ROOM in self._config:
            return self._config[CONF_ROOM]

        area = self._get_area(entity_entry, device_entry, area_reg)
        if area:
            if area.aliases:
                return sorted(area.aliases, key=_alias_priority)[0]

            return area.name

    @staticmethod
    def _get_area(
        entity_entry: RegistryEntry | None, device_entry: DeviceEntry | None, area_reg: AreaRegistry
    ) -> AreaEntry | None:
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
            if (state := item.get_instance_state()) is not None:
                self.capabilities.append(state.dict())

        for item in [c for c in entity.properties() if c.reportable]:
            if item.value_entity_id != event_entity_id:
                continue

            if initial_report and not item.report_on_startup:
                continue

            if item.report_immediately:
                self.should_report_immediately = True

            state = item.get_instance_state()
            if state is not None:
                self.properties.append(state.dict())

    @property
    def should_report(self) -> bool:
        if not self.capabilities and not self.properties:
            return False

        if self.old_state:
            if self.properties == self.old_state.properties and self.capabilities == self.old_state.capabilities:
                return False

        return True
