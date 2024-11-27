"""base parser class"""

import logging
from datetime import datetime
from pathlib import Path
import json
from time import sleep, time

from curl_cffi import requests
from rich.logging import RichHandler
import core.telegram_utils as telegram_utils
from core.utils import proxy_format_check


class Parser_base:
    def __init__(
        self,
        cookie_file_path: str = "",
        proxy: str = "",
        allow_direct: bool = False,
        proxy_file_path: str = "",
        tg_config: str = "",
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

        self.start_time = datetime.now()

        self.region_id = "50"
        self.session = None
        self.proxies: list = []
        self.parsed_proxies: list = []
        self.cookie_dict: dict = None
        self.profile: dict = {}
        self.rich_progress = None
        self.job_name: str = ""

        self.logger = None

        self.tg_client = None

    def _set_up(self):
        self._logger_setup(self.log_level)
        if self.tg_config:
            if not telegram_utils.validate_credentials(self.tg_config):
                raise Exception(f"Конфиг {self.tg_config} не прошел проверку!")
            self.tg_client = telegram_utils.Telegram(self.tg_config, self.logger)
        self._read_proxy_file() if self.proxy_file_path else None
        self._proxies_set_up()
        self._read_cookie_file() if self.cookie_file_path else None

    class Proxy:
        def __init__(self, proxy: str | None):
            self.proxy_string: str | None = proxy
            self.usable_at: int = 0
            self.busy = False

    def _logger_setup(self, log_level):
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="%H:%M:%S",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
        self.logger = logging.getLogger("rich")

    def _read_proxy_file(self):
        if Path(self.proxy_file_path).exists():
            proxy_file_contents: str = open(self.proxy_file_path, "r", encoding="utf-8").read()
            self.parsed_proxies = [line for line in proxy_file_contents.split("\n") if line]
        else:
            raise Exception(f"Путь {self.cookie_file_path} не найден!")

    def _read_cookie_file(self):
        if Path(self.cookie_file_path).exists():
            cookies = json.loads(open(self.cookie_file_path, "r", encoding="utf-8").read())
            self.cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
        else:
            raise Exception(f"Путь {self.cookie_file_path} не найден!")

    def _proxies_set_up(self):
        if self.proxy:
            is_valid_proxy = proxy_format_check(self.proxy)
            if not is_valid_proxy:
                raise Exception(f"Прокси {self.proxy} не верного формата!")
            self.proxies = [self.Proxy(self.proxy)]
        elif self.parsed_proxies:
            for proxy in self.parsed_proxies:
                is_valid_proxy = proxy_format_check(proxy)
                if not is_valid_proxy:
                    raise Exception(f"Прокси {proxy} не верного формата!")
            self.proxies = [self.Proxy(proxy) for proxy in self.parsed_proxies]
        if self.proxies and self.allow_direct:
            self.proxies.append(self.Proxy(None))
        elif not self.proxies:
            self.proxies = [self.Proxy(None)]

    def _get_proxy(self) -> str:
        while True:
            free_proxies = [proxy for proxy in self.proxies if not proxy.busy]
            if free_proxies:
                oldest_proxy = min(free_proxies, key=lambda obj: obj.usable_at)
                current_time = time()
                if oldest_proxy.usable_at <= current_time:
                    return oldest_proxy
                else:
                    sleep(oldest_proxy.usable_at - time())
                    return self._get_proxy()
            else:
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
            proxy: self.Proxy = self._get_proxy()
            proxy.busy = True
            self.logger.debug("Прокси : %s", proxy.proxy_string)
            try:
                response = requests.post(api_url, json=json_data, proxy=proxy.proxy_string, verify=False, impersonate="chrome")
                response_data: dict = response.json()
            except:
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

        raise Exception("Ошибка получения данных api")

    def _get_profile(self):
        json_data = {}
        response_json = self._api_request("https://megamarket.ru/api/mobile/v1/securityService/profile/get", json_data)
        self.profile = response_json["profile"]
