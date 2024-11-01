"""Constants for Yandex Smart Home."""
from homeassistant.components import (
    air_quality,
    automation,
    binary_sensor,
    button,
    camera,
    climate,
    cover,
    fan,
    group,
    humidifier,
    input_boolean,
    input_button,
    input_text,
    light,
    lock,
    media_player,
    remote,
    scene,
    script,
    sensor,
    switch,
    vacuum,
    water_heater,
)

DOMAIN = 'yandex_smart_home'
CONFIG = 'config'
YAML_CONFIG = 'yaml_config'
YAML_CONFIG_HASH = 'yaml_config_hash'
CONFIG_ENTRY_TITLE = 'Yandex Smart Home'
NOTIFIERS = 'notifiers'
CLOUD_MANAGER = 'cloud_manager'
CLOUD_STREAMS = 'cloud_streams'

CONF_SETTINGS = 'settings'
CONF_PRESSURE_UNIT = 'pressure_unit'
CONF_BETA = 'beta'
CONF_CLOUD_STREAM = 'cloud_stream'
CONF_NOTIFIER = 'notifier'
CONF_NOTIFIER_OAUTH_TOKEN = 'oauth_token'
CONF_NOTIFIER_SKILL_ID = 'skill_id'
CONF_NOTIFIER_USER_ID = 'user_id'
CONF_CONNECTION_TYPE = 'connection_type'
CONF_CLOUD_INSTANCE = 'cloud_instance'
CONF_CLOUD_INSTANCE_ID = 'id'
CONF_CLOUD_INSTANCE_PASSWORD = 'password'
CONF_CLOUD_INSTANCE_CONNECTION_TOKEN = 'token'
CONF_USER_ID = 'user_id'
CONF_DEVICES_DISCOVERED = 'devices_discovered'
CONF_COLOR_PROFILE = 'color_profile'
CONF_ENTITY_CONFIG = 'entity_config'
CONF_FILTER = 'filter'
CONF_NAME = 'name'
CONF_ROOM = 'room'
CONF_TYPE = 'type'
CONF_TURN_ON = 'turn_on'
CONF_TURN_OFF = 'turn_off'
CONF_DEVICE_CLASS = 'device_class'
CONF_FEATURES = 'features'
CONF_SUPPORT_SET_CHANNEL = 'support_set_channel'
CONF_STATE_UNKNOWN = 'state_unknown'
CONF_ENTITY_PROPERTY_ENTITY = 'entity'
CONF_ENTITY_PROPERTY_TYPE = 'type'
CONF_ENTITY_PROPERTY_ATTRIBUTE = 'attribute'
CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT = 'unit_of_measurement'
CONF_ENTITY_PROPERTIES = 'properties'
CONF_ENTITY_RANGE = 'range'
CONF_ENTITY_RANGE_MIN = 'min'
CONF_ENTITY_RANGE_MAX = 'max'
CONF_ENTITY_RANGE_PRECISION = 'precision'
CONF_ENTITY_MODE_MAP = 'modes'
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID = 'state_entity_id'
CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE = 'state_attribute'
CONF_ENTITY_CUSTOM_MODES = 'custom_modes'
CONF_ENTITY_CUSTOM_MODE_SET_MODE = 'set_mode'
CONF_ENTITY_CUSTOM_TOGGLES = 'custom_toggles'
CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON = 'turn_on'
CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF = 'turn_off'
CONF_ENTITY_CUSTOM_RANGES = 'custom_ranges'
CONF_ENTITY_CUSTOM_RANGE_SET_VALUE = 'set_value'
CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE = 'increase_value'
CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE = 'decrease_value'

STORE_CACHE_ATTRS = 'attrs'

CONNECTION_TYPE_DIRECT = 'direct'
CONNECTION_TYPE_CLOUD = 'cloud'

CLOUD_BASE_URL = 'https://yaha-cloud.ru'
CLOUD_STREAM_BASE_URL = 'https://stream.yaha-cloud.ru'
EVENT_DEVICE_DISCOVERY = 'yandex_smart_home_device_discovery'
EVENT_CONFIG_CHANGED = 'yandex_smart_home_config_changed'

