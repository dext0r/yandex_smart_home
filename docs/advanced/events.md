# События
После успешного выполнения команды на изменение состояния устройства в HA генерируется событие `yandex_smart_home_device_action`.

Это событие можно использовать в автоматизациях для выполнения дополнительных действий.

Поля события:

* `entity_id`: ID объекта
* `capability`: Информация об умении, полученная от УДЯ (без преобразований)

## Примеры событий
```yaml
event_type: yandex_smart_home_device_action
data:
  entity_id: fan.ceiling_fan
  capability:
    type: devices.capabilities.on_off
    state:
      instance: "on"
      value: true
origin: LOCAL
time_fired: "2023-02-08T11:51:10.033799+00:00"
context:
  id: 01GRRDV1YAFWGQQCE2QN003S02
  parent_id: null
  user_id: null
```

```yaml
event_type: yandex_smart_home_device_action
data:
  entity_id: light.bed_light
  capability:
    type: devices.capabilities.color_setting
    state:
      instance: rgb
      value: 13303562
origin: LOCAL
time_fired: "2023-02-08T11:49:03.963774+00:00"
context:
  id: 01GRRDQ6TP3BQX05RS1W84BMQ8
  parent_id: null
  user_id: null
```
