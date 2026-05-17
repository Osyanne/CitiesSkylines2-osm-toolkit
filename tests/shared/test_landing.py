"""Tests del generador de landing (index.html)."""
import sys, os, json
from pathlib import Path
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from shared.landing import build_landing_html


def _city_entry(name="Test", country="USA", tagline="t"):
    return {
        "display_name": name, "country": country,
        "bbox": [44.86, -93.38, 45.05, -93.17],
        "center": [44.97, -93.27], "zoom": 12,
        "tagline": tagline, "locale": "es"
    }


def test_landing_html_has_one_card_per_city():
    cities = {
        "minneapolis": _city_entry("Minneapolis, MN"),
        "manhattan": _city_entry("Manhattan, NYC"),
    }
    manifests = {
        "minneapolis": {"modules": {"zoning": {"hash": "a", "features": 100},
                                     "vial": {"hash": "b", "features": 200},
                                     "services": {"hash": "c", "features": 50}}},
        "manhattan": {"modules": {"zoning": {"hash": "d", "features": 500}}},
    }
    html = build_landing_html(cities, manifests)
    assert html.count('class="city-card"') == 2
    assert 'href="map.html?city=minneapolis"' in html
    assert 'href="map.html?city=manhattan"' in html
    assert "Minneapolis, MN" in html
    assert "Manhattan, NYC" in html


def test_landing_html_shows_module_badges():
    cities = {
        "minneapolis": _city_entry("Mpls"),
        "manhattan": _city_entry("Man"),
    }
    manifests = {
        "minneapolis": {"modules": {"zoning": {"hash":"a","features":1},
                                     "vial": {"hash":"b","features":1},
                                     "services": {"hash":"c","features":1}}},
        "manhattan": {"modules": {"zoning": {"hash":"d","features":1}}},
    }
    html = build_landing_html(cities, manifests)
    mpls_section = html[html.index("Mpls"):html.index("Man")]
    assert "Zoning" in mpls_section
    assert "Vial" in mpls_section
    assert "Servicios" in mpls_section
    man_section = html[html.index("Man"):]
    assert "Zoning" in man_section
    assert "Vial" not in man_section
    assert "Servicios" not in man_section


def test_landing_html_shows_feature_counts():
    cities = {"madison": _city_entry("Madison")}
    manifests = {"madison": {"modules": {"zoning": {"hash":"x","features":12345}}}}
    html = build_landing_html(cities, manifests)
    assert "12" in html


def test_landing_html_handles_city_without_manifest():
    """Ciudad en registro pero sin manifest (ej. recién agregada, no extraída aún)."""
    cities = {"future_city": _city_entry("Future")}
    manifests = {}
    html = build_landing_html(cities, manifests)
    assert "Future" in html
    assert "Sin datos" in html or "pending" in html.lower()


def test_landing_html_includes_request_city_cta():
    cities = {"madison": _city_entry("Madison")}
    manifests = {"madison": {"modules": {"zoning": {"hash":"x","features":1}}}}
    html = build_landing_html(cities, manifests)
    assert "city-request" in html.lower() or "request" in html.lower()
    assert "github.com" in html.lower() or "issues/new" in html.lower()