# Fake device class
DEVICE_CLASS_BUTTON = 'button'

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html
PREFIX_TYPES = 'devices.types.'
TYPE_LIGHT = PREFIX_TYPES + 'light'
TYPE_LIGHT_STRIP = TYPE_LIGHT + '.strip'
TYPE_LIGHT_CEILING = TYPE_LIGHT + '.ceiling'
TYPE_SOCKET = PREFIX_TYPES + 'socket'
TYPE_SWITCH = PREFIX_TYPES + 'switch'
TYPE_THERMOSTAT = PREFIX_TYPES + 'thermostat'
TYPE_THERMOSTAT_AC = PREFIX_TYPES + 'thermostat.ac'
TYPE_MEDIA_DEVICE = PREFIX_TYPES + 'media_device'
TYPE_MEDIA_DEVICE_TV = PREFIX_TYPES + 'media_device.tv'
TYPE_MEDIA_DEVICE_TV_BOX = PREFIX_TYPES + 'media_device.tv_box'
TYPE_MEDIA_DEVICE_RECIEVER = PREFIX_TYPES + 'media_device.receiver'
TYPE_CAMERA = PREFIX_TYPES + 'camera'
TYPE_COOKING = PREFIX_TYPES + 'cooking'
TYPE_COFFEE_MAKER = PREFIX_TYPES + 'cooking.coffee_maker'
TYPE_KETTLE = PREFIX_TYPES + 'cooking.kettle'
TYPE_MULTICOOKER = PREFIX_TYPES + 'cooking.multicooker'
TYPE_OPENABLE = PREFIX_TYPES + 'openable'
TYPE_OPENABLE_CURTAIN = PREFIX_TYPES + 'openable.curtain'
TYPE_OPENABLE_VALVE = PREFIX_TYPES + 'openable.valve'
TYPE_HUMIDIFIER = PREFIX_TYPES + 'humidifier'
TYPE_PURIFIER = PREFIX_TYPES + 'purifier'
TYPE_VACUUM_CLEANER = PREFIX_TYPES + 'vacuum_cleaner'
TYPE_WASHING_MACHINE = PREFIX_TYPES + 'washing_machine'
TYPE_DISHWASHER = PREFIX_TYPES + 'dishwasher'
TYPE_IRON = PREFIX_TYPES + 'iron'
TYPE_SENSOR = PREFIX_TYPES + 'sensor'
TYPE_SENSOR_MOTION = TYPE_SENSOR + '.motion'
TYPE_SENSOR_VIBRATION = TYPE_SENSOR + '.vibration'
TYPE_SENSOR_ILLUMINATION = TYPE_SENSOR + '.illumination'
TYPE_SENSOR_OPEN = TYPE_SENSOR + '.open'
TYPE_SENSOR_CLIMATE = TYPE_SENSOR + '.climate'
TYPE_SENSOR_WATER_LEAK = TYPE_SENSOR + '.water_leak'
TYPE_SENSOR_BUTTON = TYPE_SENSOR + '.button'
TYPE_SENSOR_GAS = TYPE_SENSOR + '.gas'
TYPE_SENSOR_SMOKE = TYPE_SENSOR + '.smoke'
TYPE_SMART_METER = PREFIX_TYPES + 'smart_meter'
TYPE_SMART_METER_COLD_WATER = TYPE_SMART_METER + '.cold_water'
TYPE_SMART_METER_ELECTRICITY = TYPE_SMART_METER + '.electricity'
TYPE_SMART_METER_GAS = TYPE_SMART_METER + '.gas'
TYPE_SMART_METER_HEAT = TYPE_SMART_METER + '.heat'
TYPE_SMART_METER_HOT_WATER = TYPE_SMART_METER + '.hot_water'
TYPE_PET_DRINKING_FOUNTAIN = PREFIX_TYPES + 'pet_drinking_fountain'
TYPE_PET_FEEDER = PREFIX_TYPES + 'pet_feeder'
TYPE_VENTILATION = PREFIX_TYPES + 'ventilation'
TYPE_VENTILATION_FAN = PREFIX_TYPES + 'ventilation.fan'
TYPE_OTHER = PREFIX_TYPES + 'other'
TYPES = (
    TYPE_LIGHT,
    TYPE_LIGHT_STRIP,
    TYPE_LIGHT_CEILING,
    TYPE_SOCKET,
    TYPE_SWITCH,
    TYPE_THERMOSTAT,
    TYPE_THERMOSTAT_AC,
    TYPE_MEDIA_DEVICE,
    TYPE_MEDIA_DEVICE_TV,
    TYPE_MEDIA_DEVICE_TV_BOX,
    TYPE_MEDIA_DEVICE_RECIEVER,
    TYPE_CAMERA,
    TYPE_COOKING,
    TYPE_COFFEE_MAKER,
    TYPE_KETTLE,
    TYPE_MULTICOOKER,
    TYPE_OPENABLE,
    TYPE_OPENABLE_CURTAIN,
    TYPE_OPENABLE_VALVE,
    TYPE_HUMIDIFIER,
    TYPE_PURIFIER,
    TYPE_VACUUM_CLEANER,
    TYPE_WASHING_MACHINE,
    TYPE_DISHWASHER,
    TYPE_IRON,
    TYPE_SENSOR,
    TYPE_SENSOR_MOTION,
    TYPE_SENSOR_VIBRATION,
    TYPE_SENSOR_ILLUMINATION,
    TYPE_SENSOR_OPEN,
    TYPE_SENSOR_CLIMATE,
    TYPE_SENSOR_WATER_LEAK,
    TYPE_SENSOR_BUTTON,
    TYPE_SENSOR_GAS,
    TYPE_SENSOR_SMOKE,
    TYPE_SMART_METER,
    TYPE_SMART_METER_COLD_WATER,
    TYPE_SMART_METER_ELECTRICITY,
    TYPE_SMART_METER_GAS,
    TYPE_SMART_METER_HEAT,
    TYPE_SMART_METER_HOT_WATER,
    TYPE_PET_DRINKING_FOUNTAIN,
    TYPE_PET_FEEDER,
    TYPE_VENTILATION,
    TYPE_VENTILATION_FAN,
    TYPE_OTHER,
)

DOMAIN_TO_YANDEX_TYPES = {
    air_quality.DOMAIN: TYPE_SENSOR,
    automation.DOMAIN: TYPE_OTHER,
    binary_sensor.DOMAIN: TYPE_SENSOR,
    button.DOMAIN: TYPE_OTHER,
    camera.DOMAIN: TYPE_CAMERA,
    climate.DOMAIN: TYPE_THERMOSTAT,
    cover.DOMAIN: TYPE_OPENABLE_CURTAIN,
    fan.DOMAIN: TYPE_VENTILATION_FAN,
    group.DOMAIN: TYPE_SWITCH,
    humidifier.DOMAIN: TYPE_HUMIDIFIER,
    input_boolean.DOMAIN: TYPE_SWITCH,
    input_button.DOMAIN: TYPE_OTHER,
    input_text.DOMAIN: TYPE_SENSOR,
    light.DOMAIN: TYPE_LIGHT,
    lock.DOMAIN: TYPE_OPENABLE,
    media_player.DOMAIN: TYPE_MEDIA_DEVICE,
    remote.DOMAIN: TYPE_SWITCH,
    scene.DOMAIN: TYPE_OTHER,
    script.DOMAIN: TYPE_OTHER,
    sensor.DOMAIN: TYPE_SENSOR,
    switch.DOMAIN: TYPE_SWITCH,
    vacuum.DOMAIN: TYPE_VACUUM_CLEANER,
    water_heater.DOMAIN: TYPE_KETTLE,
    'valve': TYPE_OPENABLE_VALVE,  # backward compatibility < 2024.1
}

