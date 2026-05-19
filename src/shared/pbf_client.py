"""
pbf_client.py
=============
Cliente de extracción PBF con API compatible con overpass_client.

Lee un .osm.pbf con pyosmium 4.x (`osmium.FileProcessor`), aplica FilterSpec,
y re-emite resultados en forma Overpass-compatible (dict con clave 'elements',
cada elemento con 'type', 'id', 'tags', 'geometry'/'members'/'lat,lon').

Diseñado como drop-in replacement de overpass_client para los extractores
existentes: la única diferencia es que toma FilterSpec en vez de QL string.

Uso:
    from shared.pbf_client import query
    data = query(pbf_path, bbox, filter_spec, label="apartments")
    # data["elements"] es lista con shape Overpass

Conversión a Overpass shape:
- way:      {"type": "way", "id": N, "tags": {...}, "geometry": [{"lat", "lon"}, ...]}
- node:     {"type": "node", "id": N, "tags": {...}, "lat": ..., "lon": ...}
- relation: {"type": "relation", "id": N, "tags": {...},
             "members": [{"role": "outer", "geometry": [{"lat", "lon"}, ...]}]}
"""

from __future__ import annotations

from typing import Any

import osmium


# Module-level WKBFactory — pyosmium recommends reusing one instance.
# Not strictly needed (we iterate node refs directly) but available for future use.
_WKB_FACTORY = osmium.geom.WKBFactory()


def _osmium_tags(osm_obj: Any) -> dict[str, str]:
    """
    Convert a pyosmium TagList to a plain dict of str→str.

    pyosmium 4.x exposes tags as an iterable of (key, value) pairs via
    `obj.tags`. Empty TagList returns empty dict, never None.
    """
    return {tag.k: tag.v for tag in osm_obj.tags}


def _in_bbox(lat: float, lon: float, bbox: tuple[float, float, float, float]) -> bool:
    """Bbox membership check. bbox is (south, west, north, east) inclusive."""
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east


def _node_to_overpass(node: Any) -> dict[str, Any] | None:
    """
    Convert an osmium.osm.Node to Overpass-shape dict.

    Returns None if the node has no valid location.
    """
    if not node.location.valid():
        return None
    return {
        "type": "node",
        "id": node.id,
        "tags": _osmium_tags(node),
        "lat": node.location.lat,
        "lon": node.location.lon,
    }


def _way_to_overpass(way: Any) -> dict[str, Any] | None:
    """
    Convert an osmium.osm.Way to Overpass-shape dict.

    Requires the FileProcessor was built with .with_locations() so that
    way.nodes have resolved coordinates. Returns None if locations are
    unresolved or empty.
    """
    try:
        coords: list[dict[str, float]] = []
        for noderef in way.nodes:
            if not noderef.location.valid():
                return None
            coords.append({"lat": noderef.location.lat, "lon": noderef.location.lon})
    except osmium.InvalidLocationError:
        return None
    if len(coords) < 2:
        return None
    return {
        "type": "way",
        "id": way.id,
        "tags": _osmium_tags(way),
        "geometry": coords,
    }


def _area_to_overpass(area: Any) -> dict[str, Any] | None:
    """
    Convert an osmium.osm.Area to Overpass-shape relation dict.

    Areas come from closed ways or multipolygon relations. We extract the
    outer ring (largest if multiple) and emit it as a single 'outer' member,
    matching how extract.py.coords_from_relation consumes relations.
    """
    try:
        # outer_rings() yields lists of NodeRefs for each outer ring
        outers = list(area.outer_rings())
    except Exception:
        return None
    if not outers:
        return None

    # Pick the largest outer ring by node count (proxy for area)
    largest = max(outers, key=lambda ring: len(list(ring)))
    coords: list[dict[str, float]] = []
    for noderef in largest:
        if not noderef.location.valid():
            return None
        coords.append({"lat": noderef.location.lat, "lon": noderef.location.lon})
    if len(coords) < 3:
        return None

    # Areas in osmium have an orig_id() method that returns the underlying
    # way or relation ID (with sign indicating which). For relations from
    # multipolygons, we want the relation ID; for closed ways, the way ID.
    # area.id is the synthetic area ID; orig_id() is the source object's ID.
    rel_id = area.orig_id() if hasattr(area, "orig_id") else area.id

    return {
        "type": "relation",
        "id": rel_id,
        "tags": _osmium_tags(area),
        "members": [{
            "role": "outer",
            "type": "way",
            "geometry": coords,
        }],
    }


from shapely.geometry import Point as _ShapelyPoint
from shapely.strtree import STRtree


# Aproximación métrica: 1 grado de latitud ≈ 111,000 m. Aceptable para
# distancias pequeñas (<100m) y latitudes no polares.
_DEG_PER_METER = 1.0 / 111000.0


def _element_to_points(el: dict[str, Any]) -> list[_ShapelyPoint]:
    """Convierte un elemento Overpass-shape a lista de Points shapely."""
    if el["type"] == "node":
        return [_ShapelyPoint(el["lon"], el["lat"])]
    if el["type"] == "way":
        return [_ShapelyPoint(pt["lon"], pt["lat"]) for pt in el.get("geometry", [])]
    if el["type"] == "relation":
        pts: list[_ShapelyPoint] = []
        for m in el.get("members", []):
            for pt in m.get("geometry", []):
                pts.append(_ShapelyPoint(pt["lon"], pt["lat"]))
        return pts
    return []


def _apply_spatial_join(
    targets: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    buffer_m: float,
) -> list[dict[str, Any]]:
    """
    Devuelve targets con al menos un punto a buffer_m metros o menos de algún
    punto anchor. Replica el patrón Overpass `(nodes A)->.x; way(around.x:N);`.
    """
    if not anchors or not targets:
        return []

    anchor_points: list[_ShapelyPoint] = []
    for a in anchors:
        anchor_points.extend(_element_to_points(a))
    if not anchor_points:
        return []

    tree = STRtree(anchor_points)
    buffer_deg = buffer_m * _DEG_PER_METER

    kept: list[dict[str, Any]] = []
    for t in targets:
        target_points = _element_to_points(t)
        matched = False
        for tp in target_points:
            candidates_idx = tree.query(tp.buffer(buffer_deg))
            for idx in candidates_idx:
                ap = anchor_points[idx]
                if tp.distance(ap) <= buffer_deg:
                    matched = True
                    break
            if matched:
                break
        if matched:
            kept.append(t)
    return kept
