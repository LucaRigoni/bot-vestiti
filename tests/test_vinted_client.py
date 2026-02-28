from vinted_bot.vinted_client import VintedClient


def test_build_search_params_uses_brand_and_catalog_and_newest_order() -> None:
    params = VintedClient._build_search_params(
        brand="Nike",
        max_price=30,
        per_page=20,
        brand_id=53,
        catalog_id=1234,
    )

    assert params["brand_ids[]"] == "53"
    assert params["catalog_ids[]"] == "1234"
    assert params["price_to"] == "30.00"
    assert params["order"] == "newest_first"
    assert "search_text" not in params


def test_extract_brand_id_prefers_exact_match() -> None:
    payload = {
        "brands": [
            {"id": 14, "title": "Nikelab"},
            {"id": 53, "title": "Nike"},
        ]
    }

    brand_id = VintedClient._extract_brand_id(payload, "Nike")

    assert brand_id == 53


def test_extract_catalog_id_for_gender_and_category() -> None:
    payload = {
        "catalogs": [
            {
                "id": 5,
                "title": "Uomo",
                "catalogs": [
                    {"id": 70, "title": "Pantaloni", "catalogs": []},
                    {"id": 71, "title": "Pantaloncini", "catalogs": []},
                ],
            },
            {
                "id": 1904,
                "title": "Donna",
                "catalogs": [
                    {"id": 2001, "title": "Vestiti", "catalogs": []},
                ],
            },
        ]
    }

    catalog_id = VintedClient._extract_catalog_id(payload, gender="Uomo", category="Pantaloncini")

    assert catalog_id == 71



def test_extract_catalog_options_maps_genders_to_categories() -> None:
    payload = {
        "catalogs": [
            {
                "title": "Uomo",
                "catalogs": [
                    {"title": "Pantaloni", "catalogs": []},
                    {"title": "Pantaloncini", "catalogs": []},
                ],
            },
            {
                "title": "Donna",
                "catalogs": [
                    {"title": "Vestiti", "catalogs": []},
                ],
            },
        ]
    }

    options = VintedClient._extract_catalog_options(payload)

    assert "Uomo" in options
    assert "Donna" in options
    assert "Pantaloni" in options["Uomo"]
    assert "Pantaloncini" in options["Uomo"]
    assert "Vestiti" in options["Donna"]
