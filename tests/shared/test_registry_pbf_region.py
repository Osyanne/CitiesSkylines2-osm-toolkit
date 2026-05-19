"""Tests for shared.registry pbf_region handling."""
from __future__ import annotations

import json
from pathlib import Path

from shared.registry import load_cities, get_city


def test_load_city_with_pbf_region(tmp_path: Path):
    cities_file = tmp_path / "cities.json"
    cities_file.write_text(json.dumps({
        "test": {
            "display_name": "Test",
            "country": "X",
            "bbox": [0, 0, 1, 1],
            "center": [0.5, 0.5],
            "zoom": 12,
            "tagline": "",
            "locale": "es",
            "pbf_region": "europe/test-country",
        }
    }))
    cities = load_cities(cities_file)
    entry = get_city(cities, "test")
    assert entry["pbf_region"] == "europe/test-country"


def test_load_city_without_pbf_region_ok(tmp_path: Path):
    """pbf_region es opcional — ciudades sin él siguen siendo válidas (usan Overpass)."""
    cities_file = tmp_path / "cities.json"
    cities_file.write_text(json.dumps({
        "test": {
            "display_name": "Test",
            "country": "X",
            "bbox": [0, 0, 1, 1],
            "center": [0.5, 0.5],
            "zoom": 12,
            "tagline": "",
            "locale": "es",
        }
    }))
    cities = load_cities(cities_file)
    entry = get_city(cities, "test")
    assert "pbf_region" not in entry or entry.get("pbf_region") is None


def test_real_cities_json_has_pbf_region_for_minneapolis():
    """The actual cities.json must include pbf_region for Minneapolis."""
    cities_file = Path(__file__).resolve().parents[2] / "cities.json"
    cities = load_cities(cities_file)
    entry = get_city(cities, "minneapolis")
    assert entry.get("pbf_region") == "north-america/us/minnesota"
