"""
`Compare`: la zonificación OSM con los contornos del plan oficial encima (etapa 5 del visor).

Mismo arreglo que los demás tests del visor: Chromium (Playwright) contra un http.server
local, fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

Contrato: docs/plans/2026-09-26-layout-visor/13-etapa-5-spec.md
"""
import re

import pytest

from .test_frame_export import ExportViewer
from .test_url_state import MPLS, base_url, browser, viewer  # noqa: F401 (fixtures)

pytestmark = [pytest.mark.network, pytest.mark.browser]

PLAN = "2040 Plan"
PLAN_FULL = "Mpls 2040 Plan — Primary Land Use"
DOWNTOWN = (-93.2650, 44.9778)
SUBURB = (-93.3500, 44.9400)       # St. Louis Park: dentro del bbox, fuera del plan
COMPARE_LAYERS = ["official-compare-hit", "official-compare-casing", "official-compare-line"]
OSM_LAYERS = ["zoning-fill", "zoning-line", "zoning-line-lowconf", "zoning-hover"]
OFFICIAL_LAYERS = ["official-fill", "official-line", "official-hover"]
FORBIDDEN = re.compile(r"\b(error|wrong|mismatch|incorrect|conflict)\b|≠", re.I)
ALL_OFF = "vial.off,services.off,transporte.off,infraestructura.off"

# Recorre una grilla del canvas y devuelve el primer punto que cumple `kind`.
# osm: zona del edificio bajo el punto (o null); plan: distritos bajo el punto.
FIND_JS = """([kind, y0, y1]) => {
  const map = window.CS2_MAP, c = map.getCanvas();
  const w = c.clientWidth, h = c.clientHeight;
  const near = (p, r) => [[p[0] - r, p[1] - r], [p[0] + r, p[1] + r]];
  const q = (g, layer) => map.queryRenderedFeatures(g, {layers: [layer]});
  for (let fy = y0; fy <= y1; fy += 0.015) {
    for (let fx = 0.2; fx <= 0.8; fx += 0.015) {
      const p = [w * fx, h * fy];
      const osm = q(near(p, 4), 'zoning-fill');
      const plan = q(p, 'official-compare-hit');
      const planNear = q(near(p, 4), 'official-compare-hit');
      const ks = new Set(osm.map(f => f.properties.k));
      const o = ks.size === 1 ? [...ks][0] : null;
      const pk = plan.map(f => f.properties.k);
      let ok = false;
      if (kind === 'differ') ok = o && osm.length && plan.length === 1 && planNear.length === 1 && pk[0] !== o;
      if (kind === 'same') ok = o && osm.length && plan.length === 1 && planNear.length === 1 && pk[0] === o;
      if (kind === 'outside') ok = o && osm.length && !planNear.length;
      if (kind === 'district_only') ok = !osm.length && plan.length === 1 && planNear.length === 1;
      if (ok) return {p, osm: o, plan: plan.map(f => ({k: f.properties.k, a: f.properties.a, id: f.id}))};
    }
  }
  return null;
}"""

# Distritos anidados: puntos con dos o más distritos de zonas distintas, en coordenadas
NESTED_JS = """() => {
  const map = window.CS2_MAP, c = map.getCanvas();
  const w = c.clientWidth, h = c.clientHeight, out = [];
  for (let fy = 0.05; fy <= 0.95; fy += 0.01) {
    for (let fx = 0.05; fx <= 0.95; fx += 0.01) {
      const plan = map.queryRenderedFeatures([w * fx, h * fy], {layers: ['official-compare-hit']});
      if (new Set(plan.map(f => f.properties.k)).size > 1) {
        const ll = map.unproject([w * fx, h * fy]);
        out.push([ll.lng, ll.lat]);
        if (out.length >= 25) return out;
      }
    }
  }
  return out;
}"""

AT_CENTER_JS = """() => {
  const map = window.CS2_MAP, c = map.getCanvas();
  const p = [c.clientWidth / 2, c.clientHeight / 2];
  const near = [[p[0] - 4, p[1] - 4], [p[0] + 4, p[1] + 4]];
  const osm = map.queryRenderedFeatures(near, {layers: ['zoning-fill']}).map(f => f.properties.k);
  const plan = map.queryRenderedFeatures(p, {layers: ['official-compare-hit']})
    .map(f => ({k: f.properties.k, a: f.properties.a}));
  return {p, osm, plan};
}"""


