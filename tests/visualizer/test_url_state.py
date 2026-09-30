"""
La vista en la URL y `Share view` (etapa 4 del visor).

Abre visualizer/map.html en Chromium (Playwright) contra un http.server local de
solo lectura. Necesita red (MapLibre viene de unpkg) y el navegador de
Playwright, así que queda fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

Contrato: docs/plans/2026-09-26-layout-visor/08-etapa-4-spec.md
"""
import functools
import http.server
import json
import os
import re
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

pytestmark = [pytest.mark.network, pytest.mark.browser]

VISUALIZER = Path(__file__).resolve().parents[2] / "visualizer"
MPLS = "minneapolis"   # 6 módulos + plan oficial
NYC = "new_york"       # solo zonificación
SAVE_KEY = f"cs2-view-state-{MPLS}-v2"
LOAD_MS = 60_000
CAMERA = re.compile(r"^\d+(\.\d+)?/-?\d+(\.\d+)?/-?\d+(\.\d+)?$")

IDLE_JS = """() => new Promise(resolve => {
  const map = window.CS2_MAP;
  map.once('idle', () => resolve(true));
  map.triggerRepaint();
  setTimeout(() => resolve(false), 15000);
})"""


def saved_state_js(state):
    return f"localStorage.setItem({json.dumps(SAVE_KEY)}, {json.dumps(json.dumps(state))});"


# ── Infraestructura ─────────────────────────────────────────────────────────

class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    handler = functools.partial(_QuietHandler, directory=str(VISUALIZER))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            # WebGL por software: sin GPU, Chromium headless solo usa SwiftShader con este flag
            b = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
        except Exception as e:  # navegador no instalado
            pytest.skip(f"Chromium de Playwright no disponible: {e}")
        yield b
        b.close()


class Viewer:
    """Una pestaña con el visor, y lo que el test necesita leer de ella."""

    def __init__(self, page, base):
        self.page = page
        self.base = base
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(str(e)))
        # Las descargas fallidas (las que abortamos a propósito, el favicon) no
        # cuentan: lo que interesa son los errores del código
        page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
                and self.errors.append(m.text))

    def open(self, slug, hash_=""):
        url = f"{self.base}/map.html?city={slug}" + (f"#{hash_}" if hash_ else "")
        self.page.goto(url, wait_until="domcontentloaded", timeout=LOAD_MS)
        self.wait_loaded()

    def wait_loaded(self):
        self.wait("() => { const l = document.getElementById('loading'); return l && l.style.display === 'none'; }")

    def wait(self, js, arg=None):
        self.page.wait_for_function(js, arg=arg, timeout=LOAD_MS)

    def wait_official(self):
        self.wait("() => window._cs2OfficialZoningCount !== undefined")

    def wait_late_modules(self):
        self.wait("() => window._cs2TransporteCount !== undefined && window._cs2InfraCount !== undefined")

    def params(self):
        raw = self.page.evaluate("location.hash").lstrip("#")
        out = {}
        for part in raw.split("&"):
            if part:
                key, _, value = part.partition("=")
                out[key] = value
        return out

    def layers(self):
        return dict(e.split(".", 1) for e in self.params().get("layers", "").split(",") if e)

    def module_state(self, mod):
        return self.page.get_attribute(
            f'[data-module="{mod}"] [data-module-state][aria-pressed="true"]', "data-module-state")

    def pressed(self, attr):
        return self.page.get_attribute(f'[{attr}][aria-pressed="true"]', attr)

    def hidden(self, mod):
        return self.page.evaluate(
            """mod => [...document.querySelectorAll(`[data-module="${mod}"] .cat-row`)]
                 .filter(r => !r.querySelector('.cat-check').checked).map(r => r.dataset.cat)""", mod)

    def catalog(self, mod):
        return self.page.evaluate(
            """mod => [...document.querySelectorAll(`[data-module="${mod}"] .cat-row`)].map(r => r.dataset.cat)""", mod)

    def saved(self):
        return self.page.evaluate("key => JSON.parse(localStorage.getItem(key))", SAVE_KEY)

    def camera(self):
        return self.page.evaluate(
            "() => { const m = window.CS2_MAP, c = m.getCenter(); return {zoom: m.getZoom(), lng: c.lng, lat: c.lat, pitch: m.getPitch()}; }")

    def jump(self, lng, lat, zoom):
        self.page.evaluate("([lng, lat, zoom]) => window.CS2_MAP.jumpTo({center: [lng, lat], zoom})", [lng, lat, zoom])

    def assert_no_errors(self):
        assert self.errors == [], self.errors


