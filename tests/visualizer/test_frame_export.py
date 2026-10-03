"""
Exportar el recuadro del mapa jugable como PNG para Image Overlay (etapa 6b del visor).

Mismo arreglo que los demás tests del visor: Chromium (Playwright) contra un http.server
local, fuera del CI (`-m "not network"`). A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer -m browser

El PNG se lee sin dependencias nuevas: el tamaño sale de la cabecera IHDR y los píxeles
se decodifican en el mismo navegador.

Contrato: docs/plans/2026-09-26-layout-visor/10-etapa-6b-spec.md
"""
import base64
import re
import struct

import pytest

from .test_playable_frame import CITY, FrameViewer, assert_near, fv  # noqa: F401 (fixture)
from .test_url_state import MPLS, base_url, browser, viewer  # noqa: F401 (fixtures)

pytestmark = [pytest.mark.network, pytest.mark.browser]

FRAME = "frame=43.53295,-96.73548"
CENTER = (43.53295, -96.73548)
EXPORT_MS = 180_000

# Estadísticas del PNG, decodificado en la página
STATS_JS = """async ([b64, grid]) => {
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const bmp = await createImageBitmap(new Blob([bin], {type: 'image/png'}));
  const w = bmp.width, h = bmp.height;
  const ctx = new OffscreenCanvas(w, h).getContext('2d', {willReadFrequently: true});
  ctx.drawImage(bmp, 0, 0);
  const d = ctx.getImageData(0, 0, w, h).data;
  const lum = i => 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
  let transparent = 0, opaque = 0;
  const colors = new Set();
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] === 0) transparent++;
    else if (d[i + 3] === 255) opaque++;
    if ((i / 4) % 97 === 0) colors.add(`${d[i]},${d[i + 1]},${d[i + 2]},${d[i + 3]}`);
  }
  // Esquina inferior derecha: la caja de la atribución
  let dark = 0, light = 0, covered = 0, total = 0;
  for (let y = Math.floor(h * 0.975); y < h; y++) {
    for (let x = Math.floor(w * 0.72); x < w; x++) {
      const i = (y * w + x) * 4;
      total++;
      if (d[i + 3] > 0) covered++;
      if (d[i + 3] > 0 && lum(i) < 60) dark++;
      if (d[i + 3] > 0 && lum(i) > 200) light++;
    }
  }
  // Brillo medio de cada columna de la grilla (la más clara en ±4 px de x = k·w/23)
  const columns = [];
  if (grid) {
    for (let k = 1; k < 23; k++) {
      const x0 = Math.round(k * w / 23);
      let best = 0;
      for (let x = Math.max(0, x0 - 4); x <= Math.min(w - 1, x0 + 4); x++) {
        let sum = 0;
        for (let y = 0; y < h; y += 4) sum += lum((y * w + x) * 4);
        best = Math.max(best, sum / Math.ceil(h / 4));
      }
      columns.push(best);
    }
  }
  return {w, h, transparent, opaque, colors: colors.size,
          corner: {dark, light, covered, total}, columns};
}"""

GL_LIMIT_JS = """() => {
  const gl = document.createElement('canvas').getContext('webgl2') ||
             document.createElement('canvas').getContext('webgl');
  if (!gl) return 0;
  const dims = gl.getParameter(gl.MAX_VIEWPORT_DIMS);
  return Math.min(gl.getParameter(gl.MAX_RENDERBUFFER_SIZE), gl.getParameter(gl.MAX_TEXTURE_SIZE), dims[0], dims[1]);
}"""


