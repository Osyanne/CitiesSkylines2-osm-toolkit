"""
Contador de visitas (GoatCounter, visualizer/assets/visits.js).

Abre el sitio en Chromium (Playwright) como si estuviera publicado: las
peticiones a osyanne.github.io se contestan con los archivos del repo y la de
gc.zgo.at con la copia de count.v5.js de tests/fixtures, así corre el script
real, con su hash, sin red. navigator.sendBeacon queda grabado en vez de salir,
y todo lo demás (MapLibre, fuentes, la API de GitHub) se corta: el contador no
lo necesita. A mano, desde src/:

    uv run --group thumbnails pytest ../tests/visualizer/test_visits.py -m browser
"""
import functools
import http.server
import re
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

# `network` aunque no sale a la red: así queda fuera de las corridas por defecto
# (-m "not network"), como los otros tests de navegador
pytestmark = [pytest.mark.network, pytest.mark.browser]

REPO = Path(__file__).resolve().parents[2]
SITE = "https://osyanne.github.io/CitiesSkylines2-osm-toolkit/"
LANDING = SITE + "visualizer/"
_VISITS = (REPO / "visualizer" / "assets" / "visits.js").read_text(encoding="utf-8")
COUNT_JS = re.search(r's\.src = "([^"]+)"', _VISITS).group(1)
ENDPOINT = re.search(r'"data-goatcounter", "([^"]+)"', _VISITS).group(1)
FIXTURE = REPO / "tests" / "fixtures" / "goatcounter" / COUNT_JS.rsplit("/", 1)[1]
REDDIT = "https://www.reddit.com/"
LOAD_MS = 30_000

RECORD_BEACONS = """
window.__beacons = [];
navigator.sendBeacon = (url) => { window.__beacons.push(String(url)); return true; };
"""


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True)
        except Exception as e:  # navegador no instalado
            pytest.skip(f"Chromium de Playwright no disponible: {e}")
        yield b
        b.close()


def _serve_published(route):
    url = route.request.url
    if url.startswith(SITE):
        path = REPO / urlsplit(url).path.removeprefix(urlsplit(SITE).path)
        if path.is_dir():
            path = path / "index.html"
        if path.is_file():
            return route.fulfill(path=str(path))
        return route.fulfill(status=404, body="not found")
    if url == COUNT_JS:
        return route.fulfill(path=str(FIXTURE), content_type="text/javascript; charset=utf-8",
                             headers={"Access-Control-Allow-Origin": "*"})
    return route.abort()


@pytest.fixture
def page(browser):
    """Una pestaña sobre el sitio publicado, sin red."""
    context = browser.new_context()
    context.add_init_script(RECORD_BEACONS)
    context.route("**/*", _serve_published)
    tab = context.new_page()
    yield tab
    context.close()


def open_site(page, url, referer=None):
    page.goto(url, referer=referer, wait_until="domcontentloaded", timeout=LOAD_MS)


def counted(page):
    """Lo que la página le mandó a GoatCounter: una sola visita."""
    page.wait_for_function("() => window.__beacons && window.__beacons.length > 0", timeout=LOAD_MS)
    page.wait_for_timeout(300)  # por si saliera una segunda
    beacons = page.evaluate("window.__beacons")
    assert len(beacons) == 1, beacons
    assert beacons[0].startswith(ENDPOINT + "?")
    return parse_qs(urlsplit(beacons[0]).query)


def test_the_root_redirect_counts_where_the_visit_came_from(page):
    # El post enlaza la raíz, que salta a la landing: sin el arreglo, la visita
    # figuraría como venida del propio sitio
    open_site(page, SITE, referer=REDDIT)
    page.wait_for_url(LANDING, timeout=LOAD_MS)
    hit = counted(page)
    assert hit["p"] == ["/CitiesSkylines2-osm-toolkit/visualizer/"]
    assert hit["r"] == [REDDIT]


def test_the_root_redirect_keeps_campaign_parameters(page):
    open_site(page, SITE + "?ref=reddit-claudeai")
    page.wait_for_url(LANDING + "?ref=reddit-claudeai", timeout=LOAD_MS)
    hit = counted(page)
    assert hit["p"] == ["/CitiesSkylines2-osm-toolkit/visualizer/"]
    assert hit["q"] == ["?ref=reddit-claudeai"]


def test_a_direct_visit_to_the_root_has_no_referrer(page):
    # No tiene que figurar la raíz como origen: es una visita directa
    open_site(page, SITE)
    page.wait_for_url(LANDING, timeout=LOAD_MS)
    assert "r" not in counted(page)


def test_a_reload_never_reports_the_site_root(page):
    # Al recargar, el navegador repite la raíz como referrer y ya no queda nada
    # guardado: mejor una visita directa que una venida del propio sitio
    open_site(page, SITE, referer=REDDIT)
    page.wait_for_url(LANDING, timeout=LOAD_MS)
    assert counted(page)["r"] == [REDDIT]
    page.reload(wait_until="domcontentloaded", timeout=LOAD_MS)
    assert page.evaluate("document.referrer") == SITE
    assert "r" not in counted(page)


def test_a_city_map_counts_one_path_per_city(page):
    open_site(page, LANDING + "map.html?city=minneapolis&utm_source=reddit#map=12/44.97/-93.27",
              referer=REDDIT)
    hit = counted(page)
    assert hit["p"] == ["/CitiesSkylines2-osm-toolkit/visualizer/map.html?city=minneapolis"]
    assert hit["r"] == [REDDIT]
    assert hit["q"] == ["?city=minneapolis&utm_source=reddit"]


def test_the_saved_referrer_is_used_only_once(page):
    open_site(page, SITE, referer=REDDIT)
    page.wait_for_url(LANDING, timeout=LOAD_MS)
    assert counted(page)["r"] == [REDDIT]
    # Misma pestaña, dirección escrita a mano: ya no vino de Reddit
    open_site(page, LANDING + "map.html?city=minneapolis")
    assert "r" not in counted(page)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def local_url():
    handler = functools.partial(_QuietHandler, directory=str(REPO))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize("path", ["/", "/visualizer/map.html?city=minneapolis"])
def test_nothing_is_counted_off_the_published_site(browser, local_url, path):
    # Un servidor local (tests, miniaturas) o un fork no le mandan nada a GoatCounter
    context = browser.new_context()
    requests = []
    context.on("request", lambda r: requests.append(r.url))
    context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(local_url)
                  else route.abort())
    tab = context.new_page()
    tab.goto(local_url + path, wait_until="load", timeout=LOAD_MS)
    tab.wait_for_function("() => location.pathname.startsWith('/visualizer/')", timeout=LOAD_MS)
    tab.wait_for_load_state("load")
    tab.wait_for_timeout(500)
    assert tab.evaluate("typeof window.goatcounter") == "undefined"
    assert not [u for u in requests if "goatcounter" in u or "zgo.at" in u]
    context.close()
