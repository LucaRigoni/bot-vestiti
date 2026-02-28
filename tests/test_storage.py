from pathlib import Path

from vinted_bot.models import UserPreference
from vinted_bot.storage import PreferenceStore


def test_store_roundtrip(tmp_path: Path) -> None:
    store = PreferenceStore(tmp_path / "prefs.json")
    prefs = {
        123: UserPreference(
            chat_id=123,
            brand="Nike",
            gender="Uomo",
            category="Pantaloncini",
            max_price=9.9,
            seen_item_ids={1, 2, 3},
        )
    }

    store.save(prefs)
    loaded = store.load()

    assert loaded[123].brand == "Nike"
    assert loaded[123].gender == "Uomo"
    assert loaded[123].category == "Pantaloncini"
    assert loaded[123].max_price == 9.9
    assert loaded[123].seen_item_ids == {1, 2, 3}
