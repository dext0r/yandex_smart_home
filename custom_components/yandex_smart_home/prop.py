"""Implement the Yandex Smart Home properties."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Optional, Type

from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State

from . import const
from .const import (
    CONF_PRESSURE_UNIT,
    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
    PRESSURE_FROM_PASCAL,
    PRESSURE_TO_PASCAL,
    STATE_EMPTY,
    STATE_NONE,
    STATE_NONE_UI,
)
from .error import SmartHomeError
from .helpers import Config

_LOGGER = logging.getLogger(__name__)

PREFIX_PROPERTIES = 'devices.properties.'

PROPERTIES: list[Type[AbstractProperty]] = []


def register_property(prop):
    """Decorate a function to register a property."""
    PROPERTIES.append(prop)
    return prop


class AbstractProperty(ABC):
    """Represents a Property."""

    type = ''
    instance = ''
    values = []
    retrievable = True

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        """Initialize a trait for a state."""
        self.hass = hass
        self.config = config
        self.state = state

        self.entity_config = config.get_entity_config(state.entity_id)
        self.reportable = config.is_reporting_state

    @abstractmethod
    def supported(self) -> bool:
        pass

    def description(self):
        """Return description for a devices request."""
        response = {
            'type': self.type,
            'retrievable': self.retrievable,
            'reportable': self.reportable,
        }
        parameters = self.parameters()
        if parameters is not None:
            response['parameters'] = parameters

        return response

    def get_state(self):
        """Return the state of this property for this entity."""
        value = self.get_value()
        return {
            'type': self.type,
            'state': {
                'instance': self.instance,
                'value': value
            }
        } if value is not None else None

    @abstractmethod
    def parameters(self):
        """Return parameters for a devices request."""
        pass

    @abstractmethod
    def get_value(self):
        """Return the state value of this capability for this entity."""
        pass

    def float_value(self, value: Any) -> Optional[float]:
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )

    def convert_value(self, value: Any, from_unit: Optional[str]):
        float_value = self.float_value(value)
        if float_value is None:
            return None

        if self.instance == const.FLOAT_INSTANCE_PRESSURE:
            if from_unit not in PRESSURE_TO_PASCAL:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    f'Unsupported pressure unit "{from_unit}" '
                    f'for {self.instance} instance of {self.state.entity_id}'
                )

            return round(
                float_value * PRESSURE_TO_PASCAL[from_unit] *
                PRESSURE_FROM_PASCAL[self.config.settings[CONF_PRESSURE_UNIT]], 2
            )
        elif self.instance == const.FLOAT_INSTANCE_TVOC:
            # average molecular weight of tVOC = 110 g/mol
            CONCENTRATION_TO_MCG_M3 = {
                CONCENTRATION_PARTS_PER_BILLION: 4.49629381184,
                CONCENTRATION_PARTS_PER_MILLION: 4496.29381184,
                CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT: 35.3146667215,
                CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER: 1000,
                CONCENTRATION_MICROGRAMS_PER_CUBIC_METER: 1
            }

            return round(float_value * CONCENTRATION_TO_MCG_M3.get(from_unit, 1), 2)

        return value
