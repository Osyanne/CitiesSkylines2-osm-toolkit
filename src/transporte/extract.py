"""
transporte/extract.py — Transit route extractor for CS2 OSM Toolkit
====================================================================
Pipeline:
  1. Query Overpass for route=* relations in city bbox
  2. For each relation: extract member way geometries → concatenate into LineStrings
  3. Classify by tags (LRT / Commuter / BRT / Bus)
  4. Emit visualizer/cities/<slug>/datos_transporte.js

CLI:
  cd src && uv run extract-transporte --city minneapolis
"""
from __future__ import annotations


def extract_way_geoms(relation: dict) -> list[list[list[float]]]:
    """Extract LineString geometries from way members of a relation.

    Each way member is converted to [[lat, lon], ...] form. Node members
    (typically stops/platforms) are skipped. Ways without geometry or with
    empty geometry are skipped.

    Args:
        relation: Overpass JSON relation element.

    Returns:
        List of LineStrings (each is a list of [lat, lon] pairs).
    """
    members = relation.get("members") or []
    out: list[list[list[float]]] = []
    for m in members:
        if m.get("type") != "way":
            continue
        geom = m.get("geometry") or []
        if not geom:
            continue
        out.append([[pt["lat"], pt["lon"]] for pt in geom])
    return out


def concatenate_ways(ways: list[list[list[float]]]) -> list[list[list[float]]]:
    """Concatenate adjacent way LineStrings into continuous segments.

    Two consecutive ways are merged if their endpoints touch (in any direction).
    If they don't touch, a new segment starts. Result is the minimal list of
    continuous LineStrings needed to represent the input.

    Args:
        ways: List of LineStrings (each is a list of [lat, lon] pairs).

    Returns:
        List of merged LineStrings. Empty list if input is empty.
    """
    if not ways:
        return []
    segments: list[list[list[float]]] = [list(ways[0])]
    for w in ways[1:]:
        if not w:
            continue
        current = segments[-1]
        current_end = current[-1]
        w_start = w[0]
        w_end = w[-1]
        if current_end == w_start:
            # tail-to-head: append all but first point of w
            current.extend(w[1:])
        elif current_end == w_end:
            # tail-to-tail: reverse w then append all but first
            reversed_w = list(reversed(w))
            current.extend(reversed_w[1:])
        else:
            # gap — start a new segment
            segments.append(list(w))
    return segments
