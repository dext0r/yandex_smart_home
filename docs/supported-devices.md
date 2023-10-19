## Общие { id=generic }
| Устройство             | Домен           | Примечания                                                                                                                                                          |
|------------------------|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Автоматизация          | `automation`    | Только включение/выключение. Для запуска можно создать `input_button`, передать его в УДЯ и использовать в качестве триггера в автоматизации                        |
| Бинарный датчик        | `binary_sensor` | См. [событийные датчики](#event-sensors)                                                                                                                            |
| Вентилятор             | `fan`           |                                                                                                                                                                     |
| Водонагреватель        | `water_heater`  |                                                                                                                                                                     |
| Выключатель            | `switch`        |                                                                                                                                                                     |
| Группа (старый способ) | `group`         | Только включение/выключение, для получения всех возможностей используйте [группу для конкретного типа устройств](https://www.home-assistant.io/integrations/group/) |
| Замок                  | `lock`          |                                                                                                                                                                     |
| Камера                 | `camera`        |                                                                                                                                                                     |
| Качество воздуха       | `air_quality`   |                                                                                                                                                                     |
| Кнопка HA              | `button`        | Не путать с [физическими кнопками](./devices/button.md)                                                                                                             |
| Медиа-плеер            | `media_player`  | + телевизоры и ресиверы                                                                                                                                             |
| Освещение              | `light`         |                                                                                                                                                                     |
| Пылесос                | `vacuum`        |                                                                                                                                                                     |
| Скрипт                 | `script`        |                                                                                                                                                                     |
| Сцена                  | `scene`         |                                                                                                                                                                     |
| Термостат              | `climate`       | + кондиционеры и некоторые чайники                                                                                                                                  |
| Увлажнитель            | `humidifier`    |                                                                                                                                                                     |
| Цифровой датчик        | `sensor`        | См. [цифровые датчики](#sensors)                                                                                                                                    |
| Шторы                  | `cover`         |                                                                                                                                                                     |
|                        | `input_boolean` |                                                                                                                                                                     |
|                        | `input_button`  |                                                                                                                                                                     |
|                        | `input_text`    | Только для [виртуальных кнопок](./devices/button.md)                                                                                                                |

## Цифровые датчики { id=float-sensor }
Список содержит датчики, которые будут автоматически обнаружены для объектов, выбранных [для передачи](config/filter.md) в УДЯ. На [вручную настраиваемые датчики](devices/sensor/float.md) эти условия не распространяются.

!!! danger "Для автоматического обнаружения некоторых датчиков обязательно наличие атрибутов `device_class` и `unit_of_measurement`. Если вы создаёте [датчик на шаблоне](https://www.home-assistant.io/integrations/template/#configuration-variables) - не забудьте их указать."

### Температура { id=float-sensor-temperature }
* `device_class`: `temperature`
* `unit_of_measurements`: `°C`, `°F`, `K`

Или при наличии у объекта атрибутов `temperature` или `current_temperature`

### Влажность { id=float-sensor-humidity }
* `device_class`: `humidity`
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

### Уровни частиц PM1 / PM2.5 / PM10 { id=float-sensor-pm }
При наличиии у объекта атрибутов `particulate_matter_0_1` / `particulate_matter_2_5` / `particulate_matter_10`

### Уровень TVOC { id=float-sensor-tvoc }
При наличии у объекта атрибута `total_volatile_organic_compounds`

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
Список содержит датчики, которые будут автоматически обнаружены для объектов в домене `binary_sensor`, выбранных [для передачи](config/filter.md) в УДЯ. На [вручную настраиваемые датчики](devices/sensor/event.md) эти условия не распространяются.

!!! danger "Для автоматического обнаружения датчиков обязательно наличие атрибута `device_class`.<br>Если вы создаёте [датчик на шаблоне](https://www.home-assistant.io/integrations/template/#configuration-variables) - не забудьте его указать.<br>Если другая интеграция создала датчик без `device_class` - задайте его [вручную](./devices/sensor/about.md#device-class)."

| Датчик                | `device_class`                             | 
|-----------------------|--------------------------------------------|
| Открытие/закрытие     | `door`, `garage_door`, `window`, `opening` |
| Движение              | `motion`, `occupancy`, `presence`          |
| Наличие газа          | `gas`                                      |
| Наличие дыма          | `smoke`                                    |
| Низкий уровень заряда | `battery`                                  |
| Низкий уровень воды   | `water_level`                              |
| Наличие протечки      | `moisture`                                 |
| Вибрация              | `vibration`                                |

## Не поддерживаются { id=unsupported }
| Устройство | Домен          | Примечания                                                                                                                      |
|------------|----------------|---------------------------------------------------------------------------------------------------------------------------------|
|            | `input_select` | Нет ясности что делать при выборе разных значений<br>Обратите внимание на [пользовательские умения](./advanced/capabilities.md) |
