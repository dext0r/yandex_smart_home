## Bosch SMV6ECX51E { id=bosch-smv6ecx51e }

> Интеграция: [Home Connect Alt](https://github.com/ekutner/home-connect-hass)

```yaml
yandex_smart_home:
  entity_config:
    switch.013100518886064003_bsh_common_setting_powerstate:
      type: devices.types.dishwasher
      turn_on: # По логике управления УДЯ - командой включения запускает программу
        action: button.press
        entity_id: button.013100518886064003_start_pause
      turn_off:
        action: button.press
        entity_id: button.013100518886064003_stop
      properties:
       - type: open #  Статус открытия двери
         entity: binary_sensor.013100518886064003_bsh_common_status_doorstate
       - type: water_level # Экономичность водопотребления в зависимости от программы
         entity: sensor.013100518886064003_bsh_common_option_waterforecast
       - type: battery_level # Экономичность энергопотребления в зависимости от программы
         entity: sensor.013100518886064003_bsh_common_option_energyforecast
      custom_toggles:
        controls_locked: # По логике управления УДЯ: снятие блокировки управления = включение прибора (и наоборот)
          state_entity_id: switch.013100518886064003_bsh_common_setting_powerstate
          turn_on:
            action: switch.turn_off
            entity_id: switch.013100518886064003_bsh_common_setting_powerstate
          turn_off:
            action: switch.turn_on
            entity_id: switch.013100518886064003_bsh_common_setting_powerstate
      modes:
        dishwashing:
          intensive: "Dishcare.Dishwasher.Program.Intensiv70"
          fast: "Dishcare.Dishwasher.Program.Quick65"
          auto: "Dishcare.Dishwasher.Program.Auto2"
          eco: "Dishcare.Dishwasher.Program.Eco50"
          express: "Dishcare.Dishwasher.Program.Quick45"
          glass: "Dishcare.Dishwasher.Program.Glas40"
          smart: "Dishcare.Dishwasher.Program.MachineCare"
          quiet: "Dishcare.Dishwasher.Program.NightWash"
          pre_rinse: "Dishcare.Dishwasher.Program.PreRinse"
      custom_modes:
        dishwashing:
          state_entity_id: select.013100518886064003_programs
          set_mode:
            action: select.select_option
            entity_id: select.013100518886064003_programs
            data:
              option: "{{ mode }}"
```

## Bosch SPV4HMX1DR { id=bosch-spv4hmx1dr }

> Интеграция: [Home Connect Alt](https://github.com/ekutner/home-connect-hass)

```yaml
yandex_smart_home:
  entity_config:
    switch.402020532764003998_bsh_common_setting_powerstate:
      name: Посудомойка
      room: Кухня
      type: devices.types.dishwasher
      properties:
        - type: open
          entity: binary_sensor.402020532764003998_bsh_common_status_doorstate
      modes:
        dishwashing:
          auto: "Dishcare.Dishwasher.Program.Auto2"
          eco: "Dishcare.Dishwasher.Program.Eco50"
          express: "Dishcare.Dishwasher.Program.Quick65"
          glass: "Dishcare.Dishwasher.Program.Glas40"
          intensive: "Dishcare.Dishwasher.Program.Intensiv70"
          pre_rinse: "Dishcare.Dishwasher.Program.PreRinse"
          quiet: "Dishcare.Dishwasher.Program.NightWash"
          dry: "Dishcare.Dishwasher.Program.MachineCare"
          smart: "Dishcare.Dishwasher.Program.Kurz60"
          turbo: "Dishcare.Dishwasher.Program.Super60"
          fast: "Dishcare.Dishwasher.Program.Quick45"
      custom_modes:
        dishwashing:
          state_entity_id: sensor.402020532764003998_selected_program
          set_mode:
            action: select.select_option
            entity_id: select.402020532764003998_programs
            data:
              option: '{{ mode }}'
      custom_toggles:
        pause:
          turn_on:
            action: button.press
            entity_id: button.402020532764003998_stop
          turn_off:
            action: button.press
            entity_id: button.402020532764003998_start_pause
```
