# Режимы и пользовательские умения

- [Настройка режимов/функций](#настройка-режимовфункций)
  - [thermostat](#thermostat)
  - [swing](#swing)
  - [program](#program)
  - [fan_speed](#fan_speed)
  - [fan_speed (скорость в процентах)](#fan_speed-скорость-в-процентах)
  - [cleanup_mode](#cleanup_mode)
  - [input_source](#input_source)
  - [scene](#scene)
- [Пользовательские умения](#пользовательские-умения)
  - [Умения "Режимы работы" (custom_modes)](#умения-режимы-работы-custom_modes)
    - [Примеры](#примеры)
  - [Умения "Переключатели" (custom_toggles)](#умения-переключатели-custom_toggles)
    - [Примеры](#примеры-1)
  - [Умения "Выбор значения из диапазона" (custom_ranges)](#умения-выбор-значения-из-диапазона-custom_ranges)
    - [Примеры](#примеры-2)

## Настройка режимов/функций
Для некоторых устройств в УДЯ предусмотрено управление режимами. Типичные примеры - охлаждение/нагрев/осушение для кондиционера,
или низкая/средняя скорость вращения для вентилятора.

[Список режимов](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html) в УДЯ фиксированный,
поэтому их необходимо связывать со значениями атрибутов в Home Assistant. Для большинства устройств этот процесс (маппинг)
происходит **автоматически**, но в некоторых случаях это требуется сделать вручную через параметр `modes` в `entity_config`.

Со стороны УДЯ нет жесткой привязки значений режимов к типам устройств. Другими словами, у режима "Скорость вентиляции"
(`fan_speed`) значения могут быть не только "низкое", "высокое", но и совсем от другого типа устройств, например "дичь" или "эспрессо".

Если маппинг не удался - управление функцией через УДЯ будет недоступно.

Пример конфигурации:
```yaml
yandex_smart_home:
  entity_config:
    light.led_strip:
      modes:
        scene:
          sunrise:
            - Wake up
          alarm:
            - Blink
    climate.some_ac:
      modes:
        fan_speed:
          auto: [auto]
          min: ['1','1.0']
          turbo: ['5','5.0']
          max: ['6','6.0']
        swing:
          auto: ['SWING']
          stationary: ['OFF']
```

* `scene`, `fan_speed`, `swing` - режим/функция со стороны УДЯ
* `auto`, `stationary`, `alarm` - значение режима со стороны УДЯ ([все возможные значения](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html))
* Списки значений (`Wake Up`, `Swing` и т.п.) - значения атрибута сущности в Home Assistant, которое соответствует значению режима в УДЯ.
  Задавать лучше строками в кавычках.

Ниже детальная информация по поддерживаемым режимам и их значениям.


### thermostat
Установка температурного режима работы климатической техники, например, в кондиционере.

* Поддерживаемые домены: `climate`
* Рекомендуемые значения режимов: `heat`, `cool`, `auto`, `dry`, `fan_only`
* Атрибут в Home Assistant: `hvac_modes`

### swing
Установка направления воздуха в климатической технике.

* Поддерживаемые домены: `climate`
* Рекомендуемые значение режимов: `vertical`, `horizontal`, `stationary`, `auto`
* Атрибут в Home Assistant: `swing_modes`

### program
Установка какой-либо программы работы.

* Поддерживаемые домены: `humidifier`, `fan`
* Рекомендуемые значения режимов: `normal`, `eco`, `min`, `turbo`, `medium`, `max`, `quiet`, `auto`, `high`
* Атрибут в Home Assistant:
  * `humidifier`: `available_modes`
  * `fan`: `preset_modes` (если поддерживается установка скорости в процентах)

### fan_speed
Установка режима работы скорости вентиляции, например, в кондиционере, вентиляторе или обогревателе.

* Поддерживаемые домены: `fan`, `climate`
* Рекомендуемые значения режимов: `auto`, `quiet`, `low`, `medium`, `high`, `turbo`
* Атрибут в Home Assistant:
  * `fan`: `preset_modes` (если не поддерживается установка скорости в процентах, сервис `fan.set_speed_percentage`)
  * `fan`: `speed_list` (сли не поддерживается установка скорости в процентах и режимы, устарело)
  * `climate`: `fan_modes`

### fan_speed (скорость в процентах)
Некоторые вентиляторы позволяют устанавливать скорость вентиляции в процентах, используя сервис `fan.set_speed_percentage`. Для таких вентиляторов компонент автоматически соотнесёт режим в УДЯ и скорость в процентах для режима "Скорость вентиляции".

Автоматическое соотношение можно переопределить путём указания числа с процентами в качестве режима со стороны HA в конфигурации устройства. Пример:
```yaml
yandex_smart_home:
  entity_config:
    fan.xiaomi:
      modes:
        fan_speed:
          low: ['10%']  # округляйте до целого
          normal: ['50%']
```

Рекомендуемые значения режимов: `eco`, `quiet`, `low`, `medium`, `normal`, `high`, `turbo`

### cleanup_mode
Установка режима уборки.

* Поддерживаемые домены: `vacuum`
* Рекомендуемые значения режимов: `auto`, `turbo`, `min`, `max`, `express`, `normal`, `quiet`
* Атрибут в Home Assistant: `fan_speed_list`

### input_source
Установка источника сигнала.

* Поддерживаемые домены: `media_player`
* Рекомендуемые значения режимов: `one`, `two`, `three`, `four`, `five`, `six`, `seven`, `eight`, `nine`, `ten`
* Атрибут в Home Assistant: `source_list`

### scene
Изменение режима работы светящихся элементов устройства в соответствии с предустановленными темами и сценариями освещения.

* Поддерживаемые домены: `light`
* Значения режимов: `alarm`, `alice`, `candle`, `dinner`, `fantasy`, `garland`, `jungle`, `movie`, `neon`, `night`, `ocean`, `party`, `reading`, `rest`, `romance`, `siren`, `sunrise`, `sunset` (список фиксированный, другими значениями не расширяется)
* Атрибут в Home Assistant: `effect_list`


## Пользовательские умения
Иногда возможностей компонента недостаточно и хочется добавить свои функции, переключатели и регулировки.
Это можно сделать через "пользовательские умения" для каждого устройства отдельно через `entity_config`.

**Важно!** Пользовательские умения являются приоритетными и перекрывают встроенные в компонент.

Поддерживается несколько вида пользовательских умений:
* Режимы (`mode`) - переключение режимов работы устройства (режим работы кондиционера, уборки, источника сигнала и т.п.).
  Настраиваются через словарь `custom_modes`.
* Переключатели (`toggle`) - управление функциями, которые включаются и выключаются (пауза, вращение вентилятора, ионизация и т.п.).
  Настраиваются через словарь `custom_toggles`.
* Выбор из диапазона (`range`) - управление параметрами устройства, которые имеют диапазон (яркость лампы, громкость звука, температура нагревателя).
  Настраиваются через словарь `custom_ranges`.

В каждое умение входит ряд функций (например функция `volume` в умении `range`). Для одного устройства может быть **несколько** функций в разных умениях (или в одном). Дубликаты фукнций невозможны (т.е. `volume` может быть только одна для одного устройства).
Функции никак не привязаны к типу устройства, а это значит, что функция "громкость" может быть, например, у выключателя или увлажнителя. Это позволяет реализовывать **[безумный набор умений](https://github.com/dmitry-k/yandex_smart_home/blob/master/docs/images/quasar_crazy_caps.png)** в одном устройстве.

Для всех умений есть общие и специфичные параметрами. Специфичные параметры смотрите в разделе посвящённому конкретному умению.

Общие параметры:
* `state_entity_id`: Сущность в состоянии или атрибуте которой хранится текущее значение умения (громкость, яркость, режим и т.п.).
  По умолчанию та, для которой настраивается пользовательское умение.
* `state_attribute`: Атрибут, в котором хранится текущее значение умения. Если не задан - значение берётся из состояния.


### Умения "Режимы работы" (custom_modes)
Выбирает режим работы устройства, при изменении которого будут выполняться произвольные сервисы. Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html)**.

Примеры: коферка, которая варит кофе скриптом `script.makemeonecupofcoffee` или моющий ылесос Xiaomi, в котором хочется управлять количеством подаваемой воды через сервис `xiaomi_vacuum.set_water_level`.

Для пользовательского режима автоматического связывание между значениями УДЯ и Home Assistant не производится. Вам нужно
вручную задать соответствия через `modes`!

Специфичные параметры:
* `set_mode`: Вызываемый сервис при выборе режима в УДЯ. В переменной `mode` - значение режима на стороне Home Assistant. Пример:
  ```yaml
  set_mode:
    service: xiaomi_vacuum.set_water_level
    entity_id: vacuum.xiaomi_mop
    data:
      water_level: '{{ mode }}'
  ```

#### Примеры
1. Моющий пылесос Xiaomi (`vacuum.xiaomi_mop`).

    Атрибуты:
    ```yaml
    water_level: High
    water_level_list:
      - Low
      - Med
      - High
    ```

    Конфигурация компонента:
    ```yaml
    yandex_smart_home:
      entity_config:
        vacuum.xiaomi_mop:
          modes:
            work_speed:  # соответствие между режимами УДЯ и HA
              eco: [Low]
              medium: [Med]
              max: [High]
          custom_modes:
            work_speed:
              state_attribute: water_level
              set_mode:
                service: xiaomi_vacuum.set_water_level
                entity_id: vacuum.xiaomi_mop
                data:
                  water_level: '{{ mode }}' # сюда подставятся Low/Med/High
    ```

2. Кофеварка, которая умеет варить кофе скриптами (`climate.hotcoffee`)

    Конфигурация компонента:
    ```yaml
    yandex_smart_home:
      entity_config:
        climate.hotcoffee:
          type: devices.types.cooking.coffee_maker
          modes:
            coffee_mode:
              cappuccino: [cappuccino]
              latte: [latte]
          custom_modes:
            coffee_mode:
              set_mode:
                service: script.make_me_{{ mode }}_coffee  # вызовется script.make_me_latte_coffee
    ```


### Умения "Переключатели" (custom_toggles)
Управление функциями устройств, которые включаются и выключаются. Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html)**.

Специфичные параметры:
* `turn_on` и `turn_off`: Вызываемые сервисы при включении/выключении функции в УДЯ. Пример:
  ```yaml
  turn_on:
    service: xiaomi_miio_airpurifier.fan_set_ptc_on
    entity_id: fan.xiaomi_airfresh_va4
  turn_off:
    service: xiaomi_miio_airpurifier.fan_set_ptc_off
    entity_id: fan.xiaomi_airfresh_va4
  ```

#### Примеры
1. Управление функцией подогрева для бризера Xiaomi (`fan.xiaomi_airfresh_va4`)

    Атрибуты:
    ```yaml
    model: zhimi.airfresh.va4
    ptc: false  # а может быть true (on/off тоже подходит)
    ```

    Конфигурация компонента:
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


### Умения "Выбор значения из диапазона" (custom_ranges)
Управление параметрами устройства, которые имеют диапазон регулировки (громкость, яркость, температура). Смотрите список **[всех доступных функций](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html)**.

Специфичные параметры:
* `set_value`: Сервис вызываемый при любой регулировке функции. В переменной `value` абсолютное или относительное значение (в зависимости от настроек `range`). Пример:
  ```yaml
  set_value:
    service: xiaomi_miio_airpurifier.fan_set_favorite_speed
    entity_id: fan.xiaomi_airfresh_a1
    data:
      speed: '{{ value }}'
  ```
* `range`: Граничные значения диапазона. Для `humidity`, `open`, `brightness` есть ограничение: минимум `0`, максимум `100`.
  Если не задать `min` и `max` регулировка будет только относительная (в переменной `value` - `1` или `-1`). Пример:
  ```yaml
  range:
    # диапазон от -100 до 100
    min: -100
    max: 100
    # шаг изменения при нажатии на плюс или минус в интерфейсе, необязательное, по умолчанию - 1
    precision: 2
  ```

#### Примеры
1. Изменение параметра `favorit_speed` на бризере Xiaomi (`fan.xiaomi_airfresh_a1`)

    Атрибуты:
    ```yaml
    model: dmaker.airfresh.a1
    favorite_speed: 80
    ```

    Конфигурация компонента
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
