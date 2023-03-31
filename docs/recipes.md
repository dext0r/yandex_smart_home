В этом разделе собраны конфигурации популярных устройств. При использовании обязательно поменяйте ID объектов на свои.

[Предложить свой рецепт](https://forms.yandex.ru/u/62b456db0c134229d975d1e3/){ .md-button }

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
            service: switch.turn_on
            entity_id: switch.smartmi_humidifier_child_lock
          turn_off:
            service: switch.turn_off
            entity_id: switch.smartmi_humidifier_child_lock
        backlight: # подсветка
          state_entity_id: select.smartmi_humidifier_led_brightness
          turn_on:
            service: select.select_option
            entity_id: select.smartmi_humidifier_led_brightness
            data:
              option: bright # или dim
          turn_off:
            service: select.select_option
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
          state_attribute: indicator_light.on
          turn_on:
            service: light.turn_on
            entity_id: light.deerma_jsq2w_2976_indicator_light
          turn_off:
            service: light.turn_off
            entity_id: light.deerma_jsq2w_2976_indicator_light
        mute:
          state_entity_id: switch.deerma_jsq2w_2976_alarm
          state_attribute: alarm
          turn_on:
            service: switch.turn_off
            entity_id: switch.deerma_jsq2w_2976_alarm
          turn_off:
            service: switch.turn_on
            entity_id: switch.deerma_jsq2w_2976_alarm
      modes:
        program:
          low: ["Level1"]
          medium: ["Level2"]
          high: ["Level3"]
          auto: ["Level4"]
      custom_modes:
        program:
          state_entity_id: fan.deerma_jsq2w_2976_fan_level
          state_attribute: preset_mode
          set_mode:
            service: fan.set_preset_mode
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
          quiet: ['Sleep']
          normal: ['Const Humidity']
          turbo: ['Strong']
      custom_toggles:
        keep_warm: # подогрев
          state_entity_id: switch.leshow_jsq1_ee06_warm_wind_turn
          turn_on:
            service: switch.turn_on
            entity_id: switch.leshow_jsq1_ee06_warm_wind_turn
          turn_off:
            service: switch.turn_off
            entity_id: switch.leshow_jsq1_ee06_warm_wind_turn
        backlight: # подсветка
          state_entity_id: number.leshow_jsq1_ee06_screen_brightness
          turn_on:
            service: number.set_value
            entity_id: number.leshow_jsq1_ee06_screen_brightness
            data:
              value: '1'
          turn_off:
            service: number.set_value
            entity_id: number.leshow_jsq1_ee06_screen_brightness
            data:
              value: '0'
```

## Чайник Redmond (KomX/ESPHome-Ready4Sky) { id=redmond-kettle-komx }
> Интеграция: [KomX/ESPHome-Ready4Sky](https://github.com/KomX/ESPHome-Ready4Sky)

```yaml
yandex_smart_home:
  entity_config:
    switch.rk_g200s_power:
      name: Чайник
      room: Кухня
      type: devices.types.cooking.kettle
      properties:
        - type: temperature
          entity: sensor.rk_g200s_temperature
      custom_toggles:
        backlight:
          state_entity_id: switch.rk_g200s_state_led
          turn_on:
            service: switch.turn_on
            entity_id: switch.rk_g200s_state_led
          turn_off:
            service: switch.turn_off
            entity_id: switch.rk_g200s_state_led
        mute:
          state_entity_id: switch.rk_g200s_beeper
          turn_on:
            service: switch.turn_on
            entity_id: switch.rk_g200s_beeper
          turn_off:
            service: switch.turn_off
            entity_id: switch.rk_g200s_beeper
      custom_ranges:
        temperature:
          state_entity_id: number.rk_g200s_target
          set_value:
            service: number.set_value
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
      type: devices.types.cooking.kettle
      properties:
        - type: temperature
          entity: water_heater.skykettle_rk_m216s
          attribute: current_temperature
      custom_toggles:
        backlight:
          state_entity_id: switch.skykettle_rk_m216s_enable_sync_light
          turn_on:
            service: switch.turn_on
            entity_id: switch.skykettle_rk_m216s_enable_sync_light
          turn_off:
            service: switch.turn_off
            entity_id: switch.skykettle_rk_m216s_enable_sync_light
        mute:
          state_entity_id: switch.skykettle_rk_m216s_enable_sound
          turn_on:
            service: switch.turn_on
            entity_id: switch.skykettle_rk_m216s_enable_sound
          turn_off:
            service: switch.turn_off
            entity_id: switch.skykettle_rk_m216s_enable_sound
      custom_ranges:
        temperature:
          state_attribute: temperature
          set_value:
            service: water_heater.set_temperature
            data:
              temperature: '{{ value }}'
          range:
            min: 25
            max: 100
            precision: 5
```

## Телевизор TCL 65C828 { id=android-tv-tcl }
> Интеграция: [Android TV](https://www.home-assistant.io/integrations/androidtv/)

Может использоваться и с другими телевизорами на Android TV.

```yaml
template:
  sensor:
    - name: 'TV Input Source'
      state: >
        {% set hdmi_input = state_attr('media_player.androidtv', 'hdmi_input') %}
        {% set app_id = state_attr('media_player.androidtv', 'app_id') %}
        {% if hdmi_input and hdmi_input in ['HW1', 'HW2', 'HW3', 'HW4'] %}
          {{ hdmi_input }}
        {% elif app_id and app_id in ['com.google.android.tvlauncher', 'ru.yourok.num', 'ru.kinopoisk.tv', 'ru.more.play', 'com.google.android.youtube.tv'] %}
          {{ app_id }}
        {% else %}
          unknown
        {% endif %}

script:
  change_tv_input_source:
    alias: Change TV input source
    mode: single
    icon: mdi:television
    description: Changes TV input source based on Alisa Yandex request.  Source 1 is
      mapped to ...,  Source 2 ...
    fields:
      input_source:
        name: Input source
        required: true
        example: HW1
        selector:
          select:
            options:
              - HW1
              - HW2
              - HW3
              - HW4
              - five
              - ru.yourok.num
              - ru.kinopoisk.tv
              - ru.more.play
              - YouTube
              - uknown
    sequence:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW1 }}"
            sequence:
              - service: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413744128"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW2' }}"
            sequence:
              - service: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413744384"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW3' }}"
            sequence:
                - service: androidtv.adb_command
                  target:
                    entity_id: media_player.androidtv
                  data:
                    command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413744640"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW4 }}"
            sequence:
              - service: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413745664"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'ru.yourok.num' }}"
            sequence:
              - service: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: ru.yourok.num
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'ru.kinopoisk.tv' }}"
            sequence:
              - service: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: ru.kinopoisk.tv
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'com.google.android.tvlauncher'' }}"
            sequence:
              - service: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: HOME
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'ru.more.play' }}"
            sequence:
              - service: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: ru.more.play
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'com.google.android.youtube.tv' }}"
            sequence:
              - service: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: com.google.android.youtube.tv
        default:
          - service: system_log.write
            data:
              message: "[change_tv_input_source script] No action is defined for input source '{{ input_source }}'"

