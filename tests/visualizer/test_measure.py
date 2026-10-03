"""
Medir en celdas de 8 m: la escala doble y la herramienta Measure (etapa 6c del visor).

Mismo arreglo que los demás tests del visor: Chromium (Playwright) contra un http.server
local, fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

Contrato: docs/plans/2026-09-26-layout-visor/11-etapa-6c-spec.md
"""
import re
from decimal import ROUND_HALF_UP, Decimal

import pytest

from .test_frame_export import FRAME, ExportViewer
from .test_playable_frame import CITY, haversine
from .test_url_state import base_url, browser, viewer  # noqa: F401 (fixtures)

pytestmark = [pytest.mark.network, pytest.mark.browser]

MEASURE_LAYERS = ["cs2-measure-line", "cs2-measure-points"]
SCALE = re.compile(r"^(\d[\d,]*) (m|km) · (\d[\d,]*(?:\.\d)?) cells$")
TOTAL = re.compile(r"^Total: (\d[\d,]*(?:\.\d\d)?) (m|km) · (\d[\d,]*(?:\.\d)?) cells$")


def js_round(value, places=0):
    """Redondeo de JS (mitades hacia arriba), no el de Python (mitades al par)."""
    q = Decimal(1).scaleb(-places)
    return Decimal(repr(value)).quantize(q, rounding=ROUND_HALF_UP)


def format_cells(metres):
    c = metres / 8
    if c < 100:
        text = format(js_round(c, 1), "f")
        text = text[:-2] if text.endswith(".0") else text
    else:
        text = f"{int(js_round(c)):,}"
    return f"{text} cells"


def to_metres(number, unit):
    value = float(number.replace(",", ""))
    return value * 1000 if unit == "km" else value


class MeasureViewer(ExportViewer):
    def scale(self):
        return self.page.evaluate("""() => {
          const el = document.querySelector('.cs2-scale');
          if (!el) return null;
          const map = window.CS2_MAP, c = map.getCanvas();
          const y = c.clientHeight / 2, x0 = c.clientWidth / 2 - 55;
          const dist = map.unproject([x0, y]).distanceTo(map.unproject([x0 + 110, y]));
          return {className: el.className, label: el.querySelector('.scale-label').textContent.trim(),
                  bar: el.querySelector('.scale-bar').getBoundingClientRect().width, dist110: dist};
        }""")

    def measuring(self):
        return self.page.get_attribute("button.cs2-measure", "aria-pressed") == "true"

    def start(self):
        self.page.click("button.cs2-measure")
        self.wait("() => document.querySelector('button.cs2-measure').getAttribute('aria-pressed') === 'true'")

    def canvas_box(self):
        return self.page.locator("#map canvas").bounding_box()

    def click(self, x, y):
        box = self.canvas_box()
        self.page.mouse.click(box["x"] + x, box["y"] + y)

    def lnglat(self, x, y):
        ll = self.page.evaluate("([x, y]) => { const p = window.CS2_MAP.unproject([x, y]); return [p.lat, p.lng]; }", [x, y])
        return tuple(ll)

    def points(self):
        return self.page.evaluate("""async () => {
          const src = window.CS2_MAP.getSource('cs2-measure');
          if (!src) return null;
          const feats = (await src.getData()).features || [];
          return feats.filter(f => f.geometry.type === 'Point').map(f => f.geometry.coordinates);
        }""")

    def total(self):
        return self.page.inner_text("#measure-total").strip()

    def total_metres(self):
        m = TOTAL.match(self.total())
        assert m, self.total()
        return to_metres(m.group(1), m.group(2)), float(m.group(3).replace(",", ""))

    def labels(self):
        return self.page.evaluate("""() => [...document.querySelectorAll('.measure-label')]
          .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden'
                       && getComputedStyle(e).display !== 'none' && getComputedStyle(e.parentElement).display !== 'none')
          .map(e => e.textContent.trim())""")

    def zone_point(self):
        """Un punto con una zona debajo, lejos de los paneles, el asa y los rótulos."""
        return self.page.evaluate("""() => {
          const map = window.CS2_MAP, c = map.getCanvas().getBoundingClientRect();
          const avoid = [...document.querySelectorAll('.frame-handle, #frame-panel, #measure-panel, #selection, .measure-label')]
            .filter(e => !e.hidden && e.getClientRects().length).map(e => e.getBoundingClientRect());
          for (let fy = 0.25; fy <= 0.7; fy += 0.025) {
            for (let fx = 0.25; fx <= 0.75; fx += 0.025) {
              const x = c.width * fx, y = c.height * fy, X = c.left + x, Y = c.top + y;
              if (avoid.some(r => X > r.left - 20 && X < r.right + 20 && Y > r.top - 20 && Y < r.bottom + 20)) continue;
              if (map.queryRenderedFeatures([x, y], {layers: ['zoning-fill']}).length) return [X, Y];
            }
          }
          return null;
        }""")


