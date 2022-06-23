!!! danger "Только для продвинутых пользователей!"

Иногда возможностей компонента недостаточно и хочется добавить свои функции, переключатели и регулировки.
Это можно сделать через "пользовательские умения" для каждого устройства отдельно через `entity_config`.

!!! important "**Важно!** Пользовательские умения являются приоритетными и перекрывают автоматически обнаруженные"

Поддерживается несколько видов пользовательских умений:

* Режимы (`mode`) - переключение режимов работы устройства (режим работы кондиционера, уборки, источника сигнала и т.п.).
  Настраиваются через словарь `custom_modes`.
* Переключатели (`toggle`) - управление функциями, которые включаются и выключаются (пауза, вращение вентилятора, ионизация и т.п.).
  Настраиваются через словарь `custom_toggles`.
* Выбор из диапазона (`range`) - управление параметрами устройства, которые имеют диапазон (яркость лампы, громкость звука, температура нагревателя).
  Настраиваются через словарь `custom_ranges`.

В каждое умение входит ряд функций (например функция `volume` в умении `range`). 
Для одного устройства может быть **несколько** функций в разных умениях (или в одном). 
Дубликаты функций невозможны (т.е. `volume` может быть только одна для одного устройства).

Функции никак не привязаны к типу устройства, а это значит, что функция "громкость" может быть, например, у выключателя или увлажнителя. 
Это позволяет реализовывать **[безумный набор умений](../assets/images/crazy-caps.png)** в одном устройстве.

Для всех умений есть общие и специфичные параметрами. Специфичные параметры смотрите в разделе посвящённому конкретному умению.

## Общие параметры { id=parameters }
* `state_entity_id`: Объект в состоянии или атрибуте которого хранится текущее значение умения (громкость, яркость, режим и т.п.).
  По умолчанию тот, для которого настраивается пользовательское умение.
* `state_attribute`: Атрибут, в котором хранится текущее значение умения. Если не задан - значение берётся из состояния объекта.

Допускается одновременное использование `state_entity_id` и `state_attribute`. Если ни один из этих параметров не задан - текущее значение функции передаваться не будет.

## Умения "Режимы работы" (custom_modes) { id=custom-modes }
Выбирает режим работы устройства, при изменении которого будут выполняться произвольные сервисы. Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html)**.

Примеры: кофеварка, которая варит кофе скриптом `script.makemeonecupofcoffee` или моющий пылесос Xiaomi, в котором хочется управлять количеством подаваемой воды через сервис `xiaomi_vacuum.set_water_level`.

Для пользовательского режима автоматического связывание между значениями УДЯ и Home Assistant не производится. Вам нужно
вручную [задать соответствия](../config/modes.md) через `modes`!

Специфичные параметры:

* `set_mode`: Вызываемый сервис при выборе режима в УДЯ. В переменной `mode` - значение режима на стороне Home Assistant
    
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
!!! summary "Атрибуты"
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
          type: devices.types.cooking.coffee_maker
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
Управление функциями устройств, которые включаются и выключаются. Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html)**.

Специфичные параметры:

* `turn_on` и `turn_off`: Вызываемые сервисы при включении/выключении функции в УДЯ
    
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

!!! summary "Атрибуты"
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
              state_attribute: ptc
              turn_on:
                service: xiaomi_miio_airpurifier.fan_set_ptc_on
                entity_id: fan.xiaomi_airfresh_va4
              turn_off:
                service: xiaomi_miio_airpurifier.fan_set_ptc_off
                entity_id: fan.xiaomi_airfresh_va4
    ```

## Умения "Выбор значения из диапазона" (custom_ranges) { id=custom-ranges }
Управление параметрами устройства, которые имеют диапазон регулировки (громкость, яркость, температура). Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html)**.

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

### Примеры { id=custom-ranges-examples }
#### Бризер { id=custom-ranges-example-breezer }
Изменение параметра `favorit_speed` на бризере Xiaomi (`fan.xiaomi_airfresh_a1`)

!!! summary "Атрибуты"
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