yandex_smart_home:
  entity_config:
    media_player.androidtv:
      # https://docs.yaha-cloud.ru/v0.6.x/advanced/capabilities/#custom-ranges
      # указываем, что для volume поддерживаются increase_value и decrease_value
      # и не указываем set_value - так Yandex Smart Home понимает, что абсолютные
      # значение громкости не поддерживаются ТВ
      custom_ranges:
        volume:
          increase_value:
            service: media_player.volume_up
            entity_id: media_player.androidtv
          decrease_value:
            service: media_player.volume_down
            entity_id: media_player.androidtv
      # https://docs.yaha-cloud.ru/v0.6.x/advanced/capabilities/#custom-modes
      modes:
        input_source:
          one: ['HW1'] # HDMI 1
          two: ['HW2'] # HDMI 2
          three: ['HW3'] # HDMI 3
          four: ['HW4'] # HDMI 4
          five: ['com.google.android.tvlauncher'] # home
          six: ['ru.yourok.num'] # NUM
          seven: ['ru.kinopoisk.tv'] # Кинопоиск
          eight: ['ru.more.play'] # ОККО
          nine: ['com.google.android.youtube.tv'] # YouTube
          ten: ['unknown'] # unknown app/source
      custom_modes:
        input_source:
          state_entity_id: sensor.tv_input_source
          set_mode:
            service: script.change_tv_input_source
            data:
              input_source: '{{ mode }}'
```


## Управление подсветкой Tasmota-IRVAC { id=tasmota-irhvac }
> Интеграция: [Tasmota-IRHVAC](https://github.com/hristo-atanasov/Tasmota-IRHVAC)

```yaml
yandex_smart_home:
  entity_config:
    climate.tasmota_ac:
      name: Кондиционер
      type: devices.types.thermostat.ac
      custom_toggles:
        backlight: # подсветка
          state_attribute: light
          turn_on:
            service: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'on'
          turn_off:
            service: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'off'
```
