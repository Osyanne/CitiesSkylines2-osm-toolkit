"""Generador de landing page (visualizer/index.html) desde cities.json + manifests."""
import argparse
import html
import json
from pathlib import Path

from shared.registry import load_cities, load_manifest


MODULE_LABELS = {
    "zoning": "Zoning",
    "vial": "Vial",
    "services": "Servicios",
}

REPO_URL = "https://github.com/Osyanne/CitiesSkylines2-osm-toolkit"
ISSUE_NEW_URL = f"{REPO_URL}/issues/new?template=city-request.yml"


def _format_count(n: int) -> str:
    """Format feature count humanizado: 12345 → '12.3k', 1500000 → '1.5M'."""
    n = max(0, n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def country_to_flag(code: str | None) -> str:
    """ISO 3166-1 alpha-2 code → flag emoji via regional indicator chars.

    Returns empty string for falsy or invalid input (graceful fallback for
    cities without a country_code field).
    """
    if not code or len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in code)


COUNTRY_TO_REGION = {
    # North America
    "USA": "north-america",
    "Canada": "north-america",
    "Mexico": "north-america",
    # Europe
    "Netherlands": "europe",
    "Norway": "europe",
    "Romania": "europe",
    "Germany": "europe",
    "France": "europe",
    "UK": "europe",
    "Spain": "europe",
    "Italy": "europe",
    "Portugal": "europe",
    # South America
    "Brazil": "south-america",
    "Argentina": "south-america",
    "Chile": "south-america",
    "Colombia": "south-america",
    # Asia (placeholder for future)
    "Japan": "asia",
    "China": "asia",
    "South Korea": "asia",
}


def region_counts(cities: dict) -> dict[str, int]:
    """Count cities per region for filter pills. Always includes 'all' key."""
    counts = {"all": len(cities)}
    for entry in cities.values():
        region = COUNTRY_TO_REGION.get(entry["country"], "other")
        counts[region] = counts.get(region, 0) + 1
    return counts


def _read_version_short(default: str = "v3.4") -> str:
    """Reads major.minor from pyproject.toml. Falls back to default on any error.

    Note: pyproject.toml lives at src/pyproject.toml — `parents[1]` from
    `src/shared/landing.py` resolves to `src/`.
    """
    try:
        import tomllib  # Python 3.11+
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        full = data["project"]["version"]  # e.g. "3.4.0"
        parts = full.split(".")
        return f"v{parts[0]}.{parts[1]}"
    except Exception:
        return default


def build_stats(cities: dict, manifests: dict) -> dict:
    """Compute 4 stats for the hero banner."""
    total_features = 0
    for slug, manifest in manifests.items():
        if not manifest:
            continue
        for mod in manifest.get("modules", {}).values():
            total_features += mod.get("features", 0)
    return {
        "cities_count": len(cities),
        "features_total": _format_count(total_features),
        "countries_count": len(set(c["country"] for c in cities.values())),
        "version": _read_version_short(),
    }


def _card_html(slug: str, entry: dict, manifest: dict | None) -> str:
    """Genera el <a class='city-card'> de una ciudad."""
    name = html.escape(entry["display_name"])
    country = html.escape(entry["country"])
    tagline = html.escape(entry["tagline"])

    if manifest is None or not manifest.get("modules"):
        badges_html = '<span class="badge badge-pending">Sin datos</span>'
        total = 0
    else:
        mods = manifest["modules"]
        badges_html = " ".join(
            f'<span class="badge">{html.escape(MODULE_LABELS.get(m, m))}</span>'
            for m in ["zoning", "vial", "services"]
            if m in mods
        )
        total = sum(d.get("features", 0) for d in mods.values())

    return f'''
    <a href="map.html?city={html.escape(slug)}" class="city-card">
      <div class="thumb"
           style="background-image: url('assets/thumbnails/{html.escape(slug)}.png')"></div>
      <div class="city-info">
        <h2>{name}</h2>
        <p class="country">{country}</p>
        <p class="tagline">{tagline}</p>
        <div class="badges">{badges_html}</div>
        <p class="stats">{_format_count(total)} features</p>
      </div>
    </a>'''


