# Несколько интеграций с разными фильтрами
Несмотря на то, что компонент с прямым подключением можно подключить к разным навыкам (или аккаунтам) в УДЯ, выбор устройств для передачи в УДЯ для разных навыков остается единым.

Это можно обойти созданием дубликата компонента:

* В `custom_components` скопируйте каталог `yandex_smart_home` в `yandex_smart_home2` (это пример, название здесь и далее могут быть любыми)
* В `yandex_smart_home2/manifest.json` измените параметр `domain` на `yandex_smart_home2`
* В `yandex_smart_home2/const.py` измените переменную `DOMAIN` на `yandex_smart_home2`
* В `yandex_smart_home2/const.py` измените переменную `CONFIG_ENTRY_TITLE` на `Yandex Smart Home 2`

Добавьте вновь созданную интеграцию на странице Настройки --> Устройства и службы --> Интеграции (ищите по названию из `CONFIG_ENTRY_TITLE`).

Настройка дублированного компонента выполняется через словарь `yandex_smart_home2`:

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home2:
      filters:
        include_domains:
          - switch
    ```

Дублированный компонент будет доступен по ссылке `https://YOUR_HA_DOMAIN:PORT/api/yandex_smart_home2`

Облачное подключение для дублированного компонента так же поддерживается.
