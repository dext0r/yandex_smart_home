"""Constants for Yandex Smart Home."""
from homeassistant.components import (
    binary_sensor,
    camera,
    climate,
    cover,
    fan,
    group,
    input_boolean,
    light,
    lock,
    media_player,
    scene,
    script,
    switch,
    vacuum,
)
DOMAIN = 'yandex_smart_home'

CONF_ENTITY_CONFIG = 'entity_config'
CONF_FILTER = 'filter'
CONF_ROOM = 'room'


PREFIX_TYPES = 'devices.types.'
TYPE_LIGHT = PREFIX_TYPES + 'light'
TYPE_SOCKET = PREFIX_TYPES + 'socket'
TYPE_SWITCH = PREFIX_TYPES + 'switch'
TYPE_THERMOSTAT = PREFIX_TYPES + 'thermostat'
TYPE_THERMOSTAT_AC = PREFIX_TYPES + 'thermostat.ac'
TYPE_MEDIA_DEVICE = PREFIX_TYPES + 'media_device'
TYPE_MEDIA_DEVICE_TV = PREFIX_TYPES + 'media_device.tv'
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
    cover.DOMAIN: TYPE_OTHER,
    fan.DOMAIN: TYPE_THERMOSTAT,
    group.DOMAIN: TYPE_SWITCH,
    input_boolean.DOMAIN: TYPE_SWITCH,
    light.DOMAIN: TYPE_LIGHT,
    lock.DOMAIN: TYPE_OTHER,
    media_player.DOMAIN: TYPE_MEDIA_DEVICE,
    scene.DOMAIN: TYPE_OTHER,
    script.DOMAIN: TYPE_OTHER,
    switch.DOMAIN: TYPE_SWITCH,
    vacuum.DOMAIN: TYPE_OTHER,
}

DEVICE_CLASS_TO_YANDEX_TYPES = {
    (media_player.DOMAIN, media_player.DEVICE_CLASS_TV): TYPE_MEDIA_DEVICE_TV,
}
