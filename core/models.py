from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedOffer:
    title: str
    url: str
    image_url: str
    price: float
    price_bonus: int
    bonus_amount: int
    available_quantity: int
    goods_id: str
    delivery_date: str
    merchant_id: str
    merchant_name: str
    merchant_rating: Optional[bool] = field(default=None)
    notified: Optional[bool] = field(default=None)

    @property
    def bonus_percent(self) -> int:
        """Рассичать процент бонусов от цены"""
        if self.price == 0:
            return 0
        return int((self.bonus_amount / self.price) * 100)


class Connection:
    def __init__(self, proxy: str | None):
        self.proxy_string: str | None = proxy
        self.usable_at: float = 0
        self.busy = False
