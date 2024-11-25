import unittest
from core.parser_url import Parser_url


class TestMain(unittest.TestCase):
    def test_parse(self):
        parser_instance = Parser_url(url="https://megamarket.ru/catalog/?q=lays%20%D0%B8%D0%B7%20%D0%BF%D0%B5%D1%87%D0%B8&suggestionType=constructor", log_level="DEBUG")
        parser_instance.parse()


if __name__ == "__main__":
    unittest.main()
