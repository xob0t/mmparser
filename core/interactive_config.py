"""Interactive config maker"""

import json
from pathlib import Path
import inspect
from rich.console import Console
from rich.panel import Panel
from curl_cffi import requests
from InquirerPy import inquirer

from core.parser_url import Parser_url
import core.telegram_utils as telegram_utils
import core.utils as utils

console = Console()

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


def accent(string):
    return f"[bold cyan]{string}[/bold cyan]"


def validate_url(url: str):
    try:
        if not requests.get(url).ok:
            return False
    except:
        return False

    parser = Parser_url(url)
    try:
        parsed_url = parser.parse_input_url(tries=1)
        if parsed_url:
            return parsed_url
        return False
    except Exception as e:
        print(e)
        console.print("[red]Ошибка проверки URL!")
        return False


def save_config_dict(config_dict: dict, name: str):
    try:
        file_name = f"{name}.json"
        with open(file_name, "w", encoding="utf-8") as config_file:
            json.dump(config_dict, config_file, indent=4, ensure_ascii=False)
        return file_name
    except:
        raise Exception(f"Ошибка сохранения конфига {file_name}!")


def create_config():
    console.print("[green]Добро пожаловать в интерактивный конфигуратор mmparser!")
    console.print("[cyan]В квадратных скобках указаны значения по умолчанию")

    user_input = None
    config_dict["job_name"] = ""
    while not config_dict["job_name"]:
        user_input = console.input(
            "URL, который будем парсить. Парсинг всегда начнется с 1 страницы. (Рекомендуемые: товар или поиск):\n"
        )
        if not user_input:
            continue
        console.print("[yellow]Идет проверка url...")
        parsed_input_url = validate_url(user_input)
        if not parsed_input_url:
            console.print(f"[red]URL {user_input} не прошел проверку!")
            continue
        console.print(f"[green]URL {user_input} прошел проверку!")
        search_text = parsed_input_url.get("searchText", {})
        collection_title = (parsed_input_url.get("collection", {}) or {}).get("title")
        merchant = (parsed_input_url.get("merchant", {}) or {}).get("slug")
        unknown = "Не определено"
        config_dict["url"] = user_input
        config_dict["job_name"] = utils.remove_chars(
            search_text or collection_title or merchant or unknown
        )

    use_telegram = inquirer.confirm(
        message="Присылать уведомления в Telegram?", default=True
    ).execute()
    if use_telegram:
        while True:
            console.print(
                "Telegram Bot Token и Telegram Chat Id в формате [bold cyan]token$id[/bold cyan]"
            )
            console.print(
                "Пример: [bold white]633434921:AAErf79oop8XbNNCHAssWKtUGM6QnJnXwWE[cyan]$[/cyan]34278514[/bold white]"
            )
            user_input = console.input()
            console.print("[yellow]Проверяем конфиг...")
            if telegram_utils.validate_credentials(user_input):
                console.print(f"[green]Введенный конфиг: {user_input}")
                config_dict["tg_config"] = user_input
                break
            console.print("[red]Некорректное значение!")

    while True:
        user_input = console.input(f"Название задачи \[{accent(config_dict['job_name'])}]:")or config_dict["job_name"]
        safe_user_input = utils.remove_chars(user_input)
        if not safe_user_input:
            continue
        if safe_user_input == user_input:
            config_dict["job_name"] = safe_user_input
            console.print(f"[green]{config_dict['job_name']}")
            break
        if safe_user_input != user_input:
            console.print(
                "[yellow]Из названия были убраны запрещенные символы, будет использовано:"
            )
            config_dict["job_name"] = safe_user_input
            console.print(f"[green]{config_dict['job_name']}")
            break
        console.print("[red]Не корркетное название")

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

            if (
                choice
                == "Когда в api есть информация, что есть другие предложения, или если ее нет совсем"
            ):
                break
            if choice == "Всегда":
                config_dict["all_cards"] = True
                break
            if choice == "Никогда":
                config_dict["no_cards"] = True
                break
            console.print("[red]Неверный ввод. Попробуйте еще раз.[/red]")
        while True:
            user_input = console.input(
                f"Обрабатывать только товары, название которых совпадает с regex \[{accent('Пропуск')}]:"
            )
            if user_input == "":
                config_dict["include"] = None
                break
            if user_input:
                if utils.validate_regex(user_input):
                    config_dict["include"] = user_input
                    break
                console.print(f'[red]Неверное выражение "{user_input}" ![/red]')
        while True:
            user_input = console.input(
                f"Игнорировать товары, название которых совпадает с regex \[{accent('Пропуск')}]:"
            )
            if user_input == "":
                config_dict["exclude"] = None
                break
            if user_input:
                if utils.validate_regex(user_input):
                    config_dict["exclude"] = user_input
                    break
                console.print(f'[red]Неверное выражение "{user_input}" ![/red]')

    while True:
        user_input = console.input(
            f"Использовать файл с black-листом продавцов? \[{accent('Пропуск')}]:"
        )
        if user_input == "":
            config_dict["blacklist"] = None
            break
        if user_input:
            if Path(user_input).exists():
                config_dict["blacklist"] = user_input
                break
            console.print(f'[red]Файл "{user_input}" не найден![/red]')

    while True:
        user_input = console.input(
            f"Путь к файлу с cookies в формате JSON (Cookie-Editor - Export Json) \[{accent('Пропуск')}]:"
        )
        if user_input == "":
            config_dict["cookie_file_path"] = None
            break
        if Path(user_input).exists():
            if utils.read_json_file(user_input):
                console.print(f"[green]Файл найден: {user_input}")
                config_dict["cookie_file_path"] = user_input
                break
            console.print(f"[red]Ошибка чтения cookies из файла {user_input}!")
        console.print(f"[red]Файл {user_input} не найден")

    if config_dict["cookie_file_path"]:
        config_dict["address"] = console.input(
            f"Адрес, будет использовано первое сопадение. \[{accent('Адрес из cookies')}]:"
        )
    else:
        config_dict["address"] = console.input(
            f"Адрес, будет использовано первое сопадение. \[{accent('Москва')}]:"
        )

    if config_dict["tg_config"]:
        while True:
            user_input = console.input(
                f"Если цена товара равна или ниже данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:"
            )
            if user_input == "":
                config_dict["price_value_alert"] = None
                break
            if user_input:
                num = utils.convert_float(user_input)
                if num:
                    config_dict["price_value_alert"] = num
                    break
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(
                f"Если цена-бонусы товара равна или ниже данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:"
            )
            if user_input == "":
                config_dict["price_bonus_value_alert"] = None
                break
            if user_input:
                num = utils.convert_float(user_input)
                if num:
                    config_dict["price_bonus_value_alert"] = num
                    break
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(
                f"Если количество бонусов товара равно или выше данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:"
            )
            if user_input == "":
                config_dict["bonus_value_alert"] = None
                break
            if user_input:
                num = utils.convert_float(user_input)
                if num:
                    config_dict["bonus_value_alert"] = num
                    break
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(
                f"Если процент бонусов товара равен или выше данного значения, уведомлять в TG \[{accent('Не уведомлять')}]:"
            )
            if user_input == "":
                config_dict["bonus_percent_alert"] = None
                break
            if user_input:
                num = utils.convert_float(user_input)
                if num:
                    config_dict["bonus_percent_alert"] = num
                    break
                console.print("[red]Неверный ввод![/red]")
        while True:
            user_input = console.input(
                f"Время в часах, через которое подходящий по параметрам уведомлений товар будет повторно отправлен в TG \[{accent(config_dict['alert_repeat_timeout'])}]:"
            )
            if user_input == "":
                break
            if user_input:
                num = utils.convert_float(user_input)
                if num:
                    config_dict["alert_repeat_timeout"] = num
                    break
                console.print("[red]Неверный ввод![/red]")

    choice = inquirer.select(
        message="Использовать прокси?",
        choices=["Нет", "Из строки (один)", "Из файла (список)"],
    ).execute()

    if choice == "Из строки (один)":
        while True:
            user_input = console.input(
                "Введите строку прокси в формате protocol://username:password@ip:port:"
            )
            if user_input:
                if utils.proxy_format_check(user_input):
                    config_dict["proxy"] = user_input
                    break
                console.print("[red]Неверный ввод![/red]")

    if choice == "Из файла (список)":
        while True:
            user_input = console.input(
                "Путь к файлу со списком прокси в формате protocol://username:password@ip:port:"
            )
            path_is_valid = Path(user_input).exists()
            if path_is_valid:
                console.print(f"[green]Файл найден: {user_input}")
                config_dict["proxy_list"] = user_input
                break
            console.print("[red]Файл не найден![/red]")

    if config_dict["cookie_file_path"] and config_dict["tg_config"]:
        config_dict["account_alert"] = inquirer.confirm(
            message="Если вход в аккаунт не выполнен, присылать уведомление в Telegram?",
            default=True,
        ).execute()

    if config_dict["proxy"]:
        config_dict["allow_direct"] = inquirer.confirm(
            message="Использовать прямое соединение параллельно с прокси для ускорения работы в многопотоке?",
            default=True,
        ).execute()

    while True:
        user_input = console.input(
            f"Количество потоков. По умолчанию: 1 на каждое соединиение \[{accent('По умолчанию')}]:"
        )
        if user_input == "":
            break
        if user_input:
            num = utils.convert_float(user_input)
            if num:
                config_dict["threads"] = int(num)
                break
            console.print("[red]Неверный ввод![/red]")

    while True:
        user_input = (
            console.input(
                f"Задержка между запросами в секундах для одного соединения \[{accent(config_dict['delay'])}]:"
            )
            or config_dict["delay"]
        )
        if user_input:
            num = utils.convert_float(user_input)
            if num:
                config_dict["delay"] = num
                break
            console.print("[red]Неверный ввод![/red]")

    while True:
        user_input = (
            console.input(
                f"Пауза в секундах в случае ошибки для одного соединения \[{accent(config_dict['error_delay'])}]:"
            )
            or config_dict["error_delay"]
        )
        if user_input:
            num = utils.convert_float(user_input)
            if num:
                config_dict["error_delay"] = num
                break
            console.print("[red]Неверный ввод![/red]")

    config_dict["use_merchant_blacklist"] = inquirer.confirm(
        message="Использовать черный список продавцов с ограничением на списание бонусов?",
        default=False,
    ).execute()

    file_name = save_config_dict(config_dict, config_dict["job_name"])
    console.print("[green]Настройка завершена!")
    console.print(
        f'Вы можете запустить парсер командой [bold white]mmparser -cfg "{file_name}"[/bold white]'
    )
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
            alert_repeat_timeout = config_dict["alert_repeat_timeout"],
            threads=config_dict["threads"],
            delay=config_dict["delay"],
            error_delay=config_dict["error_delay"],
            log_level=config_dict["log_level"],
        )
        parser_instance.parse()
