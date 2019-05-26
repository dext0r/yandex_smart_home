## Yandex Smart Home custom component for Home Assistant

### Installation

1. Clone this project into custom_components directory
2. Configure component via configuration.yaml
3. Create dialog via https://dialogs.yandex.ru/developer/
4. Add devices via your Yandex app on android/ios

### Configuration

Now add the following lines to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
yandex_smart_home:
  exposed_domains:
    - switch
    - light
  entity_config:
    switch.kitchen:
      name: CUSTOM_NAME_FOR_YANDEX_SMART_HOME
    light.living_room:
      room: LIVING_ROOM
```

Configuration is similar to google assistant.

{% configuration %}
expose_by_default:
  description: "Expose devices in all supported domains by default. If `exposed_domains` domains is set, only these domains are exposed by default. If `expose_by_default` is set to false, devices have to be manually exposed in `entity_config`."
  required: false
  default: true
  type: boolean
exposed_domains:
  description: List of entity domains to expose to Yandex Smart Home if `expose_by_default` is set to true. This has no effect if `expose_by_default` is set to false.
  required: false
  type: list
entity_config:
  description: Entity specific configuration for Yandex Smart Home
  required: false
  type: map
  keys:
    '`<ENTITY_ID>`':
      description: Entity to configure
      required: false
      type: map
      keys:
        name:
          description: Name of the entity to show in Yandex Smart Home
          required: false
          type: string
        expose:
          description: Force an entity to be exposed/excluded.
          required: false
          type: boolean
        room:
          description: Allows for associating this device to a Room in Yandex Smart Home.
          required: false
          type: string
{% endconfiguration %}

### Available domains

Currently only on/off action implemented, the following domains are available to be used:

- group (on/off)
- input_boolean (on/off)
- switch (on/off)
- fan (on/off)
- light (on/off)
- cover (on/off)
- media_player (on/off)

### Room/Area support

Entities that have not got rooms explicitly set and that have been placed in Home Assistant areas will return room hints to Yandex Smart Home with the devices in those areas.

### Create Dialog

Go to https://dialogs.yandex.ru/developer/ and create smart home dialog.

Field | Value
------------ | -------------
Endpoint URL | https://[YOUR HOME ASSISTANT URL:PORT]/api/yandex_smart_home

For account linking add configuration on https://dialogs.yandex.ru/developer/settings/oauth:

Field | Value
------------ | -------------
Client identifier | https://social.yandex.net/
API authorization endpoint | https://[YOUR HOME ASSISTANT URL:PORT]/auth/authorize
Token Endpoint | https://[YOUR HOME ASSISTANT URL:PORT]/auth/token
