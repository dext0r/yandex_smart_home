# Выбор типа подключения
Поменять тип подключения у существующей интеграции невозможно. Однако, можно добавить новую интеграцию с желаемым типом без удаления старой.

Примерный набор шагов для перехода с прямого подключения на облачное или наоборот:

* [Добавьте](../install/integration.md) новую интеграцию с желаемым типом подключения
* Привяжите новую интеграцию через приложение [Дом с Алисой](https://ya.cc/iot_app)
* Устройства уникальны в рамках навыка (производителя), поэтому после привязки новой интеграции появятся "дубли" устройств: одно устройство на "старом" навыке, другое - на "новом"
* Проверьте, как управляются устройства на новом навыке и если проблем не выявлено, то старый навык можно [отвязать](../quasar.md#unlink) с удалением всех устройств

## Какой тип подключения лучше? { id=compare }

|                        | Плюсы                                                                                                                                                                                     | Минусы                                                                                                                                                                                                                                                         |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Облачное<br>Yaha Cloud | <ul><li>Просто работает</li><li>Меньшее время отклика чем у прямого на значительном удалении от Москвы[^1]</li></ul>                                                                      | <ul><li>Зависит от доступности[^2] дополнительного "облачного" сервера между Home Assistant и УДЯ</li><li>Для параноиков: устройства видны не только Яндексу, но и владельцу "облачного" сервера[^3]</li></ul>                                                 |
| Прямое                 | <ul><li>Нет зависимости от дополнительного "облачного" сервера между Home Assistant и УДЯ</li><li>Для параноиков: никто, кроме Яндекса не сможет контролировать ваши устройства</li></ul> | <ul><li>Необходимо постоянно поддерживать доступ к Home Assistant из интернета (перевыпуск сертификатов, настройка динамического DNS и т.п.)</li><li>Сложность настройки</li><li>Чем вы дальше от Москвы - тем больше будет время отклика на команды</li></ul> |

!!! warning "Помните, что пользуяюсь любым облачным сервисом, будь то "Умный дом Яндекса" или навык "Yaha Cloud", вы даёте этому сервису права на контроль всех поддерживаемых устройств в Home Assistant."

[^1]: Облачное подключение держит соединение постоянно открытым. Прямое - на каждый запрос устанавливает отдельное соединение с TLS-хедшейком, время которого значительно растёт с увеличением пинга.
[^2]: [Статистика доступности](https://stats.uptimerobot.com/QX83nsXBWW)
[^3]: Но управлять он ими не будет, ему это просто не нужно :) Все данные на "облачном" обезличены, а проходящий трафик зашифрован.