def build_landing_html(cities: dict, manifests: dict) -> str:
    """Construye el HTML de la landing completo."""
    cards = "\n".join(
        _card_html(slug, entry, manifests.get(slug))
        for slug, entry in cities.items()
    )

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CS2 OSM Toolkit — Featured Cities</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0d1117; color: #c9d1d9;
      min-height: 100vh;
    }}
    header {{
      padding: 3rem 1rem 2rem; text-align: center;
      border-bottom: 1px solid #30363d;
    }}
    header h1 {{ margin: 0; font-size: 2rem; }}
    header p {{ margin: 0.5rem 0; color: #8b949e; }}
    main {{
      max-width: 1400px; margin: 0 auto; padding: 2rem 1rem;
    }}
    .cities-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 1.5rem;
    }}
    .city-card {{
      display: block; text-decoration: none; color: inherit;
      background: #161b22; border: 1px solid #30363d;
      border-radius: 6px; overflow: hidden;
      transition: transform 0.15s, border-color 0.15s;
    }}
    .city-card:hover {{ transform: translateY(-2px); border-color: #58a6ff; }}
    .thumb {{
      height: 180px;
      background-size: cover; background-position: center;
      background-color: #21262d;
    }}
    .city-info {{ padding: 1rem; }}
    .city-info h2 {{ margin: 0 0 0.25rem; font-size: 1.1rem; }}
    .country {{ margin: 0; color: #8b949e; font-size: 0.85rem; }}
    .tagline {{ margin: 0.5rem 0; font-size: 0.9rem; }}
    .badges {{ display: flex; gap: 0.3rem; flex-wrap: wrap; margin: 0.5rem 0; }}
    .badge {{
      background: #1f6feb; color: white;
      padding: 0.1rem 0.5rem; border-radius: 3px;
      font-size: 0.75rem;
    }}
    .badge-pending {{ background: #6e7681; }}
    .stats {{ margin: 0.5rem 0 0; color: #8b949e; font-size: 0.8rem; }}
    footer {{
      max-width: 1400px; margin: 3rem auto 2rem; padding: 0 1rem;
      text-align: center; color: #8b949e; font-size: 0.9rem;
    }}
    footer a {{ color: #58a6ff; }}
  </style>
</head>
<body>
  <header>
    <h1>🏙 CS2 OSM Toolkit</h1>
    <p>Mapas de zonificación reales para creadores de Cities: Skylines 2</p>
  </header>
  <main>
    <div class="cities-grid">
{cards}
    </div>
  </main>
  <footer>
    <p>
      ¿Tu ciudad no está?
      <a href="{ISSUE_NEW_URL}" target="_blank" rel="noopener">Pedila acá</a>
      ·
      <a href="{REPO_URL}" target="_blank" rel="noopener">Código en GitHub</a>
    </p>
  </footer>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(
        description="Generate landing index.html from cities.json + manifests"
    )
    parser.add_argument(
        "--cities-file", default=None,
        help="Path a cities.json (default: <repo_root>/cities.json)",
    )
    parser.add_argument(
        "--visualizer-root", default=None,
        help="Path a visualizer/ (default: <repo_root>/visualizer)",
    )
    parser.add_argument(
        "--out", default=None,
        help="Path al index.html de salida (default: <visualizer_root>/index.html)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    cities_file = Path(args.cities_file) if args.cities_file else repo_root / "cities.json"
    vis_root = Path(args.visualizer_root) if args.visualizer_root else repo_root / "visualizer"
    out_path = Path(args.out) if args.out else vis_root / "index.html"

    cities = load_cities(cities_file)
    manifests = {slug: load_manifest(vis_root, slug) for slug in cities}

    html_content = build_landing_html(cities, manifests)
    out_path.write_text(html_content, encoding="utf-8")

    # Copiar cities.json a visualizer/ — necesario porque GH Pages sirve
    # solo desde /visualizer (no puede acceder a ../cities.json).
    # El root cities.json sigue siendo source of truth; este es deployment artifact.
    deployed_registry = vis_root / "cities.json"
    deployed_registry.write_text(
        json.dumps(cities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Landing generada: {out_path}")
    print(f"Registro deployado: {deployed_registry}")
    print(f"Cities incluidas: {sorted(cities.keys())}")
