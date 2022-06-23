В этом разделе собраны конфигурации популярных устройств. При использовании обязательно поменяйте ID объектов на свои.

[Предложить свой рецепт](https://forms.yandex.ru/u/62b456db0c134229d975d1e3/){ .md-button }

## Увлажнитель Xiaomi Smartmi { id=xiaomi-smartmi-humidifier }
```yaml
yandex_smart_home:
  entity_config:
    humidifier.smartmi_humidifier:
      properties:
        - type: temperature
          entity: sensor.smartmi_humidifier_temperature
        - type: humidity
          entity: sensor.smartmi_humidifier_humidity
        - type: water_level
          entity: sensor.smartmi_humidifier_water_level
      custom_toggles:
        controls_locked: # блокировка управления
          state_entity_id: switch.smartmi_humidifier_child_lock
          turn_on:
            service: switch.turn_on
            entity_id: switch.smartmi_humidifier_child_lock
          turn_off:
            service: switch.turn_off
            entity_id: switch.smartmi_humidifier_child_lock
        backlight: # подсветка
          state_entity_id: select.smartmi_humidifier_led_brightness
          turn_on:
            service: select.select_option
            entity_id: select.smartmi_humidifier_led_brightness
            data:
              option: bright # или dim
          turn_off:
            service: select.select_option
            entity_id: select.smartmi_humidifier_led_brightness
            data:
              option: 'off'
```

## Управление подсветкой Tasmota-IRVAC { id=tasmota-irhvac }
> Интеграция: [Tasmota-IRHVAC](https://github.com/hristo-atanasov/Tasmota-IRHVAC)

```yaml
yandex_smart_home:
  entity_config:
    climate.tasmota_ac:
      name: Кондиционер
      type: devices.types.thermostat.ac
      custom_toggles:
        backlight: # подсветка
          state_attribute: light
          turn_on:
            service: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'on'
          turn_off:
            service: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'off'
```
