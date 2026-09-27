"""
Tests para shared/thumbnails.py — solo el discovery puro (sin playwright).

El path de captura via Chromium se valida manualmente porque requiere el binario
de Chromium instalado + acceso a red al deployed Pages.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest

from shared.thumbnails import discover_missing
from shared.registry import CityNotFoundError


SAMPLE_CITIES = {
    "minneapolis": {"display_name": "Minneapolis, MN"},
    "amsterdam":   {"display_name": "Amsterdam"},
    "trondheim":   {"display_name": "Trondheim"},
}


# ── discover_missing — only_city path ───────────────────────────────────────

def test_only_city_returns_that_slug(tmp_path):
    slugs = discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city="amsterdam")
    assert slugs == ["amsterdam"]


def test_only_city_overrides_existing_png(tmp_path):
    """Aunque el PNG ya exista, --city lo incluye igual (idempotente regen)."""
    (tmp_path / "amsterdam.png").write_bytes(b"\x89PNG fake")
    slugs = discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city="amsterdam")
    assert slugs == ["amsterdam"]


def test_only_city_unknown_slug_raises(tmp_path):
    with pytest.raises(CityNotFoundError, match="atlantis"):
        discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city="atlantis")


# ── discover_missing — force path ───────────────────────────────────────────

def test_force_returns_all_slugs_sorted(tmp_path):
    # Aún con PNGs presentes, --force las regenera todas
    for slug in SAMPLE_CITIES:
        (tmp_path / f"{slug}.png").write_bytes(b"\x89PNG")
    slugs = discover_missing(SAMPLE_CITIES, tmp_path, force=True, only_city=None)
    assert slugs == sorted(SAMPLE_CITIES.keys())


# ── discover_missing — default (missing-only) path ──────────────────────────

def test_default_returns_only_missing(tmp_path):
    """PNG existente → skip; PNG missing → incluido."""
    (tmp_path / "minneapolis.png").write_bytes(b"\x89PNG")
    (tmp_path / "amsterdam.png").write_bytes(b"\x89PNG")
    # trondheim.png NO existe → debería ser el único en el output
    slugs = discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city=None)
    assert slugs == ["trondheim"]


def test_default_returns_empty_when_all_present(tmp_path):
    for slug in SAMPLE_CITIES:
        (tmp_path / f"{slug}.png").write_bytes(b"\x89PNG")
    slugs = discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city=None)
    assert slugs == []


def test_default_returns_all_when_none_present(tmp_path):
    slugs = discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city=None)
    assert slugs == sorted(SAMPLE_CITIES.keys())


def test_output_is_always_sorted_for_reproducibility(tmp_path):
    slugs_force = discover_missing(SAMPLE_CITIES, tmp_path, force=True, only_city=None)
    assert slugs_force == sorted(slugs_force)

    slugs_default = discover_missing(SAMPLE_CITIES, tmp_path, force=False, only_city=None)
    assert slugs_default == sorted(slugs_default)


# ── La miniatura muestra solo zonificación, para que todas las tarjetas se vean igual ──

def test_zoning_only_js_turns_off_other_modules():
    """Presiona Off en los controles On/Dim/Off de la columna, menos en zoning."""
    from shared.thumbnails import _zoning_only_js
    js = _zoning_only_js()
    assert '[data-module-state="off"]' in js
    assert "[data-module]" in js
    assert "zoning" in js


def test_zoning_only_js_is_a_callable_arrow_for_page_evaluate():
    from shared.thumbnails import _zoning_only_js
    assert _zoning_only_js().startswith("()")


# ── El chrome del visor (columna de capas, título, controles) no sale en la foto ──

def test_hide_chrome_js_hides_layers_column_and_widens_map():
    from shared.thumbnails import _hide_chrome_js
    js = _hide_chrome_js()
    assert "#layers-col" in js
    assert "#layers-open" in js
    assert "#title-header" in js
    # Sin la columna el mapa tiene que ocupar todo el ancho
    assert "col-open" in js
    assert "CS2_MAP.resize()" in js


def test_chrome_js_does_not_target_removed_controls():
    """Las pills, la leyenda y el panel de capas viejos ya no existen."""
    from shared.thumbnails import _hide_chrome_js, _zoning_only_js
    for js in (_hide_chrome_js(), _zoning_only_js()):
        for gone in ("master-toggle", "#header-controls", ".legend", ".cs2-layers", "#fondo"):
            assert gone not in js


def test_column_starts_closed_in_captures():
    """El init script cierra la columna antes de que cargue el visor."""
    from shared.thumbnails import _start_with_column_closed_js
    js = _start_with_column_closed_js()
    assert "cs2-layers-col-v1" in js
    assert "'0'" in js


def test_selectors_match_the_viewer():
    """La clave de la columna y los selectores existen en visualizer/map.html."""
    from pathlib import Path
    map_html = (Path(__file__).resolve().parents[2] / "visualizer" / "map.html").read_text(encoding="utf-8")
    assert '"cs2-layers-col-v1"' in map_html
    assert 'id="layers-col"' in map_html
    assert 'id="layers-open"' in map_html
    assert 'data-module-state="${s}"' in map_html
    assert "window.CS2_MAP = map" in map_html
