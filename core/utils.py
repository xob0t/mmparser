import re
import json
import time
from pathlib import Path
from dataclasses import dataclass
from curl_cffi import requests
from rich.console import Console

BLACKLIST_URL = "https://megamarket.ru/promo/prodavtsy-s-oghranichieniiem-na-spisaniie-bonusov/"
BLACKLIST_FILE = "merchant_blacklist.json"
UPDATE_INTERVAL = 86400  # 24 hours

@dataclass
class MerchantInfo:
    name: str
    inn: str

def print_logo():
    console = Console()
    console.print("[blue bold]         ____ ___  ____ ___  ____  ____  _____________  _____")
    console.print("[blue bold]        / __ `__ \/ __ `__ \/ __ \/ __ `/ ___/ ___/ _ \/ ___/")
    console.print("[blue bold]       / / / / / / / / / / / /_/ / /_/ / /  (__  )  __/ /    ")
    console.print("[blue bold]      /_/ /_/ /_/_/ /_/ /_/ .___/\__,_/_/  /____/\___/_/     ")
    console.print("[blue bold]                         /_/\n")

    console.print("[white] Домашняя страница https://github.com/xob0t/mmparser")
    console.print("[green bold] ❤️  Сказать спасибо автору: https://github.com/xob0t/mmparser#купить")
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

    content_match = re.search(r'<h1>.*?</div>', html_content, re.DOTALL)
    if not content_match:
        raise ValueError("Не удалось найти нужную секцию на странице")

    relevant_content = content_match.group(0)

    merchants = []
    pattern = r'(\d+\.\s*([^(]+)\s*\([^()]+ИНН\s*(\d+)[^)]*\))'
    matches = re.findall(pattern, relevant_content)

    for _, name, inn in matches:
        name = name.strip()
        inn = inn.strip()
        if name and inn:
            merchants.append(MerchantInfo(name=name, inn=inn))

    return merchants

def load_blacklist():
    if Path(BLACKLIST_FILE).exists():
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data['timestamp'] > time.time() - UPDATE_INTERVAL:
                return [MerchantInfo(**m) for m in data['merchants']]

    merchants = parse_blacklist_page()
    data = {'timestamp': time.time(), 'merchants': [m.__dict__ for m in merchants]}
    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return merchants
