# mmparser
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/xob0t/mmparser/total)
## Купить
Парсер открыт, но не бесплатен :)
Купить - [Yoomoney](https://yoomoney.ru/fundraise/122C5TB8IKI.240412)

## Особенности
* Работа через api
* Парсинг карточек товаров при парсинге каталога/поиска
* Сохраниние результатов в sqlite БД
* Запуск с конфигом и/или аргументами
* Интерактивное создание конфигов
* Поддержка прокси строкой или списком из файла
* Поддержка ссылок каталога, поиска, и карточек товара
* Парсиг одной ссылки в многопотоке, по потоку на прокси/соединение
* Импорт cookies экспортированних в формате Json с помошью [Cookie-Editor](https://chrome.google.com/webstore/detail/hlkenndednhfkekhgcdicdfddnkalmdm)
* Блеклист продавцов
* Regex фильтр по именам товаров
* Уведомления в телеграм по заданным параметрам
* Позволяет выставить время, через которое подходящий по параметрам уведомлений товар будет повторно отправлен в TG

## Установка:
 1. Уставновить [Python](https://www.python.org/downloads/), в установщике поставить галочку "Добавить в PATH"
 2. [Скачать парсер](https://github.com/xob0t/mmparser/releases/latest/)
 3. Устновить парсер: `pip install mmparser_vX.X.X.zip`

## Пример использования
### <span style="color:yellow">Кавычки обязательны!</span>
### Просто парсинг url
`mmparser "https://megamarket.ru/catalog/?q=%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA&suggestionType=frequent_query#?filters=%7B%2288C83F68482F447C9F4E401955196697%22%3A%7B%22min%22%3A229028%2C%22max%22%3A307480%7D%2C%22A03364050801C25CD0A856C734F74FE9%22%3A%5B%221%22%5D%7D&sort=1"`
### Без аргументов, создание конфига
`mmparser`
### Запуск с конфигом
`mmparser -cfg "config.json"`
### Запуск с конфигом и аргументами
`mmparser -cfg "config.json" --allow-direct`

## Чтение результатов
При запуске парсер создаст в рабочей директории файл storage.sqlite

Это sqlite база данных, очень удобно читается в [DB Browser for SQLite](https://sqlitebrowser.org/)

## Запуск по расписанию на windows:
[Планировщик заданий Windows для начинающих](https://remontka.pro/windows-task-scheduler/)

#

```
usage: mmparser [-h] [-job JOB_NAME] [-cfg CONFIG] [-i INCLUDE] [-e EXCLUDE] [-b BLACKLIST] [-ac] [-nc] [-c COOKIES]
                [-aa ACCOUNT_ALERT] [-a ADDRESS] [-p PROXY] [-pl PROXY_LIST] [-ad] [-tc TG_CONFIG]
                [-pva PRICE_VALUE_ALERT] [-pbva PRICE_BONUS_VALUE_ALERT] [-bva BONUS_VALUE_ALERT]
                [-bpa BONUS_PERCENT_ALERT] [-art ALERT_REPEAT_TIMEOUT] [-t THREADS] [-d DELAY] [-ed ERROR_DELAY]
                [-log {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                [url]

positional arguments:
  url                   URL для парсинга

options:
  -h, --help            show this help message and exit
  -job JOB_NAME, --job-name JOB_NAME
                        Название задачи, без этого параметра будет автоопределено
  -cfg CONFIG, --config CONFIG
                        Путь к конфигу парсера
  -i INCLUDE, --include INCLUDE
                        Парсить только товары, название которых совпадает с выражением
  -e EXCLUDE, --exclude EXCLUDE
                        Пропускать товары, название которых совпадает с выражением
  -b BLACKLIST, --blacklist BLACKLIST
                        Путь к файлу со списком игнорируемых продавцов
  -ac, --all-cards      Всегда парсить карточки товаров
  -nc, --no-cards       Не парсить карточки товаров
  -c COOKIES, --cookies COOKIES
                        Путь к файлу с cookies в формате JSON (Cookie-Editor - Export Json)
  -aa ACCOUNT_ALERT, --account-alert ACCOUNT_ALERT
                        Если вы используйте cookie, и вход в аккаунт не выполнен, присылать уведомление в TG
  -a ADDRESS, --address ADDRESS
                        Адрес, будет использовано первое сопадение
  -p PROXY, --proxy PROXY
                        Строка прокси в формате protocol://username:password@ip:port
  -pl PROXY_LIST, --proxy-list PROXY_LIST
                        Путь к файлу с прокси в формате protocol://username:password@ip:port
  -ad, --allow-direct   Использовать прямое соединение параллельно с прокси для ускорения работы в многопотоке
  -tc TG_CONFIG, --tg-config TG_CONFIG
                        Telegram Bot Token и Telegram Chat Id в формате token$id
  -pva PRICE_VALUE_ALERT, --price-value-alert PRICE_VALUE_ALERT
                        Если цена товара равна или ниже данного значения, уведомлять в TG
  -pbva PRICE_BONUS_VALUE_ALERT, --price-bonus-value-alert PRICE_BONUS_VALUE_ALERT
                        Если цена-бонусы товара равна или ниже данного значения, уведомлять в TG
  -bva BONUS_VALUE_ALERT, --bonus-value-alert BONUS_VALUE_ALERT
                        Если количество бонусов товара равно или выше данного значения, уведомлять в TG
  -bpa BONUS_PERCENT_ALERT, --bonus-percent-alert BONUS_PERCENT_ALERT
                        Если процент бонусов товара равно или выше данного значения, уведомлять в TG
  -art ALERT_REPEAT_TIMEOUT, --alert-repeat-timeout ALERT_REPEAT_TIMEOUT
                        Если походящий по параметрам товар уже был отправлен в TG, повторно уведомлять по истечении
                        заданного времени, в часах
  -t THREADS, --threads THREADS
                        Количество потоков. По умолчанию: 1 на каждое соединиение
  -d DELAY, --delay DELAY
                        Задержка между запросами в секундах при работе в одном потоке. По умолчанию: 1.8
  -ed ERROR_DELAY, --error-delay ERROR_DELAY
                        Задержка между запосами в секундах в случае ошибки при работе в одном потоке. По умолчанию: 5
  -log {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Уровень лога. По умолчанию: INFO
```
