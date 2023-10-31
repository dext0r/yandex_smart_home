Управление функциями устройств, которые включаются и выключаются. [Настраиваются](about.md) через словарь `custom_toggles`. В [состоянии](about.md#state) ожидается логическое значение (`on/off/yes/no/True/False/1/0`). 

## Параметры { id=settings }
* `turn_on` и `turn_off`: Вызываемые сервисы при включении/выключении функции в УДЯ. Если не задан один или несколько сервисов - соответствующее действие выполняться не будет.
    
    !!! example "Пример"
        ```yaml
        turn_on:
          service: xiaomi_miio_airpurifier.fan_set_ptc_on
          entity_id: fan.xiaomi_airfresh_va4
        turn_off:
          service: xiaomi_miio_airpurifier.fan_set_ptc_off
          entity_id: fan.xiaomi_airfresh_va4
        ```

## Доступные функции { id=instance }
| Функция         | Описание                                                    |
|-----------------|-------------------------------------------------------------|
| backlight       | Включение подсветки                                         |
| controls_locked | Блокировка управления (детский режим)                       |
| ionization      | Включение ионизации                                         |
| keep_warm       | Включение поддержания тепла                                 |
| mute            | Выключение звука на устройстве                              |
| oscillation     | Включение вращения                                          |
| pause           | Временная остановка (паузу) текущей деятельности устройства |


## Примеры { id=examples }
### Бризер { id=example-breezer }
Управление функцией подогрева для бризера Xiaomi (`fan.xiaomi_airfresh_va4`) через функцию "Поддержание тепла"

!!! summary "Атрибуты fan.xiaomi_airfresh_va4"
    ```yaml
    model: zhimi.airfresh.va4
    ptc: false  # а может быть true (on/off тоже подходит)
    ```

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        fan.xiaomi_airfresh_va4:
          custom_toggles:
            keep_warm:
              state_entity_id: fan.xiaomi_airfresh_va4
              state_attribute: ptc
              turn_on:
                service: xiaomi_miio_airpurifier.fan_set_ptc_on
                entity_id: fan.xiaomi_airfresh_va4
              turn_off:
                service: xiaomi_miio_airpurifier.fan_set_ptc_off
                entity_id: fan.xiaomi_airfresh_va4
    ```
