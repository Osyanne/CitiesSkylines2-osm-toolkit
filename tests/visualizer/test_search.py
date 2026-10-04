"""
El buscador con Nominatim (etapa 6d del visor).

Mismo arreglo que los demás tests del visor: Chromium (Playwright) contra un http.server
local, fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

**Nunca consulta la API real de Nominatim** (su política lo pide): `page.route` intercepta
el endpoint y responde con resultados armados.

Contrato: docs/plans/2026-09-26-layout-visor/12-etapa-6d-spec.md
"""
import json
import re
import time
from urllib.parse import parse_qs, urlparse

import pytest

from .test_frame_export import FRAME
from .test_measure import MeasureViewer
from .test_playable_frame import CITY
from .test_url_state import base_url, browser, viewer  # noqa: F401 (fixtures)

pytestmark = [pytest.mark.network, pytest.mark.browser]

NOMINATIM = re.compile(r"nominatim\.openstreetmap\.org/search")
CITY_BBOX = (43.463635, -96.841049, 43.602273, -96.629906)   # s, w, n, e


def result(name, lat, lon, kind="residential", line=True):
    """Un resultado jsonv2 de Nominatim: una calle norte-sur de ~3 km."""
    s, n = lat - 0.015, lat + 0.015
    item = {
        "place_id": abs(hash(name)) % 10_000_000, "lat": f"{lat}", "lon": f"{lon}",
        "name": name, "display_name": f"{name}, Downtown, Sioux Falls, Minnehaha County, South Dakota, United States",
        "category": "highway", "type": kind,
        "boundingbox": [f"{s}", f"{n}", f"{lon - 0.0005}", f"{lon + 0.0005}"],
    }
    if line:
        item["geojson"] = {"type": "LineString", "coordinates": [[lon, s], [lon, n]]}
    return item


RESULTS = {
    "Phillips": [result("Phillips Avenue", 43.5470, -96.7280), result("Phillips Park", 43.5200, -96.7400, "park", line=False)],
    "Minnesota": [result("Minnesota Avenue", 43.5400, -96.7420)],
    "fast": [result("Fast Street", 43.5300, -96.7100)],
    "slow": [result("Slow Street", 43.5600, -96.7600)],
    "nothing": [],
}


