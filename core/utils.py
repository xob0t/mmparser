from pathlib import Path
import re
import json
import time
import pkg_resources
from curl_cffi import requests
from rich.console import Console
from packaging import version

from . import exceptions

try:
    from lxml import html
except ImportError:
    _has_lxml = False
else:
    _has_lxml = True

BLACKLIST_URL = "https://megamarket.ru/promo/prodavtsy-s-oghranichieniiem-na-spisaniie-bonusov/"
BLACKLIST_FILE = "merchant_blacklist.txt"
UPDATE_INTERVAL = 86400  # 24 часа


def print_logo():
    console = Console()
    console.print("[blue bold]         ____ ___  ____ ___  ____  ____  _____________  _____")
    console.print("[blue bold]        / __ `__ \/ __ `__ \/ __ \/ __ `/ ___/ ___/ _ \/ ___/")
    console.print("[blue bold]       / / / / / / / / / / / /_/ / /_/ / /  (__  )  __/ /    ")
    console.print("[blue bold]      /_/ /_/ /_/_/ /_/ /_/ .___/\__,_/_/  /____/\___/_/     ")
    console.print("[blue bold]                         /_/\n")

    console.print("[white] Домашняя страница https://github.com/xob0t/mmparser")
    console.print("[green bold] ❤️ Сказать спасибо автору: https://yoomoney.ru/to/410018051351692")
    console.print("")


def slugify(text: str) -> str:
    # Convert to lowercase
    lowercase_text = text.lower()

    # Remove non-word characters and replace spaces with hyphens
    slug = re.sub(r"[^\w\s-]", "_", lowercase_text).strip().replace(" ", "_")

    return slug


def proxy_format_check(string: str) -> bool:
    protocols = ("http", "socks")
    for protocol in protocols:
        if string.startswith(protocol):
            return True
    return False


def validate_regex(pattern: str) -> bool:
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


def read_json_file(file_path: str) -> dict | list | bool:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            json_data = file.read()
            json_content = json.loads(json_data)
        return json_content
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return False


def remove_chars(text: str) -> str:
    for ch in ["#", "?", "!", ":", "<", ">", '"', "/", "\\", "|", "*"]:
        if ch in text:
            text = text.replace(ch, "")
    return text


def parse_blacklist_page() -> set[str]:
    response = requests.get(BLACKLIST_URL)
    html_content = response.text

    inns = []

    if _has_lxml:
        tree = html.fromstring(html_content)
        paragraphs = tree.xpath("//p/text()")
        for p in paragraphs:
            inn_matches = re.findall(r"ИНН\s*(\d+)", p)
            inns.extend(inn_matches)
    else:
        content_match = re.search(r"<h1>.*?</div>", html_content, re.DOTALL)
        if not content_match:
            raise ValueError("Не удалось найти нужную секцию на странице")
        relevant_content = content_match.group(0)
        inn_matches = re.findall(r"ИНН\s*(\d+)", relevant_content)
        inns.extend(inn_matches)

    inns = set(inns)
    return inns


def load_blacklist() -> set[str]:
    blacklist_path = Path(BLACKLIST_FILE)

    if blacklist_path.exists():
        file_age = time.time() - blacklist_path.stat().st_mtime
        if file_age < UPDATE_INTERVAL:
            with open(BLACKLIST_FILE, "r", encoding="UTF-8") as f:
                return f.read().splitlines()

    inns = parse_blacklist_page()
    with open(BLACKLIST_FILE, "w", encoding="UTF-8") as f:
        f.write("\n".join(inns))

    return inns


def get_current_version(package_name: str) -> str | None:
    try:
        current_version = pkg_resources.get_distribution(package_name).version
        return current_version
    except pkg_resources.DistributionNotFound:
        return None


def get_latest_version(package_name: str) -> str | None:
    url = f"https://api.github.com/repos/xob0t/{package_name}/releases/latest"

    try:
        response = requests.get(url, impersonate="chrome", timeout=2)
        response.raise_for_status()
        data = response.json()
        return data.get("tag_name", "")
    except Exception:
        return None


def check_for_new_version() -> None:
    console = Console()
    package_name = "mmparser"
    current_version = get_current_version(package_name)
    latest_version = get_latest_version(package_name)

    try:
        if version.parse(current_version) < version.parse(latest_version):
            console.print(f"[orange]Доступна новая версия [bold]{package_name}[/bold]. Текущая: v{current_version}, Последняя: {latest_version}")
        else:
            console.print(f"[green]Вы используете последнюю версию [bold]{package_name}[/bold] (v{current_version}).")
    except Exception:
        console.print("[red]Ошибка проверки новой версии.")


def parse_proxy_file(path: str) -> set[str]:
    if Path(path).exists():
        proxy_file_contents: str = open(path, "r", encoding="utf-8").read()
        return set(line for line in proxy_file_contents.split("\n") if line)
    raise exceptions.ConfigError(f"Путь {path} не найден!")


def parse_cookie_file(path: str) -> dict:
    if Path(path).exists():
        cookies: list = json.loads(open(path, "r", encoding="utf-8").read())
        return {cookie["name"]: cookie["value"] for cookie in cookies}
    raise exceptions.ConfigError(f"Путь {path} не найден!")
