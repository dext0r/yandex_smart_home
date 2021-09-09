"""Implement the Yandex Smart Home float properties."""
from __future__ import annotations

from abc import ABC
import logging
from typing import Any

from homeassistant.components import air_quality, climate, fan, humidifier, light, sensor, switch
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from . import const
from .const import CONF_PRESSURE_UNIT, ERR_NOT_SUPPORTED_IN_CURRENT_MODE, STATE_EMPTY, STATE_NONE, STATE_NONE_UI
from .error import SmartHomeError
from .prop import PREFIX_PROPERTIES, AbstractProperty, register_property

_LOGGER = logging.getLogger(__name__)

PROPERTY_FLOAT = PREFIX_PROPERTIES + 'float'
PRESSURE_UNITS_TO_YANDEX_UNITS = {
    const.PRESSURE_UNIT_PASCAL: 'unit.pressure.pascal',
    const.PRESSURE_UNIT_MMHG: 'unit.pressure.mmhg',
    const.PRESSURE_UNIT_ATM: 'unit.pressure.atm',
    const.PRESSURE_UNIT_BAR: 'unit.pressure.bar'
}
PRESSURE_TO_PASCAL = {
    const.PRESSURE_UNIT_PASCAL: 1,
    const.PRESSURE_UNIT_HECTOPASCAL: 100,
    const.PRESSURE_UNIT_KILOPASCAL: 1000,
    const.PRESSURE_UNIT_MEGAPASCAL: 1000000,
    const.PRESSURE_UNIT_MMHG: 133.322,
    const.PRESSURE_UNIT_ATM: 101325,
    const.PRESSURE_UNIT_BAR: 100000,
    const.PRESSURE_UNIT_MBAR: 0.01
}
PRESSURE_FROM_PASCAL = {
    const.PRESSURE_UNIT_PASCAL: 1,
    const.PRESSURE_UNIT_MMHG: 0.00750061575846,
    const.PRESSURE_UNIT_ATM: 0.00000986923266716,
    const.PRESSURE_UNIT_BAR: 0.00001,
}
# average molecular weight of tVOC = 110 g/mol
TVOC_CONCENTRATION_TO_MCG_M3 = {
    CONCENTRATION_PARTS_PER_BILLION: 4.49629381184,
    CONCENTRATION_PARTS_PER_MILLION: 4496.29381184,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT: 35.3146667215,
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER: 1000,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER: 1
}
PROPERTY_FLOAT_INSTANCE_TO_UNITS = {
    const.FLOAT_INSTANCE_HUMIDITY: 'unit.percent',
    const.FLOAT_INSTANCE_TEMPERATURE: 'unit.temperature.celsius',
    const.FLOAT_INSTANCE_PRESSURE: PRESSURE_UNITS_TO_YANDEX_UNITS[const.PRESSURE_UNIT_MMHG],
    const.FLOAT_INSTANCE_WATER_LEVEL: 'unit.percent',
    const.FLOAT_INSTANCE_CO2_LEVEL: 'unit.ppm',
    const.FLOAT_INSTANCE_POWER: 'unit.watt',
    const.FLOAT_INSTANCE_VOLTAGE: 'unit.volt',
    const.FLOAT_INSTANCE_BATTERY_LEVEL: 'unit.percent',
    const.FLOAT_INSTANCE_AMPERAGE: 'unit.ampere',
    const.FLOAT_INSTANCE_ILLUMINATION: 'unit.illumination.lux',
    const.FLOAT_INSTANCE_TVOC: 'unit.density.mcg_m3',
    const.FLOAT_INSTANCE_PM1_DENSITY: 'unit.density.mcg_m3',
    const.FLOAT_INSTANCE_PM2_5_DENSITY: 'unit.density.mcg_m3',
    const.FLOAT_INSTANCE_PM10_DENSITY: 'unit.density.mcg_m3'
}


class FloatProperty(AbstractProperty, ABC):
    type = PROPERTY_FLOAT

    def parameters(self) -> dict[str, Any]:
        return {
            'instance': self.instance,
            'unit': PROPERTY_FLOAT_INSTANCE_TO_UNITS[self.instance]
        }

    def float_value(self, value: Any) -> float | None:
        if str(value).lower() in (STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE, STATE_NONE_UI, STATE_EMPTY):
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unsupported value {value!r} for instance {self.instance} of {self.state.entity_id}'
            )

    def convert_value(self, value: Any, from_unit: str | None) -> float | None:
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
            return round(float_value * TVOC_CONCENTRATION_TO_MCG_M3.get(from_unit, 1), 2)

        return value


