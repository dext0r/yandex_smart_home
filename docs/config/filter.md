По умолчанию в УДЯ не передаются никакие объекты.

Выбрать объекты, которые будут переданы в УДЯ в виде устройств можно двумя способами (в зависимости от ваших предпочтений): YAML конфигурация или интерфейс Home Assistant.

!!! danger "Внимание!"
    Удаление устройств из УДЯ возможно **только** вручную. Удаляйте устройство из УДЯ только после исключения объекта из списка для передачи.
    Для удаления всех устройств - [отвяжите навык (производителя)](../quasar.md#unlink).

!!! warning "Недопустимо оставлять в УДЯ устройства, у которых объект не выбран для передачи. Такие устройства будут работать некорректно."

## Через интерфейс { id=gui }

Выбрать объекты для передачи можно в [настройках интеграции](../config/getting-started.md#gui) --> Объекты для передачи в УДЯ:

![](../assets/images/filter-gui.png){ width=750 }

## Через YAML конфигурацию { id=yaml }

Объекты выбираются в разделе `filter`, поддерживаемые фильтры:

* `include_domains`
* `include_entities`
* `include_entity_globs`
* `exclude_domains`
* `exclude_entities`
* `exclude_entity_globs`

Приоритизация по фильтрам работает аналогично интеграции [Recorder](https://www.home-assistant.io/integrations/recorder/#configure-filter).

!!! warning "Выбор объектов через YAML конфигурацию должен быть явно включен в [настройках интеграции](../config/getting-started.md#gui) --> Объекты для передачи в УДЯ."

!!! example "Пример"
    ```yaml
    yandex_smart_home:
      filter:
        include_domains:
          - switch
          - light
        include_entities:
          - media_player.tv
          - media_player.tv_lg
          - media_player.receiver
        include_entity_globs:
          - sensor.temperature_*
        exclude_entities:
          - light.highlight
        exclude_entity_globs:
          - sensor.weather_*
    ```

!!! example "Пример: передача всех объектов, **не рекомендуется**!"
    ```yaml
    yandex_smart_home:
      filter:
        include_entity_globs: "*"
    ```
