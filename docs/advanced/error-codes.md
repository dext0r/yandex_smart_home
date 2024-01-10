# Коды ошибок
!!! danger "Только для продвинутых пользователей!"

Иногда устройство не способно выполнить команду или её не рекомендуется выполнять по соображениям безопасности. 
По умолчанию компонент выполняет любые команды и в большинстве случаев не возвращает никаких ошибок (Алиса отвечает "Окей, включаю").
 
Это поведение можно переопределить через шаблон `error_code_template` в `entity_config`. 

Если шаблон определён: перед выполнением команды компонент его вычислит и если что-то будет возвращено - команда выполнена не будет, а Алиса ответит текстом, соответствующем возвращённому коду ошибки.

В шаблон передаются переменные:

* `entity_id`
* `capability`: информация об умении ([документация УДЯ](https://yandex.ru/dev/dialogs/smart-home/doc/reference/post-action.html))

Простой способ увидеть реальные значения переменных - [подпишитесь](https://my.home-assistant.io/redirect/developer_events/) на события `yandex_smart_home_device_action` и поуправляйте устройством. 

Список допустимых кодов ошибок **фиксирован** ([полный список](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/response-codes.html)).

Для безусловного запрета включения или отключения устройства задайте параметры `turn_on` и/или `turn_off` равным `false` в [параметрах устройства](../config/entity.md#turn_on-off).

## Примеры { id=examples }

### Мало воды в чайнике { id=not-enough-water }
— Включи чайник

— Ой, недостаточно воды. Долейте её и повторите команду

```yaml
yandex_smart_home:
  entity_config:
    climate.kettle:
      error_code_template: |
        {% if capability.type == 'devices.capabilities.on_off' and capability.state.instance == 'on' and capability.state.value %}
          {% if states('sensor.kettle_water_level')|int(0) <= 10 %}  {# сенсор с уровнем воды в чайнике (в процентах) #}
            NOT_ENOUGH_WATER 
          {% endif %}
        {% endif %}

```

### Запрет на кондиционер в морозы { id=too-cold-for-ac }
Большинство кондиционеров имеют ограниченный рабочий диапазон температур. Можно понадеяться на встроенную автоматику, а можно просто запретить включать его голосом :)


— Включи кондиционер {>>когда за бортом -30 °C<<}

— Сначала нужно спросить разрешение от самого устройства... {>>ничего подходящего нет<<}
)
```yaml
yandex_smart_home:
  entity_config:
    climate.bedroom_ac:
      error_code_template: |
        {% set outside = states('sensor.outside_temperature')|int(-1) %} {# температура за бортом: из интеграции narodmon или прогноза погоды #}
        
        {% if capability.type == 'devices.capabilities.on_off' and capability.state.instance == 'on' and capability.state.value %}
          {# обычное включение через "Алиса, включи кондиционер" #}
          {# в большинстве случаев включается auto режим, поэтому разрешим включение до -10 °C #}
          {% if outside < -10 %}
            REMOTE_CONTROL_DISABLED
          {% endif %}
        {% endif %}

        {% if capability.type == 'devices.capabilities.mode' and capability.state.instance == 'thermostat' and capability.state.value == 'heat' %}
          {# "Алиса, включи кондиционер на обогрев", тоже ограничим до -10 °C #}
          {% if outside < -10 %}
            REMOTE_CONTROL_DISABLED
          {% endif %}
        {% endif %}

        {% if capability.type == 'devices.capabilities.mode' and capability.state.instance == 'thermostat' and capability.state.value == 'cool' %}
          {# "Алиса, включи кондиционер на охлаждение", ограничение - +5 °C #}
          {% if outside < 5 %}
            REMOTE_CONTROL_DISABLED
          {% endif %}
        {% endif %}
```
