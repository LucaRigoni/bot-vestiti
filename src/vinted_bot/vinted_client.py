from __future__ import annotations

from collections.abc import Mapping

from .models import VintedItem


class VintedClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._brand_cache: dict[str, int | None] = {}
        self._catalog_cache: dict[tuple[str, str], int | None] = {}
        self._catalog_options_cache: dict[str, list[str]] | None = None

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/json",
        }

    @staticmethod
    def _build_search_params(
        brand: str,
        max_price: float,
        per_page: int,
        brand_id: int | None,
        catalog_id: int | None,
    ) -> dict[str, str]:
        params = {
            "price_to": f"{max_price:.2f}",
            "currency": "EUR",
            "order": "newest_first",
            "per_page": str(per_page),
            "page": "1",
        }
        if brand_id is not None:
            params["brand_ids[]"] = str(brand_id)
        else:
            params["search_text"] = brand

        if catalog_id is not None:
            params["catalog_ids[]"] = str(catalog_id)

        return params

    @staticmethod
    def _extract_brand_id(payload: Mapping[str, object], brand: str) -> int | None:
        brands = payload.get("brands")
        if not isinstance(brands, list):
            return None

        target = brand.casefold()
        for entry in brands:
            if not isinstance(entry, Mapping):
                continue
            title = str(entry.get("title") or entry.get("name") or "").casefold()
            if title == target:
                try:
                    return int(entry["id"])
                except (KeyError, TypeError, ValueError):
                    return None

        if brands and isinstance(brands[0], Mapping):
            try:
                return int(brands[0]["id"])
            except (KeyError, TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _walk_catalog_tree(entries: list[object], output: list[Mapping[str, object]]) -> None:
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            output.append(entry)
            children = entry.get("catalogs")
            if isinstance(children, list):
                VintedClient._walk_catalog_tree(children, output)

    @staticmethod
    def _extract_catalog_options(payload: Mapping[str, object]) -> dict[str, list[str]]:
        catalogs = payload.get("catalogs")
        if not isinstance(catalogs, list):
            return {}

        options: dict[str, list[str]] = {}
        for entry in catalogs:
            if not isinstance(entry, Mapping):
                continue
            gender = str(entry.get("title") or entry.get("name") or "").strip()
            if not gender:
                continue
            children = entry.get("catalogs")
            if not isinstance(children, list):
                continue

            all_nodes: list[Mapping[str, object]] = []
            VintedClient._walk_catalog_tree(children, all_nodes)
            names: list[str] = []
            seen: set[str] = set()
            for node in all_nodes:
                title = str(node.get("title") or node.get("name") or "").strip()
                if not title:
                    continue
                folded = title.casefold()
                if folded in seen:
                    continue
                seen.add(folded)
                names.append(title)

            if names:
                options[gender] = names

        return options

    @staticmethod
    def _extract_catalog_id(payload: Mapping[str, object], gender: str, category: str) -> int | None:
        catalogs = payload.get("catalogs")
        if not isinstance(catalogs, list):
            return None

        gender_fold = gender.casefold()
        category_fold = category.casefold()

        gender_node: Mapping[str, object] | None = None
        for entry in catalogs:
            if not isinstance(entry, Mapping):
                continue
            title = str(entry.get("title") or entry.get("name") or "").casefold()
            if title == gender_fold:
                gender_node = entry
                break

        if gender_node is None:
            return None

        all_nodes: list[Mapping[str, object]] = []
        children = gender_node.get("catalogs")
        if isinstance(children, list):
            VintedClient._walk_catalog_tree(children, all_nodes)

        for node in all_nodes:
            title = str(node.get("title") or node.get("name") or "").casefold()
            if title == category_fold:
                try:
                    return int(node["id"])
                except (KeyError, TypeError, ValueError):
                    return None

        return None

    async def _fetch_catalog_payload(self) -> Mapping[str, object] | None:
        url = f"{self.base_url}/api/v2/catalogs"
        try:
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, headers=self._headers())
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, Mapping):
                    return payload
                return None
        except Exception:  # noqa: BLE001
            return None

    async def get_catalog_options(self) -> dict[str, list[str]]:
        if self._catalog_options_cache is not None:
            return self._catalog_options_cache

        payload = await self._fetch_catalog_payload()
        if payload is None:
            self._catalog_options_cache = {}
            return {}

        options = self._extract_catalog_options(payload)
        self._catalog_options_cache = options
        return options

    async def resolve_brand_id(self, brand: str) -> int | None:
        key = brand.casefold().strip()
        if key in self._brand_cache:
            return self._brand_cache[key]

        url = f"{self.base_url}/api/v2/brands"
        params = {"search_text": brand, "per_page": "20", "page": "1"}

        try:
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers=self._headers())
                response.raise_for_status()
                payload = response.json()
        except Exception:  # noqa: BLE001
            self._brand_cache[key] = None
            return None

        brand_id = self._extract_brand_id(payload, brand)
        self._brand_cache[key] = brand_id
        return brand_id

    async def resolve_catalog_id(self, gender: str, category: str) -> int | None:
        key = (gender.casefold().strip(), category.casefold().strip())
        if key in self._catalog_cache:
            return self._catalog_cache[key]

        payload = await self._fetch_catalog_payload()
        if payload is None:
            self._catalog_cache[key] = None
            return None

        catalog_id = self._extract_catalog_id(payload, gender, category)
        self._catalog_cache[key] = catalog_id
        return catalog_id

    async def search_items(
        self,
        brand: str,
        gender: str,
        category: str,
        max_price: float,
        per_page: int = 20,
    ) -> list[VintedItem]:
        url = f"{self.base_url}/api/v2/catalog/items"
        brand_id = await self.resolve_brand_id(brand)
        catalog_id = await self.resolve_catalog_id(gender, category)
        params = self._build_search_params(brand, max_price, per_page, brand_id, catalog_id)

        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=self._headers())
            response.raise_for_status()
            payload = response.json()

        items = payload.get("items", [])
        parsed: list[VintedItem] = []
        for item in items:
            item_id = int(item["id"])
            price = float(item.get("price", {}).get("amount", "0") or 0)
            path = item.get("url") or f"/items/{item_id}"
            full_url = path if path.startswith("http") else f"{self.base_url}{path}"

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