@pytest.fixture
def viewer(browser, base_url):
    contexts = []

    def make(*, init=(), viewport=(1440, 900), **ctx_kwargs):
        ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]}, **ctx_kwargs)
        contexts.append(ctx)
        for script in init:
            ctx.add_init_script(script)
        return Viewer(ctx.new_page(), base_url)

    yield make
    for ctx in contexts:
        ctx.close()


# ── Ida y vuelta ────────────────────────────────────────────────────────────

def test_fresh_visit_writes_the_full_state(viewer):
    v = viewer()
    v.open(MPLS)
    v.wait_late_modules()
    p = v.params()
    assert CAMERA.match(p["map"])
    assert p["base"] == "dark"
    assert p["src"] == "osm"
    assert p["layers"] == "zoning.on,vial.dim,services.off,transporte.off,infraestructura.off"
    assert not [k for k in p if k.startswith("hide.")]
    assert v.saved() is None   # la primera visita no guarda nada
    v.assert_no_errors()


def test_view_survives_a_reload(viewer):
    v = viewer()
    v.open(MPLS)
    v.wait_official()
    v.page.click('[data-module="vial"] [data-module-state="off"]')
    v.page.click('[data-basemap="sat"]')
    v.page.locator('[data-module="zoning"] .cat-row[data-cat="res_low_house"] .cat-check').set_checked(False)
    v.page.click('[data-source="official"]')
    v.jump(-93.25, 44.98, 14.5)
    v.wait("() => location.hash.includes('map=14.5/')")

    p = v.params()
    assert p["base"] == "sat"
    assert p["src"] == "official"
    assert v.layers()["vial"] == "off"
    assert p["hide.zoning"] == "res_low_house"

    v.page.reload(wait_until="domcontentloaded")
    v.wait_loaded()
    v.wait_official()
    v.wait("() => document.querySelector('[data-source=\"official\"]').getAttribute('aria-pressed') === 'true'")
    assert v.module_state("vial") == "off"
    assert v.pressed("data-basemap") == "sat"
    assert v.hidden("zoning") == ["res_low_house"]
    cam = v.camera()
    assert cam["zoom"] == pytest.approx(14.5, abs=0.01)
    assert cam["lng"] == pytest.approx(-93.25, abs=1e-4)
    assert cam["lat"] == pytest.approx(44.98, abs=1e-4)
    v.assert_no_errors()


# ── Precedencia y guardado ──────────────────────────────────────────────────

def test_url_wins_over_saved_and_importing_does_not_save(viewer):
    saved = {"modules": {"vial": "off", "services": "on"}, "basemap": "sat"}
    v = viewer(init=[saved_state_js(saved)])
    v.open(MPLS, "base=dark&layers=vial.on")
    assert v.pressed("data-basemap") == "dark"
    assert v.module_state("vial") == "on"          # de la URL
    assert v.module_state("services") == "on"      # no está en la URL: el guardado
    assert v.module_state("zoning") == "on"        # ni URL ni guardado: primera visita
    assert v.layers()["vial"] == "on"
    assert v.layers()["services"] == "on"
    assert v.saved() == saved                      # importar no escribe

    # Guardar solo el campo que la persona toca: el vial.on del link no se guarda
    v.page.click('[data-module="services"] [data-module-state="off"]')
    after = v.saved()
    assert after["modules"]["services"] == "off"
    assert after["modules"]["vial"] == "off"
    assert after["basemap"] == "sat"
    v.assert_no_errors()


