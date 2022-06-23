# Отладка компонента
## Включение отладки { id=logger }
* Добавьте в [`configuration.yaml`](https://www.home-assistant.io/docs/configuration/):
!!! example "configuration.yaml"
    ```yaml
    logger:
      default: warning
      logs:
        custom_components.yandex_smart_home: debug
    ```
* Перезапустите Home Assistant
* Отладочные сообщения будут появляться в файле `home-assistant.log` (в том ж каталоге, что и `configration.yaml`)
  
## Получение лога обновления списка устройств { id=discovery-log }
* Включите [отладку](#logger)
* Выполните [Обновление списка устройств](../quasar.md#discovery) в УДЯ, в `home-assistant.log` появятся строчки:
    ```
    [custom_components.yandex_smart_home.http] Request: https://YOUR_HA_DOMAIN/api/yandex_smart_home/v1.0/user/devices
    [custom_components.yandex_smart_home.http] Response: {"request_id": ...
    ```

  От вас потребуется только строка `Response:...`. Если до этих строк есть ошибки, захватите и их тоже.

## Получение лога обновления списка устройств (прямое подключение) { id=discovery-log-direct }
* Зайдите в свой навык на [dialogs.yandex.ru/developer](https://dialogs.yandex.ru/developer)
* Вкладка `Тестирование` --> `Опубликованная версия`
* Нажмите иконку :fontawesome-solid-plus: --> `Устройство умного дома` --> `Обновить список устройств`
* В окне отладки появится:
    ```
    Sending request to provider: GET https://YOUR_HA_DOMAIN/api/yandex_smart_home/v1.0/user/devices
    Got response from provider XXXXX: 200 {"request_id": .... (большой json)
    ```
  От вас потребуется строка `Got Response` и ниже.
  Пожалуйста, не включайте строку `Sending request`, в ней адрес вашего Home Assistant, пусть эта информация лучше остается в тайне :)
