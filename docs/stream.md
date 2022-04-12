# Видеопоток с камер

**Просмотр видеопотока с камер доступен только участникам бета-теста УДЯ ([подробнее](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/video_stream.html)). Если вы один из них, то для включения поддержки требуется задать `beta: true` в секции `settings` YAML конфигурации интеграции.**

## Предварительные требования
1. Камера должна быть добавлена в Home Assistant в виде устройства в домене `camera`
2. Должна быть включена интеграция [Stream](https://www.home-assistant.io/integrations/stream/), для включения добавьте `stream:` в `configuration.yaml` если не используете `default_config:`
3. Видеопоток должен отображаться по нажатию на иконку (I) в Панели разработчика
4. **Для прямого подключения:** на странице Конфигурация > Настройки > Общие задайте "URL-адрес для глобальной сети" (например `https://myha.dyndns.com/`). По этому адресу Home Assistant должен быть доступ как из домашней сети, так и через интернет.

## Известные проблемы
1. Не загружается поток при доступе к HA через KeenDNS. Для решения требуется обновить прошивку роутера (на 01.04.2022 исправленная прошивка пока не выпущена). В качестве временного решения добавьте в YAML конфигурацию параметр `cloud_stream: true` для использования облачного сервера:
```yaml
yandex_smart_home:
  settings:
    beta: true
    cloud_stream: true
```

## Включение отладки
В `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    homeassistant.components.http: debug
    homeassistant.components.camera: debug
    homeassistant.components.stream: debug
    custom_components.yandex_smart_home: debug
```
