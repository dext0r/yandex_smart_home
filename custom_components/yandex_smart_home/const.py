"""Constants for Yandex Smart Home."""
from homeassistant.components import (
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

# https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/device-types-docpage/
PREFIX_TYPES = 'devices.types.'
TYPE_LIGHT = PREFIX_TYPES + 'light'
TYPE_SOCKET = PREFIX_TYPES + 'socket'
TYPE_SWITCH = PREFIX_TYPES + 'switch'
TYPE_KETTLE = PREFIX_TYPES + 'cooking.kettle'
TYPE_THERMOSTAT = PREFIX_TYPES + 'thermostat'
TYPE_THERMOSTAT_AC = PREFIX_TYPES + 'thermostat.ac'
TYPE_MEDIA_DEVICE = PREFIX_TYPES + 'media_device'
TYPE_MEDIA_DEVICE_TV = PREFIX_TYPES + 'media_device.tv'
TYPE_OPENABLE = PREFIX_TYPES + 'openable'
TYPE_OPENABLE_CURTAIN = PREFIX_TYPES + 'openable.curtain'
TYPE_HUMIDIFIER = PREFIX_TYPES + 'humidifier'
TYPE_PURIFIER = PREFIX_TYPES + 'purifier'
TYPE_VACUUM_CLEANER = PREFIX_TYPES + 'vacuum_cleaner'
TYPE_OTHER = PREFIX_TYPES + 'other'

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

DOMAIN_TO_YANDEX_TYPES = {
    binary_sensor.DOMAIN: TYPE_OTHER,
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
    sensor.DOMAIN: TYPE_OTHER,
}

DEVICE_CLASS_TO_YANDEX_TYPES = {
    (media_player.DOMAIN, media_player.DEVICE_CLASS_TV): TYPE_MEDIA_DEVICE_TV,
}
