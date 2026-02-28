from __future__ import annotations

import httpx

from .models import VintedItem


class VintedClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def search_items(self, brand: str, max_price: float, per_page: int = 20) -> list[VintedItem]:
        url = f"{self.base_url}/api/v2/catalog/items"
        params = {
            "search_text": brand,
            "price_to": str(max_price),
            "currency": "EUR",
            "order": "newest_first",
            "per_page": str(per_page),
            "page": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        items = payload.get("items", [])
        parsed: list[VintedItem] = []
        for item in items:
            item_id = int(item["id"])
            price = float(item.get("price", {}).get("amount", "0") or 0)
            path = item.get("url") or f"/items/{item_id}"
            if path.startswith("http"):
                full_url = path
            else:
                full_url = f"{self.base_url}{path}"

            parsed.append(
                VintedItem(
                    item_id=item_id,
                    title=item.get("title", "Articolo"),
                    url=full_url,
                    price_eur=price,
                    image_url=(item.get("photo") or {}).get("url"),
                )
            )
        return parsed