@pytest.fixture
def mv(viewer):
    def make(**kwargs):
        v = viewer(**kwargs)
        return MeasureViewer(v.page, v.base)
    return make


# ── Escala ──────────────────────────────────────────────────────────────────

def test_scale_shows_metres_and_cells(mv):
    v = mv()
    v.open(CITY)
    labels = set()
    for zoom in (11, 13, 15, 18):
        v.jump(-96.7355, 43.5330, zoom)
        v.page.wait_for_timeout(200)
        s = v.scale()
        assert s, "no hay .cs2-scale"
        assert "maplibregl-ctrl-scale" in s["className"]
        m = SCALE.match(s["label"])
        assert m, s["label"]
        metres = to_metres(m.group(1), m.group(2))
        assert int(str(int(metres)).rstrip("0") or "0") in (1, 2, 3, 5), f"{metres} m no es un número redondo"
        assert f"{m.group(3)} cells" == format_cells(metres), s["label"]
        assert 0 < s["bar"] <= 110.5
        assert abs(s["bar"] - 110 * metres / s["dist110"]) <= 1.5, (s["bar"], metres, s["dist110"])
        labels.add(s["label"])
    assert len(labels) == 4                      # cambia con el zoom
    v.assert_no_errors()


# ── Medir ───────────────────────────────────────────────────────────────────

