"""Yandex Smart Home user device."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.components import (
    air_quality,
    automation,
    binary_sensor,
    button,
    camera,
    climate,
    cover,
    fan,
    group,
    humidifier,
    input_boolean,
    input_button,
    input_text,
    light,
    lock,
    media_player,
    scene,
    script,
    sensor,
    switch,
    vacuum,
    water_heater,
)
from homeassistant.const import ATTR_DEVICE_CLASS, CLOUD_NEVER_EXPOSED_ENTITIES, CONF_NAME, STATE_UNAVAILABLE
from homeassistant.core import State, callback
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.helpers.template import Template

from . import (  # noqa: F401
    capability_color,
    capability_custom,
    capability_mode,
    capability_onoff,
    capability_range,
    capability_toggle,
    capability_video,
    property_custom,
    property_event,
    property_float,
)
from . import const  # noqa: F401
from .capability import STATE_CAPABILITIES_REGISTRY, StateCapability
from .capability_custom import get_custom_capability
from .helpers import ActionNotAllowed, APIError
from .property import STATE_PROPERTIES_REGISTRY, StateProperty
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

if TYPE_CHECKING:
    from homeassistant.core import Context, HomeAssistant
    from homeassistant.helpers.area_registry import AreaEntry, AreaRegistry
    from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry
    from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry

    from .capability import Capability
    from .entry_data import ConfigEntryData
    from .property import Property

_LOGGER = logging.getLogger(__name__)

_DOMAIN_TO_DEVICE_TYPES: dict[str, DeviceType] = {
    air_quality.DOMAIN: DeviceType.SENSOR,
    automation.DOMAIN: DeviceType.OTHER,
    binary_sensor.DOMAIN: DeviceType.SENSOR,
    button.DOMAIN: DeviceType.OTHER,
    camera.DOMAIN: DeviceType.CAMERA,
    climate.DOMAIN: DeviceType.THERMOSTAT,
    cover.DOMAIN: DeviceType.OPENABLE_CURTAIN,
    fan.DOMAIN: DeviceType.FAN,
    group.DOMAIN: DeviceType.SWITCH,
    humidifier.DOMAIN: DeviceType.HUMIDIFIER,
    input_boolean.DOMAIN: DeviceType.SWITCH,
    input_button.DOMAIN: DeviceType.OTHER,
    input_text.DOMAIN: DeviceType.SENSOR,
    light.DOMAIN: DeviceType.LIGHT,
    lock.DOMAIN: DeviceType.OPENABLE,
    media_player.DOMAIN: DeviceType.MEDIA_DEVICE,
    scene.DOMAIN: DeviceType.OTHER,
    script.DOMAIN: DeviceType.OTHER,
    sensor.DOMAIN: DeviceType.SENSOR,
    switch.DOMAIN: DeviceType.SWITCH,
    vacuum.DOMAIN: DeviceType.VACUUM_CLEANER,
    water_heater.DOMAIN: DeviceType.KETTLE,
}

_DEVICE_CLASS_TO_DEVICE_TYPES: dict[tuple[str, str], DeviceType] = {
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.DOOR): DeviceType.SENSOR_OPEN,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.GARAGE_DOOR): DeviceType.SENSOR_OPEN,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.GAS): DeviceType.SENSOR_GAS,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.MOISTURE): DeviceType.SENSOR_WATER_LEAK,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.MOTION): DeviceType.SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.MOVING): DeviceType.SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.OCCUPANCY): DeviceType.SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.OPENING): DeviceType.SENSOR_OPEN,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.PRESENCE): DeviceType.SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.SMOKE): DeviceType.SENSOR_SMOKE,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.VIBRATION): DeviceType.SENSOR_VIBRATION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.WINDOW): DeviceType.SENSOR_OPEN,
    (media_player.DOMAIN, media_player.MediaPlayerDeviceClass.RECEIVER): DeviceType.MEDIA_DEVICE_RECIEVER,
    (media_player.DOMAIN, media_player.MediaPlayerDeviceClass.TV): DeviceType.MEDIA_DEVICE_TV,
    (sensor.DOMAIN, const.DEVICE_CLASS_BUTTON): DeviceType.SENSOR_BUTTON,
    (sensor.DOMAIN, sensor.SensorDeviceClass.CO): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.CO2): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.HUMIDITY): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.ILLUMINANCE): DeviceType.SENSOR_ILLUMINATION,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PM1): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PM10): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PM25): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PRESSURE): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.TEMPERATURE): DeviceType.SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS): DeviceType.SENSOR_CLIMATE,
    (switch.DOMAIN, switch.SwitchDeviceClass.OUTLET): DeviceType.SOCKET,
}


def _alias_priority(text: str) -> tuple[int, str]:
    """Return sort priority for alias."""
    if re.search("[а-яё]", text, flags=re.IGNORECASE):
        return 0, text

    return 1, text


class Device:
    """Represent user device."""

    __slots__ = ("_hass", "_entry_data", "_state", "_config", "id")

    id: str

    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData, device_id: str, state: State | None):
        """Initialize a device for the state."""
        self.id = device_id

        self._hass = hass
        self._entry_data = entry_data
        self._state = state or State(entity_id=device_id, state=STATE_UNAVAILABLE)
        self._config = self._entry_data.get_entity_config(self.id)

    @callback
    def get_capabilities(self) -> list[Capability[Any]]:
        """Return all capabilities of the device."""
        capabilities: list[Capability[Any]] = []

        for capability_type, config_key in (
            (CapabilityType.MODE, const.CONF_ENTITY_CUSTOM_MODES),
            (CapabilityType.TOGGLE, const.CONF_ENTITY_CUSTOM_TOGGLES),
            (CapabilityType.RANGE, const.CONF_ENTITY_CUSTOM_RANGES),
        ):
            if config_key in self._config:
                for instance in self._config[config_key]:
                    custom_capability = get_custom_capability(
                        self._hass,
                        self._entry_data,
                        self._config[config_key][instance],
                        capability_type,
                        instance,
                        self.id,
                    )

                    if custom_capability.supported and custom_capability not in capabilities:
                        capabilities.append(custom_capability)

        for CapabilityT in STATE_CAPABILITIES_REGISTRY:
            state_capability = CapabilityT(self._hass, self._entry_data, self._state)
            if state_capability.supported and state_capability not in capabilities:
                capabilities.append(state_capability)

        return capabilities

    @callback
    def get_state_capabilities(self) -> list[StateCapability[Any]]:
        """Return capabilities of the device based on the state."""
        return [c for c in self.get_capabilities() if isinstance(c, StateCapability)]

    @callback
    def get_properties(self) -> list[Property]:
        """Return all properties for the device."""
        properties: list[Property] = []

        for property_config in self._config.get(const.CONF_ENTITY_PROPERTIES, []):
            try:
                custom_property = get_custom_property(self._hass, self._entry_data, property_config, self.id)
            except APIError as e:
                _LOGGER.error(e)
                continue

            if custom_property.supported and custom_property not in properties:
                properties.append(custom_property)

        for PropertyT in STATE_PROPERTIES_REGISTRY:
            device_property = PropertyT(self._hass, self._entry_data, self._state)
            if device_property.supported and device_property not in properties:
                properties.append(device_property)

        return properties

    @callback
    def get_state_properties(self) -> list[StateProperty]:
        """Return properties for the device based on the state."""
        return [p for p in self.get_properties() if isinstance(p, StateProperty)]

    @property
    def should_expose(self) -> bool:
        """Test if the device should be exposed."""
        if self.unavailable:
            return False

        if not self.type:
            return False

        if self.id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        return self._entry_data.should_expose(self.id)

    @property
    def unavailable(self) -> bool:
        """Test if the device is unavailable."""
        return self._state.state == STATE_UNAVAILABLE

    @property
    def type(self) -> DeviceType | None:
        """Return device type."""
        if user_type := self._config.get(const.CONF_TYPE):
            return DeviceType(user_type)

        domain = self._state.domain
        device_class: str = self._config.get(const.CONF_DEVICE_CLASS, self._state.attributes.get(ATTR_DEVICE_CLASS, ""))

        return _DEVICE_CLASS_TO_DEVICE_TYPES.get((domain, device_class), _DOMAIN_TO_DEVICE_TYPES.get(domain))

    async def describe(
        self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry, area_reg: AreaRegistry
    ) -> DeviceDescription | None:
        """Return description of the device."""
        capabilities: list[CapabilityDescription] = []
        for c in self.get_capabilities():
            if c_description := c.get_description():
                capabilities.append(c_description)

        properties: list[PropertyDescription] = []
        for p in self.get_properties():
            if p_description := p.get_description():
                properties.append(p_description)

        if not capabilities and not properties:
            return None

        entity_entry, device_entry = await self._get_entity_and_device(ent_reg, dev_reg)
        device_info = DeviceInfo(model=self.id)
        if device_entry is not None:
            if device_entry.model:
                device_model = f"{device_entry.model} | {self.id}"
            else:
                device_model = self.id

            device_info = DeviceInfo(
                manufacturer=device_entry.manufacturer,
                model=device_model,
                sw_version=device_entry.sw_version,
            )

        if (room := self._get_room(entity_entry, device_entry, area_reg)) is not None:
            room = room.strip()

        assert self.type
        return DeviceDescription(
            id=self.id,
            name=self._get_name(entity_entry).strip(),
            room=room,
            type=self.type,
            capabilities=capabilities or None,
            properties=properties or None,
            device_info=device_info,
        )

    @callback
    def query(self) -> DeviceState:
        """Return state of the device."""
        if self.unavailable:
            return DeviceState(id=self.id, error_code=ResponseCode.DEVICE_UNREACHABLE)

        capabilities: list[CapabilityInstanceState] = []
        for c in [c for c in self.get_capabilities() if c.retrievable]:
            if (capability_state := c.get_instance_state()) is not None:
                capabilities.append(capability_state)

        properties: list[PropertyInstanceState] = []
        for p in [p for p in self.get_properties() if p.retrievable]:
            if (property_state := p.get_instance_state()) is not None:
                properties.append(property_state)

        if not capabilities and not properties:
            return DeviceState(id=self.id, error_code=ResponseCode.DEVICE_UNREACHABLE)

        return DeviceState(id=self.id, capabilities=capabilities, properties=properties)

    async def execute(
        self, context: Context, action: CapabilityInstanceAction
    ) -> CapabilityInstanceActionResultValue | None:
        """Execute an action to change capability state."""
        target_capability: Capability[Any] | None = None

        for capability in self.get_capabilities():
            if capability.type == action.type and capability.instance == action.state.instance:
                target_capability = capability
                break

        if not target_capability:
            raise APIError(
                ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                f"Capability not found for instance {action.state.instance.value} ({action.type.value}) of "
                f"{self.id}",
            )

        if error_code_template := self._error_code_template:
            if error_code := error_code_template.async_render(capability=action.as_dict(), parse_result=False):
                try:
                    code = ResponseCode(error_code)
                except ValueError:
                    raise APIError(ResponseCode.INTERNAL_ERROR, f"Invalid error code for {self.id}: {error_code!r}")

                raise ActionNotAllowed(code)

        try:
            return await target_capability.set_instance_state(context, action.state)
        except (APIError, ActionNotAllowed):
            raise
        except Exception as e:
            raise APIError(
                ResponseCode.INTERNAL_ERROR,
                f"Failed to execute action for instance {action.state.instance.value} ({action.type.value}) of "
                f"{self.id}: {e!r}",
            )

    async def _get_entity_and_device(
        self, ent_reg: EntityRegistry, dev_reg: DeviceRegistry
    ) -> tuple[RegistryEntry | None, DeviceEntry | None]:
        """Fetch the entity and device entries."""
        entity_entry = ent_reg.async_get(self.id)
        if not entity_entry:
            return None, None

        if entity_entry.device_id:
            device_entry = dev_reg.devices.get(entity_entry.device_id)
            return entity_entry, device_entry

        return None, None  # pragma: nocover

    def _get_name(self, entity_entry: RegistryEntry | None) -> str:
        """Return the device name."""
        if name := self._config.get(CONF_NAME):
            return str(name)

        if entity_entry and entity_entry.aliases:
            return sorted(entity_entry.aliases, key=_alias_priority)[0]

        return self._state.name or self.id

    def _get_room(
        self, entity_entry: RegistryEntry | None, device_entry: DeviceEntry | None, area_reg: AreaRegistry
    ) -> str | None:
        """Return room of the device."""
        if room := self._config.get(const.CONF_ROOM):
            return str(room)

        area = self._get_area(entity_entry, device_entry, area_reg)
        if area:
            if area.aliases:
                return sorted(area.aliases, key=_alias_priority)[0]

            return area.name

        return None

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
        """Prepare template for error code."""
        template: Template | None = self._config.get(const.CONF_ERROR_CODE_TEMPLATE)
        if template is not None:
            template.hass = self._hass

        return template


async def async_get_devices(hass: HomeAssistant, entry_data: ConfigEntryData) -> list[Device]:
    """Return list of supported user devices."""
    devices: list[Device] = []

    for state in hass.states.async_all():
        device = Device(hass, entry_data, state.entity_id, state)
        if not device.should_expose:
            continue

        devices.append(device)

    return devices


async def async_get_device_description(hass: HomeAssistant, device: Device) -> DeviceDescription | None:
    """Return description for a user device."""
    ent_reg = entity_registry.async_get(hass)
    dev_reg = device_registry.async_get(hass)
    area_reg = area_registry.async_get(hass)

    if (description := await device.describe(ent_reg, dev_reg, area_reg)) is not None:
        return description

    _LOGGER.debug(f"Missing capabilities and properties for {device.id}")
    return None


async def async_get_device_states(
    hass: HomeAssistant, entry_data: ConfigEntryData, device_ids: list[str]
) -> list[DeviceState]:
    """Return list of the states of user devices."""
    states: list[DeviceState] = []

    for device_id in device_ids:
        device = Device(hass, entry_data, device_id, hass.states.get(device_id))
        if not device.should_expose:
            _LOGGER.warning(
                f"State requested for unexposed entity {device.id}. Please either expose the entity via "
                f"filters in component configuration or delete the device from Yandex."
            )

        states.append(device.query())

    return states
