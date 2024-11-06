В УДЯ можно передавать цифровые и событийные датчики (открытие двери, нажатие кнопки и т.п.). Есть несколько способов сделать это:

## Один датчик - одно устройство { id=simple }

При выборе [поддерживаемых](../../supported-devices.md#float-sensor) объектов в доменах `sensor` и `binary_sensor` в УДЯ будут созданы несколько независимых устройств:

![](../../assets/images/devices/sensor/simple-1.png){ width=480 }
![](../../assets/images/devices/sensor/simple-3.png){ width=200 }
![](../../assets/images/devices/sensor/simple-2.png){ width=480 }

## Сборка нескольких датчиков в одном устройство { id=combine }

В [первом способе](#simple) одно физическое устройство (датчик температуры/влажности) передавалось в УДЯ как несколько независимых устройств, и это в большинстве случаев неудобно.

Есть способ лучше! Компонент позволяет объединить несколько независимых объектов в одно устройство через [YAML конфигурацию](../../config/getting-started.md#yaml).

В качестве примера возьмём этот же датчик температуры/влажности:

![](../../assets/images/devices/sensor/simple-1.png){ width=750 }

Он содержит несколько объектов, нам нужно [выяснить](../../faq.md#get-entity-id) их `entity_id`. В нашем примере это будут:

* Температура: `sensor.room_temperature`
* Влажность: `sensor.room_humidity`
* Уровень заряда: `sensor.room_meteo_battery_level`

Так же для примера добавим ещё несколько датчиков из других физических устройств:

* Уровень CO2: `sensor.room_co2_level`
* Освещённость: `sensor.room_illumination_lux`

В Home Assistant нет объекта, на который мы могли бы добавить эти сенсоры.
Поэтому в качестве объекта, из которого будут создано устройство в УДЯ, нужно выбрать **любой** существующий объект, возьмём для этих целей температуру (`sensor.room_temperature`).

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        sensor.room_temperature:
          name: Погода в комнате
          properties:
            - type: temperature
              entity: sensor.room_temperature
            - type: humidity
              entity: sensor.room_humidity
            - type: co2_level
              entity: sensor.room_co2_level
            - type: illumination
              entity: sensor.room_illumination_lux
            - type: battery_level
              entity: sensor.room_meteo_battery_level
    ```

Датчики, заданные в `properties`, обладают большим приоритетом над обнаруженными автоматически.
По этой причине мы вручную добавили датчик `temperature` вверх списка. Если этого не сделать - он будет в конце (как автоматически обнаруженный для `sensor.room_temperature`).

!!! tip "Порядок датчиков в `properties` влияет на порядок отображения в УДЯ"

!!! attention "В одном устройстве недопустимо использовать несколько датчиков с одним `type`"

!!! attention "Значение `type` не всегда совпадает с `device_class` объекта. Возможные значения `type`: [цифровые датчики](float.md#property-type), [событийные датчики](event.md#property-type)"

В [объектах для передачи в УДЯ](../../config/filter.md) нужно выбрать **только** `sensor.room_temperature`.

![](../../assets/images/devices/sensor/combine-1.png){ width=480 }
![](../../assets/images/devices/sensor/combine-2.png){ width=200 }

## Добавление датчиков к устройству { id=attach }

Некоторые устройства (термостат) уже содержат в своих атрибутах датчики, которые будет подхвачены автоматически.
А некоторые, например, увлажнитель - наоборот, все датчики выносят в отдельные объекты.

В качестве примера используем увлажнитель Xiaomi, он состоит из объектов:

* Непосредственно увлажнитель: `humidifier.air_humidifier`
* Температура: `sensor.air_humidifier_temperature`
* Влажность: `sensor.air_humidifier_humidity`
* Уровень воды: `sensor.air_humidifier_water_level`

И дополнительно добавим к нему:

* Потребляемый ток: `switch.humidifier_socket`, значение в атрибуте `current_consumption`

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        humidifier.air_humidifier:
          properties:
            - type: water_level
              entity: sensor.air_humidifier_water_level
            - type: temperature
              entity: sensor.air_humidifier_temperature
            - type: humidity
              entity: sensor.air_humidifier_humidity
            - type: power
              entity: switch.humidifier_socket
              attribute: current_consumption
    ```

!!! tip "Порядок датчиков в `properties` влияет на порядок отображения в УДЯ"

!!! attention "В одном устройстве недопустимо использовать несколько датчиков с одним `type`"

!!! attention "Значение `type` не всегда совпадает с `device_class` объекта. Возможные значения `type`: [цифровые датчики](float.md#property-type), [событийные датчики](event.md#property-type)"

В объектах для передачи в УДЯ нужно выбрать **только** `humidifier.air_humidifier`.

![](../../assets/images/devices/sensor/attach-1.png){ width=480 }
![](../../assets/images/devices/sensor/attach-2.png){ width=200 }
