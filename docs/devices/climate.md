# Кондиционеры и термостаты

Для устройств в домене `climate` реализован особый алгоритм включения:

* Если устройство поддерживается режим `heat_cool` или `auto` - включается этот режим
* Если `heat_cool` или `auto` не поддерживается - для включения вызывается сервис `climate.turn_on`.
Поведение этого сервиса зависит от интеграции, через которую подключен кондиционер.

Если при включении из УДЯ кондиционер включается в нежелательном режиме - переопределите сервис включения в `entity_config`:

!!! example "Пример: включение в режиме `cool` (охлаждение)"
    ```yaml
    yandex_smart_home:
      entity_config:
        climate.some_ac:
          turn_on:
            service: climate.set_hvac_mode
            entity_id: climate.some_ac
            data:
              hvac_mode: cool
    ```

!!! example "Пример: включение через сервис `climate.turn_on`"
    ```yaml
    yandex_smart_home:
      entity_config:
        climate.smartir_ac:
          turn_on:
             service: climate.turn_on
             entity_id: climate.smartir_ac
    ```
