"""CLI entry point — extract-official-zoning."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from official_zoning.mapping import load_mapping
from official_zoning.pipeline import process
from official_zoning.emitter import emit
from official_zoning.sources import SOURCES
from shared.registry import save_manifest_official_source


DEFAULT_CACHE = Path.home() / ".cache" / "cs2-osm-toolkit" / "official_zoning"


def _load_city_meta(slug: str) -> dict:
    """Read cities.json and return the entry for slug."""
    cities_json = Path(__file__).resolve().parent.parent.parent / "cities.json"
    if not cities_json.exists():
        cities_json = Path(__file__).resolve().parents[3] / "cities.json"
    with open(cities_json, encoding="utf-8") as f:
        cities = json.load(f)
    if slug not in cities:
        raise SystemExit(f"City '{slug}' not found in cities.json")
    return cities[slug]


def _resolve_bbox(city_meta: dict, override: list[float] | None) -> list[float]:
    return override if override else city_meta["bbox"]


def _resolve_source_name(city_meta: dict, fallback: str) -> str:
    src = city_meta.get("official_source", {})
    return src.get("source_name") or fallback


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="extract-official-zoning",
        description="Extract official zoning data for a city from its open data portal.",
    )
    parser.add_argument("--city", required=True, help=f"City slug (one of: {sorted(SOURCES)})")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output dir (default: visualizer/cities/<slug>/)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE,
        help="Cache dir for downloaded shapefiles",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("S", "W", "N", "E"),
        default=None,
        help="Override bbox from cities.json (south west north east in WGS84)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-download even if cached",
    )

    args = parser.parse_args()

    if args.city not in SOURCES:
        raise SystemExit(f"Unknown city '{args.city}'. Available: {sorted(SOURCES)}")

    source = SOURCES[args.city]
    mapping_path = Path(__file__).parent / "mappings" / f"{args.city}.yaml"
    if not mapping_path.exists():
        raise SystemExit(f"Mapping YAML missing: {mapping_path}")
    mapping = load_mapping(mapping_path)

    city_meta = _load_city_meta(args.city)
    bbox = _resolve_bbox(city_meta, args.bbox)
    source_name = _resolve_source_name(city_meta, fallback=f"{args.city} (unknown source)")

    print(f"[official_zoning] Downloading {args.city} from {source.DATA_URL[:80]}…")
    cache_path = source.download(args.cache_dir / args.city, force_refresh=args.force_refresh)
    print(f"[official_zoning] Reading {cache_path.name}…")
    gdf = source.read(cache_path)
    print(f"[official_zoning] {len(gdf)} input polygons. Reprojecting + mapping…")
    result = process(gdf, mapping, bbox)
    print(f"[official_zoning] {len(result)} polygons kept after bbox filter + mapping.")

    out_dir = args.out_dir or (Path(__file__).resolve().parents[2] / "visualizer" / "cities" / args.city)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "datos_zonificacion_official.js"
    emit(result, out_path, source_name=source_name)
    print(f"[official_zoning] Wrote {out_path} ({out_path.stat().st_size:,} bytes)")

    # Register the official_zoning module in the per-city manifest
    visualizer_root = Path(__file__).resolve().parents[2] / "visualizer"
    source_url = city_meta.get("official_source", {}).get("url", "")
    save_manifest_official_source(
        visualizer_root,
        args.city,
        out_path,
        source_name=source_name,
        source_url=source_url,
    )
    print(f"[official_zoning] Updated manifest with official_zoning entry for {args.city}.")
