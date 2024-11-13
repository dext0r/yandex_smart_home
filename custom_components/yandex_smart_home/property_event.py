"""Implement the Yandex Smart Home event properties."""

from abc import abstractmethod
from functools import cached_property
from itertools import chain
import logging
from typing import Any, Protocol, Self, cast

from homeassistant.components import binary_sensor, sensor
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.event import ATTR_EVENT_TYPE, DOMAIN as EVENT_DOMAIN, EventDeviceClass
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers.typing import ConfigType

from .const import CONF_ENTITY_EVENT_MAP, STATE_EMPTY, STATE_NONE, STATE_NONE_UI, XGW3DeviceClass
from .property import STATE_PROPERTIES_REGISTRY, Property, StateProperty
from .schema import (
    BatteryLevelEventPropertyParameters,
    BatteryLevelInstanceEvent,
    ButtonEventPropertyParameters,
    ButtonInstanceEvent,
    EventInstanceEvent,
    EventInstanceEventT,
    EventPropertyDescription,
    EventPropertyInstance,
    EventPropertyParameters,
    FoodLevelEventPropertyParameters,
    FoodLevelInstanceEvent,
    GasEventPropertyParameters,
    GasInstanceEvent,
    MotionEventPropertyParameters,
    MotionInstanceEvent,
    OpenEventPropertyParameters,
    OpenInstanceEvent,
    PropertyType,
    SmokeEventPropertyParameters,
    SmokeInstanceEvent,
    VibrationEventPropertyParameters,
    VibrationInstanceEvent,
    WaterLeakEventPropertyParameters,
    WaterLeakInstanceEvent,
    WaterLevelEventPropertyParameters,
    WaterLevelInstanceEvent,
)
from .schema.property_event import get_event_class_for_instance

_LOGGER = logging.getLogger(__name__)

_BOOLEAN_TRUE = ["yes", "true", "1", STATE_ON]
_BOOLEAN_FALSE = ["no", "false", "0", STATE_OFF]

type EventMapT[EventInstanceEventT] = dict[EventInstanceEventT, list[str]]


class EventProperty(Property, Protocol[EventInstanceEventT]):
    """Base class for event properties."""

    type: PropertyType = PropertyType.EVENT
    instance: EventPropertyInstance

    _event_map_default: EventMapT[EventInstanceEventT] = {}

    @property
    @abstractmethod
    def parameters(self) -> EventPropertyParameters[EventInstanceEventT]:
        """Return parameters for a devices list request."""
        ...

    def get_description(self) -> EventPropertyDescription:
        """Return a description for a device list request."""
        return EventPropertyDescription(
            retrievable=self.retrievable, reportable=self.reportable, parameters=self.parameters
        )

    @property
    def report_on_startup(self) -> bool:
        """Test if property value should be reported on startup."""
        return False

    @property
    def time_sensitive(self) -> bool:
        """Test if value changes should be reported immediately."""
        return True

    @property
    def event_map(self) -> dict[EventInstanceEventT, list[str]]:
        """Return an event mapping between Yandex and HA."""
        return self.event_map_config or self._event_map_default

    @property
    def event_map_config(self) -> dict[EventInstanceEventT, list[str]]:
        """Return an event mapping from a entity configuration."""
        if CONF_ENTITY_EVENT_MAP in self._entity_config:
            event_cls = get_event_class_for_instance(self.instance)
            return cast(
                dict[EventInstanceEventT, list[str]],
                {event_cls(k): v for k, v in self._entity_config[CONF_ENTITY_EVENT_MAP].get(self.instance, {}).items()},
            )

        return {}

    def get_value(self) -> EventInstanceEvent | None:
        """Return the current property value."""
        value = str(self._get_native_value()).lower()

        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

        for event, values in self.event_map.items():
            if value in values:
                return event

        _LOGGER.debug(f"Unknown event {value} for instance {self.instance} of {self.device_id}")

        return None

    @cached_property
    def _entity_config(self) -> ConfigType:
        """Return additional configuration for the device."""
        return self._entry_data.get_entity_config(self.device_id)

    @abstractmethod
    def _get_native_value(self) -> str | None:
        """Return the current property value without conversion."""
        ...

    @cached_property
    def _supported_native_values(self) -> list[str]:
        """Return a list of supported native values."""
        return list(chain.from_iterable(self.event_map.values()))


class SensorEventProperty(EventProperty[Any]):
    """Represent a binary-like property with stable current value."""

    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        if other is None:
            return False

        value, other_value = self.get_value(), other.get_value()
        if value is None or other_value is None:
            return False

        return bool(value != other_value)