DEVICE_CLASS_TO_YANDEX_TYPES = {
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.DOOR): TYPE_SENSOR_OPEN,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.GARAGE_DOOR): TYPE_SENSOR_OPEN,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.GAS): TYPE_SENSOR_GAS,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.MOISTURE): TYPE_SENSOR_WATER_LEAK,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.MOTION): TYPE_SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.MOVING): TYPE_SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.OCCUPANCY): TYPE_SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.OPENING): TYPE_SENSOR_OPEN,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.PRESENCE): TYPE_SENSOR_MOTION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.SMOKE): TYPE_SENSOR_SMOKE,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.VIBRATION): TYPE_SENSOR_VIBRATION,
    (binary_sensor.DOMAIN, binary_sensor.BinarySensorDeviceClass.WINDOW): TYPE_SENSOR_OPEN,
    (media_player.DOMAIN, media_player.MediaPlayerDeviceClass.RECEIVER): TYPE_MEDIA_DEVICE_RECIEVER,
    (media_player.DOMAIN, media_player.MediaPlayerDeviceClass.TV): TYPE_MEDIA_DEVICE_TV,
    (sensor.DOMAIN, DEVICE_CLASS_BUTTON): TYPE_SENSOR_BUTTON,
    (sensor.DOMAIN, sensor.SensorDeviceClass.CO): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.CO2): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.ENERGY): TYPE_SMART_METER_ELECTRICITY,
    (sensor.DOMAIN, sensor.SensorDeviceClass.GAS): TYPE_SMART_METER_GAS,
    (sensor.DOMAIN, sensor.SensorDeviceClass.HUMIDITY): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.ILLUMINANCE): TYPE_SENSOR_ILLUMINATION,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PM1): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PM10): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PM25): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.PRESSURE): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.TEMPERATURE): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS): TYPE_SENSOR_CLIMATE,
    (sensor.DOMAIN, sensor.SensorDeviceClass.WATER): TYPE_SMART_METER_COLD_WATER,
    (switch.DOMAIN, switch.SwitchDeviceClass.OUTLET): TYPE_SOCKET,
}

ON_OFF_INSTANCE_ON = 'on'

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html
TOGGLE_INSTANCE_BACKLIGHT = 'backlight'
TOGGLE_INSTANCE_CONTROLS_LOCKED = 'controls_locked'
TOGGLE_INSTANCE_IONIZATION = 'ionization'
TOGGLE_INSTANCE_KEEP_WARM = 'keep_warm'
TOGGLE_INSTANCE_MUTE = 'mute'
TOGGLE_INSTANCE_OSCILLATION = 'oscillation'
TOGGLE_INSTANCE_PAUSE = 'pause'
TOGGLE_INSTANCES = (
    TOGGLE_INSTANCE_BACKLIGHT,
    TOGGLE_INSTANCE_CONTROLS_LOCKED,
    TOGGLE_INSTANCE_IONIZATION,
    TOGGLE_INSTANCE_KEEP_WARM,
    TOGGLE_INSTANCE_MUTE,
    TOGGLE_INSTANCE_OSCILLATION,
    TOGGLE_INSTANCE_PAUSE,
)

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html
RANGE_INSTANCE_BRIGHTNESS = 'brightness'
RANGE_INSTANCE_CHANNEL = 'channel'
RANGE_INSTANCE_HUMIDITY = 'humidity'
RANGE_INSTANCE_OPEN = 'open'
RANGE_INSTANCE_TEMPERATURE = 'temperature'
RANGE_INSTANCE_VOLUME = 'volume'
RANGE_INSTANCES = (
    RANGE_INSTANCE_BRIGHTNESS,
    RANGE_INSTANCE_CHANNEL,
    RANGE_INSTANCE_HUMIDITY,
    RANGE_INSTANCE_OPEN,
    RANGE_INSTANCE_TEMPERATURE,
    RANGE_INSTANCE_VOLUME,
)

RANGE_INSTANCE_TO_UNITS = {
    RANGE_INSTANCE_BRIGHTNESS: 'unit.percent',
    RANGE_INSTANCE_HUMIDITY: 'unit.percent',
    RANGE_INSTANCE_OPEN: 'unit.percent',
    RANGE_INSTANCE_TEMPERATURE: 'unit.temperature.celsius'
}

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html
MODE_INSTANCE_CLEANUP_MODE = 'cleanup_mode'
MODE_INSTANCE_COFFEE_MODE = 'coffee_mode'
MODE_INSTANCE_DISHWASHING = 'dishwashing'
MODE_INSTANCE_FAN_SPEED = 'fan_speed'
MODE_INSTANCE_HEAT = 'heat'
MODE_INSTANCE_INPUT_SOURCE = 'input_source'
MODE_INSTANCE_PROGRAM = 'program'
MODE_INSTANCE_SWING = 'swing'
MODE_INSTANCE_TEA_MODE = 'tea_mode'
MODE_INSTANCE_THERMOSTAT = 'thermostat'
MODE_INSTANCE_VENTILATION_MODE = 'ventilation_mode'
MODE_INSTANCE_WORK_SPEED = 'work_speed'
MODE_INSTANCES = (
    MODE_INSTANCE_CLEANUP_MODE,
    MODE_INSTANCE_COFFEE_MODE,
    MODE_INSTANCE_DISHWASHING,
    MODE_INSTANCE_FAN_SPEED,
    MODE_INSTANCE_HEAT,
    MODE_INSTANCE_INPUT_SOURCE,
    MODE_INSTANCE_PROGRAM,
    MODE_INSTANCE_SWING,
    MODE_INSTANCE_TEA_MODE,
    MODE_INSTANCE_THERMOSTAT,
    MODE_INSTANCE_VENTILATION_MODE,
    MODE_INSTANCE_WORK_SPEED,
)

