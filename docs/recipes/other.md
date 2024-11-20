## Управление подсветкой Tasmota-IRVAC { id=tasmota-irhvac }

> Интеграция: [Tasmota-IRHVAC](https://github.com/hristo-atanasov/Tasmota-IRHVAC)

```yaml
yandex_smart_home:
  entity_config:
    climate.tasmota_ac:
      name: Кондиционер
      type: thermostat.ac
      custom_toggles:
        backlight: # подсветка
          state_entity_id: climate.tasmota_ac
          state_attribute: light
          turn_on:
            action: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'on'
          turn_off:
            action: tasmota_irhvac.set_light
            entity_id: climate.tasmota_ac
            data:
              light: 'off'
```

## Бойлер Thermex Lima 80v { id=thermex-lima-80v }

> Интеграция: [Tuya Local](https://github.com/make-all/tuya-local)

```yaml
yandex_smart_home:
  entity_config:
    switch.thermex_lima_80v_water_heater:
      name: Бойлер
      properties:
        - type: temperature
          entity: sensor.thermex_lima_80v_current_temperature
        - type: temperature
          entity: sensor.thermex_lima_80v_target_temperature
      custom_ranges:
        temperature:
          state_entity_id: number.thermex_lima_80v_set_target_temperature
          set_value:
            action: number.set_value
            entity_id: number.thermex_lima_80v_set_target_temperature
            data:
              value: '{{ value }}'
          range:
            min: 35
            max: 75
            precision: 1
```