def test_saved_state_applies_without_a_hash(viewer):
    saved = {"modules": {"vial": "off"}, "basemap": "sat", "source": "official"}
    v = viewer(init=[saved_state_js(saved)])
    v.open(MPLS)
    assert v.pressed("data-basemap") == "sat"
    assert v.module_state("vial") == "off"
    assert v.params()["src"] == "official"         # lo pedido, aunque el plan todavía cargue
    v.wait_official()
    v.wait("() => document.querySelector('[data-source=\"official\"]').getAttribute('aria-pressed') === 'true'")
    v.assert_no_errors()


def test_invalid_params_are_dropped_one_by_one(viewer):
    v = viewer()
    v.open(MPLS, "map=abc/1/2&base=purple&src=weird&layers=zoning.maybe,foo.on,vial.dim,vial.off"
                 "&hide.zoning=nope,industrial,industrial&hide.foo=bar&extra=1")
    assert v.module_state("zoning") == "on"
    assert v.module_state("vial") == "off"         # duplicado: gana la última
    assert v.pressed("data-basemap") == "dark"
    assert v.hidden("zoning") == ["industrial"]
    p = v.params()
    assert CAMERA.match(p["map"])                  # encuadró la ciudad
    assert p["base"] == "dark"
    assert p["src"] == "osm"
    assert p["hide.zoning"] == "industrial"
    assert "extra" not in p and "hide.foo" not in p
    assert "foo" not in v.layers()
    v.assert_no_errors()


def test_single_module_city_ignores_layers_and_source(viewer):
    v = viewer()
    v.open(NYC, "layers=zoning.off&src=official&base=sat")
    assert v.page.locator("[data-module-state]").count() == 0
    assert v.page.evaluate("() => window.CS2_MAP.getLayoutProperty('zoning-fill', 'visibility')") != "none"
    p = v.params()
    assert "layers" not in p and "src" not in p
    assert p["base"] == "sat"
    assert v.page.is_visible("#share-view")
    v.assert_no_errors()


def test_hash_cannot_tilt_the_map(viewer):
    v = viewer()
    v.open(MPLS, "map=14/44.9778/-93.265/0/60")
    cam = v.camera()
    assert cam["pitch"] == 0
    assert cam["zoom"] == pytest.approx(14, abs=0.01)
    v.assert_no_errors()


# ── hashchange ──────────────────────────────────────────────────────────────

def test_hashchange_reimports_without_saving(viewer):
    v = viewer()
    v.open(MPLS)
    zoom = v.camera()["zoom"]

    v.page.evaluate("location.hash = '#layers=vial.off&hide.vial=bike&base=sat'")
    v.wait("() => document.querySelector('[data-module=\"vial\"]').dataset.state === 'off'")
    assert v.pressed("data-basemap") == "sat"
    assert v.hidden("vial") == ["bike"]
    assert v.camera()["zoom"] == pytest.approx(zoom, abs=0.01)   # sin map=: la cámara queda
    assert CAMERA.match(v.params()["map"])
    assert v.saved() is None

    # Sin hash: vuelve a lo guardado (nada) y a la primera visita, todo visible
    v.page.evaluate("location.hash = ''")
    v.wait("() => document.querySelector('[data-module=\"vial\"]').dataset.state === 'dim'")
    assert v.pressed("data-basemap") == "dark"
    assert v.hidden("vial") == []
    assert v.camera()["zoom"] == pytest.approx(zoom, abs=0.01)
    assert v.saved() is None
    v.assert_no_errors()


# ── Only / Restore sobre un filtro importado ────────────────────────────────

