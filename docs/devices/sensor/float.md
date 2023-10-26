## Ручное добавление { id=properties }
Цифровые датчики могут быть добавлены к любому устройству вручную через список `properties` в `entity_config`. Каждый датчик содержит один или несколько параметров.

Устройство может иметь одновременно цифровые и [событийные датчики](event.md).

!!! example "Пример настройки датчиков"
    ```yaml
    yandex_smart_home:
      entity_config:
        sensor.bedroom_temperature:
          properties:
            - type: temperature
              entity: sensor.bedroom_temperature
            - type: humidity
              entity: sensor.bedroom_humidity
            - type: co2_level
              entity: sensor.bedroom_co2
            - type: event.motion
              entity: binary_sensor.bedroom_motion
        sensor.pet_feeder:
          type: pet_feeder
          properties:
            - type: float.food_level
              attribute: pet_feeder.pet_food_left_level
    ```

### Тип датчика { id=property-type }
> Параметр: `type` (обязательный)

Может быть задан в сокращённом или полном виде (`float.X`). Полный вид желательно использовать для датчиков, которые могут быть как числовыми, так и событийными (`battery_level`, `food_level`, `water_level`).

| Тип (сокращённый) | Тип (полный)        | Описание                                             |
|-------------------|---------------------|------------------------------------------------------|
| amperage          | float.amperage      | Текущее потребление тока                             |
| battery_level     | float.battery_level | Уровень заряда аккумулятора (в процентах)            |
| co2_level         | float.co2_level     | Уровень углекислого газа                             |
| food_level        | float.food_level    | Уровень корма (в процентах)                          |
| humidity          | float.humidity      | Влажность                                            |
| illumination      | float.illumination  | Уровень освещенности                                 |
| pm1_density       | float.pm1_density   | Уровень загрязнения воздуха частицами PM1            |
| pm2.5_density     | float.pm2.5_density | Уровень загрязнения воздуха частицами PM2.5          |
| pm10_density      | float.pm10_density  | Уровень загрязнения воздуха частицами PM10           |
| power             | float.power         | Текущая потребляемая мощность                        |
| pressure          | float.pressure      | Давление                                             |
| temperature       | float.temperature   | Температура                                          |
| tvoc              | float.tvoc          | Уровень загрязнения воздуха органическими веществами |
| voltage           | float.voltage       | Текущее напряжение                                   |
| water_level       | float.water_level   | Уровень воды (в процентах)                           |


### Источник состояния (объект) { id=property-value-state }
> Параметры: `entity` и/или `attribute`

