[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

# Компонент Yandex Smart Home для Home Assistant
Компонент позволяет добавить устройства из Home Assistant в платформу [умного дома Яндекса](https://yandex.ru/dev/dialogs/smart-home) (УДЯ)
и управлять ими с любого устройства с Алисой: умные колонки, приложение на телефоне, веб интерфейс ["квазар"](https://yandex.ru/quasar/iot).

- [Предварительные требования](#предварительные-требования)
- [Установка](#установка)
- [Настройка](#настройка)
- [Фильтрация устройств](#фильтрация-устройств)
- [Тонкая настройка устройств](#тонкая-настройка-устройств)
  - [Поддержка комнат](#поддержка-комнат)
  - [Настройка режимов/функций](#настройка-режимовфункций)
    - [thermostat](#thermostat)
    - [swing](#swing)
    - [program](#program)
    - [fan_speed](#fan_speed)
    - [cleanup_mode](#cleanup_mode)
    - [input_source](#input_source)
    - [scene](#scene)
  - [Датчики](#датчики)
  - [Ограничение уровня громкости](#ограничение-уровня-громкости)
- [Уведомления об изменении состояний устройств](#уведомления-об-изменении-состояний-устройств)
- [Прочие настройки](#прочие-настройки)
- [Проблемы](#проблемы)
  - [Яндекс не может достучаться до Home Assistant](#яндекс-не-может-достучаться-до-home-assistant)
  - [Устройство не появляется в УДЯ](#устройство-не-появляется-в-удя)
  - [Ошибка "Что-то пошло не так" при частых действиях](#ошибка-что-то-пошло-не-так-при-частых-действиях)
  - [Как отвязать диалог](#как-отвязать-диалог)
- [Полезные ссылки](#полезные-ссылки)
- [Пример конфигурации](#пример-конфигурации)


## Предварительные требования
* Home Assistant версии 2021.4 или новее.
* Доступность Home Assistant из интернета по **доменному имени** используя белый IP адрес или
  сторонние сервисы: [Dataplicity](https://github.com/AlexxIT/Dataplicity), [KeenDNS](https://keenetic.link).
* Настроенный HTTPS сертификат. Для белого IP адреса можно воспользоваться официальным аддоном Let's Encrypt.
  При использовании Dataplicity или KeenDNS HTTPS настраивается автоматически. Самоподписанные сертификаты работать не будут.


## Установка
**Способ 1:** [HACS](https://hacs.xyz/)
> HACS > Интеграции > Добавить > Yandex Smart Home > Установить

**Способ 2:** Вручную скопируйте папку `yandex_smart_home` из [latest release](https://github.com/dmitry-k/yandex_smart_home/releases/latest) в директорию `/config/custom_components`


## Настройка
Все настройки выполняются через конфигурационный файл, в интерфейсе Home Assistant компонент никак не представлен.

* Для базовой настройки компонента добавте строку `yandex_smart_home:` в файл `configuration.yaml` и перезапустите Home Assistant.
  Если у вас много устройств, или вы хотите отдавать в УДЯ только некоторые, **рекомендуется сразу** [настроить фильтры](#фильтрация-устройств).
* Зайти на [dialogs.yandex.ru](https://dialogs.yandex.ru) и создать диалог (навык) с типом "Умный дом".
  Желательно это делать из под аккаунта, который планируется использовать для управления умным домом.
  При необходимости доступ к диалогу можно предоставить другим пользователям Яндекса (вкладка Доступ).
  * Вкладка "Настройки":
    | Поле              | Значение     |
    | ----------------- | ------------ |
    | Backend           | Endpoint URL: `https://[YOUR_HA_DOMAIN:PORT]/api/yandex_smart_home` (пример: `https://XXXX.dataplicity.io/api/yandex_smart_home`) |
    | Тип доступа       | Приватный    |
    | Подзаголовок      | Любой        |
    | Имя разработчика  | Любое        |
    | Официальный навык | Нет          |
    | Описание          | Любое        |
    | Иконка            | Любая (например [эта](https://community-assets.home-assistant.io/original/3X/6/a/6a99ebb8d0b585a00b407123ff76964cb3e18780.png)) |


  * Вкладка "Связка аккаунтов":
    | Поле                        | Значение                                          |
    | --------------------------- | ------------------------------------------------- |
    | Идентификатор приложения    | https://social.yandex.net/                        |
    | Секрет приложения           | Любой, например: `secret`                         |
    | URL авторизации             | `https://[YOUR_HA_DOMAIN:PORT]/auth/authorize`    |
    | URL для получения токена    | `https://[YOUR_HA_DOMAIN:PORT]/auth/token`        |
    | URL для обновления токена   | `https://[YOUR_HA_DOMAIN:PORT]/auth/token`        |

* На вкладке "Настройки" нажать "Опубликовать" (для приватных навыков публикация автоматическая и моментальная).
  В этот момент УДЯ попробует подключиться к вашему Home Assistant, и если у него не получится - появятся ошибки валидации.
* В приложении Яндекс на Android/iOS (или в [квазаре](https://yandex.ru/quasar/iot)) добавить устройства умного дома,
  в производителях выбрать диалог, который создали ранее (ищите по названию).
* Должна произойти переадресация на страницу авторизации Home Assistant. Рекомендуется создать отдельного пользователя
  специально для УДЯ и авторизоваться под ним. В этом случае в журнале событий будет видно, когда устройством управлял Яндекс.
* Настоятельно рекомендуется настроить [уведомления об изменении состояний](#уведомления-об-изменении-состояний-устройств).


## Фильтрация устройств
По умолчанию в УДЯ отдаются все поддерживаемые компонентом устройства (в том числе из доменов `script` и `scene`).
Отфильтровать устройства можно через словарь `filter`. Поддерживаемые фильтры: `include_domains`, `include_entities`,
`include_entity_globs`, `exclude_domains`, `exlude_entities`, `exclude_entity_globs`.

Приоритизация по фильтрам работает аналогично фильтрам в интеграции [Recorder](https://www.home-assistant.io/integrations/recorder/#configure-filter).

Фильтры используется только в момент обновления списка устройств. Если устройство уже добавлено в УДЯ, его исключение
с помощью фильтров не даст никого эффекта. Поэтому фильтры лучше настраивать сразу, особенно если в Home Assistant много устройств.

Пример конфигурации:
```yaml
yandex_smart_home:
  filter:
    include_domains:
      - switch
      - light
    include_entities:
      - media_player.tv
      - media_player.tv_lg
      - media_player.receiver
    include_entity_globs:
      - sensor.temperature_*
    exclude_entities:
      - light.highlight
    exclude_entity_globs:
      - sensor.weather_*
```


## Тонкая настройка устройств
Для каждого устройства можно задать индивидуальные параметры для изменения некоторых значений по умолчанию.
Выполняется через словарь `entity_config`.

| Параметр      | По умолчанию    | Варианты                          | Описание                                                 |
| ------------- | --------------- | --------------------------------- | -------------------------------------------------------- |
| `name`        |                 | Русские буквы и пробелы           | Отображаемое название устройства
| `room`        |                 | Русские буквы и пробелы           | Комната, в которой находится устройство, [подробнее о комнатах...](#поддержка-комнат)
| `type`        | Автоматически   | [Список](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/device-types.html#device-types__types) | Переопредление стандартного типа устройства. Например домен `switch` по умолчанию отдается как "выключатель" (`devices.types.switch`) и реагирует на команду "Алиса, включи ХХХ". А если задать `devices.types.openable`, то у такого устройства изменится иконка и фраза на "Алиса, **открой** XXX"
| `channel_set_via`<br>`_media_content_id` | `false` | `true` / `false`     | Только для домена `media_player`. Выбор канала через `media_content_id`, [подробнее...](https://github.com/dmitry-k/yandex_smart_home/issues/36) (скорее всего устарело)

Пример конфигурации:
```yaml
yandex_smart_home:
  entity_config:
    fan.xiaomi_miio_device:
      name: Увлажнитель
      room: Гостинная
      type: devices.types.humidifier
    switch.gate:
      name: Ворота
      room: Улица
      type: devices.types.openable
```


### Поддержка комнат
Если для устройства заданы `name` и `room` УДЯ при обновлении списка устройств автоматически добавит его в нужную комнату.

Важные уточнения:
1. Комната уже должна существовать.
2. При ручном обновлении устройств (или при первичной настройке) важно **не выбирать** "Дом", а просто понажимать стрелку "Назад":

| <img src="quasar_discovery_1.png" width="350"> | <img src="quasar_discovery_2.png" width="350"> |
|:---:|:---:|
| Нажать "Далее" | **Не нажимать** "Выбрать", вместо этого нажимать стрелку назад |


### Настройка режимов/функций
Для некоторых устройств в УДЯ предусмотрено управление режимами. Типичные примеры - охлаждение/нагрев/осушение для кондиционера,
или низкая/средняя скорость вращения для вентилятора.

[Список режимов](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html) в УДЯ фиксированный,
поэтому их необходимо связывать со значениями атрибутов в Home Assistant. Для большинства устройств этот процесс (маппинг)
происходит **автоматически**, но в некоторых случаях это требуется сделать вручную через параметр `modes` в `entity_config`.

Со стороны УДЯ нет жесткой привязки значений режимов к типам устройств. Другими словами, у режима "Скорость вентиляции"
(`fan_speed`) значения могут быть не только "низкое", "высокое", но и совсем от другого типа устройств, например "дичь" или "эспрессо".

Если маппинг не удался - управление функцией через УДЯ будет недоступно.

Пример конфигурации:
```yaml
yandex_smart_home:
  entity_config:
    light.led_strip:
      modes:
        scene:
          sunrise:
            - Wake up
          alarm:
            - Blink
    climate.some_ac:
      modes:
        fan_speed:
          auto: [auto]
          min: ['1','1.0']
          turbo: ['5','5.0']
          max: ['6','6.0']
        swing:
          auto: ['SWING']
          stationary: ['OFF']
```

* `scene`, `fan_speed`, `swing` - режим/функция со стороны УДЯ
* `auto`, `stationary`, `alarm` - значение режима со стороны УДЯ ([все возможные значения](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html))
* Списки значений (`Wake Up`, `Swing` и т.п.) - значения атрибута сущности в Home Assistant, которое соответствует значению режима в УДЯ.
  Задавать лучше строками в кавычках.

Ниже детальная информация по поддерживаемым режимам и их значениям.


#### thermostat
Установка температурного режима работы климатической техники, например, в кондиционере.

* Поддерживаемые домены: `climate`
* Рекомендуемые значения режимов: `heat`, `cool`, `auto`, `dry`, `fan_only`
* Атрибут в Home Assistant: `hvac_modes`

#### swing
Установка направления воздуха в климатической технике.

* Поддерживаемые домены: `climate`
* Рекомендуемые значение режимов: `vertical`, `horizontal`, `stationary`, `auto`
* Атрибут в Home Assistant: `swing_modes`

#### program
Установка какой-либо программы работы.

* Поддерживаемые домены: `humidifier`
* Рекомендуемые значения режимов: `normal`, `eco`, `min`, `turbo`, `medium`, `max`, `quiet`, `auto`, `high`
* Атрибут в Home Assistant: `available_modes`

#### fan_speed
Установка режима работы скорости вентиляции, например, в кондиционере, вентиляторе или обогревателе.

* Поддерживаемые домены: `fan`, `climate`
* Рекомендуемые значения режимов: `auto`, `quiet`, `low`, `medium`, `high`, `turbo`
* Атрибут в Home Assistant:
  * `fan`: `preset_modes`, `speed_list` (устарело)
  * `climate`: `fan_modes`

#### cleanup_mode
Установка режима уборки.

* Поддерживаемые домены: `vacuum`
* Рекомендуемые значения режимов: `auto`, `turbo`, `min`, `max`, `express`, `normal`, `quiet`
* Атрибут в Home Assistant: `fan_speed_list`

#### input_source
Установка источника сигнала.

* Поддерживаемые домены: `media_player`
* Рекомендуемые значения режимов: `one`, `two`, `three`, `four`, `five`, `six`, `seven`, `eight`, `nine`, `ten`
* Атрибут в Home Assistant: `source_list`

#### scene
Изменение режима работы светящихся элементов устройства в соответствии с предустановленными темами и сценариями освещения.

* Поддерживаемые домены: `light`
* Значения режимов: `alarm`, `alice`, `candle`, `dinner`, `fantasy`, `garland`, `jungle`, `movie`, `neon`, `night`, `ocean`, `party`, `reading`, `rest`, `romance`, `siren`, `sunrise`, `sunset` (список фиксированный, другими значениями не расширяется)
* Атрибут в Home Assistant: `effect_list`


### Датчики
В УДЯ кроме устройств можно отдавать значения некоторых цифровых датчиков, таких как "температура", "заряд батареи" и других.

**Бинарные датчики (двери, утечка) и события (вибрация, нажатие кнопки) пока в бете и доступны только
ограниченныму кругу лиц ([подробнее...](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event.html)).**

Отдать показания датчика можно несколькими способами:
1. Если датчик представлен атрибутом устройства (например атрибут `water_level` у увлажнителя `humidifer.sample`) -
   достаточно отдать в УДЯ через фильтр только `humidifer.sample`, уровень воды подхватится автоматически в большинстве случаев.
2. Датчик представлен отдельным устройством, значение в state (например `sensor.room_temp` с `device_class: temperature`) -
   достаточно отдать такое устройство через фильтр. Будет работать только в случае если у датчика поддерживаемый `device_class`.
3. Датчик представлен отдельным устройством, но его требуется представить как датчик другого устройства.
   Пример: уровень батареи `sensor.room_temp_battery` включить в датчик с температуры `sensor.room_temp`, или
   влажность в комнате `sensor.bedroom_humidity` включить в увлажнитель `humidifier.bedroom`.
   В этом случае дополнительные датчики и их типы (поле `type`) задаются как элементы списка `properties` основного устройства:
  ```yaml
  yandex_smart_home:
    filter:
      include_entities:
        - humidifier.bedroom
    entity_config:
      humidifier.bedroom:
        properties:
          - type: temperature
            entity: sensor.bedroom_temperature
          - type: humidity
            entity: sensor.bedroom_humidity
          - type: water_level
            entity: sensor.humidifier_level
  ```
  Возможные значения `type`:
  * [Для цифровых датчиков](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/float-instance.html)
  * [Для бинарных датчиков и событий](https://yandex.ru/dev/dialogs/smart-home/doc/concepts/event-instance.html)


### Ограничение уровня громкости
```yaml
yandex_smart_home:
  entity_config:
    media_player.receiver:
      range:
        max: 95
        min: 20
        precision: 2
```


## Уведомления об изменении состояний устройств
Для уведомления УДЯ об актуальном состоянии устройств и датчиков **настоятельно** рекомендуется выполнить настройку службы `notifier`.
Если этого не сделать, УДЯ будет узнавать актуальное состояние только при входе в устройство или обновлении страницы.
Так же однозначно будут проблемы при использовании команд вида "Алиса, вентилятор" (без указания что именно нужно сделать),
так как состояние устройства меняется не только через УДЯ, но и в Home Assistant напрямую.

Кроме передачи состояний `notifier` инициирует обновление списка устройств в УДЯ при перезапуске Home Assistant.
Благодаря этому можно не нажимать "Обновить список устройств" при появлении нового устройства или изменении фильтров,
а достаточно просто перезапустить HA. Обновление происходит в течение 10 - 20 секунд после старта.

Для настройки понадобятся:
* `oauth_token`: Получить по [этой ссылке](https://oauth.yandex.ru/authorize?response_type=token&client_id=c473ca268cd749d3a8371351a8f2bcbd).
  В Яндексе нужно быть авторизованным под тем же аккаунтом, под которым используется УДЯ.
* `skill_id`: "Идентификатор диалога" на вкладке "Общие сведения" в [консоли](https://dialogs.yandex.ru/developer/skills) Яндекс.Диалоги.
* `user_id`: ID пользователя в Home Assistant под которым выполнялась авторизация при привязке диалога.
  Посмотреть в Настройки -> Пользователи -> (выбрать пользователя) -> ID:

  <img src="notifier_user_id.png" width="600">

Добавить в конфигурацию (`xxxx` заменить реальными значениями):
```yaml
yandex_smart_home:
  notifier:
    - oauth_token: XXXXXXXXXXXXXXXXXXXXXXXXXXX
      skill_id: xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx
      user_id: xxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # Если к диалогу предоставлен доступ другому пользователю,
    # или используется несколько разных диалогов - можно добавить несколько записей:
    - oauth_token: XXXXXXXXXXXXXXXXXXXXXXXXXXX
      skill_id: xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx
      user_id: xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```


## Прочие настройки
Задаются через словарь `settings`

| Параметр         | По умолчанию    | Возможные варианты                | Описание                                                 |
| ---------------- | --------------- | --------------------------------- | -------------------------------------------------------- |
| `pressure_unit`  | `mmHg`          | `pa`, `mmHg`, `atm`, `bar`        | Единица измерения для сущностей, передающих давление     |

Пример:
```yaml
yandex_smart_home:
  settings:
    pressure_unit: mmHg
```


## Проблемы
### Яндекс не может достучаться до Home Assistant
* Попробуйте зайти на HA через мобильный интернет (проверяем доступность через DNS).
  Убедитесь, что в браузере отображается неперечёркнутый замок (проверяем доступность по HTTPS).
* Если сертификат настраивался вручную: убедитесь, что используется fullchain сертификат
  (в случае штатного аддона Let's Encrypt он в файле fullchain.cer):
  ```yaml
  http:
    ssl_certificate: /config/acme.sh/YOUR_HA_DOMAIN/fullchain.cer
    ssl_key: /config/acme.sh/YOUR_HA_DOMAIN/YOUR_HA_DOMAIN.key
  ```
* Если DNS запись добавлялась вручную, убедитесь, что для используемого домена нет AAAA записи (должна быть только A).


### Устройство не появляется в УДЯ
* Убедитесь, что устройство не исключено в [фильтрах](#фильтрация-устройств). После изменения фильтров
  требуется полный перезапуск Home Assistant.
* Попробуйте обновить список устройств в УДЯ через [квазар](https://yandex.ru/quasar/iot):
  иконка "Добавить" -> "Устройство умного дома" -> Найти/выбрать ваш диалог -> "Обновить список устройств".
* Если это не помогает, создайте [issue](https://github.com/dmitry-k/yandex_smart_home/issues) или напишите в [чат](https://t.me/yandex_smart_home).
  К сообщению приложите:
  * **ID** и **атрибуты** проблемных устройств. Их можно найти в Панель разработчка (Developer Tools) -> Состояния (States).
  * Конфигурацию `yandex_smart_home` (лучше целиком, или только `filter` и `entity_config` для проблемного устройства).
  * Крайне желательно (но можно не сразу) приложить лог обновления списка устройства в УДЯ. Для его получения:
    1. Зайти в диалог на [dialogs.yandex.ru/developer](https://dialogs.yandex.ru/developer)
    2. Вкладка "Тестирование" -> выбрать "Опубликованная версия"
    3. Нажать иконку "Добавить" -> "Устройство умного дома" -> "Обновить список устройств"
    4. В окне отладки появится:
      ```
      Sending request to provider: GET https://YOUR_HA_DOMAIN/api/yandex_smart_home/v1.0/user/devices
      Got response from provider XXXXX: 200 {"request_id": .... (большой json)
      ```
      Нужно только то, что в строчке Got Response и ниже (лучше файлом).
      Пожалуйста, не включайте строку "Sending request", в ней адрес вашего Home Assistant, пусть эта информация лучше остается в тайне :)


### Ошибка "Что-то пошло не так" при частых действиях
Если попытаться "быстро" управлять устройством, например изменять температуру многократными нажатиями "+", выскочит ошибка:
"Что-то пошло не так. Попробуйте позднее ещё раз".

Это **нормально**. УДЯ ограничивает количество запросов, которые могут придти от пользователя в единицу времени. Нажимайте кнопки медленее :)


### Как отвязать диалог
В некоторых случаях может потребоваться полностью отвязать диалог (навыкк) от УДЯ и удалить все устройства. Это может быть полезно, когда в УДЯ
выгрузили много лишнего из Home Assistant, и удалять руками каждое устройство не хочется.

Для отвязки:
* "Добавить" -> "Устройство умного дома" -> Найти/выбрать ваш диалог.
* Нажать корзинку в правом верхнем углу.
* Поставить галочку "Удалить устройства" и нажать "Отвязать от Яндекса".


## Полезные ссылки
* https://t.me/yandex_smart_home - Чат по компоненту в Телеграме
* https://github.com/AlexxIT/YandexStation - Управление колонками с Алисой из Home Assistant и проброс устройств из УДЯ в Home Assistant
* https://github.com/allmazz/yandex_smart_home_ip - Список IP адресов платформы умного дома Яндекса


## Пример конфигурации
```yaml
yandex_smart_home:
  notifier:
    - oauth_token: AgAAAAAEEo2aYYR7m-CEyS7SEiUJjnKez3v3GZe
      skill_id: d38d4c39-5846-ba53-67acc27e08bc
      user_id: e8701ad48ba05a91604e480dd60899a3
  settings:
    pressure_unit: mmHg
  filter:
    include_domains:
      - switch
      - light
    include_entities:
      - media_player.tv
      - media_player.tv_lg
      - media_player.receiver
    include_entity_globs:
      - sensor.temperature_*
    exclude_entities:
      - light.highlight
    exclude_entity_globs:
      - sensor.weather_*
  entity_config:
    switch.kitchen:
      name: Выключатель
    light.living_room:
      name: Люстра
      modes:
        scene:
          sunrise:
            - Wake up
          alarm:
            - Blink
    media_player.tv_lg:
      channel_set_via_media_content_id: true
    fan.xiaomi_miio_device:
      name: Увлажнитель
      room: Гостинная
      type: devices.types.humidifier
      properties:
        - type: temperature
          entity: sensor.temperature_158d000444c824
        - type: humidity
          attribute: humidity
        - type: water_level
          attribute: depth
    climate.tion_breezer:
      name: Проветриватель
      modes:
        fan_speed:
          auto: [auto]
          min: [1,'1.0']
          low: [2,'2.0']
          medium: [3,'3.0']
          high: [4,'4.0']
          turbo: [5,'5.0']
          max: [6,'6.0']
    media_player.receiver:
      type: devices.types.media_device.receiver
      range:
        max: 95
        min: 20
        precision: 2
    humidifier.bedroom:
      modes:
        program:
          normal:
            - normal
          eco:
            - away
      properties:
        - type: temperature
          entity: sensor.bedroom_temperature
        - type: humidity
          entity: sensor.bedroom_humidity
        - type: water_level
          entity: sensor.humidifier_level
```
