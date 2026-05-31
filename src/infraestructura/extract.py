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
