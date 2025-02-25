"""Interactive config maker"""

import json
from pathlib import Path
import inspect
from rich.console import Console
from rich.panel import Panel
from curl_cffi import requests
from InquirerPy import inquirer

from .parser_url import Parser_url
from . import telegram, utils, exceptions

console = Console(highlight=False)


def accent(string: str) -> str:
    return f"[bold cyan]{string}[/bold cyan]"


def validate_url(url: str, config_dict: dict) -> dict | None:
    """Проверка URL"""
    try:
        if not requests.head(url).ok:
            return
    except Exception:
        return
    parser = Parser_url(url, cookie_file_path=config_dict["cookie_file_path"])
    try:
        return parser.parse_input_url(tries=1)
    except Exception as e:
        console.print(e)
        console.print("[red]Ошибка проверки URL!")
        return


def save_config_dict(config_dict: dict, name: str) -> str:
    """Сохранить конфиг в json"""
    try:
        file_name = f"{name}.json"
        with open(file_name, "w", encoding="utf-8") as config_file:
            json.dump(config_dict, config_file, indent=4, ensure_ascii=False)
        return file_name
    except Exception as exc:
        raise exceptions.ConfigError(f"Ошибка сохранения конфига {name}!") from exc


def get_job_name(config_dict: dict) -> None:
    """Определить название задачи"""
    while True:
        user_input = console.input("URL, который будем парсить. Парсинг всегда начнется с 1 страницы. (Рекомендуемые: товар или поиск):\n")
        if not user_input:
            continue
        console.print("[yellow]Идет проверка url...")
        parsed_input_url = validate_url(user_input, config_dict)
        if not parsed_input_url:
            console.print(f"[red]URL {user_input} не прошел проверку!")
            continue
        console.print(f"[green]URL {user_input} прошел проверку!")
        search_text = parsed_input_url.get("searchText", {})
        collection_title = (parsed_input_url.get("collection", {}) or {}).get("title")
        merchant = (parsed_input_url.get("merchant", {}) or {}).get("slug")
        unknown = "Не определено"
        config_dict["url"] = user_input
        config_dict["job_name"] = utils.remove_chars(search_text or collection_title or merchant or unknown)
        break


def get_telegram_config(config_dict: dict) -> None:
    """Получить конфигурацию Telegram из введенных пользователем данных"""
    use_telegram = inquirer.confirm(message="Присылать уведомления в Telegram?", default=True).execute()
    if use_telegram:
        while True:
            console.print("Telegram Bot Token и Telegram Chat Id в формате [bold cyan]token$id[/bold cyan]")
            console.print("Пример: [bold white]633434921:AAErf79oop8XbNNCHAssWKtUGM6QnJnXwWE[cyan]$[/cyan]34278514[/bold white]")
            user_input = console.input()
            console.print("[yellow]Проверяем конфиг...")
            if telegram.validate_tg_credentials(user_input):
                console.print(f"[green]Введенный конфиг: {user_input}")
                config_dict["tg_config"] = user_input
                break
            console.print("[red]Некорректное значение!")


def get_parsing_config(config_dict: dict) -> None:
    """Получить конфигурацию парсинга из введенных пользователем данных"""
    if "/details/" not in config_dict["url"]:
        while True:
            warning = """[yellow]Данные о наличии других предложений у товара доступны только в поиске.
                        При просмотре каталога для каждого товара обычно показываются несколько предложений, но не все!
                        Всегда рекомендуется использовать поисковые ссылки.
                        Общая рекомендация:
                        Если ссылка поисковая - выбираем пункт 1
                        Если ссылка на каталог, без поискового запроса - выбираем пункт 2
                        Если вам нужна только выдача поиска или каталога и ничего более - пункт 3"""
            warning = inspect.cleandoc(warning)
            panel = Panel(
                warning,
                title="[red]Особоенность api MM",
                border_style="cyan",
                padding=(1, 1),
                title_align="left",
            )
            console.print(panel)

            choice = inquirer.select(
                message="Парсить карточки товаров:",
                choices=[
                    "Когда в api есть информация, что есть другие предложения, или если ее нет совсем",
                    "Всегда",
                    "Никогда",
                ],
            ).execute()

            if choice == "Когда в api есть информация, что есть другие предложения, или если ее нет совсем":
                break
            if choice == "Всегда":
                config_dict["all_cards"] = True
                break
            if choice == "Никогда":
                config_dict["no_cards"] = True
                break
            console.print("[red]Неверный ввод. Попробуйте еще раз.[/red]")
        while True:
            user_input = console.input(f"Обрабатывать только товары, название которых совпадает с regex \[{accent('Пропуск')}]:")
            if user_input == "":
                config_dict["include"] = None
                break
            if user_input:
                if utils.validate_regex(user_input):
                    config_dict["include"] = user_input
                    break
                console.print(f'[red]Неверное выражение "{user_input}" ![/red]')
        while True:
            user_input = console.input(f"Игнорировать товары, название которых совпадает с regex \[{accent('Пропуск')}]:")
            if user_input == "":
                config_dict["exclude"] = None
                break
            if user_input:
                if utils.validate_regex(user_input):
                    config_dict["exclude"] = user_input
                    break
                console.print(f'[red]Неверное выражение "{user_input}" ![/red]')


