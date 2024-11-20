## Xiaomi Smart Tower Heater Lite { id=xiaomi-smart-tower-heater-lite }

> Интеграция: [Xiaomi Miot](https://github.com/al-one/hass-xiaomi-miot)

```yaml
# Потребуется создать вспомогательный свитч и две автоматизации включения и выключения. В первом случае - установка температуры на #99, во втором случае - нажатие кнопки Stop-work.
yandex_smart_home:
  entity_config:
    fan.zhimi_rmb1_85fa_air_purifier :
      type: devices.types.purifier
      modes:
        fan_speed:
          low: 'Sleep'
          medium: 'Favorite'
          auto: 'Auto'
      custom_modes:
        fan_speed:
          state_attribute: preset_mode
          set_mode:
            action: fan.set_preset_mode
            target:
              entity_id: fan.zhimi_rmb1_85fa_air_purifier
            data:
              preset_mode: '{{ mode }}'
      properties:
        - type: pm2.5_density
          entity: sensor.zhimi_rmb1_85fa_pm25_density_2
        - type: humidity
          entity: sensor.zhimi_rmb1_85fa_relative_humidity_2
        - type: water_level # Показывает остаток фильтра
          entity: sensor.zhimi_rmb1_85fa_filter_life_level_2
```
