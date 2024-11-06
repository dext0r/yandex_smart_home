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

Компонент автоматически пытается сопоставить значения датчика в Home Assistant со значением в УДЯ. Для каждого типа датчика поддерживается ограниченный набор событий.

Если в HA происходит событие (например, нажатие на кнопку), но в УДЯ оно не появляется - начните отладку на странице интеграции Yandex Smart Home, сгенерируйте событие и поищите в журнале событий по `Unknown event`.

| Тип           | Поддерживаемые значения: HA - УДЯ                                                                                                            |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| battery_level | `on`, `low`- Низкий<br>`off`, `normal` - Нормальный                                                                                          |
| button        | `click`, `single` - Одиночное нажатие<br>`double_click`, `double`, `many` - Двойное нажатие<br>`long_press`, `long`, `hold` - Долгое нажатие |
| food_level    | `empty` - Пустой<br>`low`- Низкий<br>`normal` - Нормальный                                                                                   |
| gas           | `on`, `detected` - Обнаружено<br>`off`, `not_detected` - Не обнаружено<br>`high` - Высокий уровень                                           |
| motion        | `on`, `detected` - Обнаружено<br>`off`, `not_detected` - Не обнаружено                                                                       |
| open          | `on`, `opened` - Открыто<br >`off`, `closed` - Закрыто                                                                                       |
| smoke         | `on`, `detected` - Обнаружено<br>`off`, `not_detected` - Не обнаружено<br>`high` - Высокий уровень                                           |
| vibration     | `tilt`, `rotate` - Переворачивание<br>`fall`, `drop` - Падение<br>`on`, `vibration` - Вибрация                                               |
| water_leak    | `on`, `leak` - Протечка<br>`off`, `dry` - Нет протечки                                                                                       |
| water_level   | `empty` - Пустой<br>`on`, `low`- Низкий<br>`off`, `normal` - Нормальный                                                                      |

!!! note ""

    * `on`: Любая логическая истина: `on`, `true`, `yes`, `1`
    * `off`: Любая логическая ложь: `off`, `false`, `no`, `0`

    Перечислена только часть поддерживаемых значений со стороны Home Assistant.

## Выбор класса бинарного датчика { id=device-class }

Некоторые интеграции создают бинарные датчики с пустым или неверным атрибутом `device_class`. Такие датчики автоматически обнаружены не будут, но по-прежнему могут
быть добавлены [вручную](#properties).

Вы можете самостоятельно задать атрибут `device_class` через параметр объекта `Отображать как` в `Настройки` --> `Устройства и объекты` --> [`Объекты`](https://my.home-assistant.io/redirect/entities/)

![](../../assets/images/devices/sensor/binary-device-class.png){ width=750 }