Задают объект и/или его атрибут, в котором находится текущее состояние датчика. Нельзя использовать совместо с [`value_template`](#property-value-template).

!!! info "Описание"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.room:
          properties:
            # Задан только атрибут, значение датчика будет взято из атрибута объекта, для которого задаются датчики
            # В даннном случае - атрибут current_temperature объекта humidifer.room
            - type: temperature
              attribute: current_temperature

            # Значение датчика будет взято из состояния объекта sensor.humidifier_room_water_level
            - type: float.water_level
              entity: sensor.humidier_room_water_level

            # Значение датчика будет взято из атрибута current_power объекта switch.humidifier_socket
            - type: power
              entity: switch.humidifer_socket
              attribute: current_power
    ```

### Источник состояния (шаблон) { id=property-value-template }
> Параметр: `value_template`

Задаёт шаблон для вычисления текущего состояние датчика. Нельзя использовать совместно с [`entity` и/или `attribute`](#property-value-state).

Используйте в случаях, когда в УДЯ требуется получиться значение отличное от значения в HA, и для этого не хочется создавать дополнительный [датчик на шаблоне](https://www.home-assistant.io/integrations/template).

!!! warning "Не рекомендуется использовать для конвертации из одних единиц измерения в другие [подробнее](#unit-conversion)"

!!! info "Пример"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.room:
          properties:
            - type: temperature 
              value_template: '{{ states("sensor.room_temperature") + 5 }}'
    ```

### Единицы измерения в HA { id=property-unit-of-measurement }
> Параметр: `unit_of_measurement`

Задаёт единицы измерения, в котором находится значение датчика в Home Assistant. Следует задавать, **только** если автоматическая [конвертация значений](#unit-conversion) работает неверно. В большинстве случаев использовать этот параметр не требуется.

Альтернативные способы задать единицы измерения:

1. Параметр `device_class` при создании датчика на [шаблоне](https://www.home-assistant.io/integrations/template/#sensor) 
2. Настройки объекта на странице `Настройки` --> `Устройства и службы` --> [`Объекты`](https://my.home-assistant.io/redirect/entities/)

!!! example "Пример"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.room:
          properties:
            - type: temperature
              attribute: current_temperature
              unit_of_measurement: °F
    ```

Возможные значения `unit_of_measurement` (регистр важен):

| Тип         | `unit_of_measurement`                                                   |
|-------------|-------------------------------------------------------------------------|
| amperage    | `A`, `mA`                                                               |
| power       | `W`, `kW`                                                               |
| pressure    | `atm`, `Pa`, `hPa`, `kPa`, `bar`, `cbar`, `mbar`, `mmHg`, `inHg`, `psi` |
| temperature | `°C`, `°F`, `K`                                                         |
| tvoc        | `µg/m³`, `mg/m³`, `μg/ft³`, `p/m³`, `ppm`, `ppb`                        |
| voltage     | `V`, `mV`                                                               |


### Единицы измерения в УДЯ { id=property-target-unit-of-measurement }
> Параметр: `target_unit_of_measurement`

Задаёт единицы измерения, в которых значение датчика должно быть представлено в УДЯ. Поддерживается только для температуры и давления.

Следует использовать в тех **редких** случаях, когда вам хочется, чтобы единицы измерения не совпадали между HA и УДЯ. Например: в HA давление в паскалях, а в УДЯ нужно в мм. рт. ст.

!!! info "Пример"
    ```yaml
    yandex_smart_home:
      entity_config:
        sensor.temperature:
          properties:
            - type: temperature
              entity: sensor.temperature
              target_unit_of_measurement: °С  # поддерживаются: °С и K
            - type: pressure
              entity_sensor.pressure
              target_unit_of_measurement: mmHg # поддерживаются: mmHg, Pa, atm, bar
    ```

## Конвертация значений { id=unit-conversion }
Единицы измерения значения датчика в УДЯ фиксированы и не могут быть произвольными:

| Тип                                          | Единицы измерения                              |
|----------------------------------------------|------------------------------------------------|
| amperage                                     | Всегда амперы                                  |
| battery_level                                | Всегда проценты                                |
| co2_level                                    | Всегда миллионые доли (ppm)                    |
| food_level                                   | Всегда проценты                                |
| humidity                                     | Всегда проценты                                |
| illumination                                 | Всегда люксы                                   |
| pm1_density<br>pm2.5_density<br>pm10_density | Всегда мкг/м³                                  |
| power                                        | Всегда ватты                                   |
| pressure                                     | На выбор: атмосферы, паскали, бары, мм рт. ст. |
| temperature                                  | На выбор: градусы по цельсию, кельвины         |
| tvoc                                         | Всегда мкг/м³                                  |
| voltage                                      | Всегда вольты                                  |
| water_level                                  | Всегда проценты                                |

Компонент автоматически выполняет конвертацию значений из единиц измерения в HA в единицы измерения в УДЯ. 

Если в HA используется значение в единцах, поддерживаемых УДЯ - конвертация выполнена не будет (например если в HA давление в барах, то и в УДЯ оно будет передано в барах).

### Изменение единиц измерения { id=select-unit-of-measurement }
В некоторых случаях компонент не может сам определить, в каких единицах измерения находится значение датчика. В этом случае значение может быть сконвертировано неверно.

Несколько способов исправить эту ситуацию:

1. Задать верные единицы измерения через `device_class` при создании [датчика на шаблоне](https://www.home-assistant.io/integrations/template/#configuration-variables)
2. Задать верные единицы измерения в настройках объекта на странице `Настройки` --> `Устройства и службы` --> [`Объекты`](https://my.home-assistant.io/redirect/entities/) 
3. Использовать параметр [`unit_of_measurement`](#property-unit-of-measurement) при ручной настройке датчика
