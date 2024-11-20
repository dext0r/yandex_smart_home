Управление параметрами устройства, которые имеют диапазон регулировки (громкость, яркость, температура).
[Настраиваются](about.md) через словарь `custom_ranges`. В [состоянии](about.md#state) ожидается числовое значение.

## Параметры { id=settings }

* `set_value`: Действие выполняемое при установке абсолютного значения функции. В переменной `value` абсолютное или относительное значение (в зависимости от настроек `range` и наличия `increase_value` и `decrease_value`).
Если не задан - установка абсолютного значения поддерживаться не будет.

    !!! example "Пример"
        ```yaml
         set_value:
           action: xiaomi_miio_airpurifier.fan_set_favorite_speed
           entity_id: fan.xiaomi_airfresh_a1
           data:
             speed: '{{ value }}'
        ```

* `increase_value` и `decrease_value`: Действия, вызываемые при относительной регулировке (кнопки `+` и `-` и "Алиса, убавь температуру"). Если не заданы - будет вызываться действие `set_value`.
* `range`: Граничные значения диапазона. Для `humidity`, `open`, `brightness` есть ограничение: минимум `0`, максимум `100`.
  Если не задать `min` и `max` регулировка будет только относительная (в переменной `value` - `1` или `-1`).

    !!! example "Пример"
        ```yaml
        range:
          # диапазон от -100 до 100
          min: -100
          max: 100
          # шаг изменения при нажатии на плюс или минус в интерфейсе, необязательное, по умолчанию - 1
          precision: 2
        ```

Для устройств, поддерживающих установку абсолютного значения, достаточно задать только `set_value`.
А для устройств с поддержкой только относительного (например IR пульт) - `increase_value` и `decrease_value`.

Если ни одно действие не задано - умение из УДЯ управляться не будет.

## Доступные функции { id=instance }

| Функция     | Описание                                                 |
| ----------- | -------------------------------------------------------- |
| brightness  | Изменение яркости световых элементов                     |
| channel     | Изменение канала, например телевизионного                |
| humidity    | Изменение влажности                                      |
| open        | Открывание чего-либо в процентах (открывание штор, окна) |
| temperature | Изменение температуры (чайника, обогревателя)            |
| volume      | Изменение громкости устройства                           |
| tea_mode    | Режима приготовления чая                                 |
| thermostat  | Температурный режим работы климатической техники         |
| work_speed  | Скорость работы                                          |

## Примеры { id=examples }

### Бризер { id=example-breezer }

Изменение параметра `favorit_speed` на бризере Xiaomi (`fan.xiaomi_airfresh_a1`)

!!! summary "Атрибуты fan.xiaomi_airfresh_a1"
    ```yaml
    model: dmaker.airfresh.a1
    favorite_speed: 80
    ```

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        fan.xiaomi_airfresh_a1:
          custom_ranges:
            volume:  # как самое подходящее
              state_entity_id: fan.xiaomi_airfresh_a1
              state_attribute: favorit_speed
              set_value:
                action: xiaomi_miio_airpurifier.fan_set_favorite_speed
                data:
                  speed: '{{ value }}'
              # значения для примера
              range:
                min: 60
                max: 300
                precision: 20 # по вкусу
    ```

### Выбор канала { id=example-tv-channel }

Выбор канала на телевизоре через `media_player.play_media`, листание каналов через отдельные скрипты, номер текущего канала нигде не хранится.

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        media_player.stupid_tv:
          custom_ranges:
            channel:
              set_value:
                action: media_player.play_media
                entity_id: media_player.stupid_tv
                data:
                  media_content_type: channel
                  media_content_id: '{{ value }}'
              increase_value:
                # действие отправит нажатие кнопки "канал вверх" по IR
                action: script.next_channel_via_ir
              decrease_value:
                # действие отправит нажатие кнопки "канал вниз" по IR
                action: script.prev_channel_via_ir
              range:
                min: 0
                max: 999
    ```