VIDEO_STREAM_INSTANCE_GET_STREAM = 'get_stream'

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/color_setting.html#discovery__discovery-parameters-color-setting-table__entry__75
COLOR_SETTING_RGB = 'rgb'
COLOR_SETTING_TEMPERATURE_K = 'temperature_k'
COLOR_SETTING_SCENE = 'scene'
COLOR_SCENE_ALARM = 'alarm'
COLOR_SCENE_ALICE = 'alice'
COLOR_SCENE_CANDLE = 'candle'
COLOR_SCENE_DINNER = 'dinner'
COLOR_SCENE_FANTASY = 'fantasy'
COLOR_SCENE_GARLAND = 'garland'
COLOR_SCENE_JUNGLE = 'jungle'
COLOR_SCENE_MOVIE = 'movie'
COLOR_SCENE_NEON = 'neon'
COLOR_SCENE_NIGHT = 'night'
COLOR_SCENE_OCEAN = 'ocean'
COLOR_SCENE_PARTY = 'party'
COLOR_SCENE_READING = 'reading'
COLOR_SCENE_REST = 'rest'
COLOR_SCENE_ROMANCE = 'romance'
COLOR_SCENE_SIREN = 'siren'
COLOR_SCENE_SUNRISE = 'sunrise'
COLOR_SCENE_SUNSET = 'sunset'
COLOR_SCENES = (
    COLOR_SCENE_ALARM,
    COLOR_SCENE_ALICE,
    COLOR_SCENE_CANDLE,
    COLOR_SCENE_DINNER,
    COLOR_SCENE_FANTASY,
    COLOR_SCENE_GARLAND,
    COLOR_SCENE_JUNGLE,
    COLOR_SCENE_MOVIE,
    COLOR_SCENE_NEON,
    COLOR_SCENE_NIGHT,
    COLOR_SCENE_OCEAN,
    COLOR_SCENE_PARTY,
    COLOR_SCENE_READING,
    COLOR_SCENE_REST,
    COLOR_SCENE_ROMANCE,
    COLOR_SCENE_SIREN,
    COLOR_SCENE_SUNRISE,
    COLOR_SCENE_SUNSET,
)

