
# Датчики
В УДЯ кроме устройств можно отдавать значения некоторых цифровых датчиков, таких как "температура", "заряд батареи" и других.

**Бинарные датчики (двери, утечка) и события (вибрация, нажатие кнопки) доступны только участникам бета-теста УДЯ ([подробнее](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event.html)). Если вы один из них, то для включения поддержки бинарных датчиков требуется задать `beta: true` в секции `settings` настроек интеграции.**

Отдать показания датчика можно несколькими способами:
1. Если датчик представлен атрибутом устройства (например атрибут `water_level` у увлажнителя `humidifer.sample`) -
   достаточно отдать в УДЯ через фильтр только `humidifer.sample`, уровень воды подхватится автоматически в большинстве случаев.

   Либо такой датчик можно сконфигурировать вручную через значения `type` и `attribute` (см. пример конфигурации ниже).

2. Датчик представлен отдельным устройством, значение в state (например `sensor.room_temp` с `device_class: temperature`) -
   достаточно отдать такое устройство через фильтр. Будет работать только в случае если у датчика поддерживаемый `device_class`.

3. Датчик представлен отдельным устройством, но его требуется представить как датчик другого устройства.
   Пример: уровень батареи `sensor.room_temp_battery` включить в датчик с температуры `sensor.room_temp`, или
   влажность в комнате `sensor.bedroom_humidity` включить в увлажнитель `humidifier.bedroom`.

   В этом случае дополнительные датчики и их типы (поле `type`) задаются как элементы списка `properties` основного устройства:
  ```yaml
  yandex_smart_home:
    filter:  # можно через GUI
      include_entities:
        - humidifier.bedroom
        - sensor.kitchen_meteo_temperature
    entity_config:
      humidifier.bedroom:
        properties:
          - type: temperature
            entity: sensor.bedroom_temperature
          - type: humidity
            entity: sensor.bedroom_humidity
          - type: tvoc
            attribute: total_volatile_organic_compounds
            unit_of_measurement: ppb  # для автоматической конвертации из миллиардных долей в мкг/м³
          - type: water_level
            entity: sensor.humidifier_level
          - type: battery_level  # если хочется переместить датчик "из атрибута" в конец списка
            attribute: battery_level
      sensor.kitchen_meteo_temperature:
        name: Погода на кухне
        properties:
          # температуру отдельно можно не прописывать, она подхватится сама
          - type: temperature
            entity: sensor.kitchen_meteo_temperature
          - type: humidity
            entity: sensor.kitchen_meteo_humidity
          - type: battery_level
            entity: sensor.kitchen_meteo_battery
  ```
  Возможные значения `type`:
  * [Для цифровых датчиков](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html)
  * [Для бинарных датчиков и событий](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html)
