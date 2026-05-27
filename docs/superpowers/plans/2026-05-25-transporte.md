# Transporte Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Transporte (transit) module to the CS2 OSM Toolkit visualizer that renders Minneapolis Metro Transit routes (LRT + Commuter Rail + BRT + Bus) as 4 colored polyline layers, activating the "Transporte" tile that's currently disabled in the HUD.

**Architecture:** Single Overpass query for `relation["route"~"^(light_rail|train|tram|bus)$"]` in the city bbox. Each relation becomes a polyline (or multi-polyline if members have gaps). Classifier maps OSM tags to one of 4 CS2 categories. Output `datos_transporte.js` uses `var DATA_TRANSPORT_<KEY>` so the visualizer's lazy-load hook can read via `window["DATA_TRANSPORT_*"]` — same convention as official_zoning. No new Python dependencies (reuses `shared.overpass_client` + `shared.registry`).

**Tech Stack:** Python 3.11 + uv; existing `requests`, `pyyaml`; existing `shared/overpass_client.py` + `shared/registry.py` + `shared/output_helpers.py`; Leaflet.js for visualizer overlay; vanilla ES2022.

**Spec:** `docs/specs/2026-05-25-transporte-design.md` (commit `a3fcf2f`)

**Branch:** `feat/transporte` (created from `main = 358b1e3`)

**Existing reference pattern:** `src/vial/{extract.py,classifiers.py,zones.py}` — the closest analog (same Overpass-driven pipeline, same output shape).

---

## File structure

```
src/transporte/
├── __init__.py
├── extract.py           # CLI entrypoint + main pipeline (Overpass → classify → emit)
├── classifiers.py       # classify_route(tags) -> "lrt"|"commuter"|"brt"|"bus"|None
└── zones.py             # TRANSPORT_LABELS dict + build_transporte_query(bbox)

tests/transporte/
├── __init__.py
├── test_zones.py        # query builder shape + label constants
├── test_classifiers.py  # 10+ tag dicts cover all 4 categories + edge cases
├── test_geometry.py     # extract_way_geom + concatenate_ways
├── test_features.py     # build_route_feature
└── test_extract_cli.py  # argparse + mocked pipeline end-to-end

visualizer/cities/minneapolis/datos_transporte.js   # generated artifact (Task 11)
```

Plus modifications:
- `src/pyproject.toml` (add `transporte` to wheel packages + add entry-point)
- `visualizer/map.html` (Tasks 8-10)
- `README.md` + `README.es.md` + `METHODOLOGY.md` (Task 12)

---

## Phase 0 — Setup (Task 1)

### Task 1: Create branch + scaffold package skeleton

**Files:**
- Create: `src/transporte/__init__.py`
- Create: `tests/transporte/__init__.py`
- Modify: `src/pyproject.toml` (add `"transporte"` to wheel packages list)

- [ ] **Step 1: Create the feature branch**

```bash
cd "C:/Users/osyanne/Documents/Claude/Projects/Proyecto mineapolis/cs2-minneapolis-zoning"
git checkout main
git pull origin main
git checkout -b feat/transporte
git status
```

Expected: `On branch feat/transporte`, working tree clean.

- [ ] **Step 2: Create directories + empty __init__ files**

```bash
mkdir -p src/transporte
mkdir -p tests/transporte
```

`src/transporte/__init__.py`:
```python
"""Transporte module — extract transit routes from OSM relations."""
```

`tests/transporte/__init__.py`: empty file.

- [ ] **Step 3: Update `src/pyproject.toml`**

Find `[tool.hatch.build.targets.wheel]`. The current `packages` list is:
```toml
packages = ["shared", "zoning", "vial", "services", "official_zoning"]
```

Change to:
```toml
packages = ["shared", "zoning", "vial", "services", "official_zoning", "transporte"]
```

- [ ] **Step 4: Verify import works**

```bash
cd src
uv run python -c "import transporte; print('OK')"
```

Expected: `OK`. No ModuleNotFoundError.

- [ ] **Step 5: Commit**

```bash
git add src/transporte/ tests/transporte/ src/pyproject.toml
git commit -m "feat(transporte): scaffold transporte package + register in wheel"
```

---

## Phase 1 — Foundation (Tasks 2-3)

### Task 2: zones.py — TRANSPORT_LABELS + query builder

**Files:**
- Create: `src/transporte/zones.py`
- Create: `tests/transporte/test_zones.py`

- [ ] **Step 1: Write the failing test `tests/transporte/test_zones.py`**

```python
"""Test the TRANSPORT_LABELS dict and Overpass query builder."""
from transporte.zones import TRANSPORT_LABELS, build_transporte_query


def test_transport_labels_has_four_categories():
    assert set(TRANSPORT_LABELS.keys()) == {"lrt", "commuter", "brt", "bus"}


def test_transport_labels_are_human_readable():
    assert TRANSPORT_LABELS["lrt"] == "LRT"
    assert TRANSPORT_LABELS["commuter"] == "Commuter Rail"
    assert TRANSPORT_LABELS["brt"] == "BRT"
    assert TRANSPORT_LABELS["bus"] == "Bus"


def test_build_query_includes_all_route_types():
    q = build_transporte_query("44.86,-93.38,45.05,-93.17")
    assert "light_rail" in q
    assert "train" in q
    assert "tram" in q
    assert "bus" in q


def test_build_query_includes_bbox():
    q = build_transporte_query("44.86,-93.38,45.05,-93.17")
    assert "44.86,-93.38,45.05,-93.17" in q


def test_build_query_uses_relation_type():
    q = build_transporte_query("44.86,-93.38,45.05,-93.17")
    assert "relation" in q.lower()


def test_build_query_includes_out_body_geom():
    """Overpass `out body geom;` returns relation members with their way geometries."""
    q = build_transporte_query("0,0,1,1")
    assert "out body geom" in q
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_zones.py -v
```

Expected: ImportError — `transporte.zones` does not exist.

- [ ] **Step 3: Implement `src/transporte/zones.py`**