def test_only_and_restore_over_an_imported_filter(viewer):
    v = viewer()
    v.open(MPLS, "hide.zoning=res_low_house,com_low")
    notice = v.page.locator('[data-module="zoning"] .notice-action')
    assert v.hidden("zoning") == ["res_low_house", "com_low"]
    assert notice.inner_text() == "Show all"       # no hay foto de un Only

    v.page.click('[data-module="zoning"] .cat-group[data-sect="Industrial"] .group-only')
    everything_but_industrial = [k for k in v.catalog("zoning") if k != "industrial"]
    assert v.hidden("zoning") == everything_but_industrial
    assert v.params()["hide.zoning"] == ",".join(everything_but_industrial)
    assert notice.inner_text() == "Restore"

    notice.click()
    assert v.hidden("zoning") == ["res_low_house", "com_low"]
    assert v.params()["hide.zoning"] == "res_low_house,com_low"
    v.assert_no_errors()


# ── Módulos que cargan tarde ────────────────────────────────────────────────

def test_late_transit_gets_the_linked_state(viewer):
    v = viewer()
    held = []
    v.page.route("**/datos_transporte.js*", lambda route: held.append(route))
    v.open(MPLS, "layers=transporte.on&hide.transporte=bus")
    # Mientras carga, la URL sigue diciendo lo que pidió el link
    assert v.layers()["transporte"] == "on"
    assert v.params()["hide.transporte"] == "bus"

    for route in held:
        route.continue_()
    v.wait("() => window._cs2TransporteCount !== undefined")
    assert v.module_state("transporte") == "on"
    assert v.hidden("transporte") == ["bus"]
    assert v.page.evaluate("() => window.CS2_MAP.getLayoutProperty('transporte-line', 'visibility')") == "visible"
    assert '"bus"' in json.dumps(v.page.evaluate("() => window.CS2_MAP.getFilter('transporte-line')"))
    assert v.layers()["transporte"] == "on"
    assert v.saved() is None
    v.assert_no_errors()


def test_failed_transit_is_written_off(viewer):
    v = viewer()
    v.page.route("**/datos_transporte.js*", lambda route: route.abort())
    v.open(MPLS, "layers=transporte.on&hide.transporte=bus")
    v.wait("() => document.querySelector('[data-module=\"transporte\"]').dataset.state === 'failed'")
    v.wait("() => location.hash.includes('transporte.off')")
    assert "hide.transporte" not in v.params()
    assert v.saved() is None
    v.assert_no_errors()


def test_picking_osm_while_the_plan_loads_wins(viewer):
    v = viewer()
    held = []
    v.page.route("**/datos_zonificacion_official.js*", lambda route: held.append(route))
    v.open(MPLS, "src=official")
    assert v.params()["src"] == "official"
    # El botón muestra lo pedido; el mapa, OSM hasta que llegue el plan
    assert v.pressed("data-source") == "official"
    assert v.page.evaluate("() => window.CS2_MAP.getLayoutProperty('zoning-fill', 'visibility')") == "visible"

    v.page.click('[data-source="osm"]')            # OSM ya se ve, pero cancela lo pedido
    assert v.pressed("data-source") == "osm"
    assert v.params()["src"] == "osm"
    for route in held:
        route.continue_()
    v.wait_official()
    v.page.wait_for_timeout(300)
    assert v.pressed("data-source") == "osm"
    assert v.params()["src"] == "osm"
    assert v.saved()["source"] == "osm"            # fue una elección de la persona
    v.assert_no_errors()


def test_failed_official_plan_falls_back_to_osm(viewer):
    v = viewer()
    v.page.route("**/datos_zonificacion_official.js*", lambda route: route.abort())
    v.open(MPLS, "src=official&hide.zoning=industrial")
    v.wait("() => document.querySelector('.src-name').textContent.includes(\"couldn't load\")")
    v.wait("() => location.hash.includes('src=osm')")
    assert v.params()["hide.zoning"] == "industrial"
    assert v.pressed("data-source") == "osm"
    assert v.saved() is None
    v.assert_no_errors()


# ── Share view ──────────────────────────────────────────────────────────────

