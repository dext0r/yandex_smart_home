## Увлажнитель Xiaomi Smartmi { id=xiaomi-smartmi-humidifier }

```yaml
yandex_smart_home:
  entity_config:
    humidifier.smartmi_humidifier:
      properties:
        - type: temperature
          entity: sensor.smartmi_humidifier_temperature
        - type: humidity
          entity: sensor.smartmi_humidifier_humidity
        - type: water_level
          entity: sensor.smartmi_humidifier_water_level
      custom_toggles:
        controls_locked: # блокировка управления
          state_entity_id: switch.smartmi_humidifier_child_lock
          turn_on:
            action: switch.turn_on
            entity_id: switch.smartmi_humidifier_child_lock
          turn_off:
            action: switch.turn_off
            entity_id: switch.smartmi_humidifier_child_lock
        backlight: # подсветка
          state_template: '{{ not is_state("select.smartmi_humidifier_led_brightness", "off") }}'
          turn_on:
            action: select.select_option
            entity_id: select.smartmi_humidifier_led_brightness
            data:
              option: bright # или dim
          turn_off:
            action: select.select_option
            entity_id: select.smartmi_humidifier_led_brightness
            data:
              option: 'off'
```

## Xiaomi Smart Humidifier 2 { id=xiaomi-smart-humidifier-2 }

