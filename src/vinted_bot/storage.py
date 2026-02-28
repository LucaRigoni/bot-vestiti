from __future__ import annotations

import json
from pathlib import Path

from .models import UserPreference


class PreferenceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[int, UserPreference]:
        if not self.path.exists():
            return {}

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        prefs: dict[int, UserPreference] = {}
        for chat_id_str, value in raw.items():
            chat_id = int(chat_id_str)
            prefs[chat_id] = UserPreference(
                chat_id=chat_id,
                brand=value["brand"],
                max_price=float(value["max_price"]),
                seen_item_ids=set(value.get("seen_item_ids", [])),
            )
        return prefs

    def save(self, prefs: dict[int, UserPreference]) -> None:
        payload: dict[str, dict[str, object]] = {}
        for chat_id, pref in prefs.items():
            payload[str(chat_id)] = {
                "brand": pref.brand,
                "max_price": pref.max_price,
                "seen_item_ids": sorted(pref.seen_item_ids)[-500:],
            }

        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