def test_two_clicks_measure_the_distance(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    assert v.page.is_visible("#measure-panel")
    v.click(400, 400)
    v.click(700, 400)
    pts = v.points()
    assert len(pts) == 2
    expected = haversine(*v.lnglat(400, 400), *v.lnglat(700, 400))
    metres, cells = v.total_metres()
    assert abs(metres - expected) <= expected * 0.005, (metres, expected)
    assert abs(cells - expected / 8) <= expected / 8 * 0.005 + 0.06
    assert len(v.labels()) == 1
    v.assert_no_errors()


def test_three_points_add_up(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    for x, y in [(350, 300), (650, 300), (650, 600)]:
        v.click(x, y)
    a = haversine(*v.lnglat(350, 300), *v.lnglat(650, 300))
    b = haversine(*v.lnglat(650, 300), *v.lnglat(650, 600))
    metres, _ = v.total_metres()
    assert abs(metres - (a + b)) <= (a + b) * 0.005
    assert len(v.points()) == 3 and len(v.labels()) == 2
    v.assert_no_errors()


def test_double_click_finishes_without_a_duplicate_or_zoom(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    v.click(400, 400)
    zoom = v.camera()["zoom"]
    box = v.canvas_box()
    v.page.mouse.dblclick(box["x"] + 700, box["y"] + 450)
    v.wait("() => document.querySelector('button.cs2-measure').getAttribute('aria-pressed') === 'false'")
    assert len(v.points()) == 2
    v.page.wait_for_timeout(500)
    assert abs(v.camera()["zoom"] - zoom) < 1e-9
    assert v.page.is_visible("#measure-panel")      # la medición queda
    v.assert_no_errors()


def test_dragging_while_measuring_adds_no_points(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    box = v.canvas_box()
    v.page.mouse.move(box["x"] + 500, box["y"] + 400)
    v.page.mouse.down()
    v.page.mouse.move(box["x"] + 700, box["y"] + 500, steps=10)
    v.page.mouse.up()
    assert not v.points()
    v.click(500, 400)
    assert len(v.points()) == 1
    v.assert_no_errors()


def test_measuring_suspends_selection(mv):
    v = mv()
    v.open(CITY)
    v.idle()
    v.start()
    point = v.zone_point()
    assert point, "no hay ninguna zona a la vista"
    v.page.mouse.click(*point)
    v.page.wait_for_timeout(400)
    assert v.page.is_hidden("#selection")           # agregó un punto, no seleccionó
    assert len(v.points()) == 1
    v.page.click("#measure-done")
    point = v.zone_point()
    v.page.mouse.click(*point)
    v.wait("() => !document.getElementById('selection').hidden")
    v.assert_no_errors()


def test_done_escape_clear_and_restart(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    v.click(400, 400)
    v.click(700, 400)
    v.page.keyboard.press("Escape")
    v.wait("() => document.querySelector('button.cs2-measure').getAttribute('aria-pressed') === 'false'")
    assert len(v.points()) == 2 and v.visible("cs2-measure-line")
    assert v.page.is_visible("#measure-panel") and v.page.is_hidden("#measure-done")
    # Measure otra vez: una medición nueva
    v.start()
    assert not v.points()
    v.click(400, 500)
    v.click(600, 500)
    v.page.click("#measure-done")
    assert len(v.points()) == 2
    v.page.click("#measure-clear")
    v.wait("() => document.getElementById('measure-panel').hidden")
    assert not v.points() or not v.visible("cs2-measure-line")
    assert v.labels() == []
    assert not v.measuring()
    v.assert_no_errors()


def test_frame_handle_hides_while_measuring(mv):
    v = mv()
    v.open(CITY, FRAME)
    assert v.page.is_visible(".frame-handle")
    v.start()
    assert v.page.locator(".frame-handle").count() == 0 or v.page.is_hidden(".frame-handle")
    assert v.page.is_visible("#frame-panel")
    v.page.click("#measure-done")
    v.wait("() => { const h = document.querySelector('.frame-handle'); return h && h.getClientRects().length > 0; }")
    v.assert_no_errors()


def test_measurement_stays_out_of_the_png(mv):
    v = mv()
    v.open(CITY, FRAME)
    every = ",".join(v.catalog("zoning"))
    w = mv()
    w.open(CITY, f"{FRAME}&hide.zoning={every}")
    w.idle()
    w.start()
    # Una línea larga que cruza el recuadro
    w.click(300, 200)
    w.click(900, 650)
    w.page.click("#measure-done")
    _, data = w.export(size=2048, bg="transparent")
    s = w.stats(data)
    assert s["painted"] < 500, f"{s['painted']} píxeles pintados: la medición entró en el PNG"
    v.assert_no_errors()
    w.assert_no_errors()


def test_phone_taps_add_points_without_preview(mv):
    v = mv(viewport=(390, 844), is_mobile=True, has_touch=True)
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    box = v.canvas_box()
    v.page.touchscreen.tap(box["x"] + 100, box["y"] + 250)
    v.page.touchscreen.tap(box["x"] + 300, box["y"] + 450)
    assert len(v.points()) == 2
    assert len(v.labels()) == 1                       # sin rótulo de vista previa
    assert "Tap" not in v.total()
    panel = v.page.locator("#measure-panel").bounding_box()
    tray = v.page.locator("#layers-col").bounding_box()
    assert panel["x"] >= 0 and panel["x"] + panel["width"] <= 390
    assert panel["y"] + panel["height"] <= tray["y"] + 1, f"el panel {panel} tapa la bandeja {tray}"
    v.assert_no_errors()


def test_finishing_with_one_point_discards_it(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    v.click(500, 400)
    v.page.click("#measure-done")
    v.wait("() => document.getElementById('measure-panel').hidden")
    assert not v.points()
    v.assert_no_errors()


def test_escape_on_the_share_panel_keeps_measuring(mv):
    no_clipboard = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                    "value: {writeText: () => Promise.reject(new Error('denied'))}});")
    v = mv(init=[no_clipboard])
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    v.click(500, 400)
    v.page.click("#share-view")
    v.wait("() => !document.getElementById('share-panel').hidden")
    v.page.keyboard.press("Escape")
    v.wait("() => document.getElementById('share-panel').hidden")
    assert v.measuring(), "el Escape del panel de Share terminó la medición"
    v.page.keyboard.press("Escape")
    v.wait("() => document.querySelector('button.cs2-measure').getAttribute('aria-pressed') === 'false'")


def test_preview_stays_under_the_cursor_when_the_map_moves(mv):
    v = mv()
    v.open(CITY)
    v.jump(-96.7355, 43.5330, 14)
    v.start()
    v.click(400, 400)                           # el click deja el foco en el mapa
    box = v.canvas_box()
    v.page.mouse.move(box["x"] + 700, box["y"] + 450, steps=5)
    v.wait("() => !document.querySelector('.measure-preview').hasAttribute('hidden')")
    v.page.keyboard.press("ArrowRight")         # paneo con el teclado, sin mover el mouse
    v.page.wait_for_timeout(800)
    end = v.page.evaluate("""() => {
      const l = document.querySelector('.measure-preview line');
      return [Number(l.getAttribute('x2')), Number(l.getAttribute('y2'))];
    }""")
    assert abs(end[0] - 700) <= 2 and abs(end[1] - 450) <= 2, f"la vista previa termina en {end}"
    v.assert_no_errors()