```python
"""
transporte/zones.py — Transit categories + Overpass query builder
=================================================================
4 categorías alineadas a CS2:
  lrt       → light_rail + tram (METRO Blue/Green Line)
  commuter  → train (Northstar)
  brt       → bus + network=METRO (METRO Rapid A/C/D/E/F)
  bus       → bus (resto, ~140 rutas locales Metro Transit)
"""

TRANSPORT_LABELS = {
    "lrt":      "LRT",
    "commuter": "Commuter Rail",
    "brt":      "BRT",
    "bus":      "Bus",
}


def build_transporte_query(bbox: str) -> str:
    """
    Build an Overpass QL query that returns all transit route relations
    intersecting the bbox, with their member ways' geometry.

    Args:
        bbox: "south,west,north,east" decimal degrees string.

    Returns:
        Overpass QL query string.
    """
    return f"""
[out:json][timeout:120];
(
  relation["route"~"^(light_rail|train|tram|bus)$"]({bbox});
);
out body geom;
""".strip()
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_zones.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/transporte/zones.py tests/transporte/test_zones.py
git commit -m "feat(transporte): TRANSPORT_LABELS + Overpass query builder"
```

---

### Task 3: classifiers.py — classify_route function

**Files:**
- Create: `src/transporte/classifiers.py`
- Create: `tests/transporte/test_classifiers.py`

- [ ] **Step 1: Write the failing test `tests/transporte/test_classifiers.py`**

```python
"""Test the route classifier: OSM tags → CS2 category."""
from transporte.classifiers import classify_route


def test_light_rail_classifies_as_lrt():
    """METRO Blue/Green Line use route=light_rail."""
    assert classify_route({"route": "light_rail", "name": "METRO Green Line"}) == "lrt"


def test_tram_classifies_as_lrt():
    """European trams map to LRT in CS2 visualization."""
    assert classify_route({"route": "tram", "name": "Tram 4"}) == "lrt"


def test_train_classifies_as_commuter():
    """Northstar uses route=train."""
    assert classify_route({"route": "train", "name": "Northstar"}) == "commuter"


def test_commuter_rail_alias_classifies_as_commuter():
    """Some OSM data uses commuter_rail as the route value."""
    assert classify_route({"route": "commuter_rail", "name": "X"}) == "commuter"


def test_metro_rapid_classifies_as_brt():
    """METRO Rapid Bus (A/C/D/E/F Line) is BRT, detected via network=METRO."""
    assert classify_route({"route": "bus", "network": "METRO", "name": "METRO A Line"}) == "brt"


def test_metro_rapid_classifies_as_brt_name_only():
    """Fallback: name contains METRO and ' Line' but network may be absent."""
    assert classify_route({"route": "bus", "name": "METRO C Line"}) == "brt"


def test_local_bus_classifies_as_bus():
    """Regular Metro Transit local bus route."""
    assert classify_route({"route": "bus", "name": "Route 5", "network": "Metro Transit"}) == "bus"


def test_bus_without_name_classifies_as_bus():
    """Bus with no name fields still classifies — doesn't match BRT pattern."""
    assert classify_route({"route": "bus"}) == "bus"


def test_unknown_route_returns_none():
    """Routes we don't care about (ferry, hiking, etc.) return None."""
    assert classify_route({"route": "ferry"}) is None


def test_missing_route_returns_none():
    """No route tag at all → None."""
    assert classify_route({"name": "something"}) is None


def test_empty_tags_returns_none():
    assert classify_route({}) is None


def test_route_value_is_case_insensitive():
    """Defensive against weird OSM data — but real OSM uses lowercase."""
    assert classify_route({"route": "Light_Rail"}) == "lrt"
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_classifiers.py -v
```

Expected: ImportError — `transporte.classifiers` does not exist.

- [ ] **Step 3: Implement `src/transporte/classifiers.py`**

```python
"""
transporte/classifiers.py — OSM route tags → CS2 transit category
==================================================================
Mapeo puro de tags route + network + name a una de 4 categorías CS2.

Reglas:
  route=light_rail              → lrt
  route=tram                    → lrt   (CS2 visualization)
  route=train | commuter_rail   → commuter
  route=bus + METRO Rapid       → brt   (detected via network or name pattern)
  route=bus (resto)             → bus
  otros / ausente               → None
"""


def classify_route(tags: dict) -> str | None:
    """Classify an OSM route relation into a CS2 transit category.

    Args:
        tags: OSM tags dict (route, network, name, etc.).

    Returns:
        "lrt" | "commuter" | "brt" | "bus" | None (skip).
    """
    route = (tags.get("route") or "").lower()
    network = tags.get("network") or ""
    name = tags.get("name") or ""

    if route in ("light_rail", "tram"):
        return "lrt"
    if route in ("train", "commuter_rail", "commuter"):
        return "commuter"
    if route == "bus":
        # BRT detection: METRO Rapid Lines have network=METRO or name like "METRO X Line".
        # Regular Metro Transit local buses use network=Metro Transit (note the space).
        if network == "METRO":
            return "brt"
        if "METRO" in name and " Line" in name:
            return "brt"
        return "bus"
    return None
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_classifiers.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/transporte/classifiers.py tests/transporte/test_classifiers.py
git commit -m "feat(transporte): classify_route — OSM tags to CS2 category"
```

---

## Phase 2 — Pipeline (Tasks 4-7)

### Task 4: Geometry helpers — extract member geoms + concatenate adjacent ways

**Files:**
- Create: `src/transporte/extract.py` (skeleton with geometry helpers only — main() comes in Task 6)
- Create: `tests/transporte/test_geometry.py`

- [ ] **Step 1: Write the failing test `tests/transporte/test_geometry.py`**

