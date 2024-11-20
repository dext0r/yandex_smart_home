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
