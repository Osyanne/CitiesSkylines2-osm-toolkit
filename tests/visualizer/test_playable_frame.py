"""
El recuadro del mapa jugable de CS2 (etapa 6a del visor).

Mismo arreglo que test_url_state.py: Chromium (Playwright) contra un http.server
local, fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

Contrato: docs/plans/2026-09-26-layout-visor/09-etapa-6a-spec.md
"""
import json
import math
import re

import pytest

from .test_url_state import IDLE_JS, MPLS, Viewer, base_url, browser, viewer  # noqa: F401 (fixtures)

pytestmark = [pytest.mark.network, pytest.mark.browser]

CITY = "sioux-falls"          # chica y de un solo módulo: carga rápido
CITY_CENTER = (43.532954, -96.7354775)
SAVE_KEY = f"cs2-view-state-{CITY}-v2"
SIDE_M = 14336
TILE_M = SIDE_M / 23
FRAME_LAYERS = ["cs2-frame-mask", "cs2-frame-grid", "cs2-frame-casing", "cs2-frame-outline"]
COORDS = re.compile(r"^-?\d+\.\d{5},-?\d+\.\d{5}$")

FRAME_JS = """async () => {
  const src = window.CS2_MAP.getSource('cs2-frame');
  if (!src) return null;
  const feats = (await src.getData()).features || [];
  const ring = f => f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates;
  const outline = feats.find(f => f.properties.part === 'outline');
  const mask = feats.find(f => f.properties.part === 'mask');
  return {
    outline: outline ? ring(outline) : null,
    grid: feats.filter(f => f.properties.part === 'grid').map(f => f.geometry.coordinates),
    maskRings: mask ? mask.geometry.coordinates.length : 0,
  };
}"""

# El rectángulo del canvas sin lo que tapa la columna/bandeja cuando se le
# superpone (spec §6), y el punto medio en píxeles relativos al canvas.
VISIBLE_CENTER_JS = """() => {
  const c = window.CS2_MAP.getCanvas().getBoundingClientRect();
  const p = document.getElementById('layers-col').getBoundingClientRect();
  let {left, top, right, bottom} = c;
  const overlaps = p.width > 0 && p.height > 0 && p.left < c.right && p.right > c.left &&
    p.top < c.bottom && p.bottom > c.top;
  if (overlaps) {
    if (p.left <= c.left + 1 && p.right >= c.right - 1) bottom = Math.min(bottom, p.top);
    else if (p.top <= c.top + 1 && p.bottom >= c.bottom - 1) left = Math.max(left, p.right);
  }
  return [(left + right) / 2 - c.left, (top + bottom) / 2 - c.top];
}"""