```python
"""Test the relation-to-polyline geometry helpers."""
from transporte.extract import extract_way_geoms, concatenate_ways


def test_extract_way_geoms_filters_to_way_members():
    """A relation may have node members (stops) — we want only ways with geometry."""
    relation = {
        "type": "relation",
        "members": [
            {"type": "way", "ref": 1, "geometry": [{"lat": 1.0, "lon": 1.0}, {"lat": 2.0, "lon": 2.0}]},
            {"type": "node", "ref": 99, "lat": 1.5, "lon": 1.5},  # stop, skip
            {"type": "way", "ref": 2, "geometry": [{"lat": 2.0, "lon": 2.0}, {"lat": 3.0, "lon": 3.0}]},
        ],
    }
    result = extract_way_geoms(relation)
    assert len(result) == 2
    assert result[0] == [[1.0, 1.0], [2.0, 2.0]]
    assert result[1] == [[2.0, 2.0], [3.0, 3.0]]


def test_extract_way_geoms_skips_empty_geometry():
    """Member ways without geometry (rare but possible) are skipped."""
    relation = {
        "type": "relation",
        "members": [
            {"type": "way", "ref": 1, "geometry": [{"lat": 1.0, "lon": 1.0}, {"lat": 2.0, "lon": 2.0}]},
            {"type": "way", "ref": 2},  # no geometry
            {"type": "way", "ref": 3, "geometry": []},  # empty
        ],
    }
    assert len(extract_way_geoms(relation)) == 1


def test_extract_way_geoms_empty_relation():
    """A relation with no members returns empty list."""
    assert extract_way_geoms({"type": "relation", "members": []}) == []
    assert extract_way_geoms({"type": "relation"}) == []


def test_concatenate_ways_continuous_single_segment():
    """Two adjacent ways (way1.end == way2.start) merge into one LineString."""
    way1 = [[1.0, 1.0], [2.0, 2.0]]
    way2 = [[2.0, 2.0], [3.0, 3.0]]
    result = concatenate_ways([way1, way2])
    assert len(result) == 1
    assert result[0] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_concatenate_ways_reversed_member():
    """way2 reversed (way2.end == way1.end) — reverse it then concat."""
    way1 = [[1.0, 1.0], [2.0, 2.0]]
    way2 = [[3.0, 3.0], [2.0, 2.0]]  # reversed
    result = concatenate_ways([way1, way2])
    assert len(result) == 1
    assert result[0] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_concatenate_ways_disjoint_emits_separate_segments():
    """Two ways with no shared endpoint stay as separate LineStrings."""
    way1 = [[1.0, 1.0], [2.0, 2.0]]
    way2 = [[5.0, 5.0], [6.0, 6.0]]
    result = concatenate_ways([way1, way2])
    assert len(result) == 2
    assert result[0] == way1
    assert result[1] == way2


def test_concatenate_ways_single():
    assert concatenate_ways([[[1.0, 1.0], [2.0, 2.0]]]) == [[[1.0, 1.0], [2.0, 2.0]]]


def test_concatenate_ways_empty():
    assert concatenate_ways([]) == []
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_geometry.py -v
```

Expected: ImportError — `transporte.extract` does not exist (or `extract_way_geoms`/`concatenate_ways` not defined).

- [ ] **Step 3: Implement geometry helpers in `src/transporte/extract.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_geometry.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/transporte/extract.py tests/transporte/test_geometry.py
git commit -m "feat(transporte): geometry helpers — extract + concatenate relation members"
```

---

### Task 5: build_route_feature — relation → feature dict

**Files:**
- Modify: `src/transporte/extract.py` (add `build_route_feature` function)
- Create: `tests/transporte/test_features.py`

- [ ] **Step 1: Write the failing test `tests/transporte/test_features.py`**

```python
"""Test the build_route_feature converter (relation element → feature dict)."""
from transporte.extract import build_route_feature


def _make_relation(tags: dict, member_ways: list[list[list[float]]]) -> dict:
    """Helper: build a fake Overpass relation element."""
    return {
        "type": "relation",
        "id": 12345,
        "tags": tags,
        "members": [
            {"type": "way", "ref": i, "geometry": [{"lat": p[0], "lon": p[1]} for p in w]}
            for i, w in enumerate(member_ways)
        ],
    }


def test_build_route_feature_lrt_green_line():
    rel = _make_relation(
        {"route": "light_rail", "name": "METRO Green Line", "ref": "Green", "operator": "Metro Transit"},
        [[[1.0, 1.0], [2.0, 2.0]], [[2.0, 2.0], [3.0, 3.0]]],
    )
    feat = build_route_feature(rel, cs2_key="lrt")
    assert feat["name"] == "METRO Green Line"
    assert feat["ref"] == "Green"
    assert feat["operator"] == "Metro Transit"
    assert feat["osm_id"] == 12345
    # Coords concatenated (way1 end == way2 start)
    assert feat["coords"] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_build_route_feature_multi_segment_when_gap():
    """When member ways don't connect, feature has coords as MultiLineString.
    Implementation choice: emit a single coords field of the LONGEST segment,
    and skip the shorter disjoint segments (a relation that doesn't form one
    continuous line is unusual; this avoids emitting multiple records per route
    while preserving the main geometry)."""
    rel = _make_relation(
        {"route": "bus", "name": "Route 5"},
        [[[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]],   # 3 points
         [[10.0, 10.0], [11.0, 11.0]]],          # 2 points, disjoint
    )
    feat = build_route_feature(rel, cs2_key="bus")
    # Picks the longest segment
    assert feat["coords"] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_build_route_feature_missing_name_falls_back_to_ref():
    rel = _make_relation(
        {"route": "bus", "ref": "5"},  # no name
        [[[1.0, 1.0], [2.0, 2.0]]],
    )
    feat = build_route_feature(rel, cs2_key="bus")
    assert feat["name"] == "Route 5"


def test_build_route_feature_no_name_no_ref_uses_unknown():
    rel = _make_relation(
        {"route": "bus"},
        [[[1.0, 1.0], [2.0, 2.0]]],
    )
    feat = build_route_feature(rel, cs2_key="bus")
    assert feat["name"] == "Unknown route"


def test_build_route_feature_no_geometry_returns_none():
    """If the relation has no member ways with geometry, return None."""
    rel = {"type": "relation", "id": 1, "tags": {"route": "bus"}, "members": []}
    assert build_route_feature(rel, cs2_key="bus") is None


def test_build_route_feature_truncates_coords_to_5_decimals():
    rel = _make_relation(
        {"route": "light_rail", "name": "X"},
        [[[44.9876543, -93.1234567], [44.9876544, -93.1234568]]],
    )
    feat = build_route_feature(rel, cs2_key="lrt")
    # 5 decimal places (~1m precision)
    assert feat["coords"][0] == [44.98765, -93.12346]
    assert feat["coords"][1] == [44.98765, -93.12346]
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_features.py -v
```

Expected: ImportError — `build_route_feature` not defined.

- [ ] **Step 3: Add `build_route_feature` to `src/transporte/extract.py`**

Append to existing `src/transporte/extract.py`:

