## Переход с 0.x на 1.x
### Состояние для custom_toggles
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