def png_size(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "no es un PNG"
    return struct.unpack(">II", data[16:24])


class ExportViewer(FrameViewer):
    def open_menu(self):
        if self.page.get_attribute("#frame-export", "aria-expanded") != "true":
            self.page.click("#frame-export")
        self.wait("() => { const m = document.getElementById('export-menu'); return m && !m.hidden && m.getClientRects().length > 0; }")

    def choose(self, size=2048, bg="map", grid=False):
        self.open_menu()
        self.page.check(f'input[name="export-size"][value="{size}"]')
        self.page.check(f'input[name="export-bg"][value="{bg}"]')
        self.page.locator("#export-grid").set_checked(grid)

    def export(self, **options):
        self.choose(**options)
        self.wait("() => !document.getElementById('export-go').disabled")
        with self.page.expect_download(timeout=EXPORT_MS) as info:
            self.page.click("#export-go")
        download = info.value
        data = open(download.path(), "rb").read()
        return download.suggested_filename, data

    def stats(self, data, grid=False):
        return self.page.evaluate(STATS_JS, [base64.b64encode(data).decode("ascii"), grid])

    def status(self):
        return self.page.inner_text("#export-status")

    def map_count(self):
        return self.page.evaluate("() => document.querySelectorAll('.maplibregl-map').length")


@pytest.fixture
def ev(viewer):
    def make(**kwargs):
        v = viewer(**kwargs)
        return ExportViewer(v.page, v.base)
    return make


# ── Menú ────────────────────────────────────────────────────────────────────

def test_menu_defaults_and_escape(ev):
    v = ev()
    v.open(CITY, FRAME)
    assert v.page.get_attribute("#frame-export", "aria-expanded") == "false"
    v.open_menu()
    assert v.page.get_attribute("#frame-export", "aria-expanded") == "true"
    assert v.page.is_checked('input[name="export-size"][value="4096"]')
    assert v.page.is_checked('input[name="export-bg"][value="map"]')
    assert not v.page.is_checked("#export-grid")
    has_8192 = v.page.locator('input[name="export-size"][value="8192"]').count() == 1
    assert has_8192 == (v.page.evaluate(GL_LIMIT_JS) >= 8192)
    v.page.keyboard.press("Escape")
    v.wait("() => document.getElementById('export-menu').hidden")
    assert v.page.get_attribute("#frame-export", "aria-expanded") == "false"
    assert v.page.evaluate("() => document.activeElement.id") == "frame-export"
    v.assert_no_errors()


# ── La imagen ───────────────────────────────────────────────────────────────

def test_export_with_the_map_background(ev):
    v = ev()
    v.open(CITY, FRAME)
    v.idle()
    camera, hash_before, saved_before = v.camera(), v.page.evaluate("location.hash"), v.saved()
    name, data = v.export(size=2048, bg="map")
    m = re.fullmatch(r"sioux-falls-playable-area-(-?\d+\.\d{4})_(-?\d+\.\d{4})-2048\.png", name)
    assert m, name
    assert_near((float(m.group(1)), float(m.group(2))), CENTER, 15, "centro en el nombre")
    assert png_size(data) == (2048, 2048)
    s = v.stats(data)
    assert s["colors"] > 50, "la imagen es casi de un solo color"
    assert s["transparent"] == 0                       # con fondo, todo opaco
    c = s["corner"]
    assert c["dark"] > c["total"] * 0.2 and c["light"] > 20, f"no aparece la atribución: {c}"
    # El mapa principal no se tocó
    assert v.camera() == camera
    assert v.page.evaluate("location.hash") == hash_before
    assert v.saved() == saved_before
    assert v.page.is_visible("#export-link")
    assert "Ready" in v.status()
    assert v.map_count() == 1                          # el mapa de exportación se fue
    v.assert_no_errors()


def test_transparent_export_keeps_alpha_and_hidden_categories_out(ev):
    v = ev()
    v.open(CITY, FRAME)
    _, full = v.export(size=2048, bg="transparent")
    s_full = v.stats(full)
    assert s_full["transparent"] > 0 and s_full["opaque"] > 0
    assert s_full["corner"]["covered"] > s_full["corner"]["total"] * 0.2   # la atribución también va
    # Con casi todas las zonas ocultas quedan muchos menos píxeles pintados
    keep = "industrial"
    hidden = ",".join(c for c in v.catalog("zoning") if c != keep)
    w = ev()
    w.open(CITY, f"{FRAME}&hide.zoning={hidden}")
    _, few = w.export(size=2048, bg="transparent")
    s_few = w.stats(few)
    assert s_few["opaque"] < s_full["opaque"] * 0.5, (s_few["opaque"], s_full["opaque"])
    v.assert_no_errors()
    w.assert_no_errors()


def test_tile_grid_option_draws_the_23_by_23_lines(ev):
    v = ev()
    v.open(CITY, FRAME)
    _, plain = v.export(size=2048, bg="map", grid=False)
    _, grid = v.export(size=2048, bg="map", grid=True)
    plain_cols = v.stats(plain, grid=True)["columns"]
    grid_cols = v.stats(grid, grid=True)["columns"]
    brighter = sum(g > p + 2 for g, p in zip(grid_cols, plain_cols))
    assert brighter >= 18, f"solo {brighter} de 22 columnas se aclararon"
    assert v.map_count() == 1                          # dos exportaciones, nada colgado
    v.assert_no_errors()


# ── Errores y esperas ───────────────────────────────────────────────────────

def test_blocked_basemap_fails_and_transparent_still_works(ev):
    v = ev()
    v.page.context.route(re.compile(r"server\.arcgisonline\.com"), lambda route: route.abort())
    v.open(CITY, FRAME)
    v.choose(size=2048, bg="map")
    v.page.click("#export-go")
    v.wait("() => document.getElementById('export-status').textContent.includes('Basemap tiles failed to load')")
    assert v.map_count() == 1
    assert not v.page.is_disabled("#export-go")
    _, data = v.export(size=2048, bg="transparent")
    assert png_size(data) == (2048, 2048)
    v.assert_no_errors()


def test_export_waits_for_layers_that_are_still_loading(ev):
    v = ev()
    held = []
    v.page.context.route("**/datos_transporte.js*", lambda route: held.append(route))
    v.open(MPLS, "layers=zoning.on,vial.dim,services.off,transporte.on,infraestructura.off&frame=44.97000,-93.27000")
    v.open_menu()
    v.wait("() => document.getElementById('export-go').disabled")
    assert "Waiting for layers" in v.status()
    for route in held:
        route.continue_()
    v.wait("() => window._cs2TransporteCount !== undefined")
    v.wait("() => !document.getElementById('export-go').disabled")
    v.assert_no_errors()


# ── Celular ─────────────────────────────────────────────────────────────────

def test_menu_fits_on_a_phone(ev):
    v = ev(viewport=(390, 844), is_mobile=True, has_touch=True)
    v.open(CITY, FRAME)
    v.open_menu()
    menu = v.page.locator("#export-menu").bounding_box()
    assert menu["x"] >= 0 and menu["y"] >= 0
    assert menu["x"] + menu["width"] <= 390 and menu["y"] + menu["height"] <= 844
    tray = v.page.locator("#layers-col").bounding_box()
    assert menu["y"] + menu["height"] <= tray["y"] + 1, f"el menú {menu} tapa la bandeja {tray}"
    v.assert_no_errors()
