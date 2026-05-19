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