@register_property
class TemperatureProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_TEMPERATURE

    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_TEMPERATURE
        elif self.state.domain == air_quality.DOMAIN:
            return self.state.attributes.get(climate.ATTR_TEMPERATURE) is not None
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE) is not None

        return False

    def get_value(self) -> float | None:
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(climate.ATTR_TEMPERATURE))
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE))


@register_property
class HumidityProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_HUMIDITY

    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_HUMIDITY
        elif self.state.domain == air_quality.DOMAIN:
            return self.state.attributes.get(climate.ATTR_HUMIDITY) is not None
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY) is not None

        return False

    def get_value(self) -> float | None:
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(climate.ATTR_HUMIDITY))
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY))


@register_property
class PressureProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_PRESSURE

    def supported(self) -> bool:
        # TODO: check pressure unit
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_PRESSURE

        return False

    def parameters(self) -> dict[str, Any]:
        return {
            'instance': self.instance,
            'unit': PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]],
        }

    def get_value(self) -> float | None:
        return self.convert_value(self.state.state, self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))


@register_property
class IlluminanceProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_ILLUMINATION

    def supported(self) -> bool:
        if self.state.domain in (sensor.DOMAIN, light.DOMAIN, fan.DOMAIN):
            if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_ILLUMINANCE:
                return True

            return 'illuminance' in self.state.attributes

        return False

    def get_value(self) -> float | None:
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)

        return self.float_value(self.state.attributes.get('illuminance'))


@register_property
class WaterLevelProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_WATER_LEVEL

    def supported(self) -> bool:
        if self.state.domain in (fan.DOMAIN, humidifier.DOMAIN):
            return 'water_level' in self.state.attributes

        return False

    def get_value(self) -> float | None:
        return self.float_value(self.state.attributes.get('water_level'))


@register_property
class CO2Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_CO2_LEVEL

    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CO2
        elif self.state.domain in (air_quality.DOMAIN, fan.DOMAIN):
            return air_quality.ATTR_CO2 in self.state.attributes

        return False

    def get_value(self) -> float | None:
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)

        return self.float_value(self.state.attributes.get(air_quality.ATTR_CO2))


@register_property
class PM1Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_PM1_DENSITY

    def supported(self) -> bool:
        if self.state.domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_0_1 in self.state.attributes

        return False

    def get_value(self) -> float | None:
        return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_0_1))


@register_property
class PM25Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_PM2_5_DENSITY

    def supported(self) -> bool:
        if self.state.domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_2_5 in self.state.attributes

        return False

    def get_value(self) -> float | None:
        return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_2_5))


@register_property
class PM10Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_PM10_DENSITY

    def supported(self) -> bool:
        if self.state.domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_10 in self.state.attributes

        return False

    def get_value(self) -> float | None:
        return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_10))


@register_property
class TVOCProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_TVOC

    def supported(self) -> bool:
        # TODO: add check for ATTR_UNIT_OF_MEASUREMENT
        if self.state.domain == air_quality.DOMAIN:
            return 'total_volatile_organic_compounds' in self.state.attributes

        return False

    def get_value(self) -> float | None:
        return self.convert_value(
            self.state.attributes.get('total_volatile_organic_compounds'),
            self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        )


@register_property
class VoltageProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_VOLTAGE

    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_VOLTAGE
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            return ATTR_VOLTAGE in self.state.attributes

        return False

    def get_value(self) -> float | None:
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)

        return self.float_value(self.state.attributes.get(ATTR_VOLTAGE))


@register_property
class CurrentProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_AMPERAGE

    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CURRENT
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            return 'current' in self.state.attributes

        return False

    def get_value(self) -> float | None:
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)

        return self.float_value(self.state.attributes.get('current'))


@register_property
class PowerProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_POWER

    def supported(self) -> bool:
        if self.state.domain == sensor.DOMAIN:
            return self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_POWER
        elif self.state.domain == switch.DOMAIN:
            return 'power' in self.state.attributes or 'load_power' in self.state.attributes

        return False

    def get_value(self) -> float | None:
        value = None
        if self.state.domain == sensor.DOMAIN:
            value = self.state.state
        elif self.state.domain == switch.DOMAIN:
            if 'power' in self.state.attributes:
                value = self.state.attributes.get('power')
            elif 'load_power' in self.state.attributes:
                value = self.state.attributes.get('load_power')

        return self.float_value(value)


@register_property
class BatteryLevelProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_BATTERY_LEVEL

    def supported(self) -> bool:
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY:
            return True

        return ATTR_BATTERY_LEVEL in self.state.attributes

    def get_value(self) -> float | None:
        value = None
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY:
            value = self.state.state
        elif ATTR_BATTERY_LEVEL in self.state.attributes:
            value = self.state.attributes.get(ATTR_BATTERY_LEVEL)

        if value in [const.STATE_LOW, const.STATE_CHARGING]:
            return 0

        return self.float_value(value)
