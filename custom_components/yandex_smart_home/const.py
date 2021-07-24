"""Constants for Yandex Smart Home."""
from homeassistant.components import (
    air_quality,
    binary_sensor,
    camera,
    climate,
    cover,
    fan,
    group,
    humidifier,
    input_boolean,
    light,
    lock,
    media_player,
    scene,
    script,
    sensor,
    switch,
    vacuum,
    water_heater
)
DOMAIN = 'yandex_smart_home'

CONFIG = 'yaml_config'
DATA_CONFIG = 'config'

CONF_SETTINGS = 'settings'
CONF_PRESSURE_UNIT = 'pressure_unit'
CONF_ENTITY_CONFIG = 'entity_config'
CONF_FILTER = 'filter'
CONF_ROOM = 'room'
CONF_TYPE = 'type'
CONF_ENTITY_PROPERTY_ENTITY = 'entity'
CONF_ENTITY_PROPERTY_TYPE = 'type'
CONF_ENTITY_PROPERTY_ATTRIBUTE = 'attribute'
CONF_ENTITY_PROPERTIES = 'properties'
CONF_CHANNEL_SET_VIA_MEDIA_CONTENT_ID = 'channel_set_via_media_content_id'
CONF_RELATIVE_VOLUME_ONLY = 'relative_volume_only'
CONF_ENTITY_RANGE = 'range'
CONF_ENTITY_RANGE_MIN = 'min'
CONF_ENTITY_RANGE_MAX = 'max'
CONF_ENTITY_RANGE_PRECISION = 'precision'
CONF_ENTITY_MODE_MAP = 'modes'

#notifier
CONF_NOTIFIER = 'notifier'
CONF_SKILL_OAUTH_TOKEN = 'oauth_token'
CONF_SKILL_ID = 'skill_id'
CONF_NOTIFIER_USER_ID = 'user_id'  
NOTIFIER_ENABLED = 'notifier_enabled'   
NOTIFIERS = 'notifiers' 

# https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/device-types.html/
PREFIX_TYPES = 'devices.types.'
TYPE_LIGHT = PREFIX_TYPES + 'light'
TYPE_SOCKET = PREFIX_TYPES + 'socket'
TYPE_SWITCH = PREFIX_TYPES + 'switch'
TYPE_THERMOSTAT = PREFIX_TYPES + 'thermostat'
TYPE_THERMOSTAT_AC = PREFIX_TYPES + 'thermostat.ac'
TYPE_MEDIA_DEVICE = PREFIX_TYPES + 'media_device'
TYPE_MEDIA_DEVICE_TV = PREFIX_TYPES + 'media_device.tv'
TYPE_MEDIA_DEVICE_TV_BOX = PREFIX_TYPES + 'media_device.tv_box'
TYPE_MEDIA_DEVICE_RECIEVER = PREFIX_TYPES + 'media_device.receiver'
TYPE_COOKING = PREFIX_TYPES + 'cooking'
TYPE_COFFEE_MAKER = PREFIX_TYPES + 'cooking.coffee_maker'
TYPE_KETTLE = PREFIX_TYPES + 'cooking.kettle'
TYPE_MULTICOOKER = PREFIX_TYPES + 'cooking.multicooker'
TYPE_OPENABLE = PREFIX_TYPES + 'openable'
TYPE_OPENABLE_CURTAIN = PREFIX_TYPES + 'openable.curtain'
TYPE_HUMIDIFIER = PREFIX_TYPES + 'humidifier'
TYPE_PURIFIER = PREFIX_TYPES + 'purifier'
TYPE_VACUUM_CLEANER = PREFIX_TYPES + 'vacuum_cleaner'
TYPE_WASHING_MACHINE = PREFIX_TYPES + 'washing_machine'
TYPE_DISHWASHER = PREFIX_TYPES + 'dishwasher'
TYPE_IRON = PREFIX_TYPES + 'iron'
TYPE_SENSOR = PREFIX_TYPES + 'sensor'
TYPE_OTHER = PREFIX_TYPES + 'other'

# Integration xiaomi_airpurifier
ATTR_TARGET_HUMIDITY = 'target_humidity'
DOMAIN_XIAOMI_AIRPURIFIER = 'xiaomi_miio_airpurifier'
MODEL_PREFIX_XIAOMI_AIRPURIFIER = 'zhimi.'
SERVICE_FAN_SET_TARGET_HUMIDITY = 'fan_set_target_humidity'

