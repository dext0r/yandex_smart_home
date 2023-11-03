Выбирает режим работы устройства, при изменении которого будет вызываться определённый сервис. [Настраиваются](about.md) через словарь `custom_modes`.

Примеры: кофеварка, которая варит кофе скриптом `script.makemeonecupofcoffee` или моющий пылесос Xiaomi, в котором хочется управлять количеством подаваемой воды через сервис `xiaomi_vacuum.set_water_level`.

Для пользовательского режима автоматического связывание между значениями УДЯ и Home Assistant не производится. Вам нужно
вручную [задать соответствия](../../config/modes.md) через `modes`!

## Параметры { id=settings }
* `set_mode`: Вызываемый сервис при выборе режима в УДЯ. В переменной `mode` - значение режима на стороне Home Assistant. Если не задан - режим из УДЯ меняться не будет.
    
    !!! example "Пример"
        ```yaml
        set_mode:
          service: xiaomi_vacuum.set_water_level
          entity_id: vacuum.xiaomi_mop
          data:
            water_level: '{{ mode }}'
        ```

## Доступные функции { id=instance }
| Функция      | Описание                                                                |
|--------------|-------------------------------------------------------------------------|
| cleanup_mode | Режима уборки                                                           |
| coffee_mode  | Режима работы кофеварки                                                 |
| dishwashing  | Режима мытья посуды                                                     |
| fan_speed    | Режима работы скорости вентиляции                                       |
| heat         | Режима нагрева                                                          |
| input_source | Источник сигнала                                                        |
| program      | Какая-либо программа работы                                             |
| scene        | Режимы освещения ([список поддерживаемых](../../config/modes.md#scene)) |
| swing        | Направление воздуха в климатической технике                             |
| tea_mode     | Режима приготовления чая                                                |
| thermostat   | Температурный режим работы климатической техники                        |
| work_speed   | Скорость работы                                                         |

## Примеры { id=examples }
### Моющий пылесос { id=example-vacuum }
Моющий пылесос Xiaomi (`vacuum.xiaomi_mop`), переключение `set_water_level` через функцию "Скорость работы"
!!! summary "Атрибуты у vacuum.xiaomi_mop"
    ```yaml
    water_level: High
    water_level_list:
      - Low
      - Med
      - High
    ```

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        vacuum.xiaomi_mop:
          modes:
            work_speed:  # соответствие между режимами УДЯ и HA
              eco: ['Low']
              medium: ['Med']
              max: ['High']
          custom_modes:
            work_speed:
              state_entity_id: vacuum.xiaomi_mop
              state_attribute: water_level
              set_mode:
                service: xiaomi_vacuum.set_water_level
                entity_id: vacuum.xiaomi_mop
                data:
                  water_level: '{{ mode }}' # сюда подставятся Low/Med/High
    ```

#### Кофеварка { id=example-coffee-machine }
Кофеварка (`climate.hotcoffee`), которая умеет варить кофе скриптами, программа выбирается через функцию "Режим работы кофеварки"

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      entity_config:
        climate.hotcoffee:
          type: cooking.coffee_maker
          modes:
            coffee_mode:
              cappuccino: ['cappuccino']
              latte: ['latte']
          custom_modes:
            coffee_mode:
              set_mode:
                service: script.make_me_{{ mode }}_coffee  # вызовется script.make_me_latte_coffee
    ```
