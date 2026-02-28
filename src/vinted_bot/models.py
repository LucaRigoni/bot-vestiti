from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UserPreference:
    chat_id: int
    brand: str
    gender: str
    category: str
    max_price: float
    seen_item_ids: set[int] = field(default_factory=set)


@dataclass
class VintedItem:
    item_id: int
    title: str
    url: str
    price_eur: float
    image_url: str | None = None
