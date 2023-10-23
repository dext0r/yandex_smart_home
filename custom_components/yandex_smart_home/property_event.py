"""Implement the Yandex Smart Home event properties."""
from abc import ABC, abstractmethod
from functools import cached_property
from itertools import chain
from typing import Any, Protocol, Self

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from .const import CONF_DEVICE_CLASS, DEVICE_CLASS_BUTTON, STATE_EMPTY, STATE_NONE, STATE_NONE_UI
from .property import STATE_PROPERTIES_REGISTRY, Property, StateProperty
from .schema import (
    BatteryLevelEventPropertyParameters,
    BatteryLevelInstanceEvent,
    ButtonEventPropertyParameters,
    ButtonInstanceEvent,
    EventInstanceEvent,
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

_BOOLEAN_TRUE = ["yes", "true", "1", STATE_ON]
_BOOLEAN_FALSE = ["no", "false", "0", STATE_OFF]


class EventProperty(Property, Protocol[EventInstanceEvent]):
    """Base class for event properties."""

    type: PropertyType = PropertyType.EVENT
    instance: EventPropertyInstance

    _event_map: dict[EventInstanceEvent, list[str]] = {}

    @property
    @abstractmethod
    def parameters(self) -> EventPropertyParameters[EventInstanceEvent]:
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

    def get_value(self) -> EventInstanceEvent | None:
        """Return the current property value."""
        value = str(self._get_native_value()).lower()

        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

        for event, values in self._event_map.items():
            if value in values:
                return event

        return None

    @abstractmethod
    def _get_native_value(self) -> str | None:
        """Return the current property value without conversion."""
        ...

    @cached_property
    def _supported_native_values(self) -> list[str]:
        """Return list of supported native values."""
        return list(chain.from_iterable(self._event_map.values()))


class SensorEventProperty(EventProperty[Any], ABC):
    """Represent a binary-like property with stable current value."""

    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        if other is None:
            return False

        value, other_value = self.get_value(), other.get_value()
        if value is None or other_value is None:
            return False

        return bool(value != other_value)


class ReactiveEventProperty(EventProperty[Any], ABC):
    """Represent a button-like event property."""

    def check_value_change(self, other: Self | None) -> bool:
        """Test if the property value differs from other property."""
        if other is None:
            return True

        value, other_value = self.get_value(), other.get_value()
        if value == other_value:
            return False

        return value is not None


class OpenEventProperty(SensorEventProperty, EventProperty[OpenInstanceEvent], ABC):
    """Base class for event property that detect opening of something."""

    instance = EventPropertyInstance.OPEN

    _event_map = {
        OpenInstanceEvent.OPENED: _BOOLEAN_TRUE + [STATE_OPEN],
        OpenInstanceEvent.CLOSED: _BOOLEAN_FALSE + [STATE_CLOSED],
    }

    @property
    def parameters(self) -> OpenEventPropertyParameters:
        """Return parameters for a devices list request."""
        return OpenEventPropertyParameters()


class MotionEventProperty(SensorEventProperty, EventProperty[MotionInstanceEvent], ABC):
    """Base class for event property that detect motion, presence or occupancy."""

    instance = EventPropertyInstance.MOTION

    _event_map = {
        MotionInstanceEvent.DETECTED: _BOOLEAN_TRUE,
        MotionInstanceEvent.NOT_DETECTED: _BOOLEAN_FALSE,
    }

    @property
    def parameters(self) -> MotionEventPropertyParameters:
        """Return parameters for a devices list request."""
        return MotionEventPropertyParameters()


class GasEventProperty(SensorEventProperty, EventProperty[GasInstanceEvent], ABC):
    """Base class for event property that detect gas presence."""

    instance = EventPropertyInstance.GAS

    _event_map = {
        GasInstanceEvent.DETECTED: _BOOLEAN_TRUE,
        GasInstanceEvent.NOT_DETECTED: _BOOLEAN_FALSE,
        GasInstanceEvent.HIGH: ["high"],
    }

    @property
    def parameters(self) -> GasEventPropertyParameters:
        """Return parameters for a devices list request."""
        return GasEventPropertyParameters()


class SmokeEventProperty(SensorEventProperty, EventProperty[SmokeInstanceEvent], ABC):
    """Base class for event property that detect smoke presence."""

    instance = EventPropertyInstance.SMOKE

    _event_map = {
        SmokeInstanceEvent.DETECTED: _BOOLEAN_TRUE,
        SmokeInstanceEvent.NOT_DETECTED: _BOOLEAN_FALSE,
        SmokeInstanceEvent.HIGH: ["high"],
    }

    @property
    def parameters(self) -> SmokeEventPropertyParameters:
        """Return parameters for a devices list request."""
        return SmokeEventPropertyParameters()


class BatteryLevelEventProperty(SensorEventProperty, EventProperty[BatteryLevelInstanceEvent], ABC):
    """Base class for event property that detect low level of a battery."""

    instance = EventPropertyInstance.BATTERY_LEVEL

    _event_map = {
        BatteryLevelInstanceEvent.LOW: _BOOLEAN_TRUE + ["low"],
        BatteryLevelInstanceEvent.NORMAL: _BOOLEAN_FALSE + ["normal"],
        BatteryLevelInstanceEvent.HIGH: ["high"],
    }

    @property
    def parameters(self) -> BatteryLevelEventPropertyParameters:
        """Return parameters for a devices list request."""
        return BatteryLevelEventPropertyParameters()


class FoodLevelEventProperty(SensorEventProperty, EventProperty[FoodLevelInstanceEvent], ABC):
    """Base class for event property that detect food level."""

    instance = EventPropertyInstance.FOOD_LEVEL

    _event_map = {
        FoodLevelInstanceEvent.EMPTY: ["empty"],
        FoodLevelInstanceEvent.LOW: ["low"],
        FoodLevelInstanceEvent.NORMAL: ["normal"],
    }

    @property
    def parameters(self) -> FoodLevelEventPropertyParameters:
        """Return parameters for a devices list request."""
        return FoodLevelEventPropertyParameters()


class WaterLevelEventProperty(SensorEventProperty, EventProperty[WaterLevelInstanceEvent], ABC):
    """Base class for event property that detect low level of water."""

    instance = EventPropertyInstance.WATER_LEVEL

    _event_map = {
        WaterLevelInstanceEvent.EMPTY: ["empty"],
        WaterLevelInstanceEvent.LOW: _BOOLEAN_TRUE + ["low"],
        WaterLevelInstanceEvent.NORMAL: _BOOLEAN_FALSE + ["normal"],
    }

    @property
    def parameters(self) -> WaterLevelEventPropertyParameters:
        """Return parameters for a devices list request."""
        return WaterLevelEventPropertyParameters()


class WaterLeakEventProperty(SensorEventProperty, EventProperty[WaterLeakInstanceEvent], ABC):
    """Base class for event property that detect water leakage."""

    instance = EventPropertyInstance.WATER_LEAK

    _event_map = {
        WaterLeakInstanceEvent.DRY: _BOOLEAN_FALSE + ["dry"],
        WaterLeakInstanceEvent.LEAK: _BOOLEAN_TRUE + ["leak"],
    }

    @property
    def parameters(self) -> WaterLeakEventPropertyParameters:
        """Return parameters for a devices list request."""
        return WaterLeakEventPropertyParameters()


class ButtonPressEventProperty(ReactiveEventProperty, EventProperty[ButtonInstanceEvent], ABC):
    """Base class for event property that detect a button interaction."""

    instance = EventPropertyInstance.BUTTON

    _event_map = {
        ButtonInstanceEvent.CLICK: ["click", "single"],
        ButtonInstanceEvent.DOUBLE_CLICK: ["double_click", "double", "triple", "quadruple", "many"],
        ButtonInstanceEvent.LONG_PRESS: ["long_press", "long", "long_click", "long_click_press", "hold"],
    }

    @property
    def retrievable(self) -> bool:
        """Test if the property can return the current value."""
        return False

    @property
    def parameters(self) -> ButtonEventPropertyParameters:
        """Return parameters for a devices list request."""
        return ButtonEventPropertyParameters()


class VibrationEventProperty(ReactiveEventProperty, EventProperty[VibrationInstanceEvent], ABC):
    """Base class for event property that detect vibration."""

    instance = EventPropertyInstance.VIBRATION

    _event_map = {
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


@STATE_PROPERTIES_REGISTRY.register
class OpenStateEventProperty(StateEventProperty, OpenEventProperty):
    """Represents the state event property that detect opening of something."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) in (
                binary_sensor.BinarySensorDeviceClass.DOOR,
                binary_sensor.BinarySensorDeviceClass.GARAGE_DOOR,
                binary_sensor.BinarySensorDeviceClass.WINDOW,
                binary_sensor.BinarySensorDeviceClass.OPENING,
            )

        return False


@STATE_PROPERTIES_REGISTRY.register
class MotionStateEventProperty(StateEventProperty, MotionEventProperty):
    """Represents the state event property that detect motion, presence or occupancy."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) in (
                binary_sensor.BinarySensorDeviceClass.MOTION,
                binary_sensor.BinarySensorDeviceClass.OCCUPANCY,
                binary_sensor.BinarySensorDeviceClass.PRESENCE,
            )

        return False


@STATE_PROPERTIES_REGISTRY.register
class GasStateEventProperty(StateEventProperty, GasEventProperty):
    """Represents the state event property that detect gas presence."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.BinarySensorDeviceClass.GAS

        return False


@STATE_PROPERTIES_REGISTRY.register
class SmokeStateEventProperty(StateEventProperty, SmokeEventProperty):
    """Represents the state event property that detect smoke presence."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.BinarySensorDeviceClass.SMOKE

        return False


@STATE_PROPERTIES_REGISTRY.register
class BatteryLevelStateEvent(StateEventProperty, BatteryLevelEventProperty):
    """Represents the state event property that detect low level of a battery."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.BinarySensorDeviceClass.BATTERY

        return False


@STATE_PROPERTIES_REGISTRY.register
class WaterLevelStateEventProperty(StateEventProperty, WaterLevelEventProperty):
    """Represents the state event property that detect low level of water."""

    instance = EventPropertyInstance.WATER_LEVEL

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == "water_level"

        return False


@STATE_PROPERTIES_REGISTRY.register
class WaterLeakStateEventProperty(StateEventProperty, WaterLeakEventProperty):
    """Represents the state event property that detect water leakage."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.BinarySensorDeviceClass.MOISTURE

        return False


@STATE_PROPERTIES_REGISTRY.register
class ButtonPressStateEventProperty(StateEventProperty, ButtonPressEventProperty):
    """Represents the state property that detect a button interaction."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BUTTON:
            return True

        if self._entry_data.get_entity_config(self.device_id).get(CONF_DEVICE_CLASS) == DEVICE_CLASS_BUTTON:
            return True

        possible_actions = self._supported_native_values
        possible_actions.extend(
            [
                "long_click_release",
                "release",
            ]
        )

        if self.state.domain == binary_sensor.DOMAIN:
            return self.state.attributes.get("last_action") in possible_actions

        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get("action") in possible_actions

        return False

    def _get_native_value(self) -> str | None:
        """Return the current property value without conversion."""
        for value in [self.state.attributes.get("last_action"), self.state.attributes.get("action"), self.state.state]:
            value = str(value).lower()
            if value in self._supported_native_values:
                return value

        return None


@STATE_PROPERTIES_REGISTRY.register
class VibrationStateEventProperty(StateEventProperty, VibrationEventProperty):
    """Represents the state event property that detect vibration."""

    @property
    def supported(self) -> bool:
        """Test if the property is supported."""
        if self.state.domain == binary_sensor.DOMAIN:
            if self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.BinarySensorDeviceClass.VIBRATION:
                return True

            return self.state.attributes.get("last_action") in self._supported_native_values

        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get("action") in self._supported_native_values

        return False

    def _get_native_value(self) -> str | None:
        """Return the current property value without conversion."""
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == binary_sensor.BinarySensorDeviceClass.VIBRATION:
            return self.state.state

        for value in [self.state.attributes.get("last_action"), self.state.attributes.get("action")]:
            value = str(value).lower()
            if value in self._supported_native_values:
                return value

        return None