> Интеграция: [Xiaomi Miot](https://github.com/al-one/hass-xiaomi-miot)

```yaml
yandex_smart_home:
  entity_config:
    humidifier.deerma_jsq2w_2976_humidifier:
      name: Увлажнитель
      properties:
        - type: temperature
          entity: sensor.deerma_jsq2w_2976_temperature
        - type: humidity
          entity: sensor.deerma_jsq2w_2976_relative_humidity
      custom_toggles:
        backlight:
          state_entity_id: light.deerma_jsq2w_2976_indicator_light
          turn_on:
            action: light.turn_on
            entity_id: light.deerma_jsq2w_2976_indicator_light
          turn_off:
            action: light.turn_off
            entity_id: light.deerma_jsq2w_2976_indicator_light
        mute:
          state_template: '{( is_state("switch.deerma_jsq2w_2976_alarm", "off") }}'
          turn_on:
            action: switch.turn_off
            entity_id: switch.deerma_jsq2w_2976_alarm
          turn_off:
            action: switch.turn_on
            entity_id: switch.deerma_jsq2w_2976_alarm
      modes:
        program:
          low: "Level1"
          medium: "Level2"
          high: "Level3"
          auto: "Level4"
      custom_modes:
        program:
          state_entity_id: fan.deerma_jsq2w_2976_fan_level
          state_attribute: preset_mode
          set_mode:
            action: fan.set_preset_mode
            entity_id: fan.deerma_jsq2w_2976_fan_level
            data:
              preset_mode: "{{ mode }}"
```

## Xiaomi Mijia Pure Smart Humidifier Pro { id=xiaomi-mijia-pure-smart-humidifier-pro }

> Интеграция: [Xiaomi Miot](https://github.com/al-one/hass-xiaomi-miot)

```yaml
yandex_smart_home:
  entity_config:
    humidifier.leshow_jsq1_ee06_humidifier:
      properties:
        - type: water_level
          entity: sensor.leshow_jsq1_ee06_water_level
        - type: humidity
          entity: sensor.gostinaya_temp_humidity
      modes:
        program:
          quiet: 'Sleep'
          normal: 'Const Humidity'
          turbo: 'Strong'
      custom_toggles:
        keep_warm: # подогрев
          state_entity_id: switch.leshow_jsq1_ee06_warm_wind_turn
          turn_on:
            action: switch.turn_on
            entity_id: switch.leshow_jsq1_ee06_warm_wind_turn
          turn_off:
            action: switch.turn_off
            entity_id: switch.leshow_jsq1_ee06_warm_wind_turn
        backlight: # подсветка
          state_entity_id: number.leshow_jsq1_ee06_screen_brightness
          turn_on:
            action: number.set_value
            entity_id: number.leshow_jsq1_ee06_screen_brightness
            data:
              value: '1'
          turn_off:
            action: number.set_value
            entity_id: number.leshow_jsq1_ee06_screen_brightness
            data:
              value: '0'
```

## Xiaomi Mi Air Purifier 2S { id=xiaomi-mi-air-purifier-2s }

> Интеграция: [Xiaomi Miio](https://www.home-assistant.io/integrations/xiaomi_miio/)

```yaml
yandex_smart_home:
  entity_config:
    fan.ochistitel_vozdukha:
      type: purifier
      properties:
        - type: pm2.5_density
          entity: sensor.ochistitel_vozdukha_pm2_5
        - type: temperature
          entity: sensor.ochistitel_vozdukha_temperature
        - type: humidity
          entity: sensor.ochistitel_vozdukha_humidity
        - type: water_level # ресурс фильтров, в УДЯ нет такой характеристики
          entity: sensor.ochistitel_vozdukha_filter_life_remaining
      custom_toggles:
        backlight:
          state_entity_id: switch.ochistitel_vozdukha_led
          turn_on:
            action: switch.turn_on
            entity_id: switch.ochistitel_vozdukha_led
          turn_off:
            action: switch.turn_off
            entity_id: switch.ochistitel_vozdukha_led
        controls_locked:
          state_entity_id: switch.ochistitel_vozdukha_child_lock
          turn_on:
            action: switch.turn_on
            entity_id: switch.ochistitel_vozdukha_child_lock
          turn_off:
            action: switch.turn_off
            entity_id: switch.ochistitel_vozdukha_child_lock
```

## Mi Air Purifier 3C { id=xiaomi-mi-air-purifier-3с }

> Интеграция: [Xiaomi Miio](https://www.home-assistant.io/integrations/xiaomi_miio/)

```yaml
yandex_smart_home:
  entity_config:
    fan.mi_air_purifier_3c:
      type: purifier
      properties:
        - type: pm2.5_density
          entity: sensor.mi_air_purifier_3c_pm2_5
      custom_toggles:
        controls_locked: # блокировка управления
          state_entity_id: switch.mi_air_purifier_3c_child_lock
          turn_on:
            action: switch.turn_on
            entity_id: switch.mi_air_purifier_3c_child_lock
          turn_off:
            action: switch.turn_off
            entity_id: switch.mi_air_purifier_3c_child_lock
        mute: # Звук
          state_template: '{( is_state("switch.mi_air_purifier_3c_buzzer", "off") }}'
          turn_on:
            action: switch.turn_off
            entity_id: switch.mi_air_purifier_3c_buzzer
          turn_off:
            action: switch.turn_on
            entity_id: switch.mi_air_purifier_3c_buzzer
      custom_ranges:
        brightness: # Яркость подсветки
          state_entity_id: number.mi_air_purifier_3c_led_brightness
          set_value:
            action: number.set_value
            target:
              entity_id: number.mi_air_purifier_3c_led_brightness
            data:
              value: "{{ ((state_attr('number.mi_air_purifier_3c_led_brightness','max'))/100*value)| round(0) }}"
          range:
            min: 0
            max: 100
            precision: 10
        volume: # Сохранённая скорость
          state_entity_id: fan.mi_air_purifier_3c
          state_attribute: favorit_speed
          set_value:
            action: number.set_value
            target:
              entity_id: number.mi_air_purifier_3c_favorite_motor_speed
            data:
              value: "{{(((state_attr('number.mi_air_purifier_3c_favorite_motor_speed','max')-300)/100*value+300)/10)| round(0)*10}}"
          range:
            min: 0
            max: 100
            precision: 1
```

## AIRMX A3S { id=airmx-a3s }

> Интеграция: [AIRMX](https://github.com/dext0r/airmx)

```yaml
yandex_smart_home:
  entity_config:
    humidifier.airwater_a3s_48403:
      properties:
        - type: water_level
          entity: sensor.airwater_a3s_48403_water_level
      modes:
        program:
          quiet: "sleep"
          medium: "manual" #  ручной режим, в нем целевая влажность 0
          auto: "auto"
      custom_ranges:
        volume:  # вентилятор для ручного режима, как самое подходящее
          state_entity_id: number.airwater_a3s_48403_fan_speed
          set_value:
            action: number.set_value
            target:
              entity_id: number.airwater_a3s_48403_fan_speed
            data:
              value: '{{ value }}'
          range:
            min: 0
            max: 100
            precision: 10
```
