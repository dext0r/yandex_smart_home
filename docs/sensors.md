
# Датчики

- [Конвертация значений](#конвертация-значений)
- [Кнопки (предварительная реализация)](#кнопки-предварительная-реализация)

В УДЯ кроме устройств можно отдавать значения некоторых цифровых датчиков, таких как "температура", "заряд батареи" и других.

**Бинарные датчики (двери, утечка) и события (вибрация, нажатие кнопки) доступны только участникам бета-теста УДЯ ([подробнее](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event.html)). Если вы один из них, то для включения поддержки бинарных датчиков требуется задать `beta: true` в секции `settings` настроек интеграции.**

Отдать показания датчика можно несколькими способами:
1. Если датчик представлен атрибутом устройства (например атрибут `water_level` у увлажнителя `humidifer.sample`) -
ё   достаточно передать в УДЯ только `humidifer.sample`, уровень воды подхватится автоматически в большинстве случаев.

   Либо такой датчик можно сконфигурировать вручную через значения `type` и `attribute` (см. пример конфигурации ниже).

2. Датчик представлен отдельным устройством, значение в state (например `sensor.room_temp` с `device_class: temperature`) -
   достаточно передать такое устройство в УДЯ. Будет работать только в случае если у датчика поддерживаемый `device_class`.

3. Датчик представлен отдельным устройством, но его требуется представить как датчик другого устройства.
   Пример: уровень батареи `sensor.room_temp_battery` включить в датчик с температуры `sensor.room_temp`, или
   влажность в комнате `sensor.bedroom_humidity` включить в увлажнитель `humidifier.bedroom`.

   В этом случае дополнительные датчики и их типы (поле `type`) задаются как элементы списка `properties` основного устройства:
  ```yaml
  yandex_smart_home:
    filter:  # можно через интерфейс
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
          - type: water_level
            entity: sensor.humidifier_level
          - type: battery_level  # если хочется переместить датчик "из атрибута" в конец списка
            attribute: battery_level
      sensor.kitchen_meteo_temperature:  # должен быть существующим устройством
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

## Конвертация значений
Компонент автоматически конвертирует значения сенсоров из одних единиц измерения в другие на основании атрибута устройства/сенсора `unit_of_measurement`. Атрибут содержит единицу измерения, в которой находится значение в Home Assistant. Если атрибут отсутствует (или неверный), его можно задать через параметр `unit_of_measurement` в `properties`, пример:
```yaml
  yandex_smart_home:
    filter:
      include_entities:
        - humidifier.bedroom
    entity_config:
      humidifier.bedroom:
        properties:
          - type: tvoc
            attribute: total_volatile_organic_compounds
            unit_of_measurement: ppb  # для автоматической конвертации из миллиардных долей в мкг/м³
```

Поддерживаемые единицы измерения:
* `amperage`: `A`, `mA`
* `tvoc`: `ppb`, `ppm`, `p/m³`, `μg/ft³`, `mg/m³`, `µg/m³`
* `pressure`: `pa`, `hPa`, `kPa`, `MPa`, `mmHg`, `atm`, `bar`, `mbar`


## Кнопки (предварительная реализация)
На данный момент поддерживаются кнопки, представленные в виде объекта (entity). События по ним (`click`, `hold` и т.п.) должны появляться в атрибутах `action`, `last_action` или состоянии самого объекта. Так же объект должен **обязательно** содержать атрибут `device_class: button`, его можно задать в YAML конфигурации Home Assistant в секции `homeassistant.customize` ([подробнее...](https://www.home-assistant.io/docs/configuration/customizing-devices/#manual-customization))

Для кнопок, которые не представлены в виде объекта или если события появляются не в атрибутах `action` и `last_action`, требуется создать вспомогательные объекты в домене `input_text` и заполнять их состояние по триггеру. Пример для кнопки `WXKG01LM`, подключенной через Z2M:
```yaml
homeassistant:
  customize:
    input_text.test_button:
      device_class: button

yandex_smart_home:
  settings:
    beta: true
  filter:  # через интерфейс тоже можно
    include_entities:
      - input_text.test_button

input_text:
  test_button:
    name: Test Button
    initial: ''

automation:
  - alias: test_button_click
    trigger:
      - platform: device
        domain: mqtt
        device_id: 88c16946d5bfcee7dfce360e772ab881
        type: action
        subtype: single
        discovery_id: 0x00158d0003cb48af action_single
    action:
      - service: input_text.set_value
        entity_id: input_text.test_button
        data:
          value: click # поддерживаются click, double_click, hold

      - service: input_text.set_value
        entity_id: input_text.test_button
        data:
          value: ''

  - alias: test_button_hold
    trigger:
      - platform: device
        domain: mqtt
        device_id: 88c16946d5bfcee7dfce360e772ab881
        type: action
        subtype: hold
        discovery_id: 0x00158d0003cb48af action_hold
    action:
      - service: input_text.set_value
        entity_id: input_text.test_button
        data:
          value: hold

      - service: input_text.set_value
        entity_id: input_text.test_button
        data:
          value: ''
```
