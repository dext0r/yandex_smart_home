## Переход с 0.x на 1.x

### Прямое подключение: настройки нотификатора { id=v1-notifier }

С версии 1.x для прямого подключения служба уведомлений о состоянии устройств ([нотификатор](https://docs.yaha-cloud.ru/v0.6.x/advanced/direct-connection/#notifier)) настраивается через [интерфейс](./config/getting-started.md#gui) (раздел `Параметры навыка`), а не YAML конфигурацию.

Параметры из секции `notifier` YAML конфигурации будут перенесены **автоматически** если в ней задан только один навык/пользователь.

Если у вас несколько записей в секции `notifier` (например задействованы несколько пользователей) – необходимо перенести параметры вручную. Для каждого пользователя/навыка потребуется создать отдельную интеграцию с прямым типом подключения.

### Состояние для custom_toggles { id=v1-custom-toggles }

Пользовательские умения типа "Переключатели" теперь ожидают бинарные значения (`on/off/yes/no/True/False/1/0`) при определении своего состояния.
До версии 1.0 умение считалось включенным, когда состояние отличалось от `off`.

!!! example "До 1.х"

  ```yaml
  yandex_smart_home:
    entity_config:
      humidifier.humidifier:
        custom_toggles:
          backlight:
            state_entity_id: select.humidifier_led_brightness  # значения high/med/off
  ```

!!! example "После 1.х"

  ```yaml
  yandex_smart_home:
    entity_config:
      humidifier.humidifier:
        custom_toggles:
          backlight:
            state_template: '{{ not is_state("select.humidifier_led_brightness", "off") }}'
  ```

### Параметр pressure_unit { id=v1-pressure-unit }

Параметр `pressure_unit` (раздел `settings`) больше не поддерживается, удалите его из YAML конфигурации.

Теперь компонент автоматически пытается сохранить единицы измерения при передаче значений датчиков из Home Assistant в УДЯ ([подробнее о конвертации значений](devices/sensor/float.md#unit-conversion))

### Прочие изменения { id=v1-not-breaking }

Прочие изменения в 1.x не ломающие обратную совместимость с v0.x:

1. При [настройке режимов](config/modes.md) в параметре `entity_config.*.modes` теперь рекомендуется использовать строки, а не списки. Использование списков допустимо, и менять это не планируется.