COLOR_NAME_RED = 'red'
COLOR_NAME_CORAL = 'coral'
COLOR_NAME_ORANGE = 'orange'
COLOR_NAME_YELLOW = 'yellow'
COLOR_NAME_LIME = 'lime'
COLOR_NAME_GREEN = 'green'
COLOR_NAME_EMERALD = 'emerald'
COLOR_NAME_TURQUOISE = 'turquoise'
COLOR_NAME_CYAN = 'cyan'
COLOR_NAME_BLUE = 'blue'
COLOR_NAME_MOONLIGHT = 'moonlight'
COLOR_NAME_LAVENDER = 'lavender'
COLOR_NAME_VIOLET = 'violet'
COLOR_NAME_PURPLE = 'purple'
COLOR_NAME_ORCHID = 'orchid'
COLOR_NAME_MAUVE = 'mauve'
COLOR_NAME_RASPBERRY = 'raspberry'
COLOR_TEMPERATURE_NAME_FIERY_WHITE = 'fiery_white'
COLOR_TEMPERATURE_NAME_SOFT_WHITE = 'soft_white'
COLOR_TEMPERATURE_NAME_WARM_WHITE = 'warm_white'
COLOR_TEMPERATURE_NAME_WHITE = 'white'
COLOR_TEMPERATURE_NAME_DAYLIGHT = 'daylight'
COLOR_TEMPERATURE_NAME_COLD_WHITE = 'cold_white'
COLOR_TEMPERATURE_NAME_MISTY_WHITE = 'misty_white'
COLOR_TEMPERATURE_NAME_HEAVENLY_WHITE = 'heavenly_white'
COLOR_NAMES = (
    COLOR_NAME_RED,
    COLOR_NAME_CORAL,
    COLOR_NAME_ORANGE,
    COLOR_NAME_YELLOW,
    COLOR_NAME_LIME,
    COLOR_NAME_GREEN,
    COLOR_NAME_EMERALD,
    COLOR_NAME_TURQUOISE,
    COLOR_NAME_CYAN,
    COLOR_NAME_BLUE,
    COLOR_NAME_MOONLIGHT,
    COLOR_NAME_LAVENDER,
    COLOR_NAME_VIOLET,
    COLOR_NAME_PURPLE,
    COLOR_NAME_ORCHID,
    COLOR_NAME_MAUVE,
    COLOR_NAME_RASPBERRY,
    COLOR_TEMPERATURE_NAME_FIERY_WHITE,
    COLOR_TEMPERATURE_NAME_SOFT_WHITE,
    COLOR_TEMPERATURE_NAME_WARM_WHITE,
    COLOR_TEMPERATURE_NAME_WHITE,
    COLOR_TEMPERATURE_NAME_DAYLIGHT,
    COLOR_TEMPERATURE_NAME_COLD_WHITE,
    COLOR_TEMPERATURE_NAME_MISTY_WHITE,
    COLOR_TEMPERATURE_NAME_HEAVENLY_WHITE
)

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html
MODE_INSTANCE_MODE_WET_CLEANING = 'wet_cleaning'
MODE_INSTANCE_MODE_DRY_CLEANING = 'dry_cleaning'
MODE_INSTANCE_MODE_MIXED_CLEANING = 'mixed_cleaning'
MODE_INSTANCE_MODE_AUTO = 'auto'
MODE_INSTANCE_MODE_ECO = 'eco'
MODE_INSTANCE_MODE_SMART = 'smart'
MODE_INSTANCE_MODE_TURBO = 'turbo'
MODE_INSTANCE_MODE_COOL = 'cool'
MODE_INSTANCE_MODE_DRY = 'dry'
MODE_INSTANCE_MODE_FAN_ONLY = 'fan_only'
MODE_INSTANCE_MODE_HEAT = 'heat'
MODE_INSTANCE_MODE_PREHEAT = 'preheat'
MODE_INSTANCE_MODE_HIGH = 'high'
MODE_INSTANCE_MODE_LOW = 'low'
MODE_INSTANCE_MODE_MEDIUM = 'medium'
MODE_INSTANCE_MODE_MAX = 'max'
MODE_INSTANCE_MODE_MIN = 'min'
MODE_INSTANCE_MODE_FAST = 'fast'
MODE_INSTANCE_MODE_SLOW = 'slow'
MODE_INSTANCE_MODE_EXPRESS = 'express'
MODE_INSTANCE_MODE_NORMAL = 'normal'
MODE_INSTANCE_MODE_QUIET = 'quiet'
MODE_INSTANCE_MODE_HORIZONTAL = 'horizontal'
MODE_INSTANCE_MODE_STATIONARY = 'stationary'
MODE_INSTANCE_MODE_VERTICAL = 'vertical'
MODE_INSTANCE_MODE_SUPPLY_AIR = 'supply_air'
MODE_INSTANCE_MODE_EXTRACTION_AIR = 'extraction_air'
MODE_INSTANCE_MODE_ONE = 'one'
MODE_INSTANCE_MODE_TWO = 'two'
MODE_INSTANCE_MODE_THREE = 'three'
MODE_INSTANCE_MODE_FOUR = 'four'
MODE_INSTANCE_MODE_FIVE = 'five'
MODE_INSTANCE_MODE_SIX = 'six'
MODE_INSTANCE_MODE_SEVEN = 'seven'
MODE_INSTANCE_MODE_EIGHT = 'eight'
MODE_INSTANCE_MODE_NINE = 'nine'
MODE_INSTANCE_MODE_TEN = 'ten'
MODE_INSTANCE_MODE_AMERICANO = 'americano'
MODE_INSTANCE_MODE_CAPPUCCINO = 'cappuccino'
MODE_INSTANCE_MODE_DOUBLE = 'double'
MODE_INSTANCE_MODE_ESPRESSO = 'espresso'
MODE_INSTANCE_MODE_DOUBLE_ESPRESSO = 'double_espresso'
MODE_INSTANCE_MODE_LATTE = 'latte'
MODE_INSTANCE_MODE_BLACK_TEA = 'black_tea'
MODE_INSTANCE_MODE_FLOWER_TEA = 'flower_tea'
MODE_INSTANCE_MODE_GREEN_TEA = 'green_tea'
MODE_INSTANCE_MODE_HERBAL_TEA = 'herbal_tea'
MODE_INSTANCE_MODE_OOLONG_TEA = 'oolong_tea'
MODE_INSTANCE_MODE_PUERH_TEA = 'puerh_tea'
MODE_INSTANCE_MODE_RED_TEA = 'red_tea'
MODE_INSTANCE_MODE_WHITE_TEA = 'white_tea'
MODE_INSTANCE_MODE_GLASS = 'glass'
MODE_INSTANCE_MODE_INTENSIVE = 'intensive'
MODE_INSTANCE_MODE_PRE_RINSE = 'pre_rinse'
MODE_INSTANCE_MODE_ASPIC = 'aspic'
MODE_INSTANCE_MODE_BABY_FOOD = 'baby_food'
MODE_INSTANCE_MODE_BAKING = 'baking'
MODE_INSTANCE_MODE_BREAD = 'bread'
MODE_INSTANCE_MODE_BOILING = 'boiling'
MODE_INSTANCE_MODE_CEREALS = 'cereals'
MODE_INSTANCE_MODE_CHEESECAKE = 'cheesecake'
MODE_INSTANCE_MODE_DEEP_FRYER = 'deep_fryer'
MODE_INSTANCE_MODE_DESSERT = 'dessert'
MODE_INSTANCE_MODE_FOWL = 'fowl'
MODE_INSTANCE_MODE_FRYING = 'frying'
MODE_INSTANCE_MODE_MACARONI = 'macaroni'
MODE_INSTANCE_MODE_MILK_PORRIDGE = 'milk_porridge'
MODE_INSTANCE_MODE_MULTICOOKER = 'multicooker'
MODE_INSTANCE_MODE_PASTA = 'pasta'
MODE_INSTANCE_MODE_PILAF = 'pilaf'
MODE_INSTANCE_MODE_PIZZA = 'pizza'
MODE_INSTANCE_MODE_SAUCE = 'sauce'
MODE_INSTANCE_MODE_SLOW_COOK = 'slow_cook'
MODE_INSTANCE_MODE_SOUP = 'soup'
MODE_INSTANCE_MODE_STEAM = 'steam'
MODE_INSTANCE_MODE_STEWING = 'stewing'
MODE_INSTANCE_MODE_VACUUM = 'vacuum'
MODE_INSTANCE_MODE_YOGURT = 'yogurt'

