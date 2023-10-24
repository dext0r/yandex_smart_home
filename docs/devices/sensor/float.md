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

Задают объект и/или его атрибут, в котором находится текущее состояние датчика. 

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
