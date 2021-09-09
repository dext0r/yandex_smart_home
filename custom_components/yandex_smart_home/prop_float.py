"""Implement the Yandex Smart Home float properties."""
from __future__ import annotations

from abc import ABC
import logging

from homeassistant.components import air_quality, climate, fan, humidifier, light, sensor, switch
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    ATTR_VOLTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
)

from . import const
from .const import CONF_PRESSURE_UNIT, PRESSURE_UNIT_MMHG, PRESSURE_UNITS_TO_YANDEX_UNITS
from .prop import PREFIX_PROPERTIES, AbstractProperty, register_property

_LOGGER = logging.getLogger(__name__)

PROPERTY_FLOAT = PREFIX_PROPERTIES + 'float'
PROPERTY_FLOAT_INSTANCE_TO_UNITS = {
    const.FLOAT_INSTANCE_HUMIDITY: 'unit.percent',
    const.FLOAT_INSTANCE_TEMPERATURE: 'unit.temperature.celsius',
    const.FLOAT_INSTANCE_PRESSURE: PRESSURE_UNITS_TO_YANDEX_UNITS[PRESSURE_UNIT_MMHG],
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

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': PROPERTY_FLOAT_INSTANCE_TO_UNITS[self.instance]
        }


@register_property
class TemperatureProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_TEMPERATURE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_TEMPERATURE
        elif domain == air_quality.DOMAIN:
            return attributes.get(climate.ATTR_TEMPERATURE) is not None
        elif domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return attributes.get(climate.ATTR_CURRENT_TEMPERATURE) is not None

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(climate.ATTR_TEMPERATURE))
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get(climate.ATTR_CURRENT_TEMPERATURE))


@register_property
class HumidityProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_HUMIDITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_HUMIDITY
        elif domain == air_quality.DOMAIN:
            return attributes.get(climate.ATTR_HUMIDITY) is not None
        elif domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return attributes.get(climate.ATTR_CURRENT_HUMIDITY) is not None

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(climate.ATTR_HUMIDITY))
        elif self.state.domain in (climate.DOMAIN, fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get(climate.ATTR_CURRENT_HUMIDITY))


@register_property
class PressureProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_PRESSURE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        # TODO: check pressure unit
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_PRESSURE

        return False

    def parameters(self):
        return {
            'instance': self.instance,
            'unit': PRESSURE_UNITS_TO_YANDEX_UNITS[self.config.settings[CONF_PRESSURE_UNIT]],
        }

    def get_value(self):
        return self.convert_value(self.state.state, self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT))


@register_property
class IlluminanceProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_ILLUMINATION

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain in (sensor.DOMAIN, light.DOMAIN, fan.DOMAIN):
            return 'illuminance' in attributes or attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_ILLUMINANCE

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (light.DOMAIN, fan.DOMAIN):
            return self.float_value(self.state.attributes.get('illuminance'))


@register_property
class WaterLevelProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_WATER_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain in (fan.DOMAIN, humidifier.DOMAIN):
            return 'water_level' in attributes

        return False

    def get_value(self):
        if self.state.domain in (fan.DOMAIN, humidifier.DOMAIN):
            return self.float_value(self.state.attributes.get('water_level'))


@register_property
class CO2Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_CO2_LEVEL

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CO2
        elif domain in (air_quality.DOMAIN, fan.DOMAIN):
            return air_quality.ATTR_CO2 in attributes

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (air_quality.DOMAIN, fan.DOMAIN):
            return self.float_value(self.state.attributes.get(air_quality.ATTR_CO2))


@register_property
class PM1Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_PM1_DENSITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_0_1 in attributes

        return False

    def get_value(self):
        if self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_0_1))


@register_property
class PM25Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_PM2_5_DENSITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_2_5 in attributes

        return False

    def get_value(self):
        value = 0
        if self.state.domain == air_quality.DOMAIN:
            value = self.state.attributes.get(air_quality.ATTR_PM_2_5)

        return self.float_value(value)


@register_property
class PM10Property(FloatProperty):
    instance = const.FLOAT_INSTANCE_PM10_DENSITY

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == air_quality.DOMAIN:
            return air_quality.ATTR_PM_10 in attributes

        return False

    def get_value(self):
        if self.state.domain == air_quality.DOMAIN:
            return self.float_value(self.state.attributes.get(air_quality.ATTR_PM_10))


@register_property
class TVOCProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_TVOC

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        # TODO: add check for ATTR_UNIT_OF_MEASUREMENT
        if domain == air_quality.DOMAIN:
            return 'total_volatile_organic_compounds' in attributes

        return False

    def get_value(self):
        if self.state.domain == air_quality.DOMAIN:
            return self.convert_value(
                self.state.attributes.get('total_volatile_organic_compounds'),
                self.state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            )


@register_property
class VoltageProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_VOLTAGE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_VOLTAGE
        elif domain in (switch.DOMAIN, light.DOMAIN):
            return ATTR_VOLTAGE in attributes

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            return self.float_value(self.state.attributes.get(ATTR_VOLTAGE))


@register_property
class CurrentProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_AMPERAGE

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_CURRENT
        elif domain in (switch.DOMAIN, light.DOMAIN):
            return 'current' in attributes

        return False

    def get_value(self):
        if self.state.domain == sensor.DOMAIN:
            return self.float_value(self.state.state)
        elif self.state.domain in (switch.DOMAIN, light.DOMAIN):
            return self.float_value(self.state.attributes.get('current'))


@register_property
class PowerProperty(FloatProperty):
    instance = const.FLOAT_INSTANCE_POWER

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        if domain == sensor.DOMAIN:
            return attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_POWER
        elif domain == switch.DOMAIN:
            return 'power' in attributes or 'load_power' in attributes

        return False

    def get_value(self):
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

    @staticmethod
    def supported(domain, features, entity_config, attributes):
        return ATTR_BATTERY_LEVEL in attributes or attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY

    def get_value(self):
        value = None
        if self.state.attributes.get(ATTR_DEVICE_CLASS) == DEVICE_CLASS_BATTERY:
            value = self.state.state
        elif ATTR_BATTERY_LEVEL in self.state.attributes:
            value = self.state.attributes.get(ATTR_BATTERY_LEVEL)

        if value in [const.STATE_LOW, const.STATE_CHARGING]:
            return 0

        return self.float_value(value)