MODE_INSTANCE_MODES = (
    MODE_INSTANCE_MODE_WET_CLEANING,
    MODE_INSTANCE_MODE_DRY_CLEANING,
    MODE_INSTANCE_MODE_MIXED_CLEANING,
    MODE_INSTANCE_MODE_AUTO,
    MODE_INSTANCE_MODE_ECO,
    MODE_INSTANCE_MODE_SMART,
    MODE_INSTANCE_MODE_TURBO,
    MODE_INSTANCE_MODE_COOL,
    MODE_INSTANCE_MODE_DRY,
    MODE_INSTANCE_MODE_FAN_ONLY,
    MODE_INSTANCE_MODE_HEAT,
    MODE_INSTANCE_MODE_PREHEAT,
    MODE_INSTANCE_MODE_HIGH,
    MODE_INSTANCE_MODE_LOW,
    MODE_INSTANCE_MODE_MEDIUM,
    MODE_INSTANCE_MODE_MAX,
    MODE_INSTANCE_MODE_MIN,
    MODE_INSTANCE_MODE_FAST,
    MODE_INSTANCE_MODE_SLOW,
    MODE_INSTANCE_MODE_EXPRESS,
    MODE_INSTANCE_MODE_NORMAL,
    MODE_INSTANCE_MODE_QUIET,
    MODE_INSTANCE_MODE_HORIZONTAL,
    MODE_INSTANCE_MODE_STATIONARY,
    MODE_INSTANCE_MODE_VERTICAL,
    MODE_INSTANCE_MODE_SUPPLY_AIR,
    MODE_INSTANCE_MODE_EXTRACTION_AIR,
    MODE_INSTANCE_MODE_ONE,
    MODE_INSTANCE_MODE_TWO,
    MODE_INSTANCE_MODE_THREE,
    MODE_INSTANCE_MODE_FOUR,
    MODE_INSTANCE_MODE_FIVE,
    MODE_INSTANCE_MODE_SIX,
    MODE_INSTANCE_MODE_SEVEN,
    MODE_INSTANCE_MODE_EIGHT,
    MODE_INSTANCE_MODE_NINE,
    MODE_INSTANCE_MODE_TEN,
    MODE_INSTANCE_MODE_AMERICANO,
    MODE_INSTANCE_MODE_CAPPUCCINO,
    MODE_INSTANCE_MODE_DOUBLE,
    MODE_INSTANCE_MODE_ESPRESSO,
    MODE_INSTANCE_MODE_DOUBLE_ESPRESSO,
    MODE_INSTANCE_MODE_LATTE,
    MODE_INSTANCE_MODE_BLACK_TEA,
    MODE_INSTANCE_MODE_FLOWER_TEA,
    MODE_INSTANCE_MODE_GREEN_TEA,
    MODE_INSTANCE_MODE_HERBAL_TEA,
    MODE_INSTANCE_MODE_OOLONG_TEA,
    MODE_INSTANCE_MODE_PUERH_TEA,
    MODE_INSTANCE_MODE_RED_TEA,
    MODE_INSTANCE_MODE_WHITE_TEA,
    MODE_INSTANCE_MODE_GLASS,
    MODE_INSTANCE_MODE_INTENSIVE,
    MODE_INSTANCE_MODE_PRE_RINSE,
    MODE_INSTANCE_MODE_ASPIC,
    MODE_INSTANCE_MODE_BABY_FOOD,
    MODE_INSTANCE_MODE_BAKING,
    MODE_INSTANCE_MODE_BREAD,
    MODE_INSTANCE_MODE_BOILING,
    MODE_INSTANCE_MODE_CEREALS,
    MODE_INSTANCE_MODE_CHEESECAKE,
    MODE_INSTANCE_MODE_DEEP_FRYER,
    MODE_INSTANCE_MODE_DESSERT,
    MODE_INSTANCE_MODE_FOWL,
    MODE_INSTANCE_MODE_FRYING,
    MODE_INSTANCE_MODE_MACARONI,
    MODE_INSTANCE_MODE_MILK_PORRIDGE,
    MODE_INSTANCE_MODE_MULTICOOKER,
    MODE_INSTANCE_MODE_PASTA,
    MODE_INSTANCE_MODE_PILAF,
    MODE_INSTANCE_MODE_PIZZA,
    MODE_INSTANCE_MODE_SAUCE,
    MODE_INSTANCE_MODE_SLOW_COOK,
    MODE_INSTANCE_MODE_SOUP,
    MODE_INSTANCE_MODE_STEAM,
    MODE_INSTANCE_MODE_STEWING,
    MODE_INSTANCE_MODE_VACUUM,
    MODE_INSTANCE_MODE_YOGURT,
)

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html
FLOAT_INSTANCE_AMPERAGE = 'amperage'
FLOAT_INSTANCE_BATTERY_LEVEL = 'battery_level'
FLOAT_INSTANCE_CO2_LEVEL = 'co2_level'
FLOAT_INSTANCE_ELECTRICITY_METER = 'electricity_meter'
FLOAT_INSTANCE_GAS_METER = 'gas_meter'
FLOAT_INSTANCE_HEAT_METER = 'heat_meter'
FLOAT_INSTANCE_HUMIDITY = 'humidity'
FLOAT_INSTANCE_ILLUMINATION = 'illumination'
FLOAT_INSTANCE_METER = 'meter'
FLOAT_INSTANCE_PM10_DENSITY = 'pm10_density'
FLOAT_INSTANCE_PM1_DENSITY = 'pm1_density'
FLOAT_INSTANCE_PM2_5_DENSITY = 'pm2.5_density'
FLOAT_INSTANCE_POWER = 'power'
FLOAT_INSTANCE_PRESSURE = 'pressure'
FLOAT_INSTANCE_TEMPERATURE = 'temperature'
FLOAT_INSTANCE_TVOC = 'tvoc'
FLOAT_INSTANCE_VOLTAGE = 'voltage'
FLOAT_INSTANCE_WATER_LEVEL = 'water_level'
FLOAT_INSTANCE_WATER_METER = 'water_meter'
FLOAT_INSTANCES = (
    FLOAT_INSTANCE_AMPERAGE,
    FLOAT_INSTANCE_BATTERY_LEVEL,
    FLOAT_INSTANCE_CO2_LEVEL,
    FLOAT_INSTANCE_ELECTRICITY_METER,
    FLOAT_INSTANCE_GAS_METER,
    FLOAT_INSTANCE_HEAT_METER,
    FLOAT_INSTANCE_HUMIDITY,
    FLOAT_INSTANCE_ILLUMINATION,
    FLOAT_INSTANCE_METER,
    FLOAT_INSTANCE_PM10_DENSITY,
    FLOAT_INSTANCE_PM1_DENSITY,
    FLOAT_INSTANCE_PM2_5_DENSITY,
    FLOAT_INSTANCE_POWER,
    FLOAT_INSTANCE_PRESSURE,
    FLOAT_INSTANCE_TEMPERATURE,
    FLOAT_INSTANCE_TVOC,
    FLOAT_INSTANCE_VOLTAGE,
    FLOAT_INSTANCE_WATER_LEVEL,
    FLOAT_INSTANCE_WATER_METER,
)

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html
EVENT_INSTANCE_VIBRATION = 'vibration'
EVENT_INSTANCE_OPEN = 'open'
EVENT_INSTANCE_BUTTON = 'button'
EVENT_INSTANCE_MOTION = 'motion'
EVENT_INSTANCE_SMOKE = 'smoke'
EVENT_INSTANCE_GAS = 'gas'
EVENT_INSTANCE_BATTERY_LEVEL = 'battery_level'
EVENT_INSTANCE_WATER_LEVEL = 'water_level'
EVENT_INSTANCE_WATER_LEAK = 'water_leak'
EVENT_INSTANCES = (
    EVENT_INSTANCE_VIBRATION,
    EVENT_INSTANCE_OPEN,
    EVENT_INSTANCE_BUTTON,
    EVENT_INSTANCE_MOTION,
    EVENT_INSTANCE_SMOKE,
    EVENT_INSTANCE_GAS,
    EVENT_INSTANCE_BATTERY_LEVEL,
    EVENT_INSTANCE_WATER_LEVEL,
    EVENT_INSTANCE_WATER_LEAK,
)

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html#event-instance__vibration
EVENT_VIBRATION_TILT = 'tilt'
EVENT_VIBRATION_FALL = 'fall'
EVENT_VIBRATION_VIBRATION = 'vibration'
EVENT_OPEN_OPENED = 'opened'
EVENT_OPEN_CLOSED = 'closed'
EVENT_BUTTON_CLICK = 'click'
EVENT_BUTTON_DOUBLE_CLICK = 'double_click'
EVENT_BUTTON_LONG_PRESS = 'long_press'
EVENT_MOTION_DETECTED = 'detected'
EVENT_MOTION_NOT_DETECTED = 'not_detected'
EVENT_SMOKE_DETECTED = 'detected'
EVENT_SMOKE_NOT_DETECTED = 'not_detected'
EVENT_SMOKE_HIGH = 'high'
EVENT_GAS_DETECTED = 'detected'
EVENT_GAS_NOT_DETECTED = 'not_detected'
EVENT_GAS_HIGH = 'high'
EVENT_BATTERY_LEVEL_LOW = 'low'
EVENT_BATTERY_LEVEL_NORMAL = 'normal'
EVENT_WATER_LEVEL_LOW = 'low'
EVENT_WATER_LEVEL_NORMAL = 'normal'
EVENT_WATER_LEAK_DRY = 'dry'
EVENT_WATER_LEAK_LEAK = 'leak'

