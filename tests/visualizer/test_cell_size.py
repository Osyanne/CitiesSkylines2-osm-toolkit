"""
Tamaño de la zona en la ficha: área del polígono entero y su equivalencia en celdas de
8 × 8 m (área ÷ 64). Pendiente de la etapa 6c del visor.

Mismo arreglo que los demás tests del visor: Chromium (Playwright) contra un http.server
local, fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

El área la calcula shared/tiles.py antes de cortar (propiedad `m2`, 2 cifras): sin teselas,
el visor la saca de los datos.
"""
import json
import math
import re

import pytest

from .test_compare import ALL_OFF, CompareViewer
from .test_playable_frame import CITY
from .test_url_state import MPLS, base_url, browser, viewer  # noqa: F401 (fixtures)

pytestmark = [pytest.mark.network, pytest.mark.browser]

SIZE = re.compile(r"^≈ (\d[\d,]*) m² · (?:≈ (\d[\d,]*) cells?|less than 1 cell)$")
RESIDENTIAL = (-93.2450, 44.9300)    # Powderhorn: casas chicas y medianas
DOWNTOWN = (-93.2650, 44.9778)

# Un punto del canvas donde la feature de arriba de `layer` tiene m2 en [lo, hi) (m2 = null
# pide una feature SIN m2), sin la otra capa (zonas o calles) a menos de 5 px.
# Prueba primero el promedio de los vértices de cada feature (sirve para las chicas) y
# después una grilla de 12 px (para los polígonos grandes con edificios encima).
FIND_JS = """([layer, lo, hi]) => {
  const map = window.CS2_MAP, c = map.getCanvas();
  const w = c.clientWidth, h = c.clientHeight;
  const ok = m2 => lo === null ? m2 === undefined : m2 >= lo && m2 < hi;
  const other = ['zoning-fill', 'vial-line'].filter(id => id !== layer && map.getLayer(id));
  const at = p => {
    if (p[0] < w * 0.25 || p[0] > w * 0.75 || p[1] < h * 0.15 || p[1] > h * 0.85) return null;
    const box = [[p[0] - 5, p[1] - 5], [p[0] + 5, p[1] + 5]];
    const here = map.queryRenderedFeatures(layer === 'zoning-fill' ? p : box, {layers: [layer]});
    // La primera es la de arriba, la que elige el click (un edificio sobre un polígono de uso de suelo)
    if (!here.length || !ok(here[0].properties.m2)) return null;
    const f = here[0].properties;
    if (other.length && map.queryRenderedFeatures(box, {layers: other}).length) return null;
    return {p, m2: f.m2 ?? null, k: f.k};
  };
  for (const f of map.queryRenderedFeatures({layers: [layer]})) {
    if (!ok(f.properties.m2)) continue;
    const g = f.geometry;
    const pts = g.type === 'Polygon' ? g.coordinates[0] : g.type === 'LineString' ? g.coordinates.slice(0, 2) : null;
    if (!pts || !pts.length) continue;
    const q = map.project(pts.reduce((s, v) => [s[0] + v[0] / pts.length, s[1] + v[1] / pts.length], [0, 0]));
    const hit = at([q.x, q.y]);
    if (hit) return hit;
  }
  for (let y = h * 0.15; y <= h * 0.85; y += 12) {
    for (let x = w * 0.25; x <= w * 0.75; x += 12) {
      const hit = at([x, y]);
      if (hit) return hit;
    }
  }
  return null;
}"""


def js_round(x):
    """Math.round de JS: las mitades hacia arriba."""
    return math.floor(x + 0.5)


def parse(text):
    m = SIZE.match(text)
    assert m, f"formato inesperado: {text!r}"
    area = int(m.group(1).replace(",", ""))
    cells = int(m.group(2).replace(",", "")) if m.group(2) else 0
    return area, cells


class SizeViewer(CompareViewer):
    def find_feature(self, layer, lo, hi, places, zoom):
        for lng, lat in places:
            self.jump(lng, lat, zoom)
            self.settle()
            hit = self.page.evaluate(FIND_JS, [layer, lo, hi])
            if hit:
                return hit
        pytest.fail(f"no encontré en {layer} ninguna feature con m2 en [{lo}, {hi}) en {places}")

    def size(self):
        el = self.page.locator("#selection .sel-size")
        return el.inner_text().strip() if el.count() else None


@pytest.fixture
def sv(viewer):
    def make(slug=MPLS, hash_=f"layers={ALL_OFF}", **kwargs):
        v = viewer(**kwargs)
        s = SizeViewer(v.page, v.base)
        s.open(slug, hash_)
        return s
    return make


def test_the_card_shows_area_and_cells(sv):
    v = sv()
    hit = v.find_feature("zoning-fill", 200, 5000, (RESIDENTIAL, DOWNTOWN), 17)
    v.click(hit["p"])
    area, cells = parse(v.size())
    assert area == hit["m2"]                     # las teselas ya traen 2 cifras
    assert cells == js_round(area / 64)
    title = v.page.get_attribute("#selection .sel-size", "title")
    assert "8 × 8 m" in title and "roads" in title
    assert not v.errors


def test_big_areas_use_thousands_separators(sv):
    v = sv()
    hit = v.find_feature("zoning-fill", 64_000, math.inf, (DOWNTOWN, RESIDENTIAL), 15)
    v.click(hit["p"])
    text = v.size()
    area, cells = parse(text)
    assert area == hit["m2"] and "," in text.split(" m²")[0]
    assert cells == js_round(area / 64) and cells >= 1000


def test_the_smallest_buildings_are_one_cell(sv):
    # El extractor descarta lo de menos de 50 m², así que "less than 1 cell" no sale con datos reales
    v = sv()
    hit = v.find_feature("zoning-fill", 50, 96, (RESIDENTIAL, DOWNTOWN), 18)
    v.click(hit["p"])
    assert v.size() == f"≈ {hit['m2']} m² · ≈ 1 cell"


def test_roads_and_plan_districts_have_no_size(sv):
    v = sv(hash_="layers=zoning.off,services.off,transporte.off,infraestructura.off")
    hit = v.find_feature("vial-line", None, None, (DOWNTOWN, RESIDENTIAL), 16)
    v.click(hit["p"])
    assert v.size() is None

    w = sv()
    w.compare()
    district = w.find("district_only")
    w.click(district["p"])
    assert w.size() is None
    assert not v.errors and not w.errors


def test_without_tiles_the_viewer_computes_the_area(sv, viewer):
    """Sin teselas (manifest sin `tiles`) el visor calcula el área de los datos completos."""
    w = viewer()
    v = SizeViewer(w.page, w.base)

    def drop_tiles(route):
        manifest = json.loads(route.fetch().text())
        manifest.pop("tiles", None)
        route.fulfill(content_type="application/json", body=json.dumps(manifest))

    v.page.route(f"**/cities/{CITY}/manifest.json*", drop_tiles)
    v.open(CITY)
    v.wait("() => window.CS2_MAP.getSource('cs2-zoning')?.type === 'geojson'")
    assert not v.page.evaluate("() => !!window.CS2_MAP.getSource('cs2')")
    center = v.page.evaluate("() => { const c = window.CS2_MAP.getCenter(); return [c.lng, c.lat]; }")
    hit = v.find_feature("zoning-fill", 200, 5000, [center], 17)
    v.click(hit["p"])
    area, cells = parse(v.size())
    assert abs(area - hit["m2"]) <= hit["m2"] * 0.05   # exacto en los datos, 2 cifras en la ficha
    assert cells == js_round(area / 64)
    assert not v.errors
