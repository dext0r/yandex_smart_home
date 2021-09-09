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
    CONF_PRESSURE_UNIT,
    ERR_DEVICE_UNREACHABLE,
    PRESSURE_UNITS_TO_YANDEX_UNITS,
    PROPERTY_TYPE_EVENT_VALUES,
    PROPERTY_TYPE_TO_UNITS,
)
from .error import SmartHomeError
from .helpers import Config
from .prop import AbstractProperty
from .prop_event import EventProperty
from .prop_float import FloatProperty

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
            if instance not in PROPERTY_TYPE_EVENT_VALUES:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Unsupported entity {property_state.entity_id} for {instance} instance '
                    f'of {state.entity_id}'
                )

            return CustomEventEntityProperty(hass, config, state, property_state, property_config)
        elif property_state.domain == sensor.DOMAIN:
            if instance not in PROPERTY_TYPE_TO_UNITS and instance in PROPERTY_TYPE_EVENT_VALUES:
                # TODO: battery_level and water_level cannot be events for sensor domain
                return CustomEventEntityProperty(hass, config, state, property_state, property_config)

        return CustomFloatEntityProperty(hass, config, state, property_state, property_config)

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        return True

    def get_value(self):
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

        self.instance_unit = PROPERTY_TYPE_TO_UNITS[self.instance]

        if self.instance == const.PROPERTY_TYPE_PRESSURE:
            self.instance_unit = PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]]

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': self.instance_unit
        }

    def get_value(self):
        value = super().get_value()

        if self.instance in [const.PROPERTY_TYPE_PRESSURE, const.PROPERTY_TYPE_TVOC]:
            value_unit = self.property_config.get(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
                                                  self.property_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))
            return self.convert_value(value, value_unit)

        return self.float_value(value)


class CustomEventEntityProperty(CustomEntityProperty, EventProperty):
    def __init__(self, hass: HomeAssistant, config: Config, state: State,
                 property_state: State, property_config: dict[str, str]):
        super().__init__(hass, config, state, property_state, property_config)

        if self.instance in [const.PROPERTY_TYPE_BUTTON, const.PROPERTY_TYPE_VIBRATION]:
            self.retrievable = False

    def get_value(self):
        return self.event_value(super().get_value())