# https://yandex.ru/dev/dialogs/smart-home/doc/concepts/response-codes.html
ERR_DEVICE_UNREACHABLE = 'DEVICE_UNREACHABLE'
ERR_INTERNAL_ERROR = 'INTERNAL_ERROR'
ERR_INVALID_ACTION = 'INVALID_ACTION'
ERR_DEVICE_OFF = 'INVALID_ACTION'
ERR_INVALID_VALUE = 'INVALID_VALUE'
ERR_NOT_SUPPORTED_IN_CURRENT_MODE = 'NOT_SUPPORTED_IN_CURRENT_MODE'

PRESSURE_UNIT_PASCAL = 'pa'
PRESSURE_UNIT_HECTOPASCAL = 'hPa'
PRESSURE_UNIT_KILOPASCAL = 'kPa'
PRESSURE_UNIT_MEGAPASCAL = 'MPa'
PRESSURE_UNIT_MMHG = 'mmHg'
PRESSURE_UNIT_ATM = 'atm'
PRESSURE_UNIT_BAR = 'bar'
PRESSURE_UNIT_MBAR = 'mbar'

# Additional states
STATE_NONE = 'none'
STATE_NONE_UI = '-'
STATE_EMPTY = ''
STATE_CHARGING = 'charging'
STATE_LOW = 'low'

# Additional attributes
ATTR_CURRENT = 'current'
ATTR_ILLUMINANCE = 'illuminance'
ATTR_LOAD_POWER = 'load_power'
ATTR_CURRENT_CONSUMPTION = 'current_consumption'
ATTR_POWER = 'power'
ATTR_TVOC = 'total_volatile_organic_compounds'
ATTR_WATER_LEVEL = 'water_level'

# Integration xiaomi_airpurifier
ATTR_TARGET_HUMIDITY = 'target_humidity'
DOMAIN_XIAOMI_AIRPURIFIER = 'xiaomi_miio_airpurifier'
MODEL_PREFIX_XIAOMI_AIRPURIFIER = 'zhimi.'
SERVICE_FAN_SET_TARGET_HUMIDITY = 'fan_set_target_humidity'

