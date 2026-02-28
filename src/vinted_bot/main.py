from __future__ import annotations

from .bot import BotRuntime, build_application
from .config import load_settings
from .storage import PreferenceStore
from .vinted_client import VintedClient


def main() -> None:
    settings = load_settings()
    store = PreferenceStore(settings.data_file)
    runtime = BotRuntime(
        settings=settings,
        store=store,
        client=VintedClient(settings.vinted_base_url),
        preferences=store.load(),
    )

    app = build_application(runtime)
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
