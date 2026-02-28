from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    polling_interval_seconds: int = 45
    vinted_base_url: str = "https://www.vinted.it"
    data_file: Path = Path("data/user_preferences.json")


BRANDS = [
    "Nike",
    "Adidas",
    "The North Face",
    "Stone Island",
    "Moncler",
    "Carhartt",
    "Ralph Lauren",
    "Tommy Hilfiger",
]


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Imposta TELEGRAM_BOT_TOKEN prima di avviare il bot.")

    interval_raw = os.getenv("POLLING_INTERVAL_SECONDS", "45")
    interval = max(15, int(interval_raw))

    base_url = os.getenv("VINTED_BASE_URL", "https://www.vinted.it").rstrip("/")
    data_file = Path(os.getenv("DATA_FILE", "data/user_preferences.json"))

    return Settings(
        telegram_token=token,
        polling_interval_seconds=interval,
        vinted_base_url=base_url,
        data_file=data_file,
    )