```python
COORD_PRECISION = 5  # 5 decimals ≈ 1.1m at the equator


def _round_coords(coords: list[list[float]]) -> list[list[float]]:
    return [[round(lat, COORD_PRECISION), round(lon, COORD_PRECISION)] for lat, lon in coords]


def build_route_feature(relation: dict, cs2_key: str) -> dict | None:
    """Convert an Overpass relation element to a feature dict.

    Args:
        relation: Overpass JSON relation element.
        cs2_key: CS2 category from classify_route().

    Returns:
        dict with keys: name, ref, coords, operator, osm_id — or None if no
        usable geometry (no member ways with coords). If the relation has
        multiple disjoint segments, only the longest one is kept in coords.
    """
    way_geoms = extract_way_geoms(relation)
    if not way_geoms:
        return None
    segments = concatenate_ways(way_geoms)
    if not segments:
        return None
    # Pick the longest continuous segment
    longest = max(segments, key=len)
    if len(longest) < 2:
        return None

    tags = relation.get("tags") or {}
    name = tags.get("name") or ""
    ref = tags.get("ref") or ""
    if not name:
        name = f"Route {ref}" if ref else "Unknown route"

    return {
        "name": name,
        "ref": ref,
        "coords": _round_coords(longest),
        "operator": tags.get("operator") or "",
        "osm_id": relation.get("id"),
    }
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_features.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/transporte/extract.py tests/transporte/test_features.py
git commit -m "feat(transporte): build_route_feature — relation to feature dict with longest-segment selection"
```

---

### Task 6: extract.py main pipeline — CLI + Overpass + emit

**Files:**
- Modify: `src/transporte/extract.py` (add parse_args, resolve_city_args, main)
- Create: `tests/transporte/test_extract_cli.py`

- [ ] **Step 1: Write the failing test `tests/transporte/test_extract_cli.py`**

```python
"""Test the CLI entrypoint (mocked Overpass, no network)."""
import sys
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from transporte.extract import main, parse_args


def test_parse_args_requires_city_or_bbox():
    """Without --city or --bbox, parsing succeeds (no required arg) but main exits."""
    # parse_args allows both to be None; main() validates.
    args = parse_args([])
    assert args.city is None
    assert args.bbox is None


def test_parse_args_accepts_city_slug():
    args = parse_args(["--city", "minneapolis"])
    assert args.city == "minneapolis"


def test_parse_args_accepts_bbox_and_slug():
    args = parse_args(["--bbox", "44,-93,45,-92", "--slug", "test"])
    assert args.bbox == "44,-93,45,-92"
    assert args.slug == "test"


def test_main_exits_when_no_city_or_bbox(capsys):
    with patch.object(sys, "argv", ["extract-transporte"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code != 0


def test_main_writes_js_file_when_pipeline_succeeds(tmp_path, monkeypatch):
    """Full pipeline with mocked Overpass: writes datos_transporte.js + updates manifest."""
    # Mock Overpass response: 2 relations (1 LRT, 1 bus)
    fake_overpass = {
        "elements": [
            {
                "type": "relation",
                "id": 100,
                "tags": {"route": "light_rail", "name": "METRO Green Line", "ref": "Green"},
                "members": [
                    {"type": "way", "ref": 1, "geometry": [{"lat": 44.97, "lon": -93.27}, {"lat": 44.98, "lon": -93.26}]},
                ],
            },
            {
                "type": "relation",
                "id": 200,
                "tags": {"route": "bus", "name": "Route 5"},
                "members": [
                    {"type": "way", "ref": 2, "geometry": [{"lat": 44.96, "lon": -93.25}, {"lat": 44.95, "lon": -93.24}]},
                ],
            },
        ]
    }
    # Mock cities.json with minneapolis bbox
    cities_data = {
        "minneapolis": {
            "display_name": "Minneapolis, MN",
            "bbox": [44.86, -93.38, 45.05, -93.17],
        }
    }
    cities_file = tmp_path / "cities.json"
    cities_file.write_text(json.dumps(cities_data), encoding="utf-8")
    vis_root = tmp_path / "visualizer"
    vis_root.mkdir()

    with patch("transporte.extract.query_with_retry", return_value=fake_overpass):
        with patch.object(sys, "argv", [
            "extract-transporte",
            "--city", "minneapolis",
            "--cities-file", str(cities_file),
            "--visualizer-root", str(vis_root),
        ]):
            main()

    out_path = vis_root / "cities" / "minneapolis" / "datos_transporte.js"
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    # Verify `var` declarations (not const — official_zoning lesson)
    assert "var DATA_TRANSPORT_LRT" in content
    assert "var DATA_TRANSPORT_BUS" in content
    assert "var DATA_TRANSPORT_COMMUTER" in content
    assert "var DATA_TRANSPORT_BRT" in content
    # Verify content
    assert "METRO Green Line" in content
    assert "Route 5" in content
    # Verify manifest entry
    manifest_path = vis_root / "cities" / "minneapolis" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "transporte" in manifest["modules"]
    assert manifest["modules"]["transporte"]["features"] == 2
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_extract_cli.py -v
```

Expected: ImportError for `parse_args` or `main` — not yet defined.

- [ ] **Step 3: Add CLI + main pipeline to `src/transporte/extract.py`**

Append to existing `src/transporte/extract.py`:

