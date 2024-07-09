import pathlib
import re
import json
import time
from curl_cffi import requests
from rich.console import Console
try:
    from lxml import html
except ImportError:
    _has_lxml = False
else:
    _has_lxml = True

BLACKLIST_URL = "https://megamarket.ru/promo/prodavtsy-s-oghranichieniiem-na-spisaniie-bonusov/"
BLACKLIST_FILE = "merchant_blacklist.txt"
UPDATE_INTERVAL = 86400  # 24 hours


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

def slugify(text):
    # Convert to lowercase
    lowercase_text = text.lower()

    # Remove non-word characters and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '_', lowercase_text).strip().replace(' ', '_')

    return slug

def proxy_format_check(string):
    protocols = ['http', 'socks']
    for protocol in protocols:
        if string.startswith(protocol):
            return True
    return False

def validate_regex(pattern):
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True

def convert_float(string):
    try:
        return float(string)
    except ValueError:
        return False

def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json_data = file.read()
            json_content = json.loads(json_data)
        return json_content
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return False

def remove_chars(text):
    for ch in ['#', '?', '!', ':', '<', '>', '"', '/', '\\', '|', '*']:
        if ch in text:
            text = text.replace(ch, '')
    return text

def parse_blacklist_page():
    response = requests.get(BLACKLIST_URL)
    html_content = response.text

    inns = []

    if _has_lxml:
        tree = html.fromstring(html_content)
        paragraphs = tree.xpath('//p/text()')
        for p in paragraphs:
            inn_matches = re.findall(r'ИНН\s*(\d+)', p)
            inns.extend(inn_matches)
    else:
        content_match = re.search(r'<h1>.*?</div>', html_content, re.DOTALL)
        if not content_match:
            raise ValueError("Не удалось найти нужную секцию на странице")
        relevant_content = content_match.group(0)
        inn_matches = re.findall(r'ИНН\s*(\d+)', relevant_content)
        inns.extend(inn_matches)

    inns = set(inns)
    return inns


def load_blacklist():
    blacklist_path = pathlib.Path(BLACKLIST_FILE)

    if blacklist_path.exists():
        file_age = time.time() - blacklist_path.stat().st_mtime
        if file_age < UPDATE_INTERVAL:
            with open(BLACKLIST_FILE, 'r') as f:
                return f.read().splitlines()

    inns = parse_blacklist_page()
    with open(BLACKLIST_FILE, 'w') as f:
        f.write('\n'.join(inns))

    return inns
