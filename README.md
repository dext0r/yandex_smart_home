[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

## Yandex Smart Home custom component for Home Assistant

### Installation

1. Configure SSL certificate if it was not done already (do not use self-signed certificate)
1. Update home assistant to 0.96.0 at least
1. Install [HACS](https://hacs.xyz/) and search for "Yandex Smart Home" there. That way you get updates automatically. But you also can just copy and add files into custom_components directory manually instead
1. Configure component via configuration.yaml (see instructions below)
1. Restart home assistant
1. Create dialog via https://dialogs.yandex.ru/developer/
1. Add devices via your Yandex app on android/ios

### Configuration

Now add the following lines to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
yandex_smart_home:
  filter:
    include_domains:
      - switch
      - light
    include_entities:
      - media_player.tv
      - media_player.tv_lg
      - media_player.receiver
    exclude_entities:
      - light.highlight
  entity_config:
    switch.kitchen:
      name: CUSTOM_NAME_FOR_YANDEX_SMART_HOME
    light.living_room:
      room: LIVING_ROOM
    media_player.tv_lg:
      channel_set_via_media_content_id: true
    fan.xiaomi_miio_device:
      name: "Увлажнитель"
      room: LIVING_ROOM
      type: devices.types.humidifier
      properties:
        - type: temperature
          entity: sensor.temperature_158d000444c824
        - type: humidity
          attribute: humidity
        - type: water_level
          attribute: depth
    climate.tion_breezer:
      name: "Проветриватель"
      modes:
        fan_speed:
          auto: [auto]
          min: [1,'1.0']
          low: [2,'2.0']
          medium: [3,'3.0']
          high: [4,'4.0']
          turbo: [5,'5.0']
          max: [6,'6.0']
    media_player.receiver:
      type: devices.types.media_device.receiver
      relative_volume_only: false
      range:
        max: 95
        min: 20
        precision: 2
```

Configuration variables:

```yaml
yandex_smart_home:
  (map) (Optional) Configuration options for the Yandex Smart Home integration.

  filter:
    (map) (Optional) description: Filters for entities to include/exclude from Yandex Smart Home.
    include_entities:
      (list) (Optional) description: Entity IDs to include.
    include_domains:
      (list) (Optional) Domains to include.
    exclude_entities:
      (list) (Optional) Entity IDs to exclude.
    exclude_domains:
      (list) (Optional) Domains to exclude.

  entity_config:
    (map) (Optional) Entity specific configuration for Yandex Smart Home.
    ENTITY_ID:
      (map) (Optional) Entity to configure.
      name:
        (string) (Optional) Name of entity to show in Yandex Smart Home.
      room:
        (string) (Optional) Associating this device to a room in Yandex Smart Home
      type:
        (string) (Optional) Allows to force set device type. For exmaple set devices.types.purifier to display device as purifier (instead default devices.types.humidifier for such devices) 
      channel_set_via_media_content_id:
        (boolean) (Optional) (media_player only) Enables ability to set channel
         by number for 
        part of TVs (TVs that support channel change via passing number as media_content_id)
      relative_volume_only:
        (boolean) (Optional) (media_player only) Force disable ability to get/set volume by number
      properties:
        - type:
            (string) (Optional) Sensor type, available types: humidity, temperature, water_level, co2_level, power, voltage, battery_level, amperage
          entity:
            (string) (Optional) Custom entity, any sensor can be added 
          attribute:
            (string) (Optional) Attribute of an object to receive data
      range: (Optional)
        max:
          (float) (Optional) Range Maximum
        min:
          (float) (Optional) Range Minimum
        precision:
          (float) (Optional) Range Precision (adjustment step)
      modes:
        (map) (Optional) Map of yandex mode functions (https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/mode-instance-docpage/)
        fan_speed|cleanup_mode:
          (map) (Optional) Map of yandex modes (https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/mode-instance-modes-docpage/) to HA modes.
          yandex_mode1: ha_mode1
          yandex_mode2: [ha_mode2, ha_mode2b]
```

### Available domains

The following domains are available to be used:

- climate (on/off, temperature, mode, fan speed) (properties: temperature , humidity)
- cover (on/off = close/open)
- fan (on/off, fan speed, oscillation)
- group (on/off)
- input_boolean (on/off)
- scene (on/off)
- script (on/off)
- light (on/off, brightness, color, color temperature)
- media_player (on/off, mute/unmute, volume, input_source, pause/unpause, channels: up/down as prev/next 
track, get/set media_content_id via channel number for part of TVs(enabled 
via extra option "channel_set_via_media_content_id: true" in entity 
configurations))
- switch (on/off)
- vacuum (on/off, pause/unpause, clean speed) (properties: battery)
- water_heater (on/off, temperature)
- lock (on/off = lock/unlock)
- sensor (properties: temperature, humidity)

### Room/Area support

Entities that have not got rooms explicitly set and that have been placed in Home Assistant areas will return room hints to Yandex Smart Home with the devices in those areas.

### Create Dialog

Go to https://dialogs.yandex.ru/developer/ and create smart home skill.

Field | Value
------------ | -------------
Endpoint URL | https://[YOUR HOME ASSISTANT URL:PORT]/api/yandex_smart_home

For account linking use button at the bottom of skill settings page, fill it
 using values like below:

Field | Value
------------ | -------------
Client identifier | https://social.yandex.net/
API authorization endpoint | https://[YOUR HOME ASSISTANT URL:PORT]/auth/authorize
Token Endpoint | https://[YOUR HOME ASSISTANT URL:PORT]/auth/token
Refreshing an Access Token | https://[YOUR HOME ASSISTANT URL:PORT]/auth/token