class ReactiveEventProperty(EventProperty[Any], Protocol):
    """Represent a button-like event property (sensor and binary_sensor platforms)."""

    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        value = self.get_value()
        if value is None:
            return False

        if other is None:
            return True

        return value != other.get_value()


class OpenEventProperty(EventProperty[OpenInstanceEvent], Protocol):
    """Base class for event property that detect opening of something."""

    instance: EventPropertyInstance = EventPropertyInstance.OPEN

    _event_map_default: EventMapT[OpenInstanceEvent] = {
        OpenInstanceEvent.OPENED: _BOOLEAN_TRUE + [STATE_OPEN],
        OpenInstanceEvent.CLOSED: _BOOLEAN_FALSE + [STATE_CLOSED],
    }

    @property
    def parameters(self) -> OpenEventPropertyParameters:
        """Return parameters for a devices list request."""
        return OpenEventPropertyParameters()


class MotionEventProperty(EventProperty[MotionInstanceEvent], Protocol):
    """Base class for event property that detect motion, presence or occupancy."""

    instance: EventPropertyInstance = EventPropertyInstance.MOTION

    _event_map_default: EventMapT[MotionInstanceEvent] = {
        MotionInstanceEvent.DETECTED: _BOOLEAN_TRUE + ["motion", "motion_detected"],
        MotionInstanceEvent.NOT_DETECTED: _BOOLEAN_FALSE,
    }

    @property
    def parameters(self) -> MotionEventPropertyParameters:
        """Return parameters for a devices list request."""
        return MotionEventPropertyParameters()


class GasEventProperty(EventProperty[GasInstanceEvent], Protocol):
    """Base class for event property that detect gas presence."""

    instance: EventPropertyInstance = EventPropertyInstance.GAS

    _event_map_default: EventMapT[GasInstanceEvent] = {
        GasInstanceEvent.DETECTED: _BOOLEAN_TRUE,
        GasInstanceEvent.NOT_DETECTED: _BOOLEAN_FALSE,
        GasInstanceEvent.HIGH: ["high"],
    }

    @property
    def parameters(self) -> GasEventPropertyParameters:
        """Return parameters for a devices list request."""
        return GasEventPropertyParameters()


class SmokeEventProperty(EventProperty[SmokeInstanceEvent], Protocol):
    """Base class for event property that detect smoke presence."""

    instance: EventPropertyInstance = EventPropertyInstance.SMOKE

    _event_map_default: EventMapT[SmokeInstanceEvent] = {
        SmokeInstanceEvent.DETECTED: _BOOLEAN_TRUE,
        SmokeInstanceEvent.NOT_DETECTED: _BOOLEAN_FALSE,
        SmokeInstanceEvent.HIGH: ["high"],
    }

    @property
    def parameters(self) -> SmokeEventPropertyParameters:
        """Return parameters for a devices list request."""
        return SmokeEventPropertyParameters()


class BatteryLevelEventProperty(EventProperty[BatteryLevelInstanceEvent], Protocol):
    """Base class for event property that detect low level of a battery."""

    instance: EventPropertyInstance = EventPropertyInstance.BATTERY_LEVEL

    _event_map_default: EventMapT[BatteryLevelInstanceEvent] = {
        BatteryLevelInstanceEvent.LOW: _BOOLEAN_TRUE + ["low"],
        BatteryLevelInstanceEvent.NORMAL: _BOOLEAN_FALSE + ["normal"],
        BatteryLevelInstanceEvent.HIGH: ["high"],
    }

    @property
    def parameters(self) -> BatteryLevelEventPropertyParameters:
        """Return parameters for a devices list request."""
        return BatteryLevelEventPropertyParameters()


class FoodLevelEventProperty(EventProperty[FoodLevelInstanceEvent], Protocol):
    """Base class for event property that detect food level."""

    instance: EventPropertyInstance = EventPropertyInstance.FOOD_LEVEL

    _event_map_default: EventMapT[FoodLevelInstanceEvent] = {
        FoodLevelInstanceEvent.EMPTY: ["empty"],
        FoodLevelInstanceEvent.LOW: ["low"],
        FoodLevelInstanceEvent.NORMAL: ["normal"],
    }

    @property
    def parameters(self) -> FoodLevelEventPropertyParameters:
        """Return parameters for a devices list request."""
        return FoodLevelEventPropertyParameters()


