## Общие { id=generic }

| Устройство              | Домен                      | Примечание                                                                                                                                                          |
| ----------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Автоматизация           | `automation`               | Только включение/выключение. Для запуска можно создать `input_button`, передать его в УДЯ и использовать в качестве триггера в автоматизации                        |
| Вентилятор              | `fan`                      |                                                                                                                                                                     |
| Виртуальный выключатель | `input_boolean`            |                                                                                                                                                                     |
| Водонагреватель         | `water_heater`             |                                                                                                                                                                     |
| Выключатель             | `switch`                   |                                                                                                                                                                     |
| Группа (старый способ)  | `group`                    | Только включение/выключение, для получения всех возможностей используйте [группу для конкретного типа устройств](https://www.home-assistant.io/integrations/group/) |
| Замок                   | `lock`                     |                                                                                                                                                                     |
| Камера                  | `camera`                   |                                                                                                                                                                     |
| Качество воздуха        | `air_quality`              |                                                                                                                                                                     |
| Медиа-плеер             | `media_player`             | + телевизоры и ресиверы                                                                                                                                             |
| Освещение               | `light`                    |                                                                                                                                                                     |
| Программная кнопка      | `button`<br>`input_button` | Не путать с [физическими кнопками](./devices/button.md)                                                                                                             |
| Пульт                   | `remote`                   | Только включение и отключение                                                                                                                                       |
| Пылесос                 | `vacuum`                   |                                                                                                                                                                     |
| Скрипт                  | `script`                   |                                                                                                                                                                     |
| Событийный датчик       | `binary_sensor`            | См. [событийные датчики](#event-sensor)                                                                                                                             |
| Сцена                   | `scene`                    |                                                                                                                                                                     |
| Текст                   | `input_text`               | Только для создания [виртуальных кнопок](./devices/button.md)                                                                                                       |
| Термостат               | `climate`                  | + кондиционеры и некоторые чайники                                                                                                                                  |
| Увлажнитель             | `humidifier`               |                                                                                                                                                                     |
| Цифровой датчик         | `sensor`                   | См. [цифровые датчики](#float-sensor)                                                                                                                               |
| Шторы                   | `cover`                    |                                                                                                                                                                     |

## Цифровые датчики { id=float-sensor }

Список ниже описывает типы датчиков и условия их обнаружения для объектов, выбранных [для передачи](config/filter.md) в УДЯ. На [вручную настраиваемые датчики](devices/sensor/float.md) эти условия не распространяются.

!!! danger "Для автоматического обнаружения некоторых датчиков обязательно наличие атрибутов `device_class` и `unit_of_measurement`. Если вы создаёте [датчик на шаблоне](https://www.home-assistant.io/integrations/template/#configuration-variables) - не забудьте их указать."

### Температура { id=float-sensor-temperature }

* `device_class`: `temperature`
* `unit_of_measurements`: `°C`, `°F`, `K`

Или при наличии у объекта атрибутов `temperature` или `current_temperature`

### Влажность { id=float-sensor-humidity }

* `device_class`: `humidity` или `moisture`
* `unit_of_measurements`: `%`

Или при наличии у объекта атрибутов `humidity` или `current_humidity`

### Давление { id=float-sensor-pressure }

* `device_class`: `pressure` или `atmospheric_pressure`
* `unit_of_measurements`: `atm`, `Pa`, `hPa`, `kPa`, `bar`, `cbar`, `mbar`, `mmHg`, `inHg`, `psi`

### Освещенность { id=float-sensor-illumination }

* `device_class`: `illumination`

Или при наличии у объекта атрибута `illuminance`

### Уровень воды { id=float-sensor-water-level }

При наличии у объекта атрибута `water_level` (только для увлажнителей и вентиляторов)

### Уровень CO2 { id=float-sensor-co2 }

* `device_class`: `carbon_dioxide`

Или при наличии у объекта атрибута `carbon_dioxide`

### Счетчик электричества { id=float-sensor-electricity-meter }

* `device_class`: `energy`
* `unit_of_measurements`: `Wh`, `kWh`, `MWh`

### Счетчик газа { id=float-sensor-gas-meter }

* `device_class`: `gas`
* `unit_of_measurements`: `m³`, `L` (и другие единицы измерения объёма)

### Счетчик воды { id=float-sensor-gas-meter }

* `device_class`: `water`
* `unit_of_measurements`: `m³`, `L` (и другие единицы измерения объёма)

### Уровни частиц PM1 / PM2.5 / PM10 { id=float-sensor-pm }

* `device_class`: `pm1` / `pm25` / `pm10`

Или при наличии у объекта атрибутов `particulate_matter_0_1` / `particulate_matter_2_5` / `particulate_matter_10`

### Уровень TVOC { id=float-sensor-tvoc }

* `device_class`: `tvoc`, `volatile_organic_compounds`, `volatile_organic_compounds_parts`

Или при наличии у объекта атрибута `total_volatile_organic_compounds`

### Напряжение { id=float-sensor-voltage }

* `device_class`: `voltage`
* `unit_of_measurement`: `mV`, `V`

Или при наличии у объекта атрибута `voltage`

### Текущее потребление тока { id=float-sensor-current }

* `device_class`: `current`
* `unit_of_measurement`: `mA`, `A`

Или при наличии у объекта атрибута `current`

### Текущая потребляемая мощность { id=float-sensor-power }

* `device_class`: `power`
* `unit_of_measurement`: `W`, `kW`

Или при наличии у объекта атрибутов `power` или `load_power` или `current_consumption`

### Уровень заряда батареи { id=float-sensor-battery-level }

* `device_class`: `battery` (домен `sensor`)
* `unit_of_measurement`: `%`

Или при наличии у объекта атрибута `battery_level`

## Событийные датчики { id=event-sensor }

Список содержит датчики, которые будут автоматически обнаружены для объектов выбранных [для передачи](config/filter.md) в УДЯ. На [вручную настраиваемые датчики](devices/sensor/event.md) эти условия не распространяются.

!!! danger "Для автоматического обнаружения некоторых датчиков обязательно наличие атрибута `device_class`.<br>Если вы создаёте [датчик на шаблоне](https://www.home-assistant.io/integrations/template/#configuration-variables) - не забудьте его указать.<br>Если другая интеграция создала датчик без `device_class` - задайте его [вручную](devices/sensor/event.md#device-class)."

| Датчик                | `device_class`                             | Домен                                                                              |
| --------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------- |
| Нажатие кнопки        | `button`                                   | Любой ([подробнее](devices/button.md))                                             |
| Нажатие кнопки        |                                            | `sensor` (компонент [Xiaomi Gateway 3](https://github.com/AlexxIT/XiaomiGateway3)) |
| Открытие/закрытие     | `door`, `garage_door`, `window`, `opening` | `binary_sensor`                                                                    |
| Движение              | `motion`, `occupancy`, `presence`          | `binary_sensor`                                                                    |
| Наличие газа          | `gas`                                      | `binary_sensor`                                                                    |
| Наличие дыма          | `smoke`                                    | `binary_sensor`                                                                    |
| Низкий уровень заряда | `battery`                                  | `binary_sensor`                                                                    |
| Наличие протечки      | `moisture`                                 | `binary_sensor`                                                                    |
| Вибрация              | `vibration`                                | `binary_sensor`                                                                    |
| Вибрация              |                                            | `sensor` (компонент [Xiaomi Gateway 3](https://github.com/AlexxIT/XiaomiGateway3)) |

## Не поддерживаются { id=unsupported }

| Домен                    | Примечания                                                                                                                           |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `alarm_control_panel`    | В УДЯ нет подходящих умений                                                                                                          |
| `device_tracker`         |                                                                                                                                      |
| `lawn_mower`             | Поддержка запланирована                                                                                                              |
| `notify`                 |                                                                                                                                      |
| `number`, `input_number` | Можно привязать к устройству через [пользовательские умения](advanced/capabilities/about.md)                                         |
| `remote`                 | Можно задействовать в [пользовательском умении](advanced/capabilities/about.md)                                                      |
| `select`, `input_select` | Нет ясности что делать при выборе разных значений<br>Можно задействовать в [пользовательском умении](advanced/capabilities/about.md) |
| `siren`                  | Поддержка запланирована                                                                                                              |
