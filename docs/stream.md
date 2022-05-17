# Видеопоток с камер

**Функциональность находится в режиме бета-тестирования.**

## Предварительные требования
1. Камера должна быть добавлена в Home Assistant в виде устройства в домене `camera`
2. Должна быть включена интеграция [Stream](https://www.home-assistant.io/integrations/stream/), для включения добавьте `stream:` в `configuration.yaml` если не используете `default_config:`
3. Видеопоток должен отображаться по нажатию на иконку (I) в Панели разработчика
4. **Для прямого подключения:** необходимо задать в настройках внешний адрес Home Assistant (например `https://myha.dyndns.com`), по этому адресу Home Assistant должен быть доступ как из домашней сети, так и через интернет. Сделать это можно несколькими способами:
   * На странице Настройки > Система > Сеть > URL-адрес сервера > Интернет (включите "Расширенный режим" в профиле пользователя)
   * Если в настройках через интерфейс задать адрес невозможно - отредактируйте файл `core.config` в каталоге `config/.storage`: `"external_url": null` замените на `"external_url": "https://адрес-вашего-ха"` 
   * Через параметр `external_url` в `configuration.yaml` ([подробнее](https://www.home-assistant.io/docs/configuration/basic/))

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
