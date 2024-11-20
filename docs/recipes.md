В этом разделе собраны конфигурации популярных устройств. При использовании обязательно поменяйте ID объектов на свои.

Рецепты присланы пользователи, поэтому работоспособность не гарантируется.

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
              - unknown
    sequence:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW1 }}"
            sequence:
              - action: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413744128"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW2' }}"
            sequence:
              - action: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413744384"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW3' }}"
            sequence:
                - action: androidtv.adb_command
                  target:
                    entity_id: media_player.androidtv
                  data:
                    command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413744640"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'HW4 }}"
            sequence:
              - action: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: "adb shell am start -a android.intent.action.VIEW -d content://android.media.tv/passthrough/com.tcl.tvinput%2F.passthroughinput.TvPassThroughService%2FHW1413745664"
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'ru.yourok.num' }}"
            sequence:
              - action: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: ru.yourok.num
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'ru.kinopoisk.tv' }}"
            sequence:
              - action: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: ru.kinopoisk.tv
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'com.google.android.tvlauncher'' }}"
            sequence:
              - action: androidtv.adb_command
                target:
                  entity_id: media_player.androidtv
                data:
                  command: HOME
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'ru.more.play' }}"
            sequence:
              - action: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: ru.more.play
          - conditions:
              - condition: template
                value_template: "{{ input_source == 'com.google.android.youtube.tv' }}"
            sequence:
              - action: media_player.select_source
                target:
                  entity_id: media_player.androidtv
                data:
                  source: com.google.android.youtube.tv
        default:
          - action: system_log.write
            data:
              message: "[change_tv_input_source script] No action is defined for input source '{{ input_source }}'"

yandex_smart_home:
  entity_config:
    media_player.androidtv:
      # https://docs.yaha-cloud.ru/dev/advanced/capabilities/range/
      # указываем, что для volume поддерживаются increase_value и decrease_value
      # и не указываем set_value - так Yandex Smart Home понимает, что абсолютные
      # значение громкости не поддерживаются ТВ
      custom_ranges:
        volume:
          increase_value:
            action: media_player.volume_up
            entity_id: media_player.androidtv
          decrease_value:
            action: media_player.volume_down
            entity_id: media_player.androidtv
      # https://docs.yaha-cloud.ru/dev/advanced/capabilities/mode/
      modes:
        input_source:
          one: 'HW1' # HDMI 1
          two: 'HW2' # HDMI 2
          three: 'HW3' # HDMI 3
          four: 'HW4' # HDMI 4
          five: 'com.google.android.tvlauncher' # home
          six: 'ru.yourok.num' # NUM
          seven: 'ru.kinopoisk.tv' # Кинопоиск
          eight: 'ru.more.play' # ОККО
          nine: 'com.google.android.youtube.tv' # YouTube
          ten: 'unknown' # unknown app/source
      custom_modes:
        input_source:
          state_entity_id: sensor.tv_input_source
          set_mode:
            action: script.change_tv_input_source
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
      type: thermostat.ac
      custom_toggles:
        backlight: # подсветка
          state_entity_id: climate.tasmota_ac
          state_attribute: light
          turn_on:
            action: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'on'
          turn_off:
            action: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'off'
```

## Бойлер Thermex Lima 80v  { id=thermex-lima-80v }

> Интеграция: [Tuya Local](https://github.com/make-all/tuya-local)

```yaml
yandex_smart_home:
  entity_config:
    switch.thermex_lima_80v_water_heater:
      name: Бойлер
      properties:
        - type: temperature
          entity: sensor.thermex_lima_80v_current_temperature
        - type: temperature
          entity: sensor.thermex_lima_80v_target_temperature
      custom_ranges:
        temperature:
          state_entity_id: number.thermex_lima_80v_set_target_temperature
          set_value:
            action: number.set_value
            entity_id: number.thermex_lima_80v_set_target_temperature
            data:
              value: '{{ value }}'
          range:
            min: 35
            max: 75
            precision: 1
```