```python
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from shared.overpass_client import query_with_retry
from shared.registry import (
    load_cities,
    get_city,
    CityNotFoundError,
    RegistryError,
    save_manifest_entry,
)
from transporte.classifiers import classify_route
from transporte.zones import TRANSPORT_LABELS, build_transporte_query


def resolve_city_args(
    city: str | None,
    bbox: str | None,
    slug: str | None,
    cities_file: Path,
) -> tuple[str, str]:
    """Resolve --city or --bbox+--slug to (bbox_str, slug)."""
    if city is not None:
        if bbox is not None:
            print(
                f"[WARNING] Ignoring --bbox '{bbox}' because --city='{city}' takes priority.",
                file=sys.stderr,
            )
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
    parser = argparse.ArgumentParser(description="Extract OSM transit routes → JS prebuilt")
    parser.add_argument("--city", help="City slug from cities.json (e.g. minneapolis)")
    parser.add_argument("--bbox", help="Escape hatch: bbox 's,w,n,e' (requires --slug)")
    parser.add_argument("--slug", help="Output slug when using --bbox without --city")
    parser.add_argument("--cities-file", default=None,
                        help="Path to cities.json (default: <repo_root>/cities.json)")
    parser.add_argument("--visualizer-root", default=None,
                        help="Path to visualizer/ (default: <repo_root>/visualizer)")
    return parser.parse_args(argv)


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
    out_path = out_dir / "datos_transporte.js"

    print(f"CS2 OSM Toolkit — Transporte Extractor")
    print(f"City         : {slug}")
    print(f"Bounding Box : {bbox}")
    print(f"Output       : {out_path}\n")

    query = build_transporte_query(bbox)
    print("[1/2] Downloading transit relations from Overpass…")
    result = query_with_retry(query, "transporte")
    elements = result.get("elements", [])
    print(f"      raw relations: {len(elements)}")

    print("\n[2/2] Classifying + building features…")
    buckets: dict[str, list] = defaultdict(list)
    skipped_class = 0
    skipped_geom = 0

    for el in elements:
        if el.get("type") != "relation":
            continue
        cs2_key = classify_route(el.get("tags") or {})
        if cs2_key is None:
            skipped_class += 1
            continue
        feat = build_route_feature(el, cs2_key)
        if feat is None:
            skipped_geom += 1
            continue
        buckets[cs2_key].append(feat)

    total = sum(len(v) for v in buckets.values())

    print()
    print(f"  {'category':<10}  count")
    print(f"  {'-'*10}  {'-'*5}")
    for key in TRANSPORT_LABELS:
        n = len(buckets.get(key, []))
        print(f"  {key:<10}  {n:>5}")
    print(f"  {'-'*10}  {'-'*5}")
    print(f"  {'TOTAL':<10}  {total:>5}")
    print(f"\n  skipped (no classifier): {skipped_class}")
    print(f"  skipped (no geometry):   {skipped_geom}")

    # Emit datos_transporte.js — separate `var` declarations per category
    # so the visualizer's lazy-load hook can access via window["DATA_TRANSPORT_*"].
    ts = datetime.now(timezone.utc).isoformat()
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"// Auto-generated by transporte.extract — {ts}\n")
        f.write(f"// {slug} — Transporte — bbox: {bbox}\n")
        f.write(f"// Source: OpenStreetMap (Overpass query route=*)\n")
        f.write(f"// Total routes: {total}\n\n")
        for key in TRANSPORT_LABELS:
            features = buckets.get(key, [])
            var_name = f"DATA_TRANSPORT_{key.upper()}"
            f.write(f"var {var_name} = ")
            json.dump(features, f, ensure_ascii=False, separators=(",", ":"))
            f.write(";\n")

    size_kb = out_path.stat().st_size / 1024
    print(f"\nDone. {out_path} — {size_kb:.1f} KB — {total} features")

    save_manifest_entry(
        visualizer_root=vis_root,
        slug=slug,
        module="transporte",
        file_path=out_path,
        features=total,
    )
    print(f"Manifest      : {vis_root / 'cities' / slug / 'manifest.json'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd src
uv run python -m pytest ../tests/transporte/test_extract_cli.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run the full transporte test suite to confirm no regressions**

```bash
cd src
uv run python -m pytest ../tests/transporte/ -v
```

Expected: ~31 tests pass (6 zones + 12 classifiers + 8 geometry + 6 features + 5 cli — minus any I miscounted, but all green).

- [ ] **Step 6: Commit**

```bash
git add src/transporte/extract.py tests/transporte/test_extract_cli.py
git commit -m "feat(transporte): CLI main pipeline — Overpass query, classify, emit JS"
```

---

### Task 7: pyproject.toml — register entry point

**Files:**
- Modify: `src/pyproject.toml`

- [ ] **Step 1: Update `src/pyproject.toml`**

Find `[project.scripts]`. Add a new line:

```toml
extract-transporte = "transporte.extract:main"
```

The full block now looks like:
```toml
[project.scripts]
extract-zoning = "zoning.extract:main"
extract-vial   = "vial.extract:main"
extract-services = "services.extract:main"
extract-google-buildings = "zoning.extract_google_buildings:main"
extract-official-zoning = "official_zoning.extract:main"
extract-transporte = "transporte.extract:main"
generate-landing = "shared.landing:main"
generate-thumbnails = "shared.thumbnails:main"
```

- [ ] **Step 2: Sync the venv**

```bash
cd src
uv sync
```

Expected: no errors. May report "no changes" if uv.lock doesn't need updating (entry points don't affect deps).

- [ ] **Step 3: Verify the CLI is callable**

```bash
cd src
uv run extract-transporte --help
```

Expected: argparse help text listing `--city`, `--bbox`, `--slug`, `--cities-file`, `--visualizer-root`.

- [ ] **Step 4: Commit**

```bash
git add src/pyproject.toml
git commit -m "feat(transporte): register extract-transporte entry point"
```

---

## Phase 3 — Visualizer integration (Tasks 8-10)

### Task 8: Activate "Transporte" tile in the HUD

**Files:**
- Modify: `visualizer/map.html` (MODULE_META.transporte block + injectPill call)

**Context:** The current `map.html` has `MODULE_META.transporte` configured with the bus icon SVG but with `label: "Transporte (próximamente)"`. The pill is injected via `injectPill("transporte", false)` which marks it disabled and adds a lock SVG overlay. We need to detect when the manifest declares `transporte` and pass `true` to `injectPill` (which removes disabled + lock and makes it interactive).

- [ ] **Step 1: Locate the relevant code**

```bash
grep -n "transporte" visualizer/map.html | head -20
```

You should see lines referencing `MODULE_META.transporte`, `injectPill("transporte", false)`, and the SVG bus icon. Note their line numbers.

- [ ] **Step 2: Update MODULE_META.transporte label**

Find:
```js
transporte: {
  label: "Transporte (próximamente)",
  cat: "var(--cat-transport)",
  svg: ...
},
```

Change `label` to `"Transporte"` (drop the "próximamente").

- [ ] **Step 3: Make the pill injection conditional on manifest**

Find where `injectPill("transporte", false)` is called. Replace with:

```js
const hasTransporte = !!(CITY_MANIFEST.modules?.transporte) && typeof DATA_TRANSPORT_LRT !== "undefined";
injectPill("transporte", hasTransporte);
```

This way: when `datos_transporte.js` is present and declared in the manifest, the pill is interactive. Otherwise it stays disabled (próximamente) for cities without transport data.

Note: `DATA_TRANSPORT_LRT` is one of the four globals; if it's `undefined`, the script didn't load yet. We use it as a sentinel — same pattern as `hasZoning`/`hasVial`/`hasServices` further up.

**Important:** `DATA_TRANSPORT_LRT` may not be available yet when `injectPill` is called (it's lazy-loaded after `loadAll()`). In that case the pill is initially disabled. Once `window.transporteLoaded()` fires (Task 9), it will call `syncTransporteAvailability()` to flip the pill to interactive.

Add this helper after `injectPill` definitions:

```js
function syncTransporteAvailability() {
  const pill = document.querySelector('.pill[data-module="transporte"]');
  if (!pill) return;
  if (typeof DATA_TRANSPORT_LRT !== "undefined") {
    pill.classList.remove("disabled");
    // Remove lock SVG
    const lock = pill.querySelector(".pill-lock");
    if (lock) lock.remove();
    pill.title = MODULE_META.transporte.label;
  }
}
```

This will be called from the `transporteLoaded` hook in Task 9.

- [ ] **Step 4: Verify map.html parses (syntactic)**

```bash
cd visualizer
python -c "open('map.html', encoding='utf-8').read(); print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add visualizer/map.html
git commit -m "feat(visualizer): conditional transporte tile activation based on manifest"
```

---

### Task 9: Lazy load + layer groups + transporteLoaded hook

**Files:**
- Modify: `visualizer/map.html` (moduleToFile + lazy load split + parallel groups + hook)

**Context:** The bootstrap already supports lazy loading of `official_zoning` via `secondaryModules` filter. We extend the same machinery to `transporte`.

- [ ] **Step 1: Add transporte to moduleToFile**

Find:
```js
const moduleToFile = {
  zoning:             "datos_zonificacion.js",
  vial:               "datos_vial.js",
  services:           "datos_servicios.js",
  external_buildings: "datos_external_buildings.js",
  official_zoning:    "datos_zonificacion_official.js",
};
```

Change to:
```js
const moduleToFile = {
  zoning:             "datos_zonificacion.js",
  vial:               "datos_vial.js",
  services:           "datos_servicios.js",
  external_buildings: "datos_external_buildings.js",
  official_zoning:    "datos_zonificacion_official.js",
  transporte:         "datos_transporte.js",
};
```

- [ ] **Step 2: Add transporte to secondaryModules**

Find the lazy-load logic:
```js
const primaryModules = modules.filter(m => m !== "official_zoning");
const secondaryModules = modules.filter(m => m === "official_zoning");
```

Change to:
```js
const SECONDARY = new Set(["official_zoning", "transporte"]);
const primaryModules = modules.filter(m => !SECONDARY.has(m));
const secondaryModules = modules.filter(m => SECONDARY.has(m));
```

Update the per-module lazy-load callback to dispatch to the right hook:
```js
for (const m of secondaryModules) {
  loadModule(m).then(() => {
    if (m === "official_zoning" && typeof window.officialZoningLoaded === "function") {
      window.officialZoningLoaded();
    }
    if (m === "transporte" && typeof window.transporteLoaded === "function") {
      window.transporteLoaded();
    }
  }).catch(err => {
    console.warn(`[${m}] Failed to load:`, err);
  });
}
```

- [ ] **Step 3: Inside renderMap(), declare transporte layer groups**

Find where `groupsOfficial` is declared (`const groupsOfficial = Object.fromEntries(...)`). Right after it, add:

```js
// Parallel layer groups for transporte — lazy-populated by window.transporteLoaded()
const transporteGroups = {
  lrt:      L.layerGroup().addTo(map),
  commuter: L.layerGroup().addTo(map),
  brt:      L.layerGroup().addTo(map),
  bus:      L.layerGroup().addTo(map),
};

