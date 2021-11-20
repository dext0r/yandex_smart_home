"""Implement the Yandex Smart Home custom properties."""
from __future__ import annotations

from abc import ABC
import logging
from typing import Any

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, State

from . import const
from .const import (
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
    ERR_DEVICE_UNREACHABLE,
    EVENT_INSTANCES,
    FLOAT_INSTANCES,
)
from .error import SmartHomeError
from .helpers import Config
from .prop import AbstractProperty
from .prop_event import EventProperty
from .prop_float import PRESSURE_UNITS_TO_YANDEX_UNITS, PROPERTY_FLOAT_INSTANCE_TO_UNITS, FloatProperty

_LOGGER = logging.getLogger(__name__)


class CustomEntityProperty(AbstractProperty, ABC):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 property_state: State, property_config: dict[str, Any]):
        self.instance = property_config[CONF_ENTITY_PROPERTY_TYPE]
        self.property_config = property_config
        self.property_state = property_state

        super().__init__(hass, config, state)

    @classmethod
    def get(cls, hass: HomeAssistant, config: Config, state: State,
            property_config: dict[str, Any]) -> CustomEventEntityProperty | CustomFloatEntityProperty:
        property_state = state
        property_entity_id = property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
        instance = property_config[CONF_ENTITY_PROPERTY_TYPE]

        if property_entity_id:
            property_state = hass.states.get(property_entity_id)
            if property_state is None:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Entity {property_entity_id} not found for {instance} instance of {state.entity_id}'
                )

        if property_state.domain == binary_sensor.DOMAIN:
            if instance not in EVENT_INSTANCES:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Unsupported entity {property_state.entity_id} for {instance} instance '
                    f'of {state.entity_id}'
                )

            return CustomEventEntityProperty(hass, config, state, property_state, property_config)
        elif property_state.domain == sensor.DOMAIN:
            if instance not in FLOAT_INSTANCES and instance in EVENT_INSTANCES:
                # TODO: battery_level and water_level cannot be events for sensor domain
                return CustomEventEntityProperty(hass, config, state, property_state, property_config)

        return CustomFloatEntityProperty(hass, config, state, property_state, property_config)

    def supported(self) -> bool:
        return True

    def get_value(self) -> str | float | None:
        if not self.retrievable:
            return None

        value_attribute = self.property_config.get(CONF_ENTITY_PROPERTY_ATTRIBUTE)

        if value_attribute:
            if value_attribute not in self.property_state.attributes:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Attribute {value_attribute} not found in entity {self.property_state.entity_id} '
                    f'for {self.instance} instance of {self.state.entity_id}'
                )

            value = self.property_state.attributes[value_attribute]
        else:
            value = self.property_state.state

        return value

    @property
    def property_entity_id(self) -> str | None:
        return self.property_config.get(CONF_ENTITY_PROPERTY_ENTITY)


class CustomFloatEntityProperty(CustomEntityProperty, FloatProperty):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 property_state: State, property_config: dict[str, str]):
        super().__init__(hass, config, state, property_state, property_config)

    @property
    def unit(self) -> str:
        if self.instance == const.FLOAT_INSTANCE_PRESSURE:
            return PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.pressure_unit]

        return PROPERTY_FLOAT_INSTANCE_TO_UNITS[self.instance]

    def get_value(self) -> float | None:
        value = super().get_value()

        if self.instance in [const.FLOAT_INSTANCE_PRESSURE, const.FLOAT_INSTANCE_TVOC]:
            value_unit = self.property_config.get(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
                                                  self.property_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))
            return self.convert_value(value, value_unit)

        return self.float_value(value)


class CustomEventEntityProperty(CustomEntityProperty, EventProperty):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 property_state: State, property_config: dict[str, str]):
        super().__init__(hass, config, state, property_state, property_config)

        if self.instance in [const.EVENT_INSTANCE_BUTTON, const.EVENT_INSTANCE_VIBRATION]:
            self.retrievable = False

    def get_value(self) -> str | None:
        return self.event_value(super().get_value())

    def supported(self) -> bool:
        return bool(self.config.beta)
