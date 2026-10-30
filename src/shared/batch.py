"""Un lote de pedidos de ciudades con un solo comando.

Las entradas ya tienen que estar en cities.json. Antes de bajar nada revisa cada
caja (rango, tamaño, centro y que caiga dentro de sus regiones de Geofabrik);
después baja los PBF, extrae la zonificación de a tres ciudades, regenera la
landing y saca las miniaturas contra un servidor local:

    uv run --group thumbnails process-cities tulsa timisoara

Queda a mano: mirar las miniaturas, el CHANGELOG y la tabla de ciudades de los
README. Una ciudad suelta se sigue pudiendo extraer con `extract-zoning --city`.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatchcase
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
import yaml
from shapely.geometry import box, shape
from shapely.ops import unary_union

from shared import landing
from shared.pbf_cache import DEFAULT_CACHE_DIR, GEOFABRIK_BASE, ensure_index, ensure_pbf
from shared.registry import RegistryError, load_cities, load_manifest, pbf_regions
from shared.thumbnails import capture_thumbnails

# Los pedidos que se recortaron medían 55 km o más de lado; Singapur entera (48 km) se dejó
MAX_SIDE_KM = 50
# Singapur y Groningen dejan 1-2 % de mar fuera del contorno de sus regiones
MIN_COVERAGE = 0.95
# Leer un PBF es CPU y cada proceso usa ~0,25 GB: tres a la vez andan bien
PARALLEL_EXTRACTIONS = 3
PAGES_LIMIT_MB = 1024
LOG_DIR = DEFAULT_CACHE_DIR.parent / "logs"


def city_problems(entry: dict, shapes: dict | None = None) -> list[str]:
    """Lo que está mal en la entrada de una ciudad, antes de bajar ningún PBF.

    `shapes` son los contornos de sus regiones de Geofabrik (`region_shapes`):
    sin ellos no se ve una caja en orden lon/lat que igual cae en rangos válidos.
    """
    s, w, n, e = entry["bbox"]
    if not (-90 <= s < n <= 90 and -180 <= w < e <= 180):
        return [f"caja {entry['bbox']} fuera de rango: ¿está en metros o en orden lon/lat?"]
    problems = []
    height = (n - s) * 111.32
    width = (e - w) * 111.32 * math.cos(math.radians((s + n) / 2))
    if max(width, height) > MAX_SIDE_KM:
        problems.append(f"caja de {width:.0f} × {height:.0f} km: más de {MAX_SIDE_KM} km de lado, recortarla")
    lat, lon = entry["center"]
    if not (s <= lat <= n and w <= lon <= e):
        problems.append(f"el centro {entry['center']} queda fuera de la caja")
    regions = pbf_regions(entry)
    if not regions:
        problems.append("sin pbf_region: el extractor no sabe qué PBF leer")
    if shapes is not None and regions:
        unknown = [r for r in regions if r not in shapes]
        if unknown:
            problems.append(f"Geofabrik no tiene la región {', '.join(unknown)}")
        known = [shapes[r] for r in regions if r in shapes]
        if known:
            area = box(w, s, e, n)
            inside = unary_union(known).intersection(area).area / area.area
            if inside < MIN_COVERAGE:
                problems.append(
                    f"solo el {inside:.0%} de la caja cae en {' + '.join(regions)}: "
                    "¿orden lon/lat, un signo perdido o falta el extracto vecino?"
                )
    return problems


def region_shapes(regions: set[str]) -> dict | None:
    """Contornos de esas regiones según el índice de Geofabrik; None si no se pudo bajar."""
    try:
        index = json.loads(ensure_index().read_text(encoding="utf-8"))
    except (requests.RequestException, OSError, ValueError) as e:
        print(f"[aviso] no se pudo leer el índice de Geofabrik ({e}): no reviso las regiones")
        return None
    shapes = {}
    for feature in index["features"]:
        url = feature["properties"].get("urls", {}).get("pbf", "")
        region = url.removeprefix(f"{GEOFABRIK_BASE}/").removesuffix("-latest.osm.pbf")
        if region in regions:
            shapes[region] = shape(feature["geometry"])
    return shapes


def extract(slug: str) -> int:
    """extract-zoning en otro proceso, con la salida en un log. Devuelve su código."""
    log = LOG_DIR / f"{slug}.log"
    print(f"[{slug}] extrayendo, log en {log}", flush=True)
    with log.open("w", encoding="utf-8") as out:
        code = subprocess.run(
            [sys.executable, "-m", "zoning.extract", "--city", slug],
            stdout=out, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        ).returncode
    print(f"[{slug}] {'listo' if code == 0 else f'falló (código {code})'}", flush=True)
    return code


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # cada ciudad pide cientos de teselas
        pass


def take_thumbnails(slugs: list[str], vis_root: Path) -> dict[str, str]:
    """Miniaturas contra un servidor local: Pages todavía no tiene las ciudades nuevas."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(vis_root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        return capture_thumbnails(
            slugs, f"http://127.0.0.1:{server.server_port}", vis_root / "assets" / "thumbnails",
        )
    except SystemExit:  # sin Playwright: capture_thumbnails ya dijo cómo instalarlo
        return {slug: "failed: falta Playwright" for slug in slugs}
    finally:
        server.shutdown()


