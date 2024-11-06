# События

После выполнения команды на изменение состояния устройства в HA генерируется событие `yandex_smart_home_device_action`.

Это событие можно использовать в автоматизациях для выполнения дополнительных действий.

Поля события:

* `entity_id`: ID объекта
* `capability`: Информация об умении, полученная от УДЯ
* `error_code`: Код ошибки (если команда завершилась с ошибкой)

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

```yaml
event_type: yandex_smart_home_device_action
data:
  entity_id: climate.hvac
  error_code: DEVICE_UNREACHABLE
origin: LOCAL
time_fired: "2023-10-13T14:43:43.633210+00:00"
context:
  id: 01HCMQWHWGZDJ9GK8KDB1V9FEQ
  parent_id: null
  user_id: null
```

```yaml
event_type: yandex_smart_home_device_action
data:
  entity_id: light.office_rgbw_lights
  capability:
    type: devices.capabilities.on_off
    state:
      instance: "on"
      value: true
  error_code: REMOTE_CONTROL_DISABLED
origin: LOCAL
time_fired: "2023-10-13T14:47:07.443147+00:00"
context:
  id: 01HCMR2RXGMA4F1E16HTDQ9V24
  parent_id: null
  user_id: null
```