const TRANSPORT_STYLE = {
  lrt:      { color: "#0084c8", weight: 3.5, opacity: 0.9  }, // Mpls LRT blue
  commuter: { color: "#7d2d3e", weight: 4.0, opacity: 0.9  }, // Northstar maroon
  brt:      { color: "#f4a261", weight: 2.5, opacity: 0.85 }, // METRO Rapid orange
  bus:      { color: "#7a93a8", weight: 1.0, opacity: 0.55 }, // muted gray-blue
};

const TRANSPORT_LABELS = {
  lrt:      "LRT",
  commuter: "Commuter Rail",
  brt:      "BRT",
  bus:      "Bus",
};
```

- [ ] **Step 4: Define window.transporteLoaded hook**

In the same scope as `window.officialZoningLoaded` (inside `renderMap()`), add:

```js
window.transporteLoaded = function () {
  let total = 0;
  for (const cat of Object.keys(transporteGroups)) {
    const varName = `DATA_TRANSPORT_${cat.toUpperCase()}`;
    const data = window[varName];
    if (!Array.isArray(data)) continue;

    const style = TRANSPORT_STYLE[cat];
    for (const route of data) {
      if (!route.coords || route.coords.length < 2) continue;
      const popup = `<b>${escHtml(route.name || "Unknown route")}</b><br>` +
                    `<span style="color:#888;font-size:11px">${escHtml(TRANSPORT_LABELS[cat])}` +
                    (route.operator ? ` · ${escHtml(route.operator)}` : "") + `</span>`;
      const polyline = L.polyline(route.coords, style).bindPopup(popup);
      transporteGroups[cat].addLayer(polyline);
      total++;
    }
  }
  window._cs2TransporteCount = total;
  console.log(`[transporte] Loaded ${total} routes across ${Object.keys(transporteGroups).length} layer groups.`);

  // Patch MODULES so existing toggle infrastructure (wireUpModuleControls +
  // toggleModule + applyModuleState) handles transporte clicks. This avoids
  // attaching a duplicate event listener — the click handler already wired
  // by wireUpModuleControls early-returns when !MODULES[key].enabled, so
  // before this point clicks were silently ignored (correct).
  MODULES.transporte = {
    label: "Transporte",
    enabled: true,
    layerGroupsRef: () => Object.values(transporteGroups),
  };
  moduleStates.transporte = "on";

  // Activate the tile UI (remove disabled state + lock SVG)
  if (typeof syncTransporteAvailability === "function") {
    syncTransporteAvailability();
  }
  // Sync the on/off class so the pill visually reflects "on"
  if (typeof syncUI === "function") {
    syncUI();
  }
};
```

`escHtml` is already defined elsewhere in `map.html` (used by zoning/vial/services popups). Reuse it.

- [ ] **Step 5: Verify map.html syntax**

```bash
cd visualizer
python -c "open('map.html', encoding='utf-8').read(); print('OK')"
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add visualizer/map.html
git commit -m "feat(visualizer): transporte lazy-load + layer groups + render hook"
```

---

### Task 10: Legend section for Transporte with counts

**Files:**
- Modify: `visualizer/map.html` (legend.onAdd HTML block + count update)

- [ ] **Step 1: Add a Transporte section to the legend**

Inside `legend.onAdd`, find where the existing sections are appended (`if (hasZoning)`, `if (hasVial)`, `if (hasServices)` — search for one of those). After the Servicios block, add:

```js
const hasTransporte = !!(CITY_MANIFEST.modules?.transporte);
if (hasTransporte) {
  html += `<h4 style="margin-top:14px"><span class="master-toggle on" data-module="transporte" title="Toggle Transporte"></span>Transporte</h4>`;
  for (const key of Object.keys(TRANSPORT_STYLE)) {
    const style = TRANSPORT_STYLE[key];
    html += `<div class="li">
      <div class="ldot" style="background:${style.color};width:14px;height:2px;border-radius:1px"></div>
      <span class="lname">${escHtml(TRANSPORT_LABELS[key])}</span>
      <span class="lcount zero" id="tcount-${key}">0</span>
    </div>`;
  }
}
```

- [ ] **Step 2: Update counts when transporte loads**

Inside `window.transporteLoaded()` (added in Task 9), after the `for (const cat of …)` loop, add count update:

```js
// Update legend counts
for (const cat of Object.keys(transporteGroups)) {
  const el = document.getElementById(`tcount-${cat}`);
  if (!el) continue;
  const count = transporteGroups[cat].getLayers().length;
  el.textContent = count.toLocaleString();
  el.classList.toggle("zero", count === 0);
}
```

- [ ] **Step 3: Verify map.html syntax**

```bash
cd visualizer
python -c "open('map.html', encoding='utf-8').read(); print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add visualizer/map.html
git commit -m "feat(visualizer): transporte section in legend with per-category counts"
```

---

## Phase 4 — Real data + docs (Tasks 11-12)

### Task 11: Generate Mpls transit data + verify in browser

**Files:**
- Create: `visualizer/cities/minneapolis/datos_transporte.js` (generated artifact)
- Modify: `visualizer/cities/minneapolis/manifest.json` (gets the transporte entry)

- [ ] **Step 1: Run the extraction**

```bash
cd src
uv run extract-transporte --city minneapolis
```

Expected output (numbers approximate):
```
CS2 OSM Toolkit — Transporte Extractor
City         : minneapolis
Bounding Box : 44.86,-93.38,45.05,-93.17
Output       : .../visualizer/cities/minneapolis/datos_transporte.js