# Error codes
# https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/response-codes-docpage/
ERR_DEVICE_UNREACHABLE = "DEVICE_UNREACHABLE"
ERR_DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
ERR_INTERNAL_ERROR = 'INTERNAL_ERROR'
ERR_INVALID_ACTION = 'INVALID_ACTION'
ERR_INVALID_VALUE = 'INVALID_VALUE'
ERR_NOT_SUPPORTED_IN_CURRENT_MODE = 'NOT_SUPPORTED_IN_CURRENT_MODE'

# Event types
EVENT_ACTION_RECEIVED = 'yandex_smart_home_action'
EVENT_QUERY_RECEIVED = 'yandex_smart_home_query'
EVENT_DEVICES_RECEIVED = 'yandex_smart_home_devices'

# Pressure units
PRESSURE_UNIT_PASCAL = 'pa'
PRESSURE_UNIT_HECTOPASCAL = 'hPa'
PRESSURE_UNIT_KILOPASCAL = 'kPa'
PRESSURE_UNIT_MEGAPASCAL = 'MPa'
PRESSURE_UNIT_MMHG = 'mmHg'
PRESSURE_UNIT_ATM = 'atm'
PRESSURE_UNIT_BAR = 'bar'
PRESSURE_UNIT_MBAR = 'mbar'

PRESSURE_UNITS_TO_YANDEX_UNITS = {
    PRESSURE_UNIT_PASCAL: 'unit.pressure.pascal',
    PRESSURE_UNIT_MMHG: 'unit.pressure.mmhg',
    PRESSURE_UNIT_ATM: 'unit.pressure.atm',
    PRESSURE_UNIT_BAR: 'unit.pressure.bar'
}

# Multiplier to convert from given pressure unit to pascal
PRESSURE_TO_PASCAL = {
    PRESSURE_UNIT_PASCAL: 1,
    PRESSURE_UNIT_HECTOPASCAL: 100,
    PRESSURE_UNIT_KILOPASCAL: 1000,
    PRESSURE_UNIT_MEGAPASCAL: 1000000,
    PRESSURE_UNIT_MMHG: 133.322,
    PRESSURE_UNIT_ATM: 101325,
    PRESSURE_UNIT_BAR: 100000,
    PRESSURE_UNIT_MBAR: 0.01
}

# Additional states
STATE_NONE = 'none'

# Multiplier to convert from pascal to given pressure unit
PRESSURE_FROM_PASCAL = {
    PRESSURE_UNIT_PASCAL: 1,
    PRESSURE_UNIT_MMHG: 0.00750061575846,
    PRESSURE_UNIT_ATM: 0.00000986923266716,
    PRESSURE_UNIT_BAR: 0.00001,
}

DOMAIN_TO_YANDEX_TYPES = {
    binary_sensor.DOMAIN: TYPE_SENSOR,
    camera.DOMAIN: TYPE_OTHER,
    climate.DOMAIN: TYPE_THERMOSTAT,
    cover.DOMAIN: TYPE_OPENABLE_CURTAIN,
    fan.DOMAIN: TYPE_HUMIDIFIER,
    group.DOMAIN: TYPE_SWITCH,
    humidifier.DOMAIN: TYPE_HUMIDIFIER,
    input_boolean.DOMAIN: TYPE_SWITCH,
    light.DOMAIN: TYPE_LIGHT,
    lock.DOMAIN: TYPE_OPENABLE,
    media_player.DOMAIN: TYPE_MEDIA_DEVICE,
    scene.DOMAIN: TYPE_OTHER,
    script.DOMAIN: TYPE_OTHER,
    switch.DOMAIN: TYPE_SWITCH,
    vacuum.DOMAIN: TYPE_VACUUM_CLEANER,
    water_heater.DOMAIN: TYPE_KETTLE,
    sensor.DOMAIN: TYPE_SENSOR,
    air_quality.DOMAIN: TYPE_SENSOR,
}

DEVICE_CLASS_TO_YANDEX_TYPES = {
    (media_player.DOMAIN, media_player.DEVICE_CLASS_TV): TYPE_MEDIA_DEVICE_TV,
}