class WaterLevelEventProperty(EventProperty[WaterLevelInstanceEvent], Protocol):
    """Base class for event property that detect low level of water."""

    instance: EventPropertyInstance = EventPropertyInstance.WATER_LEVEL

    _event_map_default: EventMapT[WaterLevelInstanceEvent] = {
        WaterLevelInstanceEvent.EMPTY: ["empty"],
        WaterLevelInstanceEvent.LOW: _BOOLEAN_TRUE + ["low"],
        WaterLevelInstanceEvent.NORMAL: _BOOLEAN_FALSE + ["normal"],
    }

    @property
    def parameters(self) -> WaterLevelEventPropertyParameters:
        """Return parameters for a devices list request."""
        return WaterLevelEventPropertyParameters()


class WaterLeakEventProperty(EventProperty[WaterLeakInstanceEvent], Protocol):
    """Base class for event property that detect water leakage."""

    instance: EventPropertyInstance = EventPropertyInstance.WATER_LEAK

    _event_map_default: EventMapT[WaterLeakInstanceEvent] = {
        WaterLeakInstanceEvent.DRY: _BOOLEAN_FALSE + ["dry"],
        WaterLeakInstanceEvent.LEAK: _BOOLEAN_TRUE + ["leak"],
    }

    @property
    def parameters(self) -> WaterLeakEventPropertyParameters:
        """Return parameters for a devices list request."""
        return WaterLeakEventPropertyParameters()


class ButtonPressEventProperty(EventProperty[ButtonInstanceEvent], Protocol):
    """Base class for event property that detect a button interaction."""

    instance: EventPropertyInstance = EventPropertyInstance.BUTTON

    _event_map_default: EventMapT[ButtonInstanceEvent] = {
        ButtonInstanceEvent.CLICK: ["click", "single", "press", "pressed"],
        ButtonInstanceEvent.DOUBLE_CLICK: [
            "double_click",
            "double_press",
            "double",
            "many",
            "quadruple",
            "triple",
            "triple_press",
            "long_triple_press",
            "long_double_press",
        ],
        ButtonInstanceEvent.LONG_PRESS: [
            "hold",
            "long_click_press",
            "long_click",
            "long_press",
            "long",
        ],
    }

    @property
    def retrievable(self) -> bool:
        """Test if the property can return the current value."""
        return False

    @property
    def parameters(self) -> ButtonEventPropertyParameters:
        """Return parameters for a devices list request."""
        return ButtonEventPropertyParameters()


class VibrationEventProperty(EventProperty[VibrationInstanceEvent], Protocol):
    """Base class for event property that detect vibration."""

    instance: EventPropertyInstance = EventPropertyInstance.VIBRATION

    _event_map_default: EventMapT[VibrationInstanceEvent] = {
        VibrationInstanceEvent.VIBRATION: _BOOLEAN_TRUE
        + [
            "vibration",
            "vibrate",
            "actively",
            "move",
            "tap_twice",
            "shake_air",
            "swing",
        ],
        VibrationInstanceEvent.TILT: ["tilt", "flip90", "flip180", "rotate"],
        VibrationInstanceEvent.FALL: ["fall", "free_fall", "drop"],
    }

    @property
    def retrievable(self) -> bool:
        """Test if the property can return the current value."""
        return False

    @property
    def parameters(self) -> VibrationEventPropertyParameters:
        """Return parameters for a devices list request."""
        return VibrationEventPropertyParameters()


class StateEventProperty(StateProperty, EventProperty[Any], Protocol):
    """Base class for a event property based on the state."""

    def _get_native_value(self) -> str | None:
        """Return the current property value without conversion."""
        return self.state.state


class EventPlatformProperty(StateProperty, EventProperty[Any], Protocol):
    """Base class for a event property based on the state of an event platform entity."""

    @property
    def retrievable(self) -> bool:
        """Test if the property can return the current value."""
        return False

    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        value = self.get_value()
        if value is None:
            return False

        if other is None:
            return True

        if self.state.state == other.state.state:
            return False

        return True

    def _get_native_value(self) -> str | None:
        """Return the current property value without conversion."""
        return self.state.attributes.get(ATTR_EVENT_TYPE)


