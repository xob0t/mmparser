"""url"""

import threading
import concurrent.futures
import datetime
import sys
import json
import signal
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, parse_qs, unquote
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from core.utils import validate_regex, slugify
import core.db as db
from core.parser_base import Parser_base


class Parser_url(Parser_base):
    def __init__(
        self,
        url: str,
        job_name: str = "",
        include: str = "",
        exclude: str = "",
        blacklist:str = "",
        all_cards: bool = False,
        no_cards: bool = False,
        cookie_file_path: str = "",
        account_alert: bool = False,
        address: str = "",
        proxy: str = "",
        allow_direct: bool = False,
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
        super().__init__(
            cookie_file_path,
            proxy,
            allow_direct,
            proxy_file_path,
            tg_config,
            delay,
            error_delay,
            log_level,
        )

        self.url = url
        self.job_name = job_name
        self.include = include
        self.exclude = exclude
        self.blacklist_path = blacklist
        self.all_cards = all_cards
        self.no_cards = no_cards
        self.address = address
        self.proxy = proxy
        self.account_alert = account_alert
        self.price_value_alert = price_value_alert or float("-inf")
        self.price_bonus_value_alert = price_bonus_value_alert or float("-inf")
        self.bonus_value_alert = bonus_value_alert or float("inf")
        self.bonus_percent_alert = bonus_percent_alert or float("inf")
        self.alert_repeat_timeout = alert_repeat_timeout or 0
        self.threads = threads

        self.blacklist:list = []
        self.parsed_url: dict = None
        self.scraped_tems_counter: int = 0
        self.rich_progress = None
        self.job_id: int = None

        self.address_id = None

        self.items_per_page: int = 44
        self.lock = threading.Lock()

        self._set_up()

    def _set_up(self):
        # Make Ctrl-C work when deamon threads are running
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        super()._set_up()
        regex_check = validate_regex(self.include) if self.include else None
        if regex_check is False:
            raise Exception(f'Неверное выражение "{self.include}"!')
        regex_check = validate_regex(self.exclude) if self.exclude else None
        if regex_check is False:
            raise Exception(f'Неверное выражение "{self.exclude}"!')
        if self.blacklist_path:
            self._read_blacklist_file()
        self.threads = self.threads or len(self.proxies)
        if not Path(db.FILENAME).exists():
            db.create_db()

    def parse(self):
        self.logger.info("Целевой URL: %s", self.url)
        self.logger.info("Потоков: %s", self.threads)
        if self.cookie_file_path:
            self._get_profile()
            if self.profile.get("isAuthenticated"):
                self.logger.info("Аккаунт: %s", self.profile["phone"])
            else:
                self.logger.warning("Вход в аккаунт не выполнен")
                if self.account_alert:
                    self.tg_client.notify(
                        f"Вход в аккаунт {self.cookie_file_path} не выполнен!"
                    )
                    raise Exception(
                        f"Вход в аккаунт {self.cookie_file_path} не выполнен!"
                    )
        if self.address:
            self._get_address_from_string()
        elif self.profile.get("isAuthenticated"):
            self._get_profile_default_address()
        if (not self.address_id or not self.region_id) and self.cookie_dict:
            self._get_cookie_address()
        self.parse_input_url()
        if self.parsed_url and not self.job_name:
            search_text = self.parsed_url.get("searchText", {})
            collection_title = (self.parsed_url.get("collection", {}) or {}).get(
                "title"
            )
            merchant = (self.parsed_url.get("merchant", {}) or {}).get("slug")
            unknown = "Не_определено"
            self.job_name = search_text or collection_title or merchant or unknown
            self.job_name = slugify(self.job_name)
        if self.parsed_url["type"] == "TYPE_PRODUCT_CARD":
            self._parse_card()
            self.logger.info(
                "%s %s", self.job_name, self.start_time.strftime("%d-%m-%Y %H:%M:%S")
            )
        else:
            self.job_id = db.new_job(self.job_name)
            self.logger.info(
                "%s %s", self.job_name, self.start_time.strftime("%d-%m-%Y %H:%M:%S")
            )
            self._parse_all()
            self.logger.info("Спаршено %s товаров", self.scraped_tems_counter)
        db.finish_job(self.job_id)

    def _read_blacklist_file(self):
        blacklist_file_contents: str = open(self.blacklist_path, "r", encoding="utf-8").read()
        self.blacklist = [line for line in blacklist_file_contents.split("\n") if line]

    def _export_to_db(
        self,
        goodsId,
        merchantId,
        url,
        title,
        finalPrice,
        finalPriceBonus,
        bonusAmount,
        bonusPercent,
        availableQuantity,
        deliveryPossibilities,
        merchantName,
        notified,
    ):
        with self.lock:
            db.add_to_db(
                self.job_id,
                self.job_name,
                goodsId,
                merchantId,
                url,
                title,
                finalPrice,
                finalPriceBonus,
                bonusAmount,
                bonusPercent,
                availableQuantity,
                deliveryPossibilities,
                merchantName,
                notified,
            )

    def parse_input_url(self, tries=10):
        json_data = {"url": self.url}
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/urlService/url/parse",
            json_data,
            tries=tries,
        )
        parsed_url = response_json["params"]
        parsed_url = self._filters_convert(parsed_url)
        parsed_url["type"] = response_json["type"]
        sorting = int(
            dict(parse_qsl(unquote(urlparse(self.url).fragment.lstrip("?")))).get(
                "sort", 0
            )
        )
        search_query_from_url = parse_qs(urlparse(self.url).query).get("q", "") or ""
        search_query_from_url = (
            search_query_from_url[0] if search_query_from_url else None
        )
        parsed_url["searchText"] = parsed_url["searchText"] or search_query_from_url
        parsed_url["sorting"] = sorting
        self.parsed_url = parsed_url
        return parsed_url

    def _get_profile_default_address(self):
        json_data = {}
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/profileService/address/list", json_data
        )
        address = [
            address
            for address in response_json["profileAddresses"]
            if address["isDefault"] is True
        ]
        if address:
            self.address_id = address[0]["addressId"]
            self.region_id = address[0]["regionId"]
            self.logger.info(f"Регион: {address[0]['region']}")
            self.logger.info(f"Адрес: {address[0]['full']}")

    def _get_cookie_address(self):
        address = self.cookie_dict.get("address_info")
        region = self.cookie_dict.get("region_info")
        if region:
            region = json.loads(unquote(region))
            self.region_id = self.region_id or region["id"]
            self.logger.info("Регион: %s", region["displayName"])
        if address:
            address = json.loads(unquote(address))
            self.address_id = self.address_id or address["addressId"]
            self.logger.info("Адрес: %s", address["full"])

    def _get_address_from_string(self):
        json_data = {"count": 10, "isSkipRegionFilter": True, "query": self.address}
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/addressSuggestService/address/suggest",
            json_data,
        )
        address = response_json["items"]
        if address:
            self.address_id = address[0]["addressId"]
            self.region_id = address[0]["regionId"]
            self.logger.info("Регион: %s", address[0]["region"])
            self.logger.info("Адрес: %s", address[0]["full"])
        else:
            sys.exit(f"По запросу {self.address} адрес не найден!")

    def _parse_item(self, item):
        if item["favoriteOffer"]["merchantName"] in self.blacklist:
                self.logger.debug("Пропуск %s", item["favoriteOffer"]["merchantName"])
                return
        delivery_possibilities = set()
        for delivery in item["favoriteOffer"]["deliveryPossibilities"]:
            delivery_info = f"{delivery['displayName']}, {delivery.get('displayDeliveryDate', '')} - {delivery.get('amount', 0)}р"
            delivery_possibilities.add(delivery_info)
        delivery_possibilities = (" \n").join(delivery_possibilities)
        price_bonus = (
            item["favoriteOffer"]["finalPrice"] - item["favoriteOffer"]["bonusAmount"]
        )
        self.scraped_tems_counter += 1

        goodsId = item["goods"]["goodsId"].split("_")[0]

        notified = self._notify_if_notify_check(
            item["goods"]["title"],
            item["favoriteOffer"]["finalPrice"],
            price_bonus,
            item["favoriteOffer"]["bonusAmount"],
            item["favoriteOffer"]["bonusPercent"],
            item["goods"]["webUrl"],
            item["favoriteOffer"]["merchantName"],
            delivery_possibilities,
            item["favoriteOffer"]["availableQuantity"],
            item["goods"]["titleImage"],
            goodsId,
            item["favoriteOffer"]["merchantId"],
        )
        self._export_to_db(
            goodsId,
            item["favoriteOffer"]["merchantId"],
            item["goods"]["webUrl"],
            item["goods"]["title"],
            item["favoriteOffer"]["finalPrice"],
            price_bonus,
            item["favoriteOffer"]["bonusAmount"],
            item["favoriteOffer"]["bonusPercent"],
            item["favoriteOffer"]["availableQuantity"],
            delivery_possibilities,
            item["favoriteOffer"]["merchantName"],
            notified,
        )

    def _filters_convert(self, parsed_url):
        for url_filter in parsed_url["selectedListingFilters"]:
            if url_filter["type"] == "EXACT_VALUE":
                url_filter["type"] = 0
            if url_filter["type"] == "LEFT_BOUND":
                url_filter["type"] = 1
            if url_filter["type"] == "RIGHT_BOUND":
                url_filter["type"] = 2
        return parsed_url

    def _parse_offers(self, item, offers):
        for offer in offers:
            if offer["merchantName"] in self.blacklist:
                self.logger.debug("Пропуск %s", offer["merchantName"])
                continue
            delivery_possibilities = set()
            for delivery in offer["deliveryPossibilities"]:
                delivery_info = f"{delivery['displayName']}, {delivery.get('displayDeliveryDate', '')} - {delivery.get('amount', 0)}р"
                delivery_possibilities.add(delivery_info)
            delivery_possibilities = (" \n").join(delivery_possibilities)
            price_bonus = offer["finalPrice"] - offer["bonusAmount"]
            self.scraped_tems_counter += 1
            goodsId = item["goodsId"].split("_")[0]
            notified = self._notify_if_notify_check(
                item["title"],
                offer["finalPrice"],
                price_bonus,
                offer["bonusAmount"],
                offer["bonusPercent"],
                item["webUrl"],
                offer["merchantName"],
                delivery_possibilities,
                offer["availableQuantity"],
                item["titleImage"],
                goodsId,
                offer["merchantId"],
            )
            self._export_to_db(
                goodsId,
                offer["merchantId"],
                item["webUrl"],
                item["title"],
                offer["finalPrice"],
                price_bonus,
                offer["bonusAmount"],
                offer["bonusPercent"],
                offer["availableQuantity"],
                delivery_possibilities,
                offer["merchantName"],
                notified,
            )

    def _notify_if_notify_check(
        self,
        title,
        finalPrice,
        price_bonus,
        bonusAmount,
        bonusPercent,
        webUrl,
        merchantName,
        delivery_possibilities,
        availableQuantity,
        titleImage,
        goodsId,
        merchantId,
    ):
        time_diff = 0
        last_notified = None
        if self.alert_repeat_timeout:
            last_notified = db.get_last_notified(
                goodsId, merchantId, finalPrice, bonusAmount
            )
            last_notified = datetime.datetime.strptime(last_notified, "%Y-%m-%d %H:%M:%S") if last_notified else None
            if last_notified:
                now = datetime.datetime.now()
                time_diff = now - last_notified
        if (
            (
                bonusPercent >= self.bonus_percent_alert
                or bonusAmount >= self.bonus_value_alert
                or finalPrice <= self.price_value_alert
                or price_bonus <= self.price_bonus_value_alert
            )
            and (not last_notified or (last_notified and time_diff.total_seconds() > self.alert_repeat_timeout * 3600))
            and self.tg_client
        ):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                message = self._tg_message_format(
                    title,
                    finalPrice,
                    price_bonus,
                    bonusAmount,
                    bonusPercent,
                    webUrl,
                    merchantName,
                    delivery_possibilities,
                    availableQuantity,
                )
                executor.submit(self.tg_client.notify, message, titleImage)
                return True
        return False

    def _tg_message_format(
        self,
        title,
        finalPrice,
        price_bonus,
        bonusAmount,
        bonusPercent,
        webUrl,
        merchantName,
        delivery_possibilities,
        availableQuantity,
    ):
        return (
            f"🛍 <b>Товар:</b> <a href=\"{webUrl}\">{title}</a>\n"
            f"💰 <b>Цена:</b> {finalPrice}р\n"
            f"💸 <b>Цена-Бонусы:</b> {price_bonus}\n"
            f"🟢 <b>Бонусы:</b> {bonusAmount}\n"
            f"🔢 <b>Процент Бонусов:</b> {bonusPercent}\n"
            f"✅ <b>Доступно:</b> {availableQuantity or '?'}\n"
            f"📦 <b>Доставка:</b> {delivery_possibilities}\n"
            f"🛒 <b>Продавец:</b> {merchantName}\n"
            f"☎️ <b>Аккаунт:</b> {self.profile.get('phone')}"
        )

    def _get_offers(self, goods_id, delay=0):
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
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/catalogService/productOffers/get",
            json_data,
            delay=delay,
        )
        return response_json["offers"]

    def _get_page(self, offset: int):
        json_data = {
            "requestVersion": 10,
            "limit": self.items_per_page,
            "offset": offset,
            "isMultiCategorySearch": self.parsed_url.get(
                "isMultiCategorySearch", False
            ),
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
            self.parsed_url["collection"] = (
                self.parsed_url["collection"]
                or self.parsed_url["menuNode"]["collection"]
            )
        json_data["collectionId"] = (
            self.parsed_url["collection"]["collectionId"]
            if self.parsed_url["collection"]
            else None
        )
        json_data["searchText"] = (
            self.parsed_url["searchText"] if self.parsed_url["searchText"] else None
        )
        json_data["selectedAssumedCollectionId"] = (
            self.parsed_url["collection"]["collectionId"]
            if self.parsed_url["collection"]
            else None
        )
        json_data["merchant"] = (
            {"id": self.parsed_url["merchant"]["id"]}
            if self.parsed_url["merchant"]
            else None
        )

        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/catalogService/catalog/search",
            json_data,
            delay=self.connection_success_delay,
        )

        return response_json

    def _parse_page(self, offset: int) -> tuple[int, int, bool, int]:
        response_json = self._get_page(offset)
        if response_json.get("error") or not response_json.get("items"):
            raise Exception()
        if response_json.get("success") is True:
            self.items_per_page = int(response_json.get("limit"))
            page_progress = self.rich_progress.add_task(
                f"[orange]Страница {int(offset/self.items_per_page)+1}"
            )
            self.rich_progress.update(page_progress, total=len(response_json["items"]))
            self.logger.debug("%s успех", offset)
            for item in response_json["items"]:
                item_title = item["goods"]["title"]
                if self._exclude_check(item_title):
                    self.rich_progress.update(page_progress, advance=1)
                    continue
                if item["isAvailable"] is True and self._include_check(item_title):
                    is_listing = self.parsed_url["type"] == "TYPE_LISTING"
                    if self.all_cards or (
                        not self.no_cards
                        and (
                            item["hasOtherOffers"]
                            or item["offerCount"] > 1
                            or is_listing
                        )
                    ):
                        self.logger.info("Парсим предложения %s", item_title)
                        offers = self._get_offers(
                            item["goods"]["goodsId"],
                            delay=self.connection_success_delay,
                        )
                        self._parse_offers(item["goods"], offers)
                    else:
                        self._parse_item(item)
                    self.rich_progress.update(page_progress, advance=1)

        self.rich_progress.remove_task(page_progress)
        parse_next_page = (
            response_json["items"] and response_json["items"][-1]["isAvailable"]
        )
        parsed_page = offset if response_json.get("success") else False
        return parsed_page, int(response_json["total"]), parse_next_page

    def _exclude_check(self, title):
        if self.exclude:
            return self.exclude.match(title)
        return False

    def _include_check(self, title):
        if self.include:
            return self.include.match(title)
        return True

    def _create_progress_bar(self):
        self.rich_progress = Progress(
            "{task.description}",
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.percentage]{task.completed}/{task.total}"),
            TimeRemainingColumn(elapsed_when_finished=True, compact=True),
        )
        self.rich_progress.start()

    def _get_card_info(self, goods_id):
        json_data = {"goodsId": goods_id, "merchantId": "0"}
        response_json = self._api_request(
            "https://megamarket.ru/api/mobile/v1/catalogService/productCardMainInfo/get",
            json_data,
        )
        return response_json["goods"]

    def _parse_card(self):
        offers = self._get_offers(self.parsed_url["goods"]["goodsId"])
        item = self._get_card_info(self.parsed_url["goods"]["goodsId"])
        self.job_name = slugify(item["title"])
        self.job_id = db.new_job(self.job_name)
        self._parse_offers(item, offers)

    def _parse_first_page(self, start_offset):
        parsed_page, total, parse_next_page = self._parse_page(start_offset)
        if not isinstance(parsed_page, int):
            self.logger.info("Ошибка получения первой страницы!")
        return total, parse_next_page

    def _parse_all(self):
        start_offset = 0
        self._create_progress_bar()
        total, parse_next_page = self._parse_first_page(start_offset)
        if not parse_next_page:
            return
        pages = [
            i
            for i in range(
                start_offset + self.items_per_page, total, self.items_per_page
            )
            if i < total - 1
        ]

        main_job = self.rich_progress.add_task("[green]Общий прогресс")
        self.rich_progress.update(main_job, total=len(pages) + 1, advance=1)
        max_threads = self.threads or (
            len(pages) if len(pages) < self.threads else self.threads
        )
        while pages:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_threads
            ) as executor:
                futures = {
                    executor.submit(self._parse_page, page): page for page in pages
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        parsed_page, _, parse_next_page = future.result()
                    except Exception:
                        parsed_page = False
                    if parsed_page:
                        self.rich_progress.update(main_job, advance=1)
                        pages.remove(parsed_page) if parsed_page in pages else None
                        if parse_next_page:
                            continue
                        self.logger.info("Дальше товары не в наличии, их не парсим")
                        for fut in futures:
                            future_page = futures[fut]
                            if future_page > parsed_page:
                                pages.remove(
                                    future_page
                                ) if future_page in pages else None
                                self.rich_progress.update(main_job, total=len(pages))
                                fut.cancel()
        self.rich_progress.stop()
