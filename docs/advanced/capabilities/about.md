!!! danger "Только для продвинутых пользователей!"

Иногда возможностей компонента недостаточно и хочется добавить свои функции, переключатели и регулировки.
Это можно сделать через "пользовательские умения" для каждого устройства отдельно через `entity_config`.

!!! important "**Важно!** Пользовательские умения являются приоритетными и перекрывают автоматически обнаруженные"

Поддерживается несколько видов пользовательских умений:

* [Режимы](mode.md) (`mode`) - переключение режимов работы устройства (режим работы кондиционера, уборки, источника сигнала и т.п.).
  Настраиваются через словарь `custom_modes`.
* [Переключатели](toggle.md) (`toggle`) - управление функциями, которые включаются и выключаются (пауза, вращение вентилятора, ионизация и т.п.).
  Настраиваются через словарь `custom_toggles`.
* [Выбор из диапазона](range.md) (`range`) - управление параметрами устройства, которые имеют диапазон (яркость лампы, громкость звука, температура нагревателя).
  Настраиваются через словарь `custom_ranges`.

В каждое умение входит ряд функций: например функция `volume` в умении `range` или функция `mute` в умении `toggle`.
У одного устройства может быть **несколько** функций в разных умениях (или в одном).
Дубликаты функций невозможны (т.е. `volume` может быть только одна для одного устройства).

Функции никак не привязаны к типу устройства, а это значит, что функцию "громкость" можно назначить, например, для выключателя или увлажнителя.
Это позволяет реализовывать **[безумный набор умений](../../assets/images/crazy-caps.png)** в одном устройстве.

!!! example "Пример настройки пользовательских умений"
    ```yaml
    yandex_smart_home:
      entity_config:
        media_player.tv:
          custom_ranges:
            channel:
              set_value:
                service: media_player.play_media
                entity_id: media_player.tv
                data:
                  media_content_type: channel
                  media_content_id: '{{ value }}'
            volume:
              increase_value:
                service: script.increase_volume
              decrease_value:
                service: script.decrease_volume
        climate.room_ac:
          custom_toggles:
            backlight:
              state_entity_id: climate.room_ac
              state_attribute: backlight
            mute:
              state_template: '{{ is_state("switch.room_ac_beeper", "off") }}'
              turn_on:
                service: switch.turn_off
                entity_id: switch.room_ac_beeper
              turn_off:
                service: switch.turn_on
                entity_id: switch.room_ac_beeper
        media_player.tv:
          modes:
            input_source:
              one: ['HW1']
              two: ['HW2']
          custom_modes:
            input_source:
              state_entity_id: sensor.tv_input_source
              set_mode:
                service: script.change_tv_input_source
                data:
                  input_source: '{{ mode }}'
    ```

## Текущее состояние умения { id=state }

Желательно, чтобы УДЯ знал о текущем состоянии умения. В противном случае состояние не будет отражено в приложении "Дом с Алисой", а Алиса не озвучит его на вопрос "Что с устройством". Отсутствие текущего состояния не влияет на возможность управления умением.

Способы задать источник состояния:

* `state_entity_id`: Объект, состояние которого содержит состояние умения
!!! example "Пример использования state_entity_id"

    ```yaml
    # Состояние функции "Блокировка управления" определяется из состояния switch.air_purifier_child_lock
    yandex_smart_home:
      entity_config:
        fan.air_purifier:
          custom_toggles:
            controls_locked:
              state_entity_id: switch.air_purifier_child_lock
              turn_on: ...
              turn_off: ...
    ```

* `state_entity_id` + `state_attribute`: Атрибут объекта `state_entity_id`, значение которого содержит состояния умения
!!! example "Пример использования state_entity_id + state_attribute"

    ```yaml
    # Состояние функции "Скорость работы" определяется из значения атрибута water_level объекта vacuum.mop
    yandex_smart_home:
      entity_config:
        vacuum.mop:
          modes:
            work_speed:
              eco: ['V1']
              medium: ['V2']
          custom_modes:
            work_speed:
              state_entity_id: vacuum.mop
              state_attribute: water_level
              set_mode: ...
    ```

    Примечание: `state_entity_id` может быть опущен, если его значение совпадает с объектом, для которого настраивается умение. Во всех примерах `state_entity_id`  указывается явно для избежания путаницы.

* `state_template`: Для определения состояния умения используется результат вычисления шаблона
!!! example "Пример использования state_template"

    ```yaml
    # Состояние функции "Отключение звука" определяется из инвертированного состояния switch.kettle_beeper
    yandex_smart_home:
      entity_config:
        water_heater.kettle:
          custom_toggles:
            mute:
              state_template: '{{ is_state("switch.kettle_beeper", "off") }}'
              turn_on: ...
              turn_off: ...
    ```