class SearchViewer(MeasureViewer):
    def mock(self, responses=RESULTS, hold=()):
        """Intercepta Nominatim. Devuelve la lista de consultas recibidas y la de rutas retenidas."""
        calls, held = [], []

        def handle(route):
            req = route.request
            params = {k: v[0] for k, v in parse_qs(urlparse(req.url).query).items()}
            calls.append({"params": params, "referer": req.headers.get("referer", ""), "t": time.monotonic()})
            q = params.get("q", "")
            if q in hold:
                held.append((route, q))
                return
            answer = responses.get(q, [])
            if isinstance(answer, int):
                route.fulfill(status=answer, body="", headers={"Access-Control-Allow-Origin": "*"})
            else:
                route.fulfill(status=200, body=json.dumps(answer),
                              headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"})

        self.page.context.route(NOMINATIM, handle)
        return calls, held

    def open_search(self):
        self.page.click("#search-open")
        self.wait("() => { const p = document.getElementById('search-panel'); return p && !p.hidden; }")

    def search(self, query):
        self.page.fill("#search-input", query)
        self.page.press("#search-input", "Enter")

    def wait_results(self):
        self.wait("() => !document.getElementById('search-results').hidden && document.querySelectorAll('#search-results [role=option]').length > 0")

    def options(self):
        return self.page.evaluate("() => [...document.querySelectorAll('#search-results [role=option]')].map(o => o.textContent.trim())")

    def search_status(self):
        return self.page.inner_text("#search-status").strip()

    def search_geometry(self):
        return self.page.evaluate("""async () => {
          const src = window.CS2_MAP.getSource('cs2-search');
          if (!src) return null;
          return ((await src.getData()).features || []).map(f => f.geometry.type);
        }""")


@pytest.fixture
def sv(viewer):
    def make(**kwargs):
        v = viewer(**kwargs)
        return SearchViewer(v.page, v.base)
    return make


# ── Configuración ───────────────────────────────────────────────────────────

def test_no_button_when_search_is_disabled(sv):
    v = sv()
    v.page.context.route("**/search-config.json", lambda route: route.fulfill(
        status=200, body='{"enabled": false}', headers={"Content-Type": "application/json"}))
    v.open(CITY)
    assert v.page.locator("#search-open").count() == 0 or v.page.is_hidden("#search-open")
    v.assert_no_errors()


# ── La consulta y la política ───────────────────────────────────────────────

def test_typing_sends_nothing_and_enter_sends_one_identified_request(sv):
    v = sv()
    calls, _ = v.mock()
    v.open(CITY)
    v.open_search()
    v.page.click("#search-input")
    v.page.keyboard.type("Phillips", delay=80)
    v.page.wait_for_timeout(1500)
    assert calls == [], "consultó mientras se escribía (la política lo prohíbe)"
    v.page.keyboard.press("Enter")
    v.wait_results()
    assert len(calls) == 1
    p = calls[0]["params"]
    assert p["q"] == "Phillips" and p["format"] == "jsonv2"
    assert p["bounded"] == "1" and p["limit"] == "8" and p["polygon_geojson"] == "1"
    assert p.get("accept-language")
    w, n, e, s = map(float, p["viewbox"].split(","))
    assert (s, w, n, e) == pytest.approx(CITY_BBOX, abs=1e-6)
    # La URL completa de la página (no solo el origen): identifica al proyecto. En el
    # servidor del test visualizer/ es la raíz; en Pages es …/visualizer/map.html
    assert calls[0]["referer"].endswith(f"/map.html?city={CITY}"), calls[0]["referer"]
    assert "Nominatim" in v.page.inner_text("#search-panel")      # atribución visible
    v.assert_no_errors()


def test_repeated_query_comes_from_the_cache(sv):
    v = sv()
    calls, _ = v.mock()
    v.open(CITY)
    v.open_search()
    v.search("Phillips")
    v.wait_results()
    v.page.wait_for_timeout(1100)
    v.search("  Phillips  ")                       # misma consulta normalizada
    v.page.press("#search-input", "Enter")
    v.page.wait_for_timeout(1500)
    assert len(calls) == 1, [c["params"]["q"] for c in calls]
    v.wait_results()
    v.assert_no_errors()


def test_one_request_per_second_and_only_the_latest_waits(sv):
    v = sv()
    calls, _ = v.mock()
    v.open(CITY)
    v.open_search()
    # Las tres en el mismo instante, desde la página: con WebGL por software cada
    # fill/press de Playwright puede tardar más de un segundo
    v.page.evaluate("""() => {
      const input = document.getElementById('search-input'), form = input.closest('form');
      for (const q of ['Phillips', 'Minnesota', 'fast']) { input.value = q; form.requestSubmit(); }
    }""")
    v.page.wait_for_function("() => document.getElementById('search-results').textContent.includes('Fast Street')",
                             timeout=10_000)
    queries = [c["params"]["q"] for c in calls]
    # Phillips puede no llegar a la red: la aborta la siguiente en el mismo instante.
    # Minnesota espera su turno y la reemplaza fast: nunca sale
    assert "Minnesota" not in queries and queries[-1] == "fast", queries
    assert queries in (["fast"], ["Phillips", "fast"]), queries
    assert all(b["t"] - a["t"] >= 0.95 for a, b in zip(calls, calls[1:]))
    v.assert_no_errors()


def test_a_late_response_does_not_overwrite_the_new_one(sv):
    v = sv()
    calls, held = v.mock(hold=("slow",))
    v.open(CITY)
    v.open_search()
    v.search("slow")
    v.page.wait_for_timeout(1100)
    v.search("fast")
    v.page.wait_for_function("() => document.getElementById('search-results').textContent.includes('Fast Street')",
                             timeout=10_000)
    for route, q in held:
        try:
            route.fulfill(status=200, body=json.dumps(RESULTS[q]),
                          headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"})
        except Exception:
            pass                                    # la consulta vieja ya estaba abortada
    v.page.wait_for_timeout(600)
    assert any("Fast Street" in o for o in v.options())
    assert not any("Slow Street" in o for o in v.options())


def test_busy_and_no_results_messages(sv):
    v = sv()
    calls, _ = v.mock({**RESULTS, "busy": 429})
    v.open(CITY)
    v.open_search()
    v.search("busy")
    v.wait("() => document.getElementById('search-status').textContent.includes('busy')")
    v.page.wait_for_timeout(1100)
    v.search("nothing")
    v.wait("() => document.getElementById('search-status').textContent.includes('No results in')")
    assert len(calls) == 2                          # sin reintentos automáticos


# ── Elegir un resultado ─────────────────────────────────────────────────────

def test_choosing_a_result_frames_it_with_pin_and_highlight(sv):
    v = sv()
    v.mock()
    v.open(CITY)
    v.open_search()
    v.search("Phillips")
    v.wait_results()
    assert v.page.get_attribute("#search-results", "role") == "listbox"
    assert v.page.get_attribute("#search-input", "aria-expanded") == "true"
    assert len(v.options()) == 2 and "Phillips Avenue" in v.options()[0]
    v.page.press("#search-input", "ArrowDown")
    first = v.page.locator("#search-results [role=option]").first
    assert first.get_attribute("aria-selected") == "true"
    assert v.page.get_attribute("#search-input", "aria-activedescendant") == first.get_attribute("id")
    v.page.press("#search-input", "Enter")
    v.wait("() => document.getElementById('search-results').hidden")
    v.idle()
    cam = v.camera()
    assert cam["zoom"] <= 17.0001
    assert 43.532 <= cam["lat"] <= 43.562 and -96.730 <= cam["lng"] <= -96.726
    assert v.page.is_visible(".search-pin")
    assert v.search_geometry() == ["LineString"] and v.visible("cs2-search-line")
    v.assert_no_errors()


def test_escape_closes_list_then_search_and_cleans_up(sv):
    v = sv()
    v.mock()
    v.open(CITY)
    v.open_search()
    v.search("Phillips")
    v.wait_results()
    v.page.press("#search-input", "Escape")
    v.wait("() => document.getElementById('search-results').hidden")
    assert v.page.is_visible("#search-panel")
    v.page.press("#search-input", "Enter")         # la misma consulta, desde la caché
    v.wait_results()
    v.page.locator("#search-results [role=option]").first.click()
    v.wait("() => document.querySelector('.search-pin') !== null")
    v.page.focus("#search-input")
    v.page.keyboard.press("Escape")
    v.wait("() => document.getElementById('search-panel').hidden")
    assert v.page.evaluate("() => document.activeElement.id") == "search-open"
    assert v.page.locator(".search-pin").count() == 0
    assert not v.search_geometry() or not v.visible("cs2-search-line")
    v.assert_no_errors()


def test_opening_search_finishes_measure(sv):
    v = sv()
    v.mock()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    v.click(400, 400)
    v.click(700, 400)
    v.open_search()
    assert not v.measuring()
    assert len(v.points()) == 2                      # la medición válida queda
    v.assert_no_errors()


def test_search_highlight_stays_out_of_the_png(sv):
    v = sv()
    v.open(CITY, FRAME)
    every = ",".join(v.catalog("zoning"))
    w = sv()
    w.mock()
    w.open(CITY, f"{FRAME}&hide.zoning={every}")
    w.open_search()
    w.search("Phillips")
    w.wait_results()
    w.page.press("#search-input", "ArrowDown")
    w.page.press("#search-input", "Enter")
    w.wait("() => document.querySelector('.search-pin') !== null")
    _, data = w.export(size=2048, bg="transparent")
    s = w.stats(data)
    assert s["painted"] < 500, f"{s['painted']} píxeles pintados: el resaltado entró en el PNG"
    v.assert_no_errors()
    w.assert_no_errors()


# ── Celular ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("viewport", [(390, 844), (844, 390)], ids=["vertical", "apaisado"])
def test_search_panel_fits_on_a_phone(sv, viewport):
    v = sv(viewport=viewport, is_mobile=True, has_touch=True)
    v.mock()
    v.open(CITY)
    v.open_search()
    v.search("Phillips")
    v.wait_results()
    panel = v.page.locator("#search-panel").bounding_box()
    assert panel["x"] >= 0 and panel["x"] + panel["width"] <= viewport[0] + 0.5
    assert panel["y"] + panel["height"] <= viewport[1] + 0.5
    row = v.page.locator("#title-ctrl").bounding_box()
    assert panel["y"] >= row["y"] + row["height"] - 1, f"el panel {panel} se monta sobre la fila de la cabecera {row}"
    v.assert_no_errors()