class CompareViewer(ExportViewer):
    def compare(self):
        self.wait_official()
        self.page.click('[data-source="compare"]')
        self.wait_compare_shown()

    def wait_compare_shown(self):
        self.wait_official()
        self.wait("() => window.CS2_MAP.getLayer('official-compare-line') && "
                  "window.CS2_MAP.getLayoutProperty('official-compare-line', 'visibility') === 'visible'")
        assert self.pressed("data-source") == "compare"

    def settle(self):
        self.wait("() => !window.CS2_FILTERS_PENDING()")
        self.idle()

    def find(self, kind, places=(DOWNTOWN, (-93.2900, 44.9500), (-93.2400, 45.0100)), zoom=17, y=(0.2, 0.8)):
        for lng, lat in places:
            self.jump(lng, lat, zoom)
            self.settle()
            hit = self.page.evaluate(FIND_JS, [kind, *y])
            if hit:
                return hit
        pytest.fail(f"no encontré ningún punto «{kind}» en {places}")

    def label(self, k):
        el = self.page.locator(f'[data-module="zoning"] .cat-row[data-cat="{k}"] .cat-name')
        return el.first.inner_text() if el.count() else k

    def canvas_point(self, p):
        box = self.page.locator("#map canvas").bounding_box()
        return box["x"] + p[0], box["y"] + p[1]

    def hover(self, p):
        # Pasar antes por fuera del mapa obliga a recalcular el tooltip
        self.page.mouse.move(2, 2)
        self.page.mouse.move(*self.canvas_point(p), steps=3)
        self.wait("() => !document.getElementById('hover-tip').hidden")
        return self.page.inner_text("#hover-tip")

    def click(self, p):
        self.page.mouse.click(*self.canvas_point(p))
        self.wait("() => !document.getElementById('selection').hidden")
        return self.page.inner_text("#selection")

    def shown(self, layers):
        return {id_: self.page.evaluate(
            "id => !!window.CS2_MAP.getLayer(id) && window.CS2_MAP.getLayoutProperty(id, 'visibility') !== 'none'", id_)
            for id_ in layers}

    def rendered_ks(self, layer):
        return self.page.evaluate(
            "id => [...new Set(window.CS2_MAP.queryRenderedFeatures({layers: [id]}).map(f => f.properties.k))]", layer)


@pytest.fixture
def cv(viewer):
    def make(**kwargs):
        v = viewer(**kwargs)
        return CompareViewer(v.page, v.base)
    return make


# ── El control ──────────────────────────────────────────────────────────────

def test_three_buttons_and_compare_waits_for_the_plan(cv):
    v = cv()
    held = []
    v.page.route("**/datos_zonificacion_official.js*", lambda route: held.append(route))
    v.open(MPLS)
    buttons = v.page.locator("[data-source]")
    assert [buttons.nth(i).get_attribute("data-source") for i in range(buttons.count())] == ["osm", "official", "compare"]
    assert v.page.is_disabled('[data-source="compare"]')
    assert v.page.is_disabled('[data-source="official"]')
    assert v.page.get_attribute('[data-source="compare"]', "title") == \
        "OSM-derived zones with the official plan's outlines on top"
    for route in held:
        route.continue_()
    v.wait_official()
    v.wait("() => !document.querySelector('[data-source=\"compare\"]').disabled")
    v.assert_no_errors()


