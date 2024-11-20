## Чайник Redmond (KomX/ESPHome-Ready4Sky) { id=redmond-kettle-komx }

> Интеграция: [KomX/ESPHome-Ready4Sky](https://github.com/KomX/ESPHome-Ready4Sky)

```yaml
yandex_smart_home:
  entity_config:
    switch.rk_g200s_power:
      name: Чайник
      room: Кухня
      type: cooking.kettle
      properties:
        - type: temperature
          entity: sensor.rk_g200s_temperature
      custom_toggles:
        backlight:
          state_entity_id: switch.rk_g200s_state_led
          turn_on:
            action: switch.turn_on
            entity_id: switch.rk_g200s_state_led
          turn_off:
            action: switch.turn_off
            entity_id: switch.rk_g200s_state_led
        mute:
          state_entity_id: switch.rk_g200s_beeper
          turn_on:
            action: switch.turn_on
            entity_id: switch.rk_g200s_beeper
          turn_off:
            action: switch.turn_off
            entity_id: switch.rk_g200s_beeper
      custom_ranges:
        temperature:
          state_entity_id: number.rk_g200s_target
          set_value:
            action: number.set_value
            entity_id: number.rk_g200s_target
            data:
              value: '{{ value }}'
          range:
            min: 35
            max: 100
            precision: 5
```

## Чайник Redmond (ClusterM/skykettle-ha) { id=redmond-kettle-clusterm }

> Интеграция: [ClusterM/skykettle-ha](https://github.com/ClusterM/skykettle-ha)

```yaml
yandex_smart_home:
  entity_config:
    water_heater.skykettle_rk_m216s:
      name: Чайник
      room: Кухня
      type: cooking.kettle
      properties:
        - type: temperature
          entity: water_heater.skykettle_rk_m216s
          attribute: current_temperature
      custom_toggles:
        backlight:
          state_entity_id: switch.skykettle_rk_m216s_enable_sync_light
          turn_on:
            action: switch.turn_on
            entity_id: switch.skykettle_rk_m216s_enable_sync_light
          turn_off:
            action: switch.turn_off
            entity_id: switch.skykettle_rk_m216s_enable_sync_light
        mute:
          state_entity_id: switch.skykettle_rk_m216s_enable_sound
          turn_on:
            action: switch.turn_on
            entity_id: switch.skykettle_rk_m216s_enable_sound
          turn_off:
            action: switch.turn_off
            entity_id: switch.skykettle_rk_m216s_enable_sound
      custom_ranges:
        temperature:
          state_entity_id: water_heater.skykettle_rk_m216s
          state_attribute: temperature
          set_value:
            action: water_heater.set_temperature
            target: water_heater.skykettle_rk_m216s
            data:
              temperature: '{{ value }}'
          range:
            min: 25
            max: 100
            precision: 5
```
