# Трансляция видеопотока с камеры

## Предварительные требования { id=requirements }

1. Камера должна быть добавлена в Home Assistant в виде устройства в домене `camera` и поддерживать стриминг
(атрибут `supported_features: 2 или 3` в панели разработчика)
2. Должна быть включена интеграция [Stream](https://www.home-assistant.io/integrations/stream/).
Для включения добавьте `stream:` в `configuration.yaml` если не используете `default_config:`
3. Видеопоток должен отображаться по нажатию на иконку (I) в Панели разработчика

!!! warning "Ограничения"

    * Поддерживаемые кодеки видео: **H264**.
    * Максимальное разрешение видео: 1920 × 1080.
    * Поддерживаемые кодеки аудио: AAC.

    Если ваша камера использует другие кодеки - измените её настройки или воспользуйтесь [go2rtc](https://github.com/AlexxIT/go2rtc) для транскодинга.

### Прямое подключение { id=direct-connection }

Необходимо задать в настройках внешний адрес Home Assistant (например `https://myha.dyndns.com`),
по этому адресу Home Assistant должен быть доступ как из домашней сети, так и через интернет.

Сделать это можно несколькими способами:

* На странице `Настройки` --> `Система` --> `Сеть` --> `URL-адрес сервера` --> `Интернет` (включите `Расширенный режим` в профиле пользователя)
* Через параметр [`external_url`](https://www.home-assistant.io/integrations/homeassistant/#external_url) в `configuration.yaml`

## Известные проблемы { id=known-bugs }

### Не загружается поток при доступе к HA через KeenDNS { id=known-bugs-keedns }

Для решения требуется обновить прошивку роутера (на 01.04.2022 исправленная прошивка пока не выпущена).
В качестве временного решения добавьте в YAML конфигурацию параметр `cloud_stream: true` для использования облачного сервера:

!!! example "configuration.yaml"
    ```yaml
    yandex_smart_home:
      settings:
        cloud_stream: true
    ```

## Включение отладки { id=debug }

!!! example "configuration.yaml"
    ```yaml
    logger:
      default: warning
      logs:
        homeassistant.components.http: debug
        homeassistant.components.camera: debug
        homeassistant.components.stream: debug
        custom_components.yandex_smart_home: debug
    ```
