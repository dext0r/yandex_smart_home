"""Constants for Yandex Smart Home."""

from enum import StrEnum

DOMAIN = "yandex_smart_home"

CONF_SETTINGS = "settings"
CONF_PRESSURE_UNIT = "pressure_unit"
CONF_BETA = "beta"
CONF_CLOUD_STREAM = "cloud_stream"
CONF_CONNECTION_TYPE = "connection_type"
CONF_CLOUD_INSTANCE = "cloud_instance"
CONF_CLOUD_INSTANCE_ID = "id"
CONF_CLOUD_INSTANCE_PASSWORD = "password"
CONF_CLOUD_INSTANCE_CONNECTION_TOKEN = "token"
CONF_USER_ID = "user_id"
CONF_SKILL = "skill"
CONF_COLOR_PROFILE = "color_profile"
CONF_ENTITY_CONFIG = "entity_config"
CONF_FILTER = "filter"
CONF_FILTER_SOURCE = "filter_source"
CONF_ENTRY_ALIASES = "entry_aliases"
CONF_LINKED_PLATFORMS = "linked_platforms"
CONF_TURN_ON = "turn_on"
CONF_TURN_OFF = "turn_off"
CONF_FEATURES = "features"
CONF_SUPPORT_SET_CHANNEL = "support_set_channel"
CONF_STATE_UNKNOWN = "state_unknown"
CONF_ERROR_CODE_TEMPLATE = "error_code_template"
CONF_ENTITY_PROPERTY_TYPE = "type"
CONF_ENTITY_PROPERTY_ENTITY = "entity"
CONF_ENTITY_PROPERTY_ATTRIBUTE = "attribute"
CONF_ENTITY_PROPERTY_VALUE_TEMPLATE = "value_template"
CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT = "unit_of_measurement"
CONF_ENTITY_PROPERTY_TARGET_UNIT_OF_MEASUREMENT = "target_unit_of_measurement"
CONF_ENTITY_PROPERTIES = "properties"
CONF_ENTITY_RANGE = "range"
CONF_ENTITY_RANGE_MIN = "min"
CONF_ENTITY_RANGE_MAX = "max"
CONF_ENTITY_RANGE_PRECISION = "precision"
CONF_ENTITY_MODE_MAP = "modes"
CONF_ENTITY_EVENT_MAP = "events"
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID = "state_entity_id"
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE = "state_attribute"
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_TEMPLATE = "state_template"
CONF_ENTITY_CUSTOM_MODES = "custom_modes"
CONF_ENTITY_CUSTOM_MODE_SET_MODE = "set_mode"
CONF_ENTITY_CUSTOM_TOGGLES = "custom_toggles"
CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON = "turn_on"
CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF = "turn_off"
CONF_ENTITY_CUSTOM_RANGES = "custom_ranges"
CONF_ENTITY_CUSTOM_RANGE_SET_VALUE = "set_value"
CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE = "increase_value"
CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE = "decrease_value"

ISSUE_ID_DEPRECATED_PRESSURE_UNIT = "deprecated_pressure_unit"
ISSUE_ID_DEPRECATED_YAML_NOTIFIER = "deprecated_yaml_notifier"
ISSUE_ID_DEPRECATED_YAML_SEVERAL_NOTIFIERS = "deprecated_yaml_several_notifiers"
ISSUE_ID_MISSING_INTEGRATION = "missing_integration"
ISSUE_ID_MISSING_SKILL_DATA = "missing_skill_data"
ISSUE_ID_RECONNECTING_TOO_FAST = "reconnecting_too_fast"

# Legacy
CONF_DEVICES_DISCOVERED = "devices_discovered"
CONF_NOTIFIER = "notifier"
CONF_NOTIFIER_OAUTH_TOKEN = "oauth_token"
CONF_NOTIFIER_SKILL_ID = "skill_id"
CONF_NOTIFIER_USER_ID = "user_id"

CLOUD_BASE_URL = "https://yaha-cloud.ru"
CLOUD_STREAM_BASE_URL = "https://stream.yaha-cloud.ru"

EVENT_DEVICE_ACTION = "yandex_smart_home_device_action"
ATTR_CAPABILITY = "capability"
ATTR_ERROR_CODE = "error_code"

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

# Custom component Xiaomi Gateway 3
ATTR_ACTION = "action"

# Integration xiaomi_airpurifier
ATTR_TARGET_HUMIDITY = "target_humidity"
DOMAIN_XIAOMI_AIRPURIFIER = "xiaomi_miio_airpurifier"
MODEL_PREFIX_XIAOMI_AIRPURIFIER = "zhimi."
SERVICE_FAN_SET_TARGET_HUMIDITY = "fan_set_target_humidity"

# https://github.com/ClusterM/skykettle-ha/blob/c1b61c4a22693d6e2b7c2f57a989df418011f2c2/custom_components/skykettle/skykettle.py#L53
SKYKETTLE_MODE_BOIL = "Boil"


class ConnectionType(StrEnum):
    """Valid connection type."""

    DIRECT = "direct"
    CLOUD = "cloud"
    CLOUD_PLUS = "cloud_plus"


class EntityFilterSource(StrEnum):
    """Possible sources for entity filter."""

    CONFIG_ENTRY = "config_entry"
    GET_FROM_CONFIG_ENTRY = "get_from_config_entry"
    YAML = "yaml"


class MediaPlayerFeature(StrEnum):
    """Media player feature that user can force enable."""

    VOLUME_MUTE = "volume_mute"
    VOLUME_SET = "volume_set"
    NEXT_PREVIOUS_TRACK = "next_previous_track"
    SELECT_SOURCE = "select_source"
    TURN_ON_OFF = "turn_on_off"
    PLAY_PAUSE = "play_pause"
    PLAY_MEDIA = "play_media"


class PropertyInstanceType(StrEnum):
    """Property instance type for config validation."""

    FLOAT = "float"
    EVENT = "event"


class XGW3DeviceClass(StrEnum):
    """Device class for Xiaomi Gateway 3 custom component."""

    ACTION = "action"
    TVOC = "tvoc"