[1/2] Downloading transit relations from Overpass…
      raw relations: 145

[2/2] Classifying + building features…

  category    count
  ----------  -----
  lrt             4   (Blue + Green + Green Extension + 1 alt branch)
  commuter        1   (Northstar)
  brt             5   (METRO A/C/D/E/F Line)
  bus           135   (local Metro Transit routes)
  ----------  -----
  TOTAL         145

  skipped (no classifier): 0
  skipped (no geometry):   0

Done. .../datos_transporte.js — ~60 KB — 145 features
Manifest      : .../manifest.json
```

If Overpass returns substantially fewer or weird numbers, inspect with:
```bash
cd src
uv run python -c "
from shared.overpass_client import query_with_retry
from transporte.zones import build_transporte_query
q = build_transporte_query('44.86,-93.38,45.05,-93.17')
r = query_with_retry(q, 'transporte')
print('relations:', len(r['elements']))
from collections import Counter
print(Counter(e['tags'].get('route', '?') for e in r['elements']))
"
```

- [ ] **Step 2: Inspect the manifest**

```bash
cat visualizer/cities/minneapolis/manifest.json
```

Verify `transporte` module is present with `features` populated:
```json
{
  "modules": {
    "zoning": { "hash": "…", "features": 184723 },
    "vial":   { "hash": "…", "features": 108859 },
    "services": { "hash": "…", "features": 2272 },
    "official_zoning": { "hash": "…", "source_name": "…", "source_url": "…" },
    "transporte": { "hash": "…", "features": 145 }
  },
  …
}
```

- [ ] **Step 3: Browser smoke test**

Start the server (or reuse cs2-mockups on :5180 if it's already running):
```bash
cd visualizer
python -m http.server 8767
```

Open: `http://localhost:8767/map.html?city=minneapolis`

Verify in DevTools console:
```js
window._cs2TransporteCount   // should be ~145
Object.keys(window).filter(k => k.startsWith("DATA_TRANSPORT_"))
// ["DATA_TRANSPORT_LRT", "DATA_TRANSPORT_COMMUTER", "DATA_TRANSPORT_BRT", "DATA_TRANSPORT_BUS"]
```

Visually:
- The "Transporte" tile in the top bar is **no longer disabled** (no lock, colored orange).
- Click the tile → all 4 transit layer groups toggle off (you should see the polylines disappear).
- Click again → they come back.
- LRT (Mpls Blue + Green Line) should appear as bright blue lines (`#0084c8`).
- Northstar appears as a maroon line extending northwest.
- METRO Rapid (orange) along major corridors.
- Bus routes (faint gray-blue) covering most of the city.
- Legend shows "Transporte" section with 4 counts.
- Click any polyline → popup shows route name + category + operator.

- [ ] **Step 4: Commit the generated artifact**

```bash
git add visualizer/cities/minneapolis/datos_transporte.js visualizer/cities/minneapolis/manifest.json
git commit -m "feat(transporte): generate Minneapolis transit data — 4 categories"
```

If `--out-dir` was respected, only `datos_transporte.js` may show as new and the manifest as modified. Either is fine.

---

### Task 12: README + METHODOLOGY + final test sweep

**Files:**
- Modify: `README.md` (add Transporte section)
- Modify: `README.es.md` (Spanish version)
- Modify: `METHODOLOGY.md` (section 16)

- [ ] **Step 1: Run the full project test suite (offline)**

```bash
cd src
uv run python -m pytest ../tests -m "not network" 2>&1 | tail -5
```

Expected: ~380 passed (was ~360 pre-feature; +37 from transporte tests minus possible test-isolation cleanup).

If any pre-existing test breaks, investigate before continuing.

- [ ] **Step 2: Update `README.md`**

Find the "Official zoning overlay" section (added in the previous sprint). After it, add:

```markdown
## Transit overlay (Minneapolis)

The Mpls visualizer renders the full Metro Transit network as a 4-category overlay:

| Category | Source | Routes |
|---|---|---|
| LRT | OSM `route=light_rail` | METRO Blue Line, Green Line |
| Commuter Rail | OSM `route=train` | Northstar |
| BRT | OSM `route=bus` + METRO Rapid pattern | METRO A/C/D/E/F Line |
| Bus | OSM `route=bus` (rest) | ~135 local Metro Transit routes |

Generate transit data for a city (Mpls works out of the box; other cities depend on
their OSM transit coverage):

\`\`\`bash
cd src
uv run extract-transporte --city minneapolis
\`\`\`

The visualizer auto-detects the new module via the manifest and activates the
"Transporte" tile in the HUD.
```

- [ ] **Step 3: Update `README.es.md`**

Add the Spanish equivalent of the Transit section (translate the table headers and prose).

- [ ] **Step 4: Update `METHODOLOGY.md`**

Append a section 16:

```markdown
## 16. Transit overlay (added 2026-05-25)

A 4-category transit overlay sourced from OpenStreetMap route relations.
A single Overpass query fetches all `route=light_rail|train|tram|bus`
relations in the city bbox; each relation becomes one polyline (multi-way
relations are concatenated where members touch; disjoint segments emit the
longest continuous piece).

### Category mapping

| OSM route | Network/name hint | CS2 category |
|---|---|---|
| `light_rail` | — | LRT |
| `tram` | — | LRT (display) |
| `train` / `commuter_rail` | — | Commuter Rail |
| `bus` | `network=METRO` or `name` matches `METRO X Line` | BRT |
| `bus` | (other) | Bus |

### Sources shipped

Minneapolis (Metro Transit, ~145 routes including Blue/Green Line LRT, Northstar
commuter rail, METRO Rapid A/C/D/E/F BRT, ~135 local bus routes).

### Activation

The visualizer activates the "Transporte" tile automatically when the per-city
manifest declares the `transporte` module. The tile starts disabled (with a
lock icon) on cities that haven't generated transit data.
```

- [ ] **Step 5: Commit docs**

```bash
git add README.md README.es.md METHODOLOGY.md
git commit -m "docs(transporte): README + Methodology — usage + category mapping"
```

- [ ] **Step 6: Run pytest one final time + show summary**

```bash
cd src
uv run python -m pytest ../tests -m "not network" 2>&1 | tail -3
```

Expected: clean exit with ~380 passing.

- [ ] **Step 7: Do NOT push**

Leave the branch local. The user will decide whether to merge to main and push. The branch summary:

```bash
git log --oneline main..feat/transporte | nl
git diff --stat main..feat/transporte
```

Expected: ~12 commits, ~25-30 files changed (excluding generated JS), ~600-800 line diff.

---

## Self-review checklist (post-plan)

- [x] **Spec coverage:** Every spec section maps to a task:
  - §1 Motivation — not actionable
  - §2 Goals — covered by Tasks 6/9/10 (4 categories + tile activation + popup names)
  - §3 Non-goals — explicitly out of scope, no tasks
  - §4 Architectural decisions — embedded in Tasks 2, 3, 6, 9
  - §5 Architecture — Task 1 (scaffold) + Task 7 (entry point)
  - §6 Data pipeline — Task 6 (main pipeline)
  - §7 Classifier — Task 3
  - §8 Output schema — Task 6 (emit step) + uses `var` per spec lesson
  - §9 Visualizer integration — Tasks 8, 9, 10
  - §10 Testing strategy — every task has tests
  - §11 Out of scope — observed (no markers, no multi-city in v1)
  - §12 Risks — mitigations baked into Task 4 (gap handling) + Task 6 (skip counts)
  - §13 Effort estimate — ~4-6h, 12 tasks
  - §14 Success criteria — Tasks 11 + 12 verify

- [x] **No placeholders:** No TBD/TODO/"add error handling"/"similar to Task N". Every code step has the actual code.

- [x] **Type consistency:**
  - `classify_route(tags: dict) -> str | None` used consistently in Tasks 3 + 6
  - `extract_way_geoms(relation: dict) -> list[list[list[float]]]` consistent in Tasks 4 + 5
  - `concatenate_ways(ways) -> list[list[list[float]]]` consistent
  - `build_route_feature(relation, cs2_key) -> dict | None` consistent in Tasks 5 + 6
  - `TRANSPORT_LABELS` keys `{lrt, commuter, brt, bus}` consistent across Tasks 2, 3, 6, 9, 10
  - `DATA_TRANSPORT_<KEY>` (uppercase) consistent in Task 6 emitter and Task 9 hook

- [x] **`var` not `const` for output:** Task 6 emitter writes `var DATA_TRANSPORT_X = …` per the official_zoning lesson.

- [x] **Manifest cache-bust:** Already applied in main from the previous sprint (`fetch(url, { cache: "no-store" })`), no action needed.

- [x] **No Co-Authored-By trailers:** All commit messages in Tasks 1-12 are plain (no trailer footer).

---

## Notes for the executing engineer

- **Phase order matters:** Do Phase 0 → 1 → 2 → 3 → 4 in sequence. Phase 3 (visualizer) needs Phase 2's pipeline to actually generate data in Phase 4.
- **Overpass servers can be slow:** The query in Task 11 may take 30-90s. Don't worry about it. If it times out, `query_with_retry` from `shared/overpass_client` already retries with 3 different endpoints.
- **`window.transporteLoaded()` callback order:** The pill click handler (Task 9) is wired inside the callback so it only attaches AFTER the JS file loads. Initial click state is "on" because all 4 layer groups are added to the map by default. If you change this, also update Task 10's count update timing.
- **`escHtml` is reused:** Don't re-define it. Find the existing definition (used in zoning popups) and reuse it from the same scope.
- **Path resolution in tests:** `tests/transporte/test_extract_cli.py` uses `tmp_path` + `--cities-file` + `--visualizer-root` overrides to avoid touching the real Mpls manifest. This matches the test isolation pattern from the official_zoning module (which had test pollution issues).
- **Tile activation timing:** Per Task 8, the pill starts `disabled` (per `injectPill("transporte", false)` if there's no `DATA_TRANSPORT_LRT` global). The Task 9 hook calls `syncTransporteAvailability()` after the lazy load completes, which flips it interactive. There's a brief window where the tile shows disabled before transit data finishes loading — that's expected for lazy-loaded modules.