class OpenStateEventProperty(StateEventProperty, SensorEventProperty, OpenEventProperty):
    """Represents the state event property that detect opening of something."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == binary_sensor.DOMAIN and self._state_device_class in (
            BinarySensorDeviceClass.DOOR,
            BinarySensorDeviceClass.GARAGE_DOOR,
            BinarySensorDeviceClass.WINDOW,
            BinarySensorDeviceClass.OPENING,
        )


class MotionStateEventProperty(SensorEventProperty, StateEventProperty, MotionEventProperty):
    """Represents the state event property that detect motion, presence or occupancy."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == binary_sensor.DOMAIN and self._state_device_class in (
            BinarySensorDeviceClass.MOTION,
            BinarySensorDeviceClass.OCCUPANCY,
            BinarySensorDeviceClass.PRESENCE,
        )


class MotionEventPlatformProperty(EventPlatformProperty, MotionEventProperty):
    """Represents the event platform property that detect motion."""

    @property
    def parameters(self) -> MotionEventPropertyParameters:
        """Return parameters for a devices list request."""
        return MotionEventPropertyParameters(
            events=[{"value": MotionInstanceEvent.DETECTED}]  # type: ignore[dict-item]
        )

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == EVENT_DOMAIN and self._state_device_class == EventDeviceClass.MOTION


class GasStateEventProperty(StateEventProperty, SensorEventProperty, GasEventProperty):
    """Represents the state event property that detect gas presence."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == binary_sensor.DOMAIN and self._state_device_class == BinarySensorDeviceClass.GAS


class SmokeStateEventProperty(StateEventProperty, SensorEventProperty, SmokeEventProperty):
    """Represents the state event property that detect smoke presence."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == binary_sensor.DOMAIN and self._state_device_class == BinarySensorDeviceClass.SMOKE


class BatteryLevelStateEvent(StateEventProperty, SensorEventProperty, BatteryLevelEventProperty):
    """Represents the state event property that detect low level of a battery."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return self.state.domain == binary_sensor.DOMAIN and self._state_device_class == BinarySensorDeviceClass.BATTERY


class WaterLeakStateEventProperty(StateEventProperty, SensorEventProperty, WaterLeakEventProperty):
    """Represents the state event property that detect water leakage."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        return (
            self.state.domain == binary_sensor.DOMAIN and self._state_device_class == BinarySensorDeviceClass.MOISTURE
        )


class ButtonPressStateEventProperty(StateEventProperty, ReactiveEventProperty, ButtonPressEventProperty):
    """Represents the state property that detect a button interaction."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == EVENT_DOMAIN:
            return False

        if self._state_device_class == EventDeviceClass.BUTTON:
            return True

        if self._entry_data.get_entity_config(self.device_id).get(CONF_DEVICE_CLASS) == EventDeviceClass.BUTTON:
            return True

        if self.state.domain == sensor.DOMAIN and self._state_device_class == XGW3DeviceClass.ACTION:
            possible_actions = self._supported_native_values
            possible_actions.extend(
                [
                    "long_click_release",
                    "release",
                ]
            )

            return self.state.attributes.get("action") in possible_actions

        return False


class ButtonPressEventPlatformProperty(EventPlatformProperty, ButtonPressEventProperty):
    """Represents the event platform property that detect a button interaction."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == EVENT_DOMAIN:
            if self._state_device_class in [EventDeviceClass.DOORBELL, EventDeviceClass.BUTTON]:
                return True

            if self._entry_data.get_entity_config(self.device_id).get(CONF_DEVICE_CLASS) == EventDeviceClass.BUTTON:
                return True

        return False


class VibrationStateEventProperty(StateEventProperty, ReactiveEventProperty, VibrationEventProperty):
    """Represents the state event property that detect vibration."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            if self._state_device_class == BinarySensorDeviceClass.VIBRATION:
                return True

        if self.state.domain == sensor.DOMAIN and self._state_device_class == XGW3DeviceClass.ACTION:
            return self.state.attributes.get("action") in self._supported_native_values

        return False


STATE_PROPERTIES_REGISTRY.register(OpenStateEventProperty)
STATE_PROPERTIES_REGISTRY.register(MotionStateEventProperty)
STATE_PROPERTIES_REGISTRY.register(MotionEventPlatformProperty)
STATE_PROPERTIES_REGISTRY.register(GasStateEventProperty)
STATE_PROPERTIES_REGISTRY.register(SmokeStateEventProperty)
STATE_PROPERTIES_REGISTRY.register(BatteryLevelStateEvent)
STATE_PROPERTIES_REGISTRY.register(WaterLeakStateEventProperty)
STATE_PROPERTIES_REGISTRY.register(ButtonPressStateEventProperty)
STATE_PROPERTIES_REGISTRY.register(ButtonPressEventPlatformProperty)
STATE_PROPERTIES_REGISTRY.register(VibrationStateEventProperty)
