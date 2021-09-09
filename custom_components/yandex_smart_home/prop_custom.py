"""Implement the Yandex Smart Home custom properties."""
from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State

from . import const
from .const import (
    CONF_ENTITY_PROPERTY_ATTRIBUTE,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
    CONF_PRESSURE_UNIT,
    ERR_DEVICE_UNREACHABLE,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    PRESSURE_UNITS_TO_YANDEX_UNITS,
    PROPERTY_TYPE_EVENT_VALUES,
    PROPERTY_TYPE_TO_UNITS,
    STATE_EMPTY,
    STATE_NONE,
    STATE_NONE_UI,
)
from .error import SmartHomeError
from .helpers import Config
from .prop import _Property
from .prop_event import PROPERTY_EVENT
from .prop_float import PROPERTY_FLOAT

_LOGGER = logging.getLogger(__name__)


class CustomEntityProperty(_Property):
    """Represents a Property."""

    def __init__(self, hass: HomeAssistant, config: Config, state: State, property_config: dict[str, str]):
        super().__init__(hass, config, state)

        self.type = PROPERTY_FLOAT
        self.property_config = property_config
        self.instance = property_config[CONF_ENTITY_PROPERTY_TYPE]
        self.instance_unit: Optional[str] = None
        self.property_state = state

        if self.property_entity_id:
            self.property_state = self.hass.states.get(self.property_entity_id)
            if self.property_state is None:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Entity {self.property_entity_id} not found for {self.instance} instance of {self.state.entity_id}'
                )

        if self.property_state.domain == binary_sensor.DOMAIN:
            if self.instance not in PROPERTY_TYPE_EVENT_VALUES:
                raise SmartHomeError(
                    ERR_DEVICE_UNREACHABLE,
                    f'Unsupported entity {self.property_state.entity_id} for {self.instance} instance '
                    f'of {self.state.entity_id}'
                )

            self.type = PROPERTY_EVENT
            self.values = PROPERTY_TYPE_EVENT_VALUES.get(self.instance)
        elif self.property_state.domain == sensor.DOMAIN:
            if self.instance not in PROPERTY_TYPE_TO_UNITS and self.instance in PROPERTY_TYPE_EVENT_VALUES:
                # TODO: battery_level and water_level cannot be events for sensor domain
                self.type = PROPERTY_EVENT
                self.values = PROPERTY_TYPE_EVENT_VALUES.get(self.instance)

        if self.instance in [const.PROPERTY_TYPE_BUTTON, const.PROPERTY_TYPE_VIBRATION]:
            self.retrievable = False

        if self.type == PROPERTY_FLOAT:
            self.instance_unit = PROPERTY_TYPE_TO_UNITS[self.instance]

            if self.instance == const.PROPERTY_TYPE_PRESSURE:
                self.instance_unit = PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]]

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        return True

    def parameters(self):
        if self.type == PROPERTY_FLOAT:
            return {
                'instance': self.instance,
                'unit': self.instance_unit
            }
        elif self.type == PROPERTY_EVENT:
            return {
                'instance': self.instance,
                'events': [
                    {'value': v}
                    for v in self.values
                ]
            }

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

        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            if self.type == PROPERTY_FLOAT:
                return None

            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for {self.instance} instance of {self.state.entity_id}'
            )

        if self.instance in [const.PROPERTY_TYPE_PRESSURE, const.PROPERTY_TYPE_TVOC]:
            value_unit = self.property_config.get(CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT,
                                                  self.property_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))
            return self.convert_value(value, value_unit)

        return self.float_value(value) if self.type != PROPERTY_EVENT else self.event_value(value)

    @property
    def property_entity_id(self) -> str | None:
        return self.property_config.get(CONF_ENTITY_PROPERTY_ENTITY)
