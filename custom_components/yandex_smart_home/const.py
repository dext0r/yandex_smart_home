"""Constants for Yandex Smart Home."""
from enum import StrEnum

DOMAIN = "yandex_smart_home"
CONFIG_ENTRY_TITLE = "Yandex Smart Home"

CONF_SETTINGS = "settings"
CONF_PRESSURE_UNIT = "pressure_unit"
CONF_BETA = "beta"
CONF_CLOUD_STREAM = "cloud_stream"
CONF_NOTIFIER = "notifier"
CONF_NOTIFIER_OAUTH_TOKEN = "oauth_token"
CONF_NOTIFIER_SKILL_ID = "skill_id"
CONF_NOTIFIER_USER_ID = "user_id"
CONF_CONNECTION_TYPE = "connection_type"
CONF_CLOUD_INSTANCE = "cloud_instance"
CONF_CLOUD_INSTANCE_ID = "id"
CONF_CLOUD_INSTANCE_PASSWORD = "password"
CONF_CLOUD_INSTANCE_CONNECTION_TOKEN = "token"
CONF_USER_ID = "user_id"
CONF_COLOR_PROFILE = "color_profile"
CONF_ENTITY_CONFIG = "entity_config"
CONF_FILTER = "filter"
CONF_NAME = "name"
CONF_ROOM = "room"
CONF_TYPE = "type"
CONF_TURN_ON = "turn_on"
CONF_TURN_OFF = "turn_off"
CONF_DEVICE_CLASS = "device_class"
CONF_FEATURES = "features"
CONF_SUPPORT_SET_CHANNEL = "support_set_channel"
CONF_STATE_UNKNOWN = "state_unknown"
CONF_ERROR_CODE_TEMPLATE = "error_code_template"
CONF_ENTITY_PROPERTY_ENTITY = "entity"
CONF_ENTITY_PROPERTY_TYPE = "type"
CONF_ENTITY_PROPERTY_ATTRIBUTE = "attribute"
CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT = "unit_of_measurement"
CONF_ENTITY_PROPERTIES = "properties"
CONF_ENTITY_RANGE = "range"
CONF_ENTITY_RANGE_MIN = "min"
CONF_ENTITY_RANGE_MAX = "max"
CONF_ENTITY_RANGE_PRECISION = "precision"
CONF_ENTITY_MODE_MAP = "modes"
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID = "state_entity_id"
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE = "state_attribute"
CONF_ENTITY_CUSTOM_MODES = "custom_modes"
CONF_ENTITY_CUSTOM_MODE_SET_MODE = "set_mode"
CONF_ENTITY_CUSTOM_TOGGLES = "custom_toggles"
CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON = "turn_on"
CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF = "turn_off"
CONF_ENTITY_CUSTOM_RANGES = "custom_ranges"
CONF_ENTITY_CUSTOM_RANGE_SET_VALUE = "set_value"
CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE = "increase_value"
CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE = "decrease_value"
CONF_DEVICES_DISCOVERED = "devices_discovered"

CLOUD_BASE_URL = "https://yaha-cloud.ru"
CLOUD_STREAM_BASE_URL = "https://stream.yaha-cloud.ru"
EVENT_DEVICE_ACTION = "yandex_smart_home_device_action"

# Fake device class
DEVICE_CLASS_BUTTON = "button"

# Additional states
STATE_NONE = "none"
STATE_NONE_UI = "-"
STATE_EMPTY = ""
STATE_CHARGING = "charging"
STATE_LOW = "low"

# Additional attributes
ATTR_CURRENT = "current"
ATTR_ILLUMINANCE = "illuminance"
ATTR_LOAD_POWER = "load_power"
ATTR_CURRENT_CONSUMPTION = "current_consumption"
ATTR_POWER = "power"
ATTR_TVOC = "total_volatile_organic_compounds"
ATTR_WATER_LEVEL = "water_level"

# Integration xiaomi_airpurifier
ATTR_TARGET_HUMIDITY = "target_humidity"
DOMAIN_XIAOMI_AIRPURIFIER = "xiaomi_miio_airpurifier"
MODEL_PREFIX_XIAOMI_AIRPURIFIER = "zhimi."
SERVICE_FAN_SET_TARGET_HUMIDITY = "fan_set_target_humidity"

