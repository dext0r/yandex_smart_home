!!! danger "Только для продвинутых пользователей!"

Иногда возможностей компонента недостаточно и хочется добавить свои функции, переключатели и регулировки.
Это можно сделать через "пользовательские умения" для каждого устройства отдельно через `entity_config`.

!!! important "**Важно!** Пользовательские умения являются приоритетными и перекрывают автоматически обнаруженные"

Поддерживается несколько видов пользовательских умений:

* [Режимы](#custom-modes) (`mode`) - переключение режимов работы устройства (режим работы кондиционера, уборки, источника сигнала и т.п.).
  Настраиваются через словарь `custom_modes`.
* [Переключатели](#custom-toggles) (`toggle`) - управление функциями, которые включаются и выключаются (пауза, вращение вентилятора, ионизация и т.п.).
  Настраиваются через словарь `custom_toggles`.
* [Выбор из диапазона](#custom-ranges) (`range`) - управление параметрами устройства, которые имеют диапазон (яркость лампы, громкость звука, температура нагревателя).
  Настраиваются через словарь `custom_ranges`.

В каждое умение входит ряд функций (например функция `volume` в умении `range`). 
У одного устройства может быть **несколько** функций в разных умениях (или в одном). 
Дубликаты функций невозможны (т.е. `volume` может быть только одна для одного устройства).

Функции никак не привязаны к типу устройства, а это значит, что функцию "громкость" можно назначить, например, для выключателя или увлажнителя. 
Это позволяет реализовывать **[безумный набор умений](../assets/images/crazy-caps.png)** в одном устройстве.

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

## Умения "Режимы работы" (custom_modes) { id=custom-modes }
Выбирает режим работы устройства, при изменении которого будет вызываться определённый сервис. Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html)**.

Примеры: кофеварка, которая варит кофе скриптом `script.makemeonecupofcoffee` или моющий пылесос Xiaomi, в котором хочется управлять количеством подаваемой воды через сервис `xiaomi_vacuum.set_water_level`.

Для пользовательского режима автоматического связывание между значениями УДЯ и Home Assistant не производится. Вам нужно
вручную [задать соответствия](../config/modes.md) через `modes`!

Параметры:

* `set_mode`: Вызываемый сервис при выборе режима в УДЯ. В переменной `mode` - значение режима на стороне Home Assistant. Если не задан - режим из УДЯ меняться не будет.
    
    !!! example "Пример"
        ```yaml
        set_mode:
          service: xiaomi_vacuum.set_water_level
          entity_id: vacuum.xiaomi_mop
          data:
            water_level: '{{ mode }}'
        ```

### Примеры { id=custom-modes-examples }
#### Моющий пылесос { id=custom-modes-example-vacuum }
Моющий пылесос Xiaomi (`vacuum.xiaomi_mop`), переключение `set_water_level` через функцию "Скорость работы"
!!! summary "Атрибуты у vacuum.xiaomi_mop"
    ```yaml
    water_level: High
    water_level_list:
      - Low
      - Med
      - High
    ```

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        vacuum.xiaomi_mop:
          modes:
            work_speed:  # соответствие между режимами УДЯ и HA
              eco: ['Low']
              medium: ['Med']
              max: ['High']
          custom_modes:
            work_speed:
              state_entity_id: vacuum.xiaomi_mop
              state_attribute: water_level
              set_mode:
                service: xiaomi_vacuum.set_water_level
                entity_id: vacuum.xiaomi_mop
                data:
                  water_level: '{{ mode }}' # сюда подставятся Low/Med/High
    ```

#### Кофеварка { id=custom-modes-example-coffee-machine }
Кофеварка (`climate.hotcoffee`), которая умеет варить кофе скриптами, программа выбирается через функцию "Режим работы кофеварки"

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        climate.hotcoffee:
          type: cooking.coffee_maker
          modes:
            coffee_mode:
              cappuccino: ['cappuccino']
              latte: ['latte']
          custom_modes:
            coffee_mode:
              set_mode:
                service: script.make_me_{{ mode }}_coffee  # вызовется script.make_me_latte_coffee
    ```

## Умения "Переключатели" (custom_toggles) { id=custom-toggles }
Управление функциями устройств, которые включаются и выключаются. Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html)**. В [состоянии](#state) ожидается логическое значение (`on/off/yes/no/True/False/1/0`).

Параметры:

* `turn_on` и `turn_off`: Вызываемые сервисы при включении/выключении функции в УДЯ. Если не задан один или несколько сервисов - соответствующее действие выполняться не будет.
    
    !!! example "Пример"
        ```yaml
        turn_on:
          service: xiaomi_miio_airpurifier.fan_set_ptc_on
          entity_id: fan.xiaomi_airfresh_va4
        turn_off:
          service: xiaomi_miio_airpurifier.fan_set_ptc_off
          entity_id: fan.xiaomi_airfresh_va4
        ```

### Примеры { id=custom-toggles-examples }
#### Бризер { id=custom-toggles-example-breezer }
Управление функцией подогрева для бризера Xiaomi (`fan.xiaomi_airfresh_va4`) через функцию "Поддержание тепла"

!!! summary "Атрибуты fan.xiaomi_airfresh_va4"
    ```yaml
    model: zhimi.airfresh.va4
    ptc: false  # а может быть true (on/off тоже подходит)
    ```

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        fan.xiaomi_airfresh_va4:
          custom_toggles:
            keep_warm:
              state_entity_id: fan.xiaomi_airfresh_va4
              state_attribute: ptc
              turn_on:
                service: xiaomi_miio_airpurifier.fan_set_ptc_on
                entity_id: fan.xiaomi_airfresh_va4
              turn_off:
                service: xiaomi_miio_airpurifier.fan_set_ptc_off
                entity_id: fan.xiaomi_airfresh_va4
    ```

## Умения "Выбор значения из диапазона" (custom_ranges) { id=custom-ranges }
Управление параметрами устройства, которые имеют диапазон регулировки (громкость, яркость, температура). Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html)**. В [состоянии](#state) ожидается числовое значение.

Специфичные параметры:

* `set_value`: Сервис вызываемый при установке абсолютного значения функции. В переменной `value` абсолютное или относительное значение (в зависимости от настроек `range` и наличия `increase_value` и `decrease_value`). 
Если не задан - установка абсолютного значения поддерживаться не будет.

    !!! example "Пример"
        ```yaml
         set_value:
           service: xiaomi_miio_airpurifier.fan_set_favorite_speed
           entity_id: fan.xiaomi_airfresh_a1
           data:
             speed: '{{ value }}'
        ```

* `increase_value` и `decrease_value`: Сервисы, вызываемые при относительной регулировке (кнопки `+` и `-` и "Алиса, убавь температуру"). Если не заданы - будет вызываться сервис `set_value`.
* `range`: Граничные значения диапазона. Для `humidity`, `open`, `brightness` есть ограничение: минимум `0`, максимум `100`.
  Если не задать `min` и `max` регулировка будет только относительная (в переменной `value` - `1` или `-1`).

    !!! example "Пример"
        ```yaml  
        range:
          # диапазон от -100 до 100
          min: -100
          max: 100
          # шаг изменения при нажатии на плюс или минус в интерфейсе, необязательное, по умолчанию - 1
          precision: 2
        ```

Для устройств, поддерживающих установку абсолютного значения, достаточно задать только `set_value`.
А для устройств с поддержкой только относительного (например IR пульт) - `increase_value` и `decrease_value`.

Если ни один сервис не задан - умение из УДЯ управляться не будет.

### Примеры { id=custom-ranges-examples }
#### Бризер { id=custom-ranges-example-breezer }
Изменение параметра `favorit_speed` на бризере Xiaomi (`fan.xiaomi_airfresh_a1`)

!!! summary "Атрибуты fan.xiaomi_airfresh_a1"
    ```yaml
    model: dmaker.airfresh.a1
    favorite_speed: 80
    ```

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        fan.xiaomi_airfresh_a1:
          custom_ranges:
            volume:  # как самое подходящее
              state_entity_id: fan.xiaomi_airfresh_a1 
              state_attribute: favorit_speed
              set_value:
                service: xiaomi_miio_airpurifier.fan_set_favorite_speed
                data:
                  speed: '{{ value }}'
              # значения для примера
              range:
                min: 60
                max: 300
                precision: 20 # по вкусу
    ```

#### Выбор канала { id=custom-ranges-example-tv-channel }
Выбор канала на телевизоре через `media_player.play_media`, листание каналов через отдельные скрипты, номер текущего канала нигде не хранится.

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        media_player.stupid_tv:
          custom_ranges:
            channel:
              set_value:
                service: media_player.play_media
                entity_id: media_player.stupid_tv
                data:
                  media_content_type: channel
                  media_content_id: '{{ value }}'
              increase_value:
                # сервис отправит нажатие кнопки "канал вверх" по IR
                service: script.next_channel_via_ir
              decrease_value:
                # сервис отправит нажатие кнопки "канал вниз" по IR
                service: script.prev_channel_via_ir
              range:
                min: 0
                max: 999
    ```
