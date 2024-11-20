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

## Xiaomi Smart Kettle 2 Pro { id=xiaomi-smart-kettle-2-pro }

> Интеграция: [Xiaomi Miot](https://github.com/al-one/hass-xiaomi-miot)

```yaml
# Потребуется создать вспомогательный свитч и две автоматизации включения и выключения. В первом случае - установка температуры на #99, во втором случае - нажатие кнопки Stop-work.
yandex_smart_home:
  entity_config:
    input_boolean.kettle_switch:
      type: devices.types.cooking.kettle
      properties:
        - type: temperature
          entity: water_heater.yunmi_v19_4c2c_kettle
          attribute: current_temperature
      custom_toggles:
        mute:
          state_entity_id: switch.yunmi_v19_4c2c_no_disturb
          turn_on:
            action: switch.turn_on
            entity_id: switch.yunmi_v19_4c2c_no_disturb
          turn_off:
            action: switch.turn_off
            entity_id: switch.yunmi_v19_4c2c_no_disturb
      custom_ranges:
        temperature:
          state_entity_id: water_heater.yunmi_v19_4c2c_kettle
          set_value:
            action: water_heater.set_temperature
            entity_id: water_heater.yunmi_v19_4c2c_kettle
            data:
              temperature: '{{ value }}'
          range:
            min: 40
            max: 100
            precision: 1
```

## Polaris PWK 1775CGLD { id=polaris-pwk-1775cgld }

> Интеграция: MQTT

```yaml
yandex_smart_home:
  entity_config:
    water_heater.polaris_kettle:
      name: Чайник
      room: Кухня
      type: devices.types.cooking.kettle
      properties:
        - type: water_level
          entity: sensor.polaris_kettle_water_level_percent
      turn_on:
        action: water_heater.set_operation_mode
        target:
          entity_id: water_heater.polaris_kettle
        data:
          operation_mode: Разогрев с удержанием
      turn_off:
        action: water_heater.turn_off
        target:
          entity_id: water_heater.polaris_kettle
      custom_ranges:
        temperature:
          state_entity_id: water_heater.polaris_kettle
          state_attribute: temperature
          set_value:
            action: water_heater.set_temperature
            target:
              entity_id: water_heater.polaris_kettle
            data:
              temperature: '{{ value }}'
              operation_mode: Разогрев с удержанием
          range:
            min: 30
            max: 100
            precision: 1
      custom_toggles:
        mute:
          state_entity_id: switch.polaris_kettle_mute
          turn_on:
            action: switch.turn_on
            target:
              entity_id: switch.polaris_kettle_mute
          turn_off:
            action: switch.turn_off
            target:
              entity_id: switch.polaris_kettle_mute
        keep_warm:
          state_entity_id: binary_sensor.polaris_kettle_keep_warm_on
          turn_on:
            action: water_heater.set_operation_mode
            target:
              entity_id: water_heater.polaris_kettle
            data:
              operation_mode: Разогрев с удержанием
          turn_off:
            action: water_heater.set_operation_mode
            target:
              entity_id: water_heater.polaris_kettle
            data:
              operation_mode: 'off'
      modes:
        tea_mode:
          black_tea: 'black_tea'
          flower_tea: 'flower_tea'
          green_tea: 'green_tea'
          herbal_tea: 'herbal_tea'
          oolong_tea: 'oolong_tea'
          puerh_tea: 'puerh_tea'
          red_tea: 'red_tea'
          white_tea: 'white_tea'
      custom_modes:
        tea_mode:
          set_mode:
            action: script.{{ mode }}
```
