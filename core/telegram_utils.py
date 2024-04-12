from curl_cffi import requests

def validate_credentials(tg_config):
    def is_valid_token(bot_token):
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        return requests.get(url).ok

    def is_valid_chat_id(bot_token, chat_id):
        url = f"https://api.telegram.org/bot{bot_token}/getChat?chat_id={chat_id}"
        return requests.get(url).ok
    try:
        bot_token = tg_config.split('$')[0]
        chat_id = tg_config.split('$')[1]
    except IndexError:
        return False
    if not bot_token or not chat_id:
        return False
    if not is_valid_token(bot_token) or not is_valid_chat_id(bot_token, chat_id):
        return False
    return True

class Telegram:
    def __init__(self, tg_config, logger):
        self.bot_token = tg_config.split('$')[0]
        self.chat_id = tg_config.split('$')[1]
        self.logger = logger
        if not self.bot_token or not self.chat_id:
            raise Exception("Не валидный конфиг Telegram!")
    def notify(self, message, image_url = None):
        if image_url:
            base_url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            params = {
                'chat_id': self.chat_id,
                'caption': message,
                'photo': image_url,
                'parse_mode': 'HTML'
            }
            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                self.logger.info("Уведомление успешно отправлено!")
            except Exception as e:
                self.logger.info(f"Ошибка отправки сообщения с картинкой: {e}")
        else:
            base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            params = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                self.logger.info("Сообщение успешно отправлено!")
            except Exception as e:
                self.logger.info(f"Ошибка отправки сообщения: {e}")