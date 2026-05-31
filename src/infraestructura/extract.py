"""
infraestructura/extract.py -- Infra extractor para CS2 OSM Toolkit
=================================================================
Pipeline:
  1. Query Overpass (build_infraestructura_query) por utilities en el bbox
  2. classify_infra(tags) -> (categoria, subtipo)
  3. infra_geometry(element, subtipo) -> (kind, coords)  [point/polygon/line]
  4. build_infra_feature(...) -> dict
  5. Emit visualizer/cities/<slug>/datos_infraestructura.js

CLI: cd src && uv run extract-infraestructura --city minneapolis
"""
from __future__ import annotations


def _latlon_list(geometry: list) -> list[list[float]]:
    return [[p["lat"], p["lon"]] for p in (geometry or [])]


def _is_closed(coords: list[list[float]]) -> bool:
    return len(coords) >= 4 and coords[0] == coords[-1]


def _longest_member_way(element: dict) -> list[list[float]]:
    """Devuelve las coords del member way mas largo de una relation (o [])."""
    best: list[list[float]] = []
    for m in element.get("members", []):
        if m.get("type") != "way":
            continue
        coords = _latlon_list(m.get("geometry"))
        if len(coords) > len(best):
            best = coords
    return best


def _outer_ring(element: dict) -> list[list[float]]:
    """Outer ring de una relation multipolygon (primer member role=outer con geom),
    fallback al member way mas largo."""
    for m in element.get("members", []):
        if m.get("type") == "way" and m.get("role") == "outer":
            coords = _latlon_list(m.get("geometry"))
            if coords:
                return coords
    return _longest_member_way(element)


def infra_geometry(element: dict, subtype: str) -> tuple[str, list] | None:
    """(kind, coords) o None si no hay geometria usable.

    - node            -> ("point", [lat,lon])
    - way cerrado     -> ("polygon", [[lat,lon],...])
    - way abierto + transmision -> ("line", [[lat,lon],...])
    - way abierto otro -> ("point", [lat,lon] del primer nodo)
    - relation + transmision -> ("line", member way mas largo)
    - relation otro   -> ("polygon", outer ring)
    """
    etype = element.get("type")
    if etype == "node":
        return ("point", [element["lat"], element["lon"]])

    if etype == "way":
        coords = _latlon_list(element.get("geometry"))
        if not coords:
            return None
        if _is_closed(coords):
            return ("polygon", coords)
        if subtype == "transmision":
            return ("line", coords)
        return ("point", coords[0])

    if etype == "relation":
        if subtype == "transmision":
            coords = _longest_member_way(element)
            return ("line", coords) if len(coords) >= 2 else None
        ring = _outer_ring(element)
        return ("polygon", ring) if len(ring) >= 3 else None

    return None


def build_infra_feature(element: dict, category: str, subtype: str) -> dict | None:
    """Convierte un element Overpass + su clasificacion en un feature dict.

    Devuelve None si no hay geometria usable.
    """
    geo = infra_geometry(element, subtype)
    if geo is None:
        return None
    kind, coords = geo

    tags = element.get("tags") or {}
    name = tags.get("name") or ""
    operator = tags.get("operator") or ""
    if not name:
        name = operator or f"{INFRA_LABELS.get(category, category)} sin nombre"

    return {
        "name": name,
        "category": category,
        "subtype": subtype,
        "kind": kind,
        "coords": coords,
        "operator": operator,
        "osm_id": element.get("id"),
    }


# --------------------------------------------------------------------------
# CLI + main pipeline
# --------------------------------------------------------------------------

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from shared.overpass_client import query_with_retry
from shared.registry import (
    load_cities, get_city, CityNotFoundError, RegistryError, save_manifest_entry,
)
from infraestructura.classifiers import classify_infra
from infraestructura.zones import INFRA_LABELS, build_infraestructura_query

CATEGORIES = ("power", "water", "waste", "telecom")


def resolve_city_args(city, bbox, slug, cities_file: Path) -> tuple[str, str]:
    if city is not None:
        cities = load_cities(cities_file)
        entry = get_city(cities, city)
        s, w, n, e = entry["bbox"]
        return (f"{s},{w},{n},{e}", city)
    if bbox is not None:
        if slug is None:
            raise ValueError("If you pass --bbox you must also pass --slug")
        return (bbox, slug)
    raise ValueError("You must pass --city or --bbox+--slug")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract OSM infrastructure -> JS prebuilt")
    p.add_argument("--city", help="City slug from cities.json (e.g. minneapolis)")
    p.add_argument("--bbox", help="Escape hatch: bbox 's,w,n,e' (requires --slug)")
    p.add_argument("--slug", help="Output slug when using --bbox without --city")
    p.add_argument("--cities-file", default=None)
    p.add_argument("--visualizer-root", default=None)
    return p.parse_args(argv)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    cities_file = Path(args.cities_file) if args.cities_file else repo_root / "cities.json"
    vis_root = Path(args.visualizer_root) if args.visualizer_root else repo_root / "visualizer"

    try:
        bbox, slug = resolve_city_args(args.city, args.bbox, args.slug, cities_file)
    except (CityNotFoundError, RegistryError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    out_dir = vis_root / "cities" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "datos_infraestructura.js"

    print("CS2 OSM Toolkit - Infraestructura Extractor")
    print(f"City         : {slug}")
    print(f"Bounding Box : {bbox}")

    query = build_infraestructura_query(bbox)
    print("[1/2] Downloading infrastructure from Overpass...")
    result = query_with_retry(query, "infraestructura")
    elements = result.get("elements", [])
    print(f"      raw elements: {len(elements)}")

    print("[2/2] Classifying + building features...")
    buckets: dict[str, list] = defaultdict(list)
    skipped_class = skipped_geom = 0
    for el in elements:
        if el.get("type") not in ("node", "way", "relation"):
            continue
        hit = classify_infra(el.get("tags") or {})
        if hit is None:
            skipped_class += 1
            continue
        category, subtype = hit
        feat = build_infra_feature(el, category, subtype)
        if feat is None:
            skipped_geom += 1
            continue
        buckets[category].append(feat)

    total = sum(len(v) for v in buckets.values())
    print(f"  {'category':<10}  count")
    for key in CATEGORIES:
        print(f"  {key:<10}  {len(buckets.get(key, [])):>5}")
    print(f"  TOTAL: {total}   skipped(class)={skipped_class} skipped(geom)={skipped_geom}")

    with out_path.open("w", encoding="utf-8") as f:
        f.write("// Auto-generated by infraestructura.extract\n")
        f.write(f"// {slug} - Infraestructura - bbox: {bbox}\n")
        f.write(f"// Total: {total}\n\n")
        for key in CATEGORIES:
            f.write(f"var DATA_INFRA_{key.upper()} = ")
            json.dump(buckets.get(key, []), f, ensure_ascii=False, separators=(",", ":"))
            f.write(";\n")

    print(f"Done. {out_path} - {out_path.stat().st_size/1024:.1f} KB - {total} features")
    save_manifest_entry(visualizer_root=vis_root, slug=slug,
                        module="infraestructura", file_path=out_path, features=total)


if __name__ == "__main__":
    main()