def haversine(lat1, lng1, lat2, lng2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def saved_frame_js(lat, lng, on=True):
    state = {"frame": {"on": on, "lat": lat, "lng": lng}}
    return f"localStorage.setItem({json.dumps(SAVE_KEY)}, {json.dumps(json.dumps(state))});"


class FrameViewer(Viewer):
    def idle(self):
        # Con WebGL por software las teselas tardan 20-40 s en terminar de
        # cargar después de abrir: 15 s no alcanzan
        assert self.page.evaluate(IDLE_JS.replace("15000", "60000")), "el mapa no terminó de dibujar en 60 s"

    def saved(self):
        return self.page.evaluate("key => JSON.parse(localStorage.getItem(key))", SAVE_KEY)

    def is_on(self):
        return self.page.get_attribute("button.cs2-frame", "aria-pressed") == "true"

    def toggle(self, expect_on):
        self.page.click("button.cs2-frame")
        self.wait("on => document.querySelector('button.cs2-frame').getAttribute('aria-pressed') === String(on)",
                  expect_on)

    def frame(self):
        info = self.page.evaluate(FRAME_JS)
        assert info and info["outline"], "la fuente cs2-frame no tiene contorno"
        lngs = [p[0] for p in info["outline"]]
        lats = [p[1] for p in info["outline"]]
        info.update(west=min(lngs), east=max(lngs), south=min(lats), north=max(lats))
        info["center"] = ((info["south"] + info["north"]) / 2, (info["west"] + info["east"]) / 2)
        return info

    def hash_frame(self):
        value = self.params()["frame"]
        if value == "off":
            return "off"
        assert COORDS.match(value), value
        lat, lng = map(float, value.split(","))
        return lat, lng

    def map_center(self):
        c = self.camera()
        return c["lat"], c["lng"]

    def to_pixel(self, lat, lng):
        return self.page.evaluate("([lng, lat]) => { const p = window.CS2_MAP.project([lng, lat]); return [p.x, p.y]; }",
                                  [lng, lat])

    def visible_center(self):
        return self.page.evaluate(VISIBLE_CENTER_JS)

    def frame_layers_visible(self):
        return [self.visible(layer) for layer in FRAME_LAYERS]

    def zone_point(self):
        """Un punto de la página con una zona debajo, lejos del asa, el panel y la ficha."""
        return self.page.evaluate("""() => {
          const map = window.CS2_MAP, c = map.getCanvas().getBoundingClientRect();
          const avoid = [...document.querySelectorAll('.frame-handle, #frame-panel, #selection')]
            .filter(e => !e.hidden && e.getClientRects().length).map(e => e.getBoundingClientRect());
          for (let fy = 0.25; fy <= 0.75; fy += 0.025) {
            for (let fx = 0.25; fx <= 0.75; fx += 0.025) {
              const x = c.width * fx, y = c.height * fy, X = c.left + x, Y = c.top + y;
              if (avoid.some(r => X > r.left - 20 && X < r.right + 20 && Y > r.top - 20 && Y < r.bottom + 20)) continue;
              if (map.queryRenderedFeatures([x, y], {layers: ['zoning-fill']}).length) return [X, Y];
            }
          }
          return null;
        }""")


@pytest.fixture
def fv(viewer):
    def make(**kwargs):
        v = viewer(**kwargs)
        return FrameViewer(v.page, v.base)
    return make


def assert_near(a, b, metres, what=""):
    d = haversine(a[0], a[1], b[0], b[1])
    assert d <= metres, f"{what}: {a} y {b} están a {d:.1f} m"


# ── Prender y apagar ────────────────────────────────────────────────────────

def test_fresh_visit_starts_off(fv):
    v = fv()
    v.open(CITY)
    assert not v.is_on()
    assert v.page.is_hidden("#frame-panel")
    assert v.frame_layers_visible() == [False] * 4
    p = v.params()
    assert p["frame"] == "off"
    assert list(p)[-1] == "frame"         # va último, después de los hide.*
    assert v.saved() is None              # la primera visita no guarda nada
    v.assert_no_errors()


def test_turning_on_uses_the_visible_center(fv):
    v = fv()
    v.open(CITY)
    expected = v.map_center()             # en escritorio la columna no tapa el mapa
    v.toggle(True)
    assert v.page.is_visible("#frame-panel")
    assert "14.3 km" in v.page.inner_text("#frame-panel")
    assert v.frame_layers_visible() == [True] * 4
    frame = v.frame()
    assert_near(frame["center"], expected, 2, "centro del recuadro")
    lat, lng = v.hash_frame()
    assert_near((lat, lng), frame["center"], 2, "frame= en la URL")
    saved = v.saved()["frame"]
    assert saved["on"] is True
    assert_near((saved["lat"], saved["lng"]), frame["center"], 2, "frame guardado")
    # Apagarlo no olvida la posición
    v.toggle(False)
    assert v.hash_frame() == "off" and v.saved()["frame"]["on"] is False
    assert v.frame_layers_visible() == [False] * 4
    v.toggle(True)
    assert_near(v.frame()["center"], frame["center"], 1, "posición recordada")
    v.assert_no_errors()


def test_far_from_the_city_it_goes_to_the_city_center(fv):
    v = fv()
    v.open(CITY)
    v.jump(-94.5, 42.5, 10)               # el centro visible cae fuera del bbox
    v.toggle(True)
    frame = v.frame()
    assert_near(frame["center"], CITY_CENTER, 2, "centro de la ciudad")
    v.idle()
    x, y = v.to_pixel(*frame["center"])  # la cámara fue a buscarlo
    box = v.page.locator("#map canvas").bounding_box()
    assert 0 <= x <= box["width"] and 0 <= y <= box["height"]
    v.assert_no_errors()


def test_geometry_is_14336_m_with_a_23_by_23_grid(fv):
    v = fv()
    v.open(CITY, "frame=43.53295,-96.73548")
    f = v.frame()
    for (lat1, lng1), (lat2, lng2), side in [
        ((f["south"], f["west"]), (f["south"], f["east"]), "sur"),
        ((f["north"], f["west"]), (f["north"], f["east"]), "norte"),
        ((f["south"], f["west"]), (f["north"], f["west"]), "oeste"),
        ((f["south"], f["east"]), (f["north"], f["east"]), "este"),
    ]:
        assert abs(haversine(lat1, lng1, lat2, lng2) - SIDE_M) <= SIDE_M * 0.005, side
    assert len(f["outline"]) == 5 and f["outline"][0] == f["outline"][-1]
    assert len(f["grid"]) == 44
    vertical = sorted(line[0][0] for line in f["grid"] if line[0][0] == line[-1][0])
    horizontal = sorted(line[0][1] for line in f["grid"] if line[0][1] == line[-1][1])
    assert len(vertical) == len(horizontal) == 22
    for i, lng in enumerate(vertical, start=1):
        assert abs(lng - (f["west"] + i * (f["east"] - f["west"]) / 23)) < 1e-9
    for i, lat in enumerate(horizontal, start=1):
        assert abs(lat - (f["south"] + i * (f["north"] - f["south"]) / 23)) < 1e-9
    assert f["maskRings"] == 2            # el mundo, con el recuadro como agujero
    v.assert_no_errors()


# ── Mover ───────────────────────────────────────────────────────────────────

def test_center_here_moves_it_to_the_visible_center(fv):
    v = fv()
    v.open(CITY)
    v.toggle(True)
    v.jump(-96.70, 43.55, 12)
    v.page.click("#frame-center")
    target = (43.55, -96.70)
    assert_near(v.frame()["center"], target, 2, "Center here")
    assert_near(v.hash_frame(), target, 2, "frame= después de Center here")
    saved = v.saved()["frame"]
    assert_near((saved["lat"], saved["lng"]), target, 2, "guardado después de Center here")
    v.assert_no_errors()


def test_dragging_the_handle_moves_only_the_frame(fv):
    v = fv()
    v.open(CITY, "frame=43.53295,-96.73548")
    v.idle()
    handle = v.page.locator(".frame-handle")
    assert handle.is_visible()
    camera = v.map_center()
    box = handle.bounding_box()
    x0, y0 = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    v.page.mouse.move(x0, y0)
    v.page.mouse.down()
    v.page.mouse.move(x0 + 180, y0 + 110, steps=12)
    v.page.mouse.up()
    canvas = v.page.locator("#map canvas").bounding_box()
    dropped = v.page.evaluate(
        "([x, y]) => { const ll = window.CS2_MAP.unproject([x, y]); return [ll.lat, ll.lng]; }",
        [x0 + 180 - canvas["x"], y0 + 110 - canvas["y"]])
    assert_near(v.frame()["center"], dropped, 40, "el recuadro sigue al asa")
    assert_near(v.map_center(), camera, 0.5, "el mapa no se movió")
    assert v.page.is_hidden("#selection")          # soltar no abre la ficha
    saved = v.saved()["frame"]
    assert_near((saved["lat"], saved["lng"]), v.frame()["center"], 2, "guardado al soltar")
    assert_near(v.hash_frame(), v.frame()["center"], 2, "frame= al soltar")
    v.assert_no_errors()


def test_releasing_the_drag_outside_the_map_ends_it(fv):
    v = fv()
    v.open(CITY, "frame=43.53295,-96.73548")
    v.idle()
    handle = v.page.locator(".frame-handle").bounding_box()
    panel = v.page.locator("#frame-panel").bounding_box()
    v.page.mouse.move(handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2)
    v.page.mouse.down()
    # Soltar sobre el panel: fuera del canvas del mapa
    v.page.mouse.move(panel["x"] + panel["width"] / 2, panel["y"] + panel["height"] / 2, steps=12)
    v.page.mouse.up()
    assert "is-dragging" not in (v.page.get_attribute(".frame-handle", "class") or "")
    released = v.frame()["center"]
    saved = v.saved()["frame"]
    assert_near((saved["lat"], saved["lng"]), released, 2, "guardado al soltar afuera")
    # Sin botón apretado el recuadro ya no sigue al cursor
    v.page.mouse.move(panel["x"] + 150, panel["y"] - 200, steps=8)
    assert_near(v.frame()["center"], released, 0.5, "el recuadro quedó suelto")
    # Y el próximo click en el mapa selecciona, no se lo traga el arrastre
    v.page.wait_for_timeout(400)
    point = v.zone_point()
    assert point, "no hay ninguna zona a la vista"
    v.page.mouse.click(*point)
    v.wait("() => !document.getElementById('selection').hidden")
    v.assert_no_errors()


def test_floating_selection_card_does_not_cover_the_panel(fv):
    v = fv(viewport=(800, 700))           # la columna arranca cerrada: la ficha flota
    v.open(CITY, "frame=43.53295,-96.73548")
    v.idle()
    point = v.zone_point()
    assert point, "no hay ninguna zona a la vista"
    v.page.mouse.click(*point)
    v.wait("() => !document.getElementById('selection').hidden")
    v.page.wait_for_timeout(300)
    card = v.page.locator("#selection").bounding_box()
    panel = v.page.locator("#frame-panel").bounding_box()
    overlap = (min(card["x"] + card["width"], panel["x"] + panel["width"]) - max(card["x"], panel["x"]) > 0 and
               min(card["y"] + card["height"], panel["y"] + panel["height"]) - max(card["y"], panel["y"]) > 0)
    assert not overlap, f"la ficha {card} tapa el panel {panel}"
    v.assert_no_errors()


def test_arrow_keys_on_the_handle_move_one_tile(fv):
    v = fv()
    v.open(CITY, "frame=43.53295,-96.73548")
    start = v.frame()["center"]
    camera = v.map_center()
    v.page.locator(".frame-handle").focus()
    v.page.keyboard.press("ArrowRight")
    east = v.frame()["center"]
    assert abs(haversine(*start, *east) - TILE_M) <= TILE_M * 0.005
    assert east[1] > start[1] and abs(east[0] - start[0]) < 1e-9
    v.page.keyboard.press("ArrowUp")
    north = v.frame()["center"]
    assert abs(haversine(*east, *north) - TILE_M) <= TILE_M * 0.005
    assert north[0] > east[0] and abs(north[1] - east[1]) < 1e-9
    assert_near(v.map_center(), camera, 0.5, "las flechas no mueven el mapa")
    saved = v.saved()["frame"]
    assert_near((saved["lat"], saved["lng"]), north, 2, "guardado con las flechas")
    v.assert_no_errors()


# ── Precedencia: URL → guardado → apagado ───────────────────────────────────

SAVED = (43.50000, -96.75000)
LINKED = (43.56000, -96.70000)


def test_frame_off_in_the_url_beats_saved_on(fv):
    v = fv(init=[saved_frame_js(*SAVED)])
    v.open(CITY, "frame=off")
    assert not v.is_on() and v.frame_layers_visible() == [False] * 4
    assert v.saved()["frame"] == {"on": True, "lat": SAVED[0], "lng": SAVED[1]}   # importar no guarda
    v.toggle(True)                                  # la posición recordada sale de lo guardado
    assert_near(v.frame()["center"], SAVED, 2, "posición guardada")
    v.assert_no_errors()


def test_coordinates_in_the_url_beat_saved(fv):
    v = fv(init=[saved_frame_js(*SAVED)])
    v.open(CITY, f"frame={LINKED[0]:.5f},{LINKED[1]:.5f}")
    assert v.is_on()
    assert_near(v.frame()["center"], LINKED, 2, "frame= de la URL")
    assert v.saved()["frame"]["lat"] == SAVED[0]
    v.assert_no_errors()


def test_saved_frame_applies_without_a_hash(fv):
    v = fv(init=[saved_frame_js(*SAVED)])
    v.open(CITY)
    assert v.is_on()
    assert_near(v.frame()["center"], SAVED, 2, "frame guardado")
    assert_near(v.hash_frame(), SAVED, 2, "frame= escrito desde lo guardado")
    v.assert_no_errors()


@pytest.mark.parametrize("bad", ["abc", "95,10", "43.5", "43.5,-96.7,1", "NaN,1", "43.5,200"])
def test_invalid_frame_falls_back_to_saved_and_is_normalized(fv, bad):
    v = fv(init=[saved_frame_js(*SAVED)])
    v.open(CITY, f"frame={bad}")
    assert v.is_on()
    assert_near(v.frame()["center"], SAVED, 2, "cae a lo guardado")
    assert v.params()["frame"] == f"{SAVED[0]:.5f},{SAVED[1]:.5f}"
    v.assert_no_errors()


def test_invalid_frame_without_saved_is_off(fv):
    v = fv()
    v.open(CITY, "frame=95,10")
    assert not v.is_on()
    assert v.params()["frame"] == "off"
    assert v.saved() is None
    v.assert_no_errors()


def test_hashchange_reimports_the_frame_without_saving(fv):
    v = fv(init=[saved_frame_js(*SAVED)])
    v.open(CITY)
    v.page.evaluate("location.hash = '#base=dark&frame=off'")
    v.wait("() => document.querySelector('button.cs2-frame').getAttribute('aria-pressed') === 'false'")
    v.page.evaluate(f"location.hash = '#base=dark&frame={LINKED[0]:.5f},{LINKED[1]:.5f}'")
    v.wait("() => document.querySelector('button.cs2-frame').getAttribute('aria-pressed') === 'true'")
    assert_near(v.frame()["center"], LINKED, 2, "frame= importado")
    assert v.saved()["frame"] == {"on": True, "lat": SAVED[0], "lng": SAVED[1]}
    v.assert_no_errors()


# ── Convivencia con el resto del visor ──────────────────────────────────────

def test_frame_stays_on_top_of_late_layers(fv):
    v = fv()
    v.open(MPLS, "src=official&layers=zoning.on,vial.on,services.on,transporte.on,infraestructura.on"
                 "&frame=44.97000,-93.27000")
    v.wait_late_modules()
    v.wait_official()
    v.idle()
    ids = v.page.evaluate("() => window.CS2_MAP.getStyle().layers.map(l => l.id)")
    assert ids[-4:] == FRAME_LAYERS
    v.assert_no_errors()


def test_clicking_the_frame_selects_the_zone_below(fv):
    v = fv()
    v.open(CITY, "frame=43.53295,-96.73548")
    v.jump(-96.7355, 43.5330, 14)
    v.idle()
    # Un punto sobre una línea de la grilla, con una zona debajo y lejos del asa
    point = v.page.evaluate("""async () => {
      const map = window.CS2_MAP;
      const feats = (await map.getSource('cs2-frame').getData()).features;
      const w = map.getCanvas().clientWidth, h = map.getCanvas().clientHeight;
      for (const f of feats.filter(f => f.properties.part === 'grid')) {
        const [a, b] = f.geometry.coordinates;
        for (let t = 0.02; t < 1; t += 0.01) {
          const p = map.project([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
          if (p.x < 80 || p.y < 80 || p.x > w - 80 || p.y > h - 120) continue;
          if (Math.hypot(p.x - w / 2, p.y - h / 2) < 60) continue;
          if (map.queryRenderedFeatures([p.x, p.y], {layers: ['zoning-fill']}).length) return [p.x, p.y];
        }
      }
      return null;
    }""")
    assert point, "no hay ninguna zona debajo de la grilla en la vista"
    box = v.page.locator("#map canvas").bounding_box()
    v.page.mouse.click(box["x"] + point[0], box["y"] + point[1])
    v.wait("() => !document.getElementById('selection').hidden")
    v.assert_no_errors()


@pytest.mark.parametrize("viewport", [(375, 812), (844, 390)], ids=["vertical", "apaisado"])
def test_phone_has_no_handle_and_centers_above_the_tray(fv, viewport):
    v = fv(viewport=viewport, is_mobile=True, has_touch=True)
    v.open(CITY)
    v.toggle(True)
    assert v.page.locator(".frame-handle").count() == 0 or v.page.is_hidden(".frame-handle")
    v.jump(-96.72, 43.54, 12)
    v.page.click("#frame-center")
    v.idle()
    x, y = v.to_pixel(*v.frame()["center"])
    ex, ey = v.visible_center()
    assert abs(x - ex) <= 2 and abs(y - ey) <= 2, f"recuadro en {(x, y)}, centro visible en {(ex, ey)}"
    # El panel no se monta sobre la bandeja plegada
    panel = v.page.locator("#frame-panel").bounding_box()
    tray = v.page.locator("#layers-col").bounding_box()
    assert not (min(panel["x"] + panel["width"], tray["x"] + tray["width"]) - max(panel["x"], tray["x"]) > 0 and
                min(panel["y"] + panel["height"], tray["y"] + tray["height"]) - max(panel["y"], tray["y"]) > 0),         f"el panel {panel} se superpone con la bandeja {tray}"
    v.assert_no_errors()


def test_thumbnails_keep_the_frame_hidden(fv):
    from shared.thumbnails import _hide_chrome_js

    v = fv()
    v.open(CITY)
    v.page.evaluate(_hide_chrome_js())
    assert v.page.is_hidden("button.cs2-frame") and v.page.is_hidden("#frame-panel")
    assert v.frame_layers_visible() == [False] * 4
    v.assert_no_errors()
