"""mmparser"""

import logging
from datetime import datetime
from time import sleep, time
import threading
import concurrent.futures
import sys
import json
import signal
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, parse_qs, unquote, urljoin

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.logging import RichHandler
from curl_cffi import requests

from .models import ParsedOffer, Connection
from .exceptions import ConfigError, ApiError
from . import db_utils, utils
from .telegram import TelegramClient, validate_tg_credentials


class Parser_url:
    def __init__(
        self,
        url: str,
        job_name: str = "",
        include: str = "",
        exclude: str = "",
        blacklist: str = "",
        all_cards: bool = False,
        no_cards: bool = False,
        cookie_file_path: str = "",
        account_alert: bool = False,
        address: str = "",
        proxy: str = "",
        allow_direct: bool = False,
        use_merchant_blacklist: bool = False,
        proxy_file_path: str = "",
        tg_config: str = "",
        price_value_alert: float = None,
        price_bonus_value_alert: float = None,
        bonus_value_alert: float = None,
        bonus_percent_alert: float = None,
        alert_repeat_timeout: float = None,
        threads: int = None,
        delay: float = None,
        error_delay: float = None,
        log_level: str = "INFO",
    ):
        self.cookie_file_path = cookie_file_path
        self.proxy = proxy
        self.allow_direct = allow_direct
        self.proxy_file_path = proxy_file_path
        self.tg_config = tg_config
        self.connection_success_delay = delay or 1.8
        self.connection_error_delay = error_delay or 10.0
        self.log_level = log_level

        self.start_time: datetime = None

        self.region_id = "50"
        self.session = None
        self.connections: list[Connection] = []
        self.parsed_proxies: set | None = None
        self.cookie_dict: dict = None
        self.profile: dict = {}
        self.rich_progress = None
        self.job_name: str = ""

        self.logger: logging.Logger = self._create_logger(self.log_level)
        self.tg_client: TelegramClient = None

        self.url: str = url
        self.job_name: str = job_name
        self.include: str = include
        self.exclude: str = exclude
        self.blacklist_path: str = blacklist
        self.all_cards: bool = all_cards
        self.no_cards: bool = no_cards
        self.address: str = address
        self.proxy: str = proxy
        self.account_alert: bool = account_alert
        self.use_merchant_blacklist: bool = use_merchant_blacklist
        self.merchant_blacklist: list = utils.load_blacklist() if use_merchant_blacklist else []
        self.price_value_alert: float = price_value_alert or float("-inf")
        self.price_bonus_value_alert: float = price_bonus_value_alert or float("-inf")
        self.bonus_value_alert: float = bonus_value_alert or float("inf")
        self.bonus_percent_alert: float = bonus_percent_alert or float("inf")
        self.alert_repeat_timeout: float = alert_repeat_timeout or 0
        self.threads: int = threads

        self.blacklist: list = []
        self.parsed_url: dict = None
        self.scraped_tems_counter: int = 0
        self.rich_progress = None
        self.job_id: int = None

        self.address_id: str = None
        self.lock = threading.Lock()

        self._set_up()

    def _create_logger(self, log_level: str) -> logging.Logger:
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="%H:%M:%S",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
        return logging.getLogger("rich")

    def _proxies_set_up(self) -> None:
        """Настройка и валидация прокси"""
        if self.proxy:
            is_valid_proxy = utils.proxy_format_check(self.proxy)
            if not is_valid_proxy:
                raise ConfigError(f"Прокси {self.proxy} не верного формата!")
            self.connections = [Connection(self.proxy)]
        elif self.parsed_proxies:
            for proxy in self.parsed_proxies:
                is_valid_proxy = utils.proxy_format_check(proxy)
                if not is_valid_proxy:
                    raise ConfigError(f"Прокси {proxy} не верного формата!")
            self.connections = [Connection(proxy) for proxy in self.parsed_proxies]
        if self.connections and self.allow_direct:
            self.connections.append(Connection(None))
        elif not self.connections:
            self.connections = [Connection(None)]

    def _get_connection(self) -> str:
        """Получить самое позднее использованное `Соединение`"""
        while True:
            free_proxies = [proxy for proxy in self.connections if not proxy.busy]
            if free_proxies:
                oldest_proxy = min(free_proxies, key=lambda obj: obj.usable_at)
                current_time = time()
                if oldest_proxy.usable_at <= current_time:
                    return oldest_proxy
                sleep(oldest_proxy.usable_at - time())
                return self._get_connection()
            # No free proxies, wait and retry
            sleep(1)

    def _api_request(self, api_url: str, json_data: dict, tries: int = 10, delay: float = 0) -> dict:
        json_data["auth"] = {
            "locationId": self.region_id,
            "appPlatform": "WEB",
            "appVersion": 1710405202,
            "experiments": {},
            "os": "UNKNOWN_OS",
        }
        for i in range(0, tries):
            proxy: Connection = self._get_connection()
            proxy.busy = True
            self.logger.debug("Прокси : %s", proxy.proxy_string)
            try:
                response = requests.post(api_url, json=json_data, proxy=proxy.proxy_string, verify=False, impersonate="chrome")
                response_data: dict = response.json()
            except Exception:
                response = None
            if response and response.status_code == 200 and not response_data.get("error"):
                proxy.usable_at = time() + delay
                proxy.busy = False
                return response_data
            if response and response.status_code == 200 and response_data.get("code") == 7:
                self.logger.debug("Соединение %s: слишком частые запросы", proxy.proxy_string)
                proxy.usable_at = time() + self.connection_error_delay
            else:
                sleep(1 * i)
            proxy.busy = False

        raise ApiError("Ошибка получения данных api")

    def _get_profile(self) -> None:
        """Получить и сохранить информацию профиля ММ"""
        response_json = self._api_request("https://megamarket.ru/api/mobile/v1/securityService/profile/get", json_data={})
        self.profile = response_json["profile"]

    def _set_up(self) -> None:
        """Парсинг в валидация конфигурации"""
        if self.tg_config:
            if not validate_tg_credentials(self.tg_config):
                raise ConfigError(f"Конфиг {self.tg_config} не прошел проверку!")
            self.tg_client = TelegramClient(self.tg_config, self.logger)
        self.parsed_proxies = self.proxy_file_path and utils.parse_proxy_file(self.proxy_file_path)
        self._proxies_set_up()
        self.cookie_dict = self.cookie_file_path and utils.parse_cookie_file(self.cookie_file_path)

        # Make Ctrl-C work when deamon threads are running
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        regex_check = self.include and utils.validate_regex(self.include)
        if regex_check is False:
            raise ConfigError(f'Неверное выражение "{self.include}"!')
        regex_check = self.exclude and utils.validate_regex(self.exclude)
        if regex_check is False:
            raise ConfigError(f'Неверное выражение "{self.exclude}"!')
        if self.blacklist_path:
            self._read_blacklist_file()
        self.threads = self.threads or len(self.connections)
        if not Path(db_utils.FILENAME).exists():
            db_utils.create_db()

    def parse(self) -> None:
        """Метод запуска парсинга"""
        utils.check_for_new_version()
        self.start_time = datetime.now()
        self.logger.info("Целевой URL: %s", self.url)
        self.logger.info("Потоков: %s", self.threads)
        if self.cookie_file_path:
            self._get_profile()
            if self.profile.get("isAuthenticated"):
                self.logger.info("Аккаунт: %s", self.profile["phone"])
            else:
                self.logger.warning("Вход в аккаунт не выполнен")
                if self.account_alert and self.tg_client:
                    self.tg_client.notify(f"Вход в аккаунт {self.cookie_file_path} не выполнен!")
                    raise Exception(f"Вход в аккаунт {self.cookie_file_path} не выполнен!")
        if self.address:
            self._get_address_from_string(self.address)
        elif self.profile.get("isAuthenticated"):
            self._get_profile_default_address()
        if (not self.address_id or not self.region_id) and self.cookie_dict:
            self._get_address_info(self.cookie_dict)
        self.parse_input_url()
        if self.parsed_url and not self.job_name:
            search_text = self.parsed_url.get("searchText", {})
            collection_title = (self.parsed_url.get("collection", {}) or {}).get("title")
            merchant = (self.parsed_url.get("merchant", {}) or {}).get("slug")
            unknown = "Не_определено"
            self.job_name = search_text or collection_title or merchant or unknown
            self.job_name = utils.slugify(self.job_name)
        if self.parsed_url["type"] == "TYPE_PRODUCT_CARD":
            self._parse_card()
            self.logger.info("%s %s", self.job_name, self.start_time.strftime("%d-%m-%Y %H:%M:%S"))
        else:
            self.job_id = db_utils.new_job(self.job_name)
            self.logger.info("%s %s", self.job_name, self.start_time.strftime("%d-%m-%Y %H:%M:%S"))
            self._parse_multi_page()
            self.logger.info("Спаршено %s товаров", self.scraped_tems_counter)
        db_utils.finish_job(self.job_id)

    def _read_blacklist_file(self):
        blacklist_file_contents: str = open(self.blacklist_path, "r", encoding="utf-8").read()
        self.blacklist = [line for line in blacklist_file_contents.split("\n") if line]

    def _export_to_db(self, parsed_offer: ParsedOffer) -> None:
        """Экспорт одного предложения в базу данных"""
        with self.lock:
            db_utils.add_to_db(
                self.job_id,
                self.job_name,
                parsed_offer.goods_id,
                parsed_offer.merchant_id,
                parsed_offer.url,
                parsed_offer.title,
                parsed_offer.price,
                parsed_offer.price_bonus,
                parsed_offer.bonus_amount,
                parsed_offer.bonus_percent,
                parsed_offer.available_quantity,
                parsed_offer.delivery_date,
                parsed_offer.merchant_name,
                parsed_offer.merchant_rating,
                parsed_offer.notified,
            )

    def parse_input_url(self, tries: int = 10) -> dict:
        """Парсинг url мм с использованием api самого мм"""
        json_data = {"url": self.url}
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/urlService/url/parse",
            json_data,
            tries=tries,
        )
        parsed_url = response_json["params"]
        parsed_url = self._filters_convert(parsed_url)
        parsed_url["type"] = response_json["type"]
        sorting = int(dict(parse_qsl(unquote(urlparse(self.url).fragment.lstrip("?")))).get("sort", 0))
        search_query_from_url = parse_qs(urlparse(self.url).query).get("q", "") or ""
        search_query_from_url = search_query_from_url[0] if search_query_from_url else None
        parsed_url["searchText"] = parsed_url["searchText"] or search_query_from_url
        parsed_url["sorting"] = sorting
        self.parsed_url = parsed_url
        return parsed_url

    def _get_profile_default_address(self) -> None:
        """Получить данные адреса аккаунта мм"""
        json_data = {}
        response_json = self._api_request("https://megamarket.ru/api/mobile/v1/profileService/address/list", json_data)
        address = [address for address in response_json["profileAddresses"] if address["isDefault"] is True]
        if address:
            self.address_id = address[0]["addressId"]
            self.region_id = address[0]["regionId"]
            self.logger.info(f"Регион: {address[0]['region']}")
            self.logger.info(f"Адрес: {address[0]['full']}")

    def _get_address_info(self, cookie_dict: dict) -> None:
        """Получить данные адреса принадлежащие аккаунту из cookies"""
        address = cookie_dict.get("address_info")
        region = cookie_dict.get("region_info")
        if region:
            region = json.loads(unquote(region))
            self.region_id = self.region_id or region["id"]
            self.logger.info("Регион: %s", region["displayName"])
        if address:
            address = json.loads(unquote(address))
            self.address_id = self.address_id or address["addressId"]
            self.logger.info("Адрес: %s", address["full"])

    def _get_address_from_string(self, address: str) -> None:
        """Установить адрес доставки по строке адреса"""
        json_data = {"count": 10, "isSkipRegionFilter": True, "query": address}
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/addressSuggestService/address/suggest",
            json_data,
        )
        address = response_json.get("items")
        if address:
            self.address_id = address[0]["addressId"]
            self.region_id = address[0]["regionId"]
            self.logger.info("Регион: %s", address[0]["region"])
            self.logger.info("Адрес: %s", address[0]["full"])
        else:
            sys.exit(f"По запросу {address} адрес не найден!")

    def _get_merchant_inn(self, merchant_id: str) -> str:
        """Получить ИНН по ID продавца"""
        json_data = {"merchantId": merchant_id}
        response_json = self._api_request("https://megamarket.ru/api/mobile/v1/partnerService/merchant/legalInfo/get", json_data)
        return response_json["merchant"]["legalInfo"]["inn"]

    def _parse_item(self, item: dict):
        """Парсинг дефолтного предложения товара"""
        if item["favoriteOffer"]["merchantName"] in self.blacklist:
            self.logger.debug("Пропуск %s", item["favoriteOffer"]["merchantName"])
            return

        if self.use_merchant_blacklist:
            merchant_inn = self._get_merchant_inn(item["favoriteOffer"]["merchantId"])
            if merchant_inn in self.merchant_blacklist:
                self.logger.debug("Пропуск %s", item["favoriteOffer"]["merchantName"])
                return

        self.scraped_tems_counter += 1

        delivery_date_iso: str = item["favoriteOffer"]["deliveryPossibilities"][0].get("displayDeliveryDate", "")
        delivery_date = delivery_date_iso.split("T")[0]

        parsed_offer = ParsedOffer(
            title=item["goods"]["title"],
            price=item["favoriteOffer"]["finalPrice"],
            delivery_date=delivery_date,
            price_bonus=item["favoriteOffer"]["finalPrice"] - item["favoriteOffer"]["bonusAmount"],
            goods_id=item["goods"]["goodsId"].split("_")[0],
            bonus_amount=item["favoriteOffer"]["bonusAmount"],
            url=item["goods"]["webUrl"],
            available_quantity=item["favoriteOffer"]["availableQuantity"],
            merchant_id=item["favoriteOffer"]["merchantId"],
            merchant_name=item["favoriteOffer"]["merchantName"],
            image_url=item["goods"]["titleImage"],
        )

        parsed_offer.notified = self._notify_if_notify_check(parsed_offer)
        self._export_to_db(parsed_offer)

    def _filters_convert(self, parsed_url: dict) -> dict:
        """Конвертация фильтров каталога или поиска"""
        for url_filter in parsed_url["selectedListingFilters"]:
            if url_filter["type"] == "EXACT_VALUE":
                url_filter["type"] = 0
            if url_filter["type"] == "LEFT_BOUND":
                url_filter["type"] = 1
            if url_filter["type"] == "RIGHT_BOUND":
                url_filter["type"] = 2
        return parsed_url

    def _parse_offer(self, item: dict, offer: dict) -> None:
        """Парсинг предложения товара"""
        if offer["merchantName"] in self.blacklist:
            self.logger.debug("Пропуск %s", offer["merchantName"])
            return

        if self.use_merchant_blacklist:
            merchant_inn = self._get_merchant_inn(offer["merchantId"])
            if merchant_inn in self.merchant_blacklist:
                self.logger.debug("Пропуск %s", offer["merchantName"])
                return

        delivery_date_iso: str = offer["deliveryPossibilities"][0]["date"]
        delivery_date = delivery_date_iso.split("T")[0]

        # добавление merchantId в конец url
        offer_url: str = item["webUrl"]
        if offer_url.endswith("/"):
            offer_url = offer_url[:-1]
        offer_url = f'{offer_url}_{offer["merchantId"]}'

        parsed_offer = ParsedOffer(
            delivery_date=delivery_date,
            price_bonus=offer["finalPrice"] - offer["bonusAmountFinalPrice"],
            goods_id=item["goodsId"].split("_")[0],
            title=item["title"],
            price=offer["finalPrice"],
            bonus_amount=offer["bonusAmountFinalPrice"],
            url=offer_url,
            available_quantity=offer["availableQuantity"],
            merchant_id=offer["merchantId"],
            merchant_name=offer["merchantName"],
            merchant_rating=offer["merchantSummaryRating"],
            image_url=item["titleImage"],
        )

        self.scraped_tems_counter += 1
        parsed_offer.notified = self._notify_if_notify_check(parsed_offer)
        self._export_to_db(parsed_offer)

    def _notify_if_notify_check(self, parsed_offer: ParsedOffer):
        """Отправить уведомление в tg если предложение подходит по параметрам"""
        time_diff = 0
        last_notified = None
        if self.alert_repeat_timeout:
            last_notified = db_utils.get_last_notified(parsed_offer.goods_id, parsed_offer.merchant_id, parsed_offer.price, parsed_offer.bonus_amount)
            last_notified = datetime.strptime(last_notified, "%Y-%m-%d %H:%M:%S") if last_notified else None
            if last_notified:
                now = datetime.now()
                time_diff = now - last_notified
        if (
            (parsed_offer.bonus_percent >= self.bonus_percent_alert or parsed_offer.bonus_amount >= self.bonus_value_alert or parsed_offer.price <= self.price_value_alert or parsed_offer.price_bonus <= self.price_bonus_value_alert)
            and (not last_notified or (last_notified and time_diff.total_seconds() > self.alert_repeat_timeout * 3600))
            and self.tg_client
        ):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                message = self._format_tg_message(parsed_offer)
                executor.submit(self.tg_client.notify, message, parsed_offer.image_url)
                return True
        return False

    def _format_tg_message(self, parsed_offer: ParsedOffer) -> str:
        """Форматировать данные для отправки в telegram"""
        return (
            f"🛍 <b>Товар:</b> <a href=\"{parsed_offer.url}\">{parsed_offer.title}</a>\n"
            f"💰 <b>Цена:</b> {parsed_offer.price}₽\n"
            f"💸 <b>Цена-Бонусы:</b> {parsed_offer.price_bonus}\n"
            f"🟢 <b>Бонусы:</b> {parsed_offer.bonus_amount}\n"
            f"🔢 <b>Процент Бонусов:</b> {parsed_offer.bonus_percent}\n"
            f"✅ <b>Доступно:</b> {parsed_offer.available_quantity or '?'}\n"
            f"📦 <b>Доставка:</b> {parsed_offer.delivery_date}\n"
            f"🛒 <b>Продавец:</b> {parsed_offer.merchant_name} {parsed_offer.merchant_rating}{'⭐' if parsed_offer.merchant_rating else ''}\n"
            f"☎️ <b>Аккаунт:</b> {self.profile.get('phone')}"
        )

    def _get_offers(self, goods_id: str, delay: int = 0) -> list[dict]:
        """Получить список предложений товара"""
        json_data = {
            "addressId": self.address_id,
            "collectionId": None,
            "goodsId": goods_id,
            "listingParams": {
                "priorDueDate": "UNKNOWN_OFFER_DUE_DATE",
                "selectedFilters": [],
            },
            "merchantId": "0",
            "requestVersion": 11,
            "shopInfo": {},
        }
        response_json = self._api_request("https://megamarket.ru/api/mobile/v1/catalogService/productOffers/get", json_data, delay=delay)
        return response_json["offers"]

    def _get_page(self, offset: int) -> dict:
        """Получить страницу каталога или поиска"""
        json_data = {
            "requestVersion": 10,
            "limit": 44,
            "offset": offset,
            "isMultiCategorySearch": self.parsed_url.get("isMultiCategorySearch", False),
            "searchByOriginalQuery": False,
            "selectedSuggestParams": [],
            "expandedFiltersIds": [],
            "sorting": self.parsed_url["sorting"],
            "ageMore18": None,
            "addressId": self.address_id,
            "showNotAvailable": True,
            "selectedFilters": self.parsed_url.get("selectedListingFilters", []),
        }
        if self.parsed_url.get("type", "") == "TYPE_MENU_NODE":
            self.parsed_url["collection"] = self.parsed_url["collection"] or self.parsed_url["menuNode"]["collection"]
        json_data["collectionId"] = self.parsed_url["collection"]["collectionId"] if self.parsed_url["collection"] else None
        json_data["searchText"] = self.parsed_url["searchText"] if self.parsed_url["searchText"] else None
        json_data["selectedAssumedCollectionId"] = self.parsed_url["collection"]["collectionId"] if self.parsed_url["collection"] else None
        json_data["merchant"] = {"id": self.parsed_url["merchant"]["id"]} if self.parsed_url["merchant"] else None

        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/catalogService/catalog/search",
            json_data,
            delay=self.connection_success_delay,
        )

        if response_json.get("error"):
            raise ApiError()
        if response_json.get("success") is True:
            return response_json

    def _parse_page(self, response_json: dict) -> tuple[int, int, bool]:
        """Парсинг страницы каталога или поиска"""
        items_per_page = int(response_json.get("limit"))
        page_progress = self.rich_progress.add_task(f"[orange]Страница {int(int(response_json.get('offset'))/items_per_page)+1}")
        self.rich_progress.update(page_progress, total=len(response_json["items"]))
        for item in response_json["items"]:
            item_title = item["goods"]["title"]
            if self._exclude_check(item_title) or (item["isAvailable"] is not True) or (not self._include_check(item_title)):
                # пропускаем, если товар не доступен или исключен
                self.rich_progress.update(page_progress, advance=1)
                continue
            is_listing = self.parsed_url["type"] == "TYPE_LISTING"
            if self.all_cards or (not self.no_cards and (item["hasOtherOffers"] or item["offerCount"] > 1 or is_listing)):
                self.logger.info("Парсим предложения %s", item_title)
                offers = self._get_offers(item["goods"]["goodsId"], delay=self.connection_success_delay)
                for offer in offers:
                    self._parse_offer(item["goods"], offer)
            else:
                self._parse_item(item)
            self.rich_progress.update(page_progress, advance=1)

        self.rich_progress.remove_task(page_progress)
        parse_next_page = response_json["items"] and response_json["items"][-1]["isAvailable"]
        return parse_next_page

    def _exclude_check(self, title: str) -> bool:
        if self.exclude:
            return self.exclude.match(title)
        return False

    def _include_check(self, title: str) -> bool:
        if self.include:
            return self.include.match(title)
        return True

    def _create_progress_bar(self) -> None:
        """Создание и запуск полосы прогресса"""
        self.rich_progress = Progress(
            "{task.description}",
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
            TimeRemainingColumn(elapsed_when_finished=True, compact=True),
        )
        self.rich_progress.start()

    def _get_card_info(self, goods_id: str) -> dict:
        """Получить карточку товара"""
        json_data = {"goodsId": goods_id, "merchantId": "0"}
        response_json = self._api_request("https://megamarket.ru/api/mobile/v1/catalogService/productCardMainInfo/get", json_data)
        return response_json["goods"]

    def _parse_card(self) -> None:
        """Парсинг карточки товара"""
        item = self._get_card_info(self.parsed_url["goods"]["goodsId"])
        offers = self._get_offers(self.parsed_url["goods"]["goodsId"])
        self.job_name = utils.slugify(item["title"])
        self.job_id = db_utils.new_job(self.job_name)
        for offer in offers:
            self._parse_offer(item, offer)

    def _process_page(self, offset: int, main_job) -> bool:
        """Получение и парсинг страницы каталога или поиска"""
        response_json = self._get_page(offset)
        parse_next_page = self._parse_page(response_json)
        self.rich_progress.update(main_job, advance=1)
        return parse_next_page

    def _parse_multi_page(self) -> None:
        """Запуск и менеджмент парсинга каталога или поиска"""
        start_offset = 0
        response_json = self._get_page(start_offset)
        if len(response_json["items"]) == 0 and response_json["processor"]["type"] in ("MENU_NODE", "COLLECTION"):
            self.logger.debug("Редирект в каталог")
            self.url = urljoin("https://megamarket.ru", response_json["processor"]["url"])
            return self.parse()
        items_per_page = int(response_json.get("limit"))
        item_count_total = int(response_json["total"])

        pages_to_parse = list(range(start_offset, item_count_total, items_per_page))
        self._create_progress_bar()
        main_job = self.rich_progress.add_task("[green]Общий прогресс", total=len(pages_to_parse))
        max_threads = min(len(pages_to_parse), self.threads)
        while pages_to_parse:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(self._process_page, page, main_job): page for page in pages_to_parse}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        parse_next_page = future.result()
                    except Exception:
                        continue
                    page = futures[future]
                    if page in pages_to_parse:
                        pages_to_parse.remove(page)
                    if not parse_next_page:
                        self.logger.info("Дальше товары не в наличии, их не парсим")
                        for fut in futures:
                            future_page = futures[fut]
                            if future_page > page:
                                if future_page in pages_to_parse:
                                    pages_to_parse.remove(future_page)
                                self.rich_progress.update(main_job, total=len(pages_to_parse))
                                fut.cancel()
        self.rich_progress.stop()