def test_share_copies_the_current_view(viewer):
    v = viewer(permissions=["clipboard-read", "clipboard-write"])
    v.open(MPLS, "base=sat")
    assert v.page.is_hidden("#share-status") and v.page.is_hidden("#share-panel")
    # Dos saltos seguidos: el hash de MapLibre puede quedar atrasado (throttle de
    # 300 ms), el link no
    v.jump(-93.26, 44.97, 13)
    v.jump(-93.2650, 44.9778, 15.25)
    v.page.click("#share-view")
    v.wait("() => !document.getElementById('share-status').hidden")
    assert "Link copied" in v.page.inner_text("#share-status")
    link = v.page.evaluate("() => navigator.clipboard.readText()")
    assert link.startswith(f"{v.base}/map.html?city={MPLS}#map=15.25/")
    assert "base=sat" in link
    assert link == v.page.evaluate("location.href")   # compartir también reescribe el hash
    v.wait("() => document.getElementById('share-status').hidden")
    v.assert_no_errors()


def _select_a_building(v):
    """Clickea el centro de Minneapolis hasta que quede algo seleccionado."""
    v.jump(-93.2650, 44.9778, 17.5)
    v.page.evaluate(IDLE_JS)
    box = v.page.locator("#map canvas").bounding_box()
    for fy in (0.5, 0.45, 0.55, 0.4, 0.6):
        for fx in (0.5, 0.45, 0.55, 0.4, 0.6):
            v.page.mouse.click(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy)
            if v.page.is_visible("#selection"):
                return
    pytest.fail("no se pudo seleccionar nada en el centro de Minneapolis")


def test_share_without_clipboard_shows_the_link(viewer):
    no_clipboard = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, "
                    "value: {writeText: () => Promise.reject(new Error('denied'))}});")
    v = viewer(init=[no_clipboard])
    v.open(MPLS)
    _select_a_building(v)

    v.page.click("#share-view")
    v.wait("() => !document.getElementById('share-panel').hidden")
    field = v.page.locator("#share-panel input")
    link = field.input_value()
    assert link.startswith(f"{v.base}/map.html?city={MPLS}#map=")
    assert field.evaluate("el => el.selectionStart === 0 && el.selectionEnd === el.value.length")

    # Esc cierra el panel, devuelve el foco y no borra la selección
    v.page.keyboard.press("Escape")
    assert v.page.is_hidden("#share-panel")
    assert v.page.evaluate("() => document.activeElement.id") == "share-view"
    assert v.page.is_visible("#selection")
    v.assert_no_errors()


NATIVE_SHARE = """
window.__shared = []; window.__copied = [];
Object.defineProperty(navigator, 'share', {configurable: true,
  value: data => { window.__shared.push(data); return window.__shareResult(); }});
Object.defineProperty(navigator, 'clipboard', {configurable: true,
  value: {writeText: text => { window.__copied.push(text); return Promise.resolve(); }}});
"""


@pytest.mark.parametrize("outcome", ["shared", "cancelled"])
def test_share_uses_the_native_sheet_on_touch(viewer, outcome):
    result = ("window.__shareResult = () => Promise.resolve();" if outcome == "shared" else
              "window.__shareResult = () => Promise.reject(new DOMException('cancel', 'AbortError'));")
    v = viewer(init=[NATIVE_SHARE, result], viewport=(390, 844), is_mobile=True, has_touch=True)
    v.open(MPLS)
    v.page.click("#share-view")
    v.wait("() => window.__shared.length === 1")
    shared = v.page.evaluate("() => window.__shared[0]")
    assert shared["url"].startswith(f"{v.base}/map.html?city={MPLS}#map=")
    assert "Minneapolis" in shared["title"]
    v.page.wait_for_timeout(300)
    assert v.page.evaluate("() => window.__copied") == []    # cancelar tampoco copia
    assert v.page.is_hidden("#share-status") and v.page.is_hidden("#share-panel")
    v.assert_no_errors()


def test_thumbnails_hide_the_share_button(viewer):
    from shared.thumbnails import _hide_chrome_js

    v = viewer()
    v.open(NYC)
    v.page.evaluate(_hide_chrome_js())
    assert v.page.is_hidden("#share-view")
    v.assert_no_errors()
