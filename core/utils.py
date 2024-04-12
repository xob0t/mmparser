import re
import json
from rich.console import Console

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