# https://github.com/syssi/xiaomi_airpurifier#service-fanset_preset_mode
XIAOMI_FAN_PRESET_LEVEL_1 = "Level 1"
XIAOMI_FAN_PRESET_LEVEL_2 = "Level 2"
XIAOMI_FAN_PRESET_LEVEL_3 = "Level 3"
XIAOMI_FAN_PRESET_LEVEL_4 = "Level 4"
XIAOMI_FAN_PRESET_LEVEL_5 = "Level 5"

# https://github.com/home-assistant/core/blob/d5a8f1af1d2dc74a12fb6870a4f1cb5318f88bf9/homeassistant/components/xiaomi_miio/fan.py#L744
XIAOMI_FAN_PRESET_NATURE = "Nature"
XIAOMI_FAN_PRESET_NORMAL = "Normal"

# https://github.com/ollo69/ha-smartthinq-sensors/blob/2d6212c9e060dc1d4947e1fed195af154442b941/custom_components/smartthinq_sensors/wideq/ac.py#L141
SMARTTHINQ_FAN_PRESET_NATURE = "NATURE"

# https://github.com/home-assistant/core/blob/6830eec549c372946b19035000c10afecd2f2da3/homeassistant/components/xiaomi_miio/fan.py#L275
XIAOMI_AIRPURIFIER_PRESET_AUTO = "Auto"
XIAOMI_AIRPURIFIER_PRESET_SILENT = "Silent"
XIAOMI_AIRPURIFIER_PRESET_LOW = "Low"
XIAOMI_AIRPURIFIER_PRESET_FAVORITE = "Favorite"
XIAOMI_AIRPURIFIER_PRESET_IDLE = "Idle"
XIAOMI_AIRPURIFIER_PRESET_MEDIUM = "Medium"
XIAOMI_AIRPURIFIER_PRESET_HIGH = "High"
XIAOMI_AIRPURIFIER_PRESET_STRONG = "Strong"
XIAOMI_AIRPURIFIER_PRESET_FAN = "Fan"
XIAOMI_AIRPURIFIER_PRESET_MIDDLE = "Middle"

# https://github.com/home-assistant/core/blob/d5a8f1af1d2dc74a12fb6870a4f1cb5318f88bf9/homeassistant/components/xiaomi_miio/humidifier.py#L316
XIAOMI_HUMIDIFIER_PRESET_MID = "Mid"

# https://github.com/airens/tion_home_assistant#climateset_fan_mode
TION_FAN_SPEED_1 = "1"
TION_FAN_SPEED_2 = "2"
TION_FAN_SPEED_3 = "3"
TION_FAN_SPEED_4 = "4"
TION_FAN_SPEED_5 = "5"
TION_FAN_SPEED_6 = "6"

# https://github.com/home-assistant/core/pull/67743
FAN_SPEED_OFF = "off"
FAN_SPEED_LOW = "low"
FAN_SPEED_MEDIUM = "medium"
FAN_SPEED_HIGH = "high"

# https://github.com/dmitry-k/yandex_smart_home/issues/173
FAN_SPEED_MIN = "min"
FAN_SPEED_MAX = "max"

# https://github.com/dmitry-k/yandex_smart_home/issues/347
FAN_SPEED_MID = "mid"

# https://github.com/dext0r/yandex_smart_home/issues/440
FAN_SPEED_LOW_MID = "low_mid"
FAN_SPEED_MID_HIGH = "mid_high"

# SmartIR
FAN_SPEED_HIGHEST = "highest"

# https://github.com/humbertogontijo/python-roborock/blob/1616217a06e20d51921de984134555bcc0775a92/roborock/code_mappings.py#L61
CLEANUP_MODE_OFF = "off"
CLEANUP_MODE_SILENT = "silent"
CLEANUP_MODE_BALANCED = "balanced"
CLEANUP_MODE_TURBO = "turbo"
CLEANUP_MODE_MAX = "max"
CLEANUP_MODE_MAX_PLUS = "max_plus"
CLEANUP_MODE_CUSTOM = "custom"


class ConnectionType(StrEnum):
    """Valid connection type."""

    DIRECT = "direct"
    CLOUD = "cloud"


class MediaPlayerFeature(StrEnum):
    """Media player feature that user can force enable."""

    VOLUME_MUTE = "volume_mute"
    VOLUME_SET = "volume_set"
    NEXT_PREVIOUS_TRACK = "next_previous_track"
    SELECT_SOURCE = "select_source"
    TURN_ON_OFF = "turn_on_off"
    PLAY_PAUSE = "play_pause"
    PLAY_MEDIA = "play_media"