def test_source_key_only_in_compare(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    col = v.page.inner_text("#layers-col")
    assert "Fill: OSM-derived" in col
    assert f"Outline: {PLAN_FULL}" in col
    assert "differences are expected" in col
    v.page.click('[data-source="osm"]')
    v.wait("() => !document.querySelector('#layers-col').innerText.includes('Fill: OSM-derived')")
    v.assert_no_errors()


def test_visible_layers_per_mode(cv):
    v = cv()
    v.open(MPLS)
    v.wait_official()
    expect = {
        "osm": set(OSM_LAYERS),
        "official": set(OFFICIAL_LAYERS),
        "compare": set(OSM_LAYERS) | set(COMPARE_LAYERS) | {"official-hover"},
    }
    every = OSM_LAYERS + OFFICIAL_LAYERS + COMPARE_LAYERS
    for mode in ["compare", "official", "osm", "compare"]:
        v.page.click(f'[data-source="{mode}"]')
        v.wait(f"() => document.querySelector('[data-source=\"{mode}\"]').getAttribute('aria-pressed') === 'true'")
        v.idle()
        state = v.shown(every)
        assert {k for k, on in state.items() if on} == expect[mode], (mode, state)
    v.assert_no_errors()


# ── Estado: URL, guardado, carga tardía ─────────────────────────────────────

def test_compare_in_the_url_and_in_saved_state(cv):
    v = cv()
    v.open(MPLS, "src=compare")
    v.wait_compare_shown()
    assert v.params()["src"] == "compare"
    assert v.saved() is None                      # importar un link no guarda preferencias

    w = cv()
    w.open(MPLS)
    w.compare()
    w.wait("() => location.hash.includes('src=compare')")
    assert w.saved()["source"] == "compare"
    w.page.goto(f"{w.base}/map.html?city={MPLS}", wait_until="domcontentloaded")
    w.wait_loaded()
    w.wait_compare_shown()                         # sin hash: sale del guardado
    w.page.click("#share-view")
    assert "src=compare" in w.page.evaluate("location.href")
    v.assert_no_errors()
    w.assert_no_errors()


def test_compare_link_waits_for_a_late_plan(cv):
    v = cv()
    held = []
    v.page.route("**/datos_zonificacion_official.js*", lambda route: held.append(route))
    v.open(MPLS, "src=compare")
    assert v.params()["src"] == "compare"
    assert v.pressed("data-source") == "compare"   # lo pedido
    assert v.visible("zoning-fill")                # lo que se ve: OSM
    for route in held:
        route.continue_()
    v.wait_compare_shown()
    assert v.params()["src"] == "compare"
    v.assert_no_errors()


def test_unknown_source_is_ignored(cv):
    v = cv()
    v.open(MPLS, "src=comparar")
    assert v.params()["src"] == "osm"
    v.assert_no_errors()


# ── Filtros y On/Dim/Off ────────────────────────────────────────────────────

def test_only_filters_both_sources_but_not_the_query_layer(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    v.jump(*DOWNTOWN, 13)
    v.settle()
    v.page.click('[data-module="zoning"] .cat-row[data-cat="industrial"] .only-btn')
    v.settle()
    assert v.rendered_ks("official-compare-line") == ["industrial"]
    assert v.rendered_ks("official-compare-casing") == ["industrial"]
    assert set(v.rendered_ks("zoning-fill")) <= {"industrial"}
    assert len(v.rendered_ks("official-compare-hit")) > 1   # la consulta no se filtra
    v.assert_no_errors()


def test_dim_and_off_apply_to_both_sources(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("differ")
    full = v.page.evaluate("() => window.CS2_MAP.getPaintProperty('official-compare-line', 'line-opacity')")
    v.page.click('[data-module="zoning"] [data-module-state="dim"]')
    v.idle()
    dim = v.page.evaluate("() => window.CS2_MAP.getPaintProperty('official-compare-line', 'line-opacity')")
    assert dim < full
    assert all(v.shown(COMPARE_LAYERS).values())
    v.page.click('[data-module="zoning"] [data-module-state="off"]')
    v.idle()
    assert not any(v.shown(COMPARE_LAYERS + ["zoning-fill"]).values())
    v.page.mouse.move(*v.canvas_point(hit["p"]), steps=3)
    v.page.wait_for_timeout(300)
    assert v.page.is_hidden("#hover-tip")          # con Off no hay consulta
    v.assert_no_errors()


# ── Consulta: hover, click, toque ───────────────────────────────────────────

def test_hover_on_a_building_with_a_different_plan_zone(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("differ")
    text = v.hover(hit["p"])
    assert v.label(hit["osm"]) in text
    assert f"Plan: {v.label(hit['plan'][0]['k'])}" in text
    assert "same zone" not in text
    v.assert_no_errors()


def test_hover_on_a_building_with_the_same_plan_zone(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("same")
    text = v.hover(hit["p"])
    assert v.label(hit["osm"]) in text
    assert "Plan: same zone" in text
    v.assert_no_errors()


def test_hover_outside_the_plan(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("outside", places=(SUBURB, (-93.3600, 44.9000), (-93.2000, 45.0400)))
    text = v.hover(hit["p"])
    assert v.label(hit["osm"]) in text
    assert f"Outside the {PLAN}" in text
    v.assert_no_errors()


def test_hover_on_a_district_without_a_building(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("district_only")
    text = v.hover(hit["p"])
    assert v.label(hit["plan"][0]["k"]) in text
    assert f"{PLAN} · no OSM zone here" in text
    v.assert_no_errors()


def test_nested_districts_the_smaller_one_wins(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    v.jump(-93.2650, 44.9800, 12.3)
    v.settle()
    candidates = v.page.evaluate(NESTED_JS)
    assert candidates, "no encontré distritos anidados en Minneapolis"
    for lng, lat in candidates:
        v.jump(lng, lat, 16)
        v.settle()
        at = v.page.evaluate(AT_CENTER_JS)
        ks = {d["k"] for d in at["plan"]}
        # Un punto limpio: dos zonas del plan y ninguna coincide con el edificio (si hay)
        if len(ks) < 2 or ks & set(at["osm"]) or len(set(at["osm"])) > 1:
            continue
        assert all(d["a"] is not None for d in at["plan"]), "los distritos no guardan su área en `a`"
        small = min(at["plan"], key=lambda d: d["a"])
        big = max(at["plan"], key=lambda d: d["a"])
        text = v.hover(at["p"])
        assert v.label(small["k"]) in text, (text, small, big)
        assert v.label(big["k"]) not in text, (text, small, big)
        v.assert_no_errors()
        return
    pytest.fail(f"ninguno de los {len(candidates)} puntos anidados sirvió para probar")


def test_click_on_a_building_shows_the_plan_and_selects_the_district(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("differ")
    text = v.click(hit["p"])
    assert v.label(hit["osm"]) in text
    assert PLAN in text and v.label(hit["plan"][0]["k"]) in text
    assert PLAN_FULL in text
    district = hit["plan"][0]["id"]
    assert v.page.evaluate(
        "id => window.CS2_MAP.getFeatureState({source: 'cs2-official', id}).selected", district) is True
    v.assert_no_errors()


def test_click_on_a_district_alone(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    hit = v.find("district_only")
    text = v.click(hit["p"])
    assert v.label(hit["plan"][0]["k"]) in text
    assert f"{PLAN} · no OSM zone here" in text
    assert PLAN_FULL in text
    assert "Only this zone" in text and "Explore on OSM" in text
    v.assert_no_errors()


def test_phone_buttons_fit_and_a_tap_shows_both_zones(cv):
    v = cv(viewport=(390, 844), is_mobile=True, has_touch=True)
    v.open(MPLS)
    v.wait_official()
    if v.page.is_hidden('[data-source="compare"]'):
        v.page.click("#layers-tray-toggle")
    tops = [v.page.locator(f'[data-source="{s}"]').bounding_box()["y"] for s in ("osm", "official", "compare")]
    assert max(tops) - min(tops) <= 2, f"los botones no entran en una línea: {tops}"
    v.page.click('[data-source="compare"]')
    v.wait_compare_shown()
    if v.page.get_attribute("#layers-tray-toggle", "aria-expanded") == "true":
        v.page.click("#layers-tray-toggle")    # plegar la bandeja para tocar el mapa
    hit = v.find("differ", y=(0.15, 0.45))
    v.page.touchscreen.tap(*v.canvas_point(hit["p"]))
    v.wait("() => !document.getElementById('selection').hidden")
    text = v.page.inner_text("#selection")
    assert v.label(hit["osm"]) in text and v.label(hit["plan"][0]["k"]) in text
    v.assert_no_errors()


# ── Export PNG ──────────────────────────────────────────────────────────────

def test_export_in_compare_draws_the_outlines_and_stays_empty_when_all_hidden(cv):
    frame = f"frame={DOWNTOWN[1]},{DOWNTOWN[0]}"
    v = cv()
    v.open(MPLS, f"{frame}&layers=zoning.on,{ALL_OFF}")
    v.wait_official()
    _, osm_png = v.export(size=2048, bg="transparent")
    osm = v.stats(osm_png)

    w = cv()
    w.open(MPLS, f"{frame}&src=compare&layers=zoning.on,{ALL_OFF}")
    w.wait_compare_shown()
    _, cmp_png = w.export(size=2048, bg="transparent")
    cmp = w.stats(cmp_png)
    assert cmp["painted"] > osm["painted"], (cmp["painted"], osm["painted"])   # los contornos suman

    hidden = ",".join(w.catalog("zoning"))
    x = cv()
    x.open(MPLS, f"{frame}&src=compare&layers=zoning.on,{ALL_OFF}&hide.zoning={hidden}")
    x.wait_compare_shown()
    _, empty_png = x.export(size=2048, bg="transparent")
    empty = x.stats(empty_png)
    assert empty["painted"] == 0, empty["painted"]
    assert empty["corner"]["covered"] > 0       # la atribución sí va
    for t in (v, w, x):
        t.assert_no_errors()


# ── Textos ──────────────────────────────────────────────────────────────────

def test_no_word_calls_a_difference_an_error(cv):
    v = cv()
    v.open(MPLS)
    v.compare()
    texts = [v.page.inner_text("#layers-col")]
    hit = v.find("differ")
    texts.append(v.hover(hit["p"]))
    texts.append(v.click(hit["p"]))
    texts.append(v.page.get_attribute('[data-source="compare"]', "title"))
    for text in texts:
        assert not FORBIDDEN.search(text), text
    v.assert_no_errors()