def published_sizes(repo_root: Path) -> dict[str, int]:
    """Bytes de cada archivo que serviría Pages: lo versionado más lo nuevo de
    visualizer/, menos lo que saca `_config.yml`."""
    skipped = yaml.safe_load((repo_root / "_config.yml").read_text(encoding="utf-8"))["exclude"]
    paths = set()
    for extra in ([], ["--others", "--exclude-standard", "--", "visualizer"]):
        listing = subprocess.run(
            ["git", "ls-files", "-z", *extra], cwd=repo_root, capture_output=True, check=True,
        ).stdout
        paths.update(listing.decode("utf-8").split("\0"))
    sizes = {}
    for path in paths:
        full = repo_root / path
        if path and full.is_file() and not any(fnmatchcase(path, p) for p in skipped):
            sizes[path] = full.stat().st_size
    return sizes


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")  # la consola de Windows usa cp1252

    parser = argparse.ArgumentParser(
        description="Procesa un lote de ciudades de cities.json: revisa las cajas, "
                    "extrae la zonificación, regenera la landing y saca las miniaturas.",
    )
    parser.add_argument("slugs", nargs="+", help="slugs de cities.json, p. ej. tulsa timisoara")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    vis_root = repo_root / "visualizer"
    try:
        cities = load_cities(repo_root / "cities.json")
    except RegistryError as e:
        sys.exit(f"Error: {e}")
    slugs = list(dict.fromkeys(args.slugs))
    unknown = [s for s in slugs if s not in cities]
    if unknown:
        sys.exit(f"Error: no están en cities.json: {', '.join(unknown)}")

    regions = sorted({r for s in slugs for r in pbf_regions(cities[s])})
    shapes = region_shapes(set(regions))
    problems = {s: city_problems(cities[s], shapes) for s in slugs}
    if any(problems.values()):
        for slug, found in problems.items():
            for problem in found:
                print(f"[{slug}] {problem}")
        sys.exit("Corregí cities.json y volvé a correrlo: no se bajó nada.")

    # Todos los PBF antes de extraer: en paralelo, dos extracciones bajaban el mismo a la vez
    for region in regions:
        ensure_pbf(region)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(PARALLEL_EXTRACTIONS) as pool:
        codes = dict(zip(slugs, pool.map(extract, slugs)))
    done = [s for s in slugs if codes[s] == 0]

    # La landing antes que las miniaturas: map.html lee visualizer/cities.json
    landing.main([])
    thumbs = take_thumbnails(done, vis_root) if done else {}

    sizes = published_sizes(repo_root)
    print(f"\n{'Ciudad':<20} {'Polígonos':>10} {'Teselas':>8} {'Publicado':>10}  Miniatura")
    for slug in slugs:
        manifest = load_manifest(vis_root, slug) or {"modules": {}}
        polygons = manifest["modules"].get("zoning", {}).get("features", 0)
        prefix = f"visualizer/cities/{slug}/"
        tiles = sum(1 for p in sizes if p.startswith(f"{prefix}tiles/") and p.endswith(".gz"))
        thumb = f"visualizer/assets/thumbnails/{slug}.png"
        mb = (sum(v for p, v in sizes.items() if p.startswith(prefix)) + sizes.get(thumb, 0)) / 2**20
        state = f"falló la extracción, ver {LOG_DIR / slug}.log" if codes[slug] else thumbs.get(slug, "")
        print(f"{slug:<20} {polygons:>10,} {tiles:>8} {mb:>7.1f} MB  {state}")
    print(f"\nSitio publicado: {sum(sizes.values()) / 2**20:.0f} MB de {PAGES_LIMIT_MB} MB")
    print("Queda a mano: mirar las miniaturas, el CHANGELOG y la tabla de ciudades de los README.")
    if len(done) < len(slugs) or any(v != "ok" for v in thumbs.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
