#

```
         ____ ___  ____ ___  ____  ____  _____________  _____
        / __ `__ \/ __ `__ \/ __ \/ __ `/ ___/ ___/ _ \/ ___/
       / / / / / / / / / / / /_/ / /_/ / /  (__  )  __/ /
      /_/ /_/ /_/_/ /_/ /_/ .___/\__,_/_/  /____/\___/_/
                         /_/
```

![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/xob0t/mmparser/total)

## Сказать спасибо автору - [Yoomoney](https://yoomoney.ru/to/410018051351692)

Связь со мной [tg](https://t.me/mobate) - Индивидуальной поддержкой бесплатно не занимаюсь

### Демо ускорено в 10 раз

[![asciicast](https://asciinema.org/a/fYFj0HVO16r16vaK1reEa4617.svg)](https://asciinema.org/a/fYFj0HVO16r16vaK1reEa4617)

<details>
  <summary>Пример уведомления Telegram</summary>
  <img src="media/tg_demo.jpg">
</details>

## Особенности

- Работа через api
- Парсинг карточек товаров при парсинге каталога/поиска
- Сохранение результатов в sqlite БД
- Запуск с конфигом и/или аргументами
- Интерактивное создание конфигов
- Поддержка прокси строкой или списком из файла
- Поддержка ссылок каталога, поиска, и карточек товара
- Парсинг одной ссылки в многопотоке, по потоку на прокси/соединение
- Импорт cookies экспортированних в формате Json с помошью [Cookie-Editor](https://chrome.google.com/webstore/detail/hlkenndednhfkekhgcdicdfddnkalmdm)
- Блеклист продавцов
- Regex фильтр по именам товаров
- Уведомления в телеграм по заданным параметрам
- Позволяет выставить время, через которое подходящий по параметрам уведомлений товар будет повторно отправлен в TG
- Использование блеклиста продавцов с ограничением на списание бонусов
- Сссылки на каталог супермаркетов не поддерживаются :(

## Установка:

1.  Установить [Python](https://www.python.org/downloads/), в установщике поставить галочку "Добавить в PATH"
2.  [Скачать парсер](https://github.com/xob0t/mmparser/releases/latest/download/mmparser.zip)
3.  Установить парсер: `pip install mmparser.zip -U`

## Пример использования

### <span style="color:yellow">Кавычки обязательны!</span>

### Просто парсинг url

```
mmparser "https://megamarket.ru/catalog/?q=%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA&suggestionType=frequent_query#?filters=%7B%2288C83F68482F447C9F4E401955196697%22%3A%7B%22min%22%3A229028%2C%22max%22%3A307480%7D%2C%22A03364050801C25CD0A856C734F74FE9%22%3A%5B%221%22%5D%7D&sort=1"
```

### Парсинг url с cookie файлом

```
mmparser -cookies "cookies.json" "https://megamarket.ru/catalog/details/processor-amd-ryzen-5-5600-am4-oem-600008773764/"
```

### Без аргументов, создание конфига

```
mmparser
```

### Запуск с конфигом

```
mmparser -config "config.json"
```

## Чтение результатов

При запуске парсер создаст в рабочей директории файл storage.sqlite

Это sqlite база данных, очень удобно читается в [DB Browser for SQLite](https://sqlitebrowser.org/)

## Запуск по расписанию на windows:

[Планировщик заданий Windows для начинающих](https://remontka.pro/windows-task-scheduler/)

#

```
mmparser [-h] [-job-name JOB_NAME] [-config CONFIG] [-include INCLUDE] [-exclude EXCLUDE] [-blacklist BLACKLIST] [-all-cards] [-no-cards] [-cookies COOKIES] [-account-alert ACCOUNT_ALERT] [-address ADDRESS] [-proxy PROXY] [-proxy-list PROXY_LIST] [-allow-direct] [-tg-config TG_CONFIG] [-price-value-alert PRICE_VALUE_ALERT]
                [-price-bonus-value-alert PRICE_BONUS_VALUE_ALERT] [-bonus-value-alert BONUS_VALUE_ALERT] [-bonus-percent-alert BONUS_PERCENT_ALERT] [-use-merchant-blacklist] [-alert-repeat-timeout ALERT_REPEAT_TIMEOUT] [-threads THREADS] [-delay DELAY] [-error-delay ERROR_DELAY] [-log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                [url]

positional arguments:
  url                   URL для парсинга

options:
  -h, --help            show this help message and exit
  -job-name JOB_NAME    Название задачи, без этого параметра будет автоопределено
  -config CONFIG        Путь к конфигу парсера
  -include INCLUDE      Парсить только товары, название которых совпадает с выражением
  -exclude EXCLUDE      Пропускать товары, название которых совпадает с выражением
  -blacklist BLACKLIST  Путь к файлу со списком игнорируемых продавцов
  -all-cards            Всегда парсить карточки товаров
  -no-cards             Не парсить карточки товаров
  -cookies COOKIES      Путь к файлу с cookies в формате JSON (Cookie-Editor - Export Json)
  -account-alert ACCOUNT_ALERT
                        Если вы используйте cookie, и вход в аккаунт не выполнен, присылать уведомление в TG
  -address ADDRESS      Адрес, будет использовано первое сопадение
  -proxy PROXY          Строка прокси в формате protocol://username:password@ip:port
  -proxy-list PROXY_LIST
                        Путь к файлу с прокси в формате protocol://username:password@ip:port
  -allow-direct         Использовать прямое соединение параллельно с прокси для ускорения работы в многопотоке
  -tg-config TG_CONFIG  Telegram Bot Token и Telegram Chat Id в формате token$id
  -price-value-alert PRICE_VALUE_ALERT
                        Если цена товара равна или ниже данного значения, уведомлять в TG
  -price-bonus-value-alert PRICE_BONUS_VALUE_ALERT
                        Если цена-бонусы товара равна или ниже данного значения, уведомлять в TG
  -bonus-value-alert BONUS_VALUE_ALERT
                        Если количество бонусов товара равно или выше данного значения, уведомлять в TG
  -bonus-percent-alert BONUS_PERCENT_ALERT
                        Если процент бонусов товара равно или выше данного значения, уведомлять в TG
  -use-merchant-blacklist
                        Использовать черный список продавцов с ограничением на списание бонусов
  -alert-repeat-timeout ALERT_REPEAT_TIMEOUT
                        Если походящий по параметрам товар уже был отправлен в TG, повторно уведомлять по истечении заданного времени, в часах
  -threads THREADS      Количество потоков. По умолчанию: 1 на каждое соединиение
  -delay DELAY          Задержка между запросами в секундах при работе в одном потоке. По умолчанию: 1.8
  -error-delay ERROR_DELAY
                        Задержка между запосами в секундах в случае ошибки при работе в одном потоке. По умолчанию: 5
  -log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Уровень лога. По умолчанию: INFO
```