def get_blacklist_config(config_dict: dict) -> None:
    """Получить конфигурацию черного списка из введенных пользователем данных"""
    while True:
        user_input = console.input(f"Использовать файл с black-листом продавцов? \[{accent('Пропуск')}]:")
        if user_input == "":
            config_dict["blacklist"] = None
            break
        if user_input:
            if Path(user_input).exists():
                config_dict["blacklist"] = user_input
                break
            console.print(f'[red]Файл "{user_input}" не найден![/red]')


def get_cookie_config(config_dict: dict) -> None:
    """Получить конфигурацию cookie из пользовательского ввода"""
    while True:
        user_input = console.input("Путь к файлу с cookies в формате JSON (Cookie-Editor - Export Json):")
        if not Path(user_input).exists():
            console.print(f"[red]Файл {user_input} не найден")
            continue
        if utils.read_json_file(user_input):
            console.print(f"[green]Файл найден: {user_input}")
            config_dict["cookie_file_path"] = user_input
            break
        console.print(f"[red]Ошибка чтения cookies из файла {user_input}!")


def get_address_config(config_dict: dict) -> None:
    """Получить конфигурацию адреса из введенных пользователем данных"""
    if config_dict["cookie_file_path"]:
        config_dict["address"] = console.input(f"Адрес, будет использовано первое сопадение. \[{accent('Адрес из cookies')}]:")
    else:
        config_dict["address"] = console.input(f"Адрес, будет использовано первое сопадение. \[{accent('Москва')}]:")


def get_alert_config(config_dict: dict) -> None:
    """Получить конфигурацию оповещения из пользовательского ввода"""
    if config_dict["tg_config"]:
        while True:
            user_input = console.input(f"Если цена товара равна или ниже данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:")
            if user_input == "":
                config_dict["price_value_alert"] = None
                break
            try:
                config_dict["price_value_alert"] = float(user_input)
                break
            except ValueError:
                console.print("[red]Неверный ввод![/red]")

        while True:
            user_input = console.input(f"Если цена-бонусы товара равна или ниже данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:")
            if user_input == "":
                config_dict["price_bonus_value_alert"] = None
                break
            try:
                config_dict["price_bonus_value_alert"] = float(user_input)
                break
            except ValueError:
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(f"Если количество бонусов товара равно или выше данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:")
            if user_input == "":
                config_dict["bonus_value_alert"] = None
                break
            try:
                config_dict["bonus_value_alert"] = float(user_input)
                break
            except ValueError:
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(f"Если процент бонусов товара равен или выше данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:")
            if user_input == "":
                config_dict["bonus_percent_alert"] = None
                break
            try:
                config_dict["bonus_percent_alert"] = float(user_input)
                break
            except ValueError:
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(f"Время в часах, через которое подходящий по параметрам уведомлений товар будет повторно отправлен в TG \[{accent(config_dict['alert_repeat_timeout'])}]:")
            if user_input == "":
                config_dict["alert_repeat_timeout"] = None
                break
            try:
                config_dict["alert_repeat_timeout"] = float(user_input)
                break
            except ValueError:
                console.print("[red]Неверный ввод![/red]")


def get_proxy_config(config_dict: dict) -> None:
    """Получить конфигурацию прокси из введенных пользователем данных"""
    choice = inquirer.select(
        message="Использовать прокси?",
        choices=["Нет", "Из строки (один)", "Из файла (список)"],
    ).execute()

    if choice == "Из строки (один)":
        while True:
            user_input = console.input("Введите строку прокси в формате protocol://username:password@ip:port:")
            if user_input:
                if utils.proxy_format_check(user_input):
                    config_dict["proxy"] = user_input
                    break
                console.print("[red]Неверный ввод![/red]")

    if choice == "Из файла (список)":
        while True:
            user_input = console.input("Путь к файлу со списком прокси в формате protocol://username:password@ip:port:")
            if Path(user_input).exists():
                console.print(f"[green]Файл найден: {user_input}")
                config_dict["proxy_file_path"] = user_input
                break
            console.print("[red]Файл не найден![/red]")


