"""cli"""
import argparse
from pathlib import Path
from core.parser_url import Parser_url
from core.interactive_config import create_config
from core.utils import read_json_file, print_logo

def run_url_parser(args, config = {}):
    parser_instance = Parser_url(
        url = config.get('url') or args.url,
        job_name = config.get('job_name') or args.job_name,
        include = config.get('include') or args.include,
        exclude = config.get('exclude') or args.exclude,
        blacklist = config.get('blacklist') or args.blacklist,
        all_cards = config.get('all_cards') or args.all_cards,
        no_cards = config.get('no_cards') or args.no_cards,
        cookie_file_path = config.get('cookie_file_path') or args.cookies,
        address = config.get('address') or args.address,
        proxy = config.get('proxy') or args.proxy,
        allow_direct = config.get('allow_direct') or args.allow_direct,
        proxy_file_path = config.get('proxy_file_path') or args.proxy_list,
        tg_config = config.get('tg_config') or args.tg_config,
        price_value_alert = config.get('price_value_alert') or args.price_value_alert,
        price_bonus_value_alert = config.get('price_bonus_value_alert') or args.price_bonus_value_alert,
        bonus_value_alert = config.get('bonus_value_alert') or args.bonus_value_alert,
        bonus_percent_alert = config.get('bonus_percent_alert') or args.bonus_percent_alert,
        alert_repeat_timeout = config.get('alert_repeat_timeout') or args.alert_repeat_timeout,
        use_merchant_blacklist = config.get('use_merchant_blacklist') or args.use_merchant_blacklist,
        threads = config.get('threads') or args.threads,
        delay = config.get('delay') or args.delay,
        error_delay = config.get('error_delay') or args.error_delay,
        log_level = config.get('log_level') or args.log_level
    )
    parser_instance.parse()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", type=str, help="URL для парсинга")
    parser.add_argument("-job", "--job-name", type=str, help="Название задачи, без этого параметра будет автоопределено")
    parser.add_argument("-cfg", "--config", type=str, help="Путь к конфигу парсера")
    parser.add_argument("-i", "--include", type=str, help="Парсить только товары, название которых совпадает с выражением")
    parser.add_argument("-e", "--exclude", type=str, help="Пропускать товары, название которых совпадает с выражением")
    parser.add_argument("-b", "--blacklist", type=str, help="Путь к файлу со списком игнорируемых продавцов")
    parser.add_argument("-ac", "--all-cards", action='store_true', help="Всегда парсить карточки товаров")
    parser.add_argument("-nc", "--no-cards", action='store_true', help="Не парсить карточки товаров")
    parser.add_argument("-c", "--cookies", type=str, help="Путь к файлу с cookies в формате JSON (Cookie-Editor - Export Json)")
    parser.add_argument("-aa", "--account-alert", type=str, help="Если вы используйте cookie, и вход в аккаунт не выполнен, присылать уведомление в TG")
    parser.add_argument("-a", "--address", type=str, help="Адрес, будет использовано первое сопадение")
    parser.add_argument("-p", "--proxy", type=str, help="Строка прокси в формате protocol://username:password@ip:port")
    parser.add_argument("-pl", "--proxy-list", type=str, help="Путь к файлу с прокси в формате protocol://username:password@ip:port")
    parser.add_argument("-ad", "--allow-direct", action="store_true", help="Использовать прямое соединение параллельно с прокси для ускорения работы в многопотоке")
    parser.add_argument("-tc", "--tg-config",type=str, help="Telegram Bot Token и Telegram Chat Id в формате token$id")
    parser.add_argument("-pva", "--price-value-alert", type=float, help="Если цена товара равна или ниже данного значения, уведомлять в TG")
    parser.add_argument("-pbva", "--price-bonus-value-alert", type=float, help="Если цена-бонусы товара равна или ниже данного значения, уведомлять в TG")
    parser.add_argument("-bva", "--bonus-value-alert", type=float, help="Если количество бонусов товара равно или выше данного значения, уведомлять в TG")
    parser.add_argument("-bpa", "--bonus-percent-alert", type=float, help="Если процент бонусов товара равно или выше данного значения, уведомлять в TG")
    parser.add_argument("-mb", "--use-merchant-blacklist", action="store_true", help="Использовать черный список продавцов с ограничением на списание бонусов")
    parser.add_argument("-art", "--alert-repeat-timeout", type=float, help="Если походящий по параметрам товар уже был отправлен в TG, повторно уведомлять по истечении заданного времени, в часах")
    parser.add_argument("-t", "--threads", type=int, help="Количество потоков. По умолчанию: 1 на каждое соединиение")
    parser.add_argument("-d", "--delay", type=float, help="Задержка между запросами в секундах при работе в одном потоке. По умолчанию: 1.8")
    parser.add_argument("-ed", "--error-delay", type=float, help="Задержка между запосами в секундах в случае ошибки при работе в одном потоке. По умолчанию: 5")
    parser.add_argument('-log', '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Уровень лога. По умолчанию: INFO')
    args = parser.parse_args()

    print_logo()

    if not args.config:
        if args.url:
            run_url_parser(args)
        else:
            create_config()

    if args.config:
        if Path(args.config).exists():
            try:
                config = read_json_file(args.config)
            except:
                raise Exception('Ошибка чтения конфига!')
            run_url_parser(args, config)
        else:
            raise Exception('Файл конфига не найден!')

if __name__ == "__main__":
    main()
