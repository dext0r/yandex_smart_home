Событийные датчики используются для отображения свойств устройства в УДЯ. Например: открытие двери (закрыта/открыта) или уровень воды (пустой/низкий/нормальный).

Для [автоматически обнаруженных](../../supported-devices.md#event-sensor) датчиков из `binary_sensor` будут использоваться только два значения,
например для "Наличие газа": `on` - обнаружено, `off` - не обнаружено, а "Высокий уровень" (`high`) никак задействован не будет.

Для задействования всех возможных событий используйте `sensor` на [шаблоне](https://www.home-assistant.io/integrations/template/#state-based-template-binary-sensors-buttons-images-numbers-selects-and-sensors) или параметр [`value_template`](#property-value-template).

## Ручное добавление { id=properties }

Событийные датчики могут быть добавлены к любому устройству вручную через список `properties` в `entity_config`.
Каждый датчик содержит один или несколько параметров.

Устройство может иметь одновременно событийные и [цифровые датчики](float.md).

!!! example "Пример настройки датчиков"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.room:
          properties:
            - type: float.water_level
              entity: sensor.room_humidifier_water_level
            - type: open
              value_template: '{{ is_state("binary_sensor.room_humidifier_water_tank", "off" }}'
        media_player.tv:
          properties:
            - type: motion
              entity: binary_sensor.motion_near_tv
    ```

### Тип датчика { id=property-type }

> Параметр: `type` (обязательный)

Может быть задан в сокращённом или полном виде (`event.X`). Полный вид желательно использовать для датчиков, которые могут быть как числовыми, так и событийными (`battery_level`, `food_level`, `water_level`).

| Тип (сокр.)   | Тип (полный)        | Описание                                                            |
| ------------- | ------------------- | ------------------------------------------------------------------- |
| battery_level | event.battery_level | События заряда батареи                                              |
| button        | event.button        | События нажатия кнопки                                              |
| food_level    | event.food_level    | События, связанные с уровнем корма                                  |
| gas           | event.gas           | События наличия газа в помещении                                    |
| motion        | event.motion        | События, связанные с наличием движения в области действия датчика   |
| open          | event.open          | События открытия/закрытия дверей, окон и т. п.                      |
| smoke         | event.smoke         | События наличия дыма в помещении                                    |
| vibration     | event.vibration     | События физического воздействия: вибрация, падение, переворачивание |
| water_leak    | event.water_leak    | События протечки воды                                               |
| water_level   | event.water_level   | События, связанные с уровнем воды                                   |

### Источник состояния (объект) { id=property-value-state }

> Параметры: `entity` и/или `attribute`

Задают объект и/или его атрибут, в котором находится текущее состояние датчика. Нельзя использовать совместно с [`value_template`](#property-value-template).

!!! info "Описание"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.room:
          properties:
            # Задан только атрибут, значение датчика будет взято из атрибута объекта, для которого задаются датчики
            # В данном случае - атрибут humidifier.fault объекта humidifier.room
            - type: event.water_leak
              attribute: humidifier.fault

            # Значение датчика будет взято из состояния объекта sensor.humidifier_room_water_tank
            - type: event.open
              entity: sensor.humidifier_room_water_tank

            # Значение датчика будет взято из атрибута action объекта sensor.button
            - type: event.button
              entity: sensor.button
              attribute: action
    ```

### Источник состояния (шаблон) { id=property-value-template }

> Параметр: `value_template`

Задаёт шаблон для вычисления текущего состояние датчика. Нельзя использовать совместно с [`entity` и/или `attribute`](#property-value-state).

!!! info "Описание"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.room:
          properties:
            - type: event.water_level
              value_template: |
                {% set water_level = states("sensor.humidifier_room_water_level")|int(0) %}
                {% if water_level > 60 %}
                  normal
                {% elif water_level > 20 %}
                  empty
                {% else %}
                  low
                {% endif %}
    ```

## Типы событий { id=event-types }

Компонент автоматически пытается сопоставить значения датчика в Home Assistant с событием в УДЯ.
Для каждого типа датчика поддерживается ограниченный [набор событий](https://yandex.ru/dev/dialogs/smart-home/doc/ru/concepts/event-instance).

| Тип           | События                                                                                           | Поддерживаемые значения в HA                                                          |
| ------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| battery_level | `low` — Низкий<br>`normal` — Нормальный                                                           | `on`, `low`<br>`off`, `normal`                                                        |
| button        | `single` — Одиночное нажатие<br>`double_click` — Двойное нажатие<br>`long_press` — Долгое нажатие | `click`, `single`<br>`double_click`, `double`, `many`<br>`long_press`, `long`, `hold` |
| food_level    | `empty` — Пустой<br>`low`— Низкий<br>`normal` — Нормальный                                        | `empty` <br>`low`<br>`normal`                                                         |
| gas           | `detected` — Обнаружено<br>`not_detected` — Не обнаружено<br>`high` — Высокий уровень             | `on`, `detected`<br>`off`, `not_detected`<br>`high`                                   |
| motion        | `detected` — Обнаружено<br>`not_detected` — Не обнаружено                                         | `on`, `detected`<br>`off`, `not_detected`                                             |
| open          | `opened` — Открыто<br >`off`, `closed` — Закрыто                                                  | `on`, `opened`<br >`off`, `closed`                                                    |
| smoke         | `detected` — Обнаружено<br>`not_detected` — Не обнаружено<br>`high` — Высокий уровень             | `on`, `detected`<br>`off`, `not_detected`<br>`high`                                   |
| vibration     | `tilt` — Переворачивание<br>`fall` — Падение<br>`vibration` — Вибрация                            | `tilt`, `rotate`<br>`fall`, `drop`<br>`on`, `vibration`                               |
| water_leak    | `leak` — Протечка<br>`dry` — Нет протечки                                                         | `on`, `leak`<br>`off`, `dry`                                                          |
| water_level   | `empty` — Пустой<br>`low` — Низкий<br>`normal` — Нормальный                                       | `empty`<br>`on`, `low`<br>`off`, `normal`                                             |

!!! note ""

    * `on`: Любая логическая истина: `on`, `true`, `yes`, `1`
    * `off`: Любая логическая ложь: `off`, `false`, `no`, `0`

    Перечислена только часть поддерживаемых значений со стороны Home Assistant.

Сопоставление значений можно так же можно настроить вручную через раздел `entity_config` в [YAML конфигурации](../../config/getting-started.md#yaml).
При ручной настройке отключается автоматическое сопоставление для этого устройства и типа события.

!!! example "Пример сопоставления событий"
    ```yaml
    yandex_smart_home:
      entity_config:
        sensor.button:
          events:
            button:
              single: click_1
              double_click: click_double_1
    ```

    * `button` - тип события со стороны УДЯ
    * `single`, `double_click` - событие со стороны УДЯ
    * `click_1`, `click_double_1` - значения датчика со стороны Home Assistant

Если в HA происходит событие (например, нажатие на кнопку), но в УДЯ оно не появляется — начните отладку на странице интеграции Yandex Smart Home,
сгенерируйте событие и поищите в журнале событий по `Unknown event`. После этого задайте соответствия вручную.

## Выбор класса бинарного датчика { id=device-class }

Некоторые интеграции создают бинарные датчики с пустым или неверным атрибутом `device_class`. Такие датчики автоматически обнаружены не будут, но по-прежнему могут
быть добавлены [вручную](#properties).

Вы можете самостоятельно задать атрибут `device_class` через параметр объекта `Отображать как` в `Настройки` --> `Устройства и объекты` --> [`Объекты`](https://my.home-assistant.io/redirect/entities/)

![](../../assets/images/devices/sensor/binary-device-class.png){ width=750 }