def get_account_alert_config(config_dict: dict) -> None:
    """Получить конфигурацию оповещения по ошибкам учетной записи из введенных пользователем данных"""
    if config_dict["cookie_file_path"] and config_dict["tg_config"]:
        config_dict["account_alert"] = inquirer.confirm(
            message="Если вход в аккаунт не выполнен, присылать уведомление в Telegram?",
            default=True,
        ).execute()


def get_performance_config(config_dict: dict) -> None:
    """Получить конфигурацию производительности из введенных пользователем данных"""
    while True:
        user_input = console.input(f"Количество потоков. По умолчанию: 1 на каждое соединиение \[{accent('По умолчанию')}]:")
        if user_input == "":
            break
        try:
            config_dict["threads"] = float(user_input)
            break
        except ValueError:
            console.print("[red]Неверный ввод![/red]")

    while True:
        user_input = console.input(f"Задержка между запросами в секундах для одного соединения \[{accent(config_dict['delay'])}]:") or config_dict["delay"]
        try:
            config_dict["delay"] = float(user_input)
            break
        except ValueError:
            console.print("[red]Неверный ввод![/red]")

    while True:
        user_input = console.input(f"Пауза в секундах в случае ошибки для одного соединения \[{accent(config_dict['error_delay'])}]:") or config_dict["error_delay"]
        try:
            config_dict["error_delay"] = float(user_input)
            break
        except ValueError:
            console.print("[red]Неверный ввод![/red]")


def get_merchant_blacklist_config(config_dict: dict) -> None:
    """Получить конфигурацию черного списка продавцов из введенных пользователем данных"""
    config_dict["use_merchant_blacklist"] = inquirer.confirm(
        message="Использовать черный список продавцов с ограничением на списание бонусов?",
        default=False,
    ).execute()


def create_config():
    console.print("[green]Добро пожаловать в интерактивный конфигуратор mmparser!")
    console.print("[cyan]В квадратных скобках указаны значения по умолчанию")

    config_dict = {
        "url": "",
        "job_name": "Не определено",
        "include": "",
        "exclude": "",
        "blacklist": "",
        "all_cards": False,
        "no_cards": False,
        "cookie_file_path": "",
        "address": "",
        "proxy": "",
        "allow_direct": True,
        "proxy_file_path": "",
        "tg_config": "",
        "price_value_alert": "",
        "price_bonus_value_alert": "",
        "bonus_value_alert": "",
        "bonus_percent_alert": "",
        "alert_repeat_timeout": 0,
        "use_merchant_blacklist": False,
        "threads": 0,
        "delay": 1.8,
        "error_delay": 5,
        "account_alert": False,
        "log_level": "INFO",
    }

    get_cookie_config(config_dict)
    get_job_name(config_dict)
    get_telegram_config(config_dict)
    get_parsing_config(config_dict)
    get_blacklist_config(config_dict)
    get_address_config(config_dict)
    get_alert_config(config_dict)
    get_proxy_config(config_dict)
    get_account_alert_config(config_dict)
    get_performance_config(config_dict)
    get_merchant_blacklist_config(config_dict)

    file_name = save_config_dict(config_dict, config_dict["job_name"])
    console.print("[green]Настройка завершена!")
    console.print(f'Вы можете запустить парсер командой [bold white]mmparser -config "{file_name}"[/bold white]')
    run = inquirer.confirm(message="Запустить сейчас?", default=True).execute()
    if run:
        console.print("[cyan]Запускаем парсер...")
        parser_instance = Parser_url(
            url=config_dict["url"],
            job_name=config_dict["job_name"],
            include=config_dict["include"],
            exclude=config_dict["exclude"],
            blacklist=config_dict["blacklist"],
            all_cards=config_dict["all_cards"],
            no_cards=config_dict["no_cards"],
            cookie_file_path=config_dict["cookie_file_path"],
            address=config_dict["address"],
            proxy=config_dict["proxy"],
            allow_direct=config_dict["allow_direct"],
            proxy_file_path=config_dict["proxy_file_path"],
            tg_config=config_dict["tg_config"],
            price_value_alert=config_dict["price_value_alert"],
            price_bonus_value_alert=config_dict["price_bonus_value_alert"],
            bonus_value_alert=config_dict["bonus_value_alert"],
            bonus_percent_alert=config_dict["bonus_percent_alert"],
            alert_repeat_timeout=config_dict["alert_repeat_timeout"],
            use_merchant_blacklist=config_dict["use_merchant_blacklist"],
            threads=config_dict["threads"],
            delay=config_dict["delay"],
            error_delay=config_dict["error_delay"],
            log_level=config_dict["log_level"],
        )
        parser_instance.parse()