# https://github.com/syssi/xiaomi_airpurifier#service-fanset_preset_mode
XIAOMI_FAN_PRESET_LEVEL_1 = 'Level 1'
XIAOMI_FAN_PRESET_LEVEL_2 = 'Level 2'
XIAOMI_FAN_PRESET_LEVEL_3 = 'Level 3'
XIAOMI_FAN_PRESET_LEVEL_4 = 'Level 4'
XIAOMI_FAN_PRESET_LEVEL_5 = 'Level 5'

# https://github.com/home-assistant/core/blob/d5a8f1af1d2dc74a12fb6870a4f1cb5318f88bf9/homeassistant/components/xiaomi_miio/fan.py#L744
XIAOMI_FAN_PRESET_NATURE = 'Nature'
XIAOMI_FAN_PRESET_NORMAL = 'Normal'

# https://github.com/ollo69/ha-smartthinq-sensors/blob/2d6212c9e060dc1d4947e1fed195af154442b941/custom_components/smartthinq_sensors/wideq/ac.py#L141
SMARTTHINQ_FAN_PRESET_NATURE = 'NATURE'

# https://github.com/home-assistant/core/blob/6830eec549c372946b19035000c10afecd2f2da3/homeassistant/components/xiaomi_miio/fan.py#L275
XIAOMI_AIRPURIFIER_PRESET_AUTO = 'Auto'
XIAOMI_AIRPURIFIER_PRESET_SILENT = 'Silent'
XIAOMI_AIRPURIFIER_PRESET_LOW = 'Low'
XIAOMI_AIRPURIFIER_PRESET_FAVORITE = 'Favorite'
XIAOMI_AIRPURIFIER_PRESET_IDLE = 'Idle'
XIAOMI_AIRPURIFIER_PRESET_MEDIUM = 'Medium'
XIAOMI_AIRPURIFIER_PRESET_HIGH = 'High'
XIAOMI_AIRPURIFIER_PRESET_STRONG = 'Strong'
XIAOMI_AIRPURIFIER_PRESET_FAN = 'Fan'
XIAOMI_AIRPURIFIER_PRESET_MIDDLE = 'Middle'

# https://github.com/home-assistant/core/blob/d5a8f1af1d2dc74a12fb6870a4f1cb5318f88bf9/homeassistant/components/xiaomi_miio/humidifier.py#L316
XIAOMI_HUMIDIFIER_PRESET_MID = 'Mid'
# leshow.humidifier.jsq1
XIAOMI_HUMIDIFIER_CONST_HUMIDITY = 'Const Humidity'

# https://github.com/airens/tion_home_assistant#climateset_fan_mode
TION_FAN_SPEED_1 = '1'
TION_FAN_SPEED_2 = '2'
TION_FAN_SPEED_3 = '3'
TION_FAN_SPEED_4 = '4'
TION_FAN_SPEED_5 = '5'
TION_FAN_SPEED_6 = '6'

# https://github.com/ClusterM/skykettle-ha/blob/c1b61c4a22693d6e2b7c2f57a989df418011f2c2/custom_components/skykettle/skykettle.py#L53
SKYKETTLE_MODE_BOIL = "Boil"

# https://github.com/home-assistant/core/pull/67743
FAN_SPEED_OFF = 'off'
FAN_SPEED_LOW = 'low'
FAN_SPEED_MEDIUM = 'medium'
FAN_SPEED_HIGH = 'high'

# https://github.com/dmitry-k/yandex_smart_home/issues/173
FAN_SPEED_MIN = 'min'
FAN_SPEED_MAX = 'max'

# https://github.com/dmitry-k/yandex_smart_home/issues/347
FAN_SPEED_MID = 'mid'

# https://github.com/dext0r/yandex_smart_home/issues/440
FAN_SPEED_LOW_MID = 'low_mid'
FAN_SPEED_MID_HIGH = 'mid_high'

# SmartIR
FAN_SPEED_HIGHEST = 'highest'

# https://github.com/home-assistant/core/blob/2981d7ed0ec78f2271f5b6fac26a98d1b1b280df/homeassistant/components/esphome/climate.py#L110
FAN_SPEED_QUIET = 'quiet'

# https://github.com/humbertogontijo/python-roborock/blob/1616217a06e20d51921de984134555bcc0775a92/roborock/code_mappings.py#L61
CLEANUP_MODE_OFF = 'off'
CLEANUP_MODE_SILENT = 'silent'
CLEANUP_MODE_BALANCED = 'balanced'
CLEANUP_MODE_TURBO = 'turbo'
CLEANUP_MODE_MAX = 'max'
CLEANUP_MODE_MAX_PLUS = 'max_plus'
CLEANUP_MODE_CUSTOM = 'custom'

MEDIA_PLAYER_FEATURE_VOLUME_MUTE = 'volume_mute'
MEDIA_PLAYER_FEATURE_VOLUME_SET = 'volume_set'
MEDIA_PLAYER_FEATURE_NEXT_PREVIOUS_TRACK = 'next_previous_track'
MEDIA_PLAYER_FEATURE_SELECT_SOURCE = 'select_source'
MEDIA_PLAYER_FEATURE_TURN_ON_OFF = 'turn_on_off'
MEDIA_PLAYER_FEATURE_PLAY_PAUSE = 'play_pause'
MEDIA_PLAYER_FEATURE_PLAY_MEDIA = 'play_media'
MEDIA_PLAYER_FEATURES = (
    MEDIA_PLAYER_FEATURE_VOLUME_MUTE,
    MEDIA_PLAYER_FEATURE_VOLUME_SET,
    MEDIA_PLAYER_FEATURE_NEXT_PREVIOUS_TRACK,
    MEDIA_PLAYER_FEATURE_SELECT_SOURCE,
    MEDIA_PLAYER_FEATURE_TURN_ON_OFF,
    MEDIA_PLAYER_FEATURE_PLAY_PAUSE,
    MEDIA_PLAYER_FEATURE_PLAY_MEDIA,
)
