[![Donate](https://img.shields.io/badge/-Donate-purple.svg)](https://money.yandex.ru/to/41001142896898)

## Yandex Smart Home custom component for Home Assistant

### Installation

1. Configure SSL certificate if it was not done already (do not use self-signed certificate)
1. Update home assistant to 0.96.0 at least
1. Clone this project into custom_components directory(create if required, 
path should look like ~/.homeassistant/custom_components/yandex_smart_home)
1. Configure component via configuration.yaml
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
    exclude_entities:
      - light.highlight
  entity_config:
    switch.kitchen:
      name: CUSTOM_NAME_FOR_YANDEX_SMART_HOME
    light.living_room:
      room: LIVING_ROOM
    media_player.tv_lg:
      channel_set_via_media_content_id: true
```

Configuration variables:

```
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
      channel_set_via_media_content_id:
        (boolean) (Optional) (media_player only) Enables ability to set channel
         by number for 
        part of TVs (TVs that support channel change via passing number as media_content_id)
      relative_volume_only:
        (boolean) (Optional) (media_player only) Force disable ability to get/set volume by number
```

### Available domains

The following domains are available to be used:

- climate (on/off, temperature, mode, fan speed)
- cover (on/off = close/open)
- fan (on/off, fan speed)
- group (on/off)
- input_boolean (on/off)
- scene (on/off)
- script (on/off)
- light (on/off, brightness, color, color temperature)
- media_player (on/off, mute/unmute, volume, channels: up/down as prev/next 
track, get/set media_content_id via channel number for part of TVs(enabled 
via extra option "channel_set_via_media_content_id: true" in entity 
configurations))
- switch (on/off)
- vacuum (on/off)

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
