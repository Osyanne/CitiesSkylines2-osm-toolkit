"""
End-to-end parity test: PBF source vs Overpass source.

Marked as integration — requires network (Overpass) and the regional PBF
cached locally. Skipped by default; run with:

    cd src
    CS2_PARITY_TEST=1 uv run python -m pytest ../tests/integration/test_pbf_overpass_parity.py -v -s

Expected runtime: 5-15 minutes for Minneapolis (Overpass queries are slow).

Tolerance: per source key, PBF count must be within +/- 20% of Overpass count.
Some divergence is expected because:
  - PBF snapshot is taken once daily by Geofabrik; Overpass is live OSM
  - Tag regex matching in Overpass (e.g. `building:use~"residential"`) approximates
    to list-equality in PBF (`["residential", "residential;commercial"]`)
  - Element-level dedup semantics differ slightly
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


# Allow running from repo root or src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("CS2_PARITY_TEST") != "1",
    reason="Set CS2_PARITY_TEST=1 to run (network + ~5-15 min runtime)",
)
def test_zoning_pbf_overpass_parity_minneapolis():
    """Per source key, PBF and Overpass element counts within +/- 20%."""
    from shared.registry import load_cities, get_city
    from shared.overpass_client import query_with_retry
    from shared.pbf_cache import ensure_pbf
    from shared.pbf_client import query as pbf_query
    from zoning.zones import build_queries, build_pbf_filters

    cities_file = Path(__file__).resolve().parents[2] / "cities.json"
    city = get_city(load_cities(cities_file), "minneapolis")
    bbox_tuple = tuple(city["bbox"])  # (south, west, north, east)
    bbox_str = ",".join(str(v) for v in bbox_tuple)
    pbf_path = ensure_pbf(city["pbf_region"])

    overpass_queries = build_queries(bbox_str)
    pbf_specs = build_pbf_filters(bbox_tuple)

    failures: list[str] = []

    for key in overpass_queries:
        try:
            op_data = query_with_retry(overpass_queries[key], label=f"op:{key}")
            op_count = len(op_data.get("elements", []))
        except Exception as e:
            failures.append(f"{key}: Overpass FAILED: {type(e).__name__}: {e}")
            continue

        try:
            pbf_data = pbf_query(pbf_path, bbox_tuple, pbf_specs[key], label=f"pbf:{key}")
            pbf_count = len(pbf_data["elements"])
        except Exception as e:
            failures.append(f"{key}: PBF FAILED: {type(e).__name__}: {e}")
            continue

        if op_count == 0 and pbf_count == 0:
            continue
        if op_count == 0:
            failures.append(f"{key}: Overpass=0 but PBF={pbf_count} (likely Overpass throttled)")
            continue

        ratio = pbf_count / op_count
        if not (0.8 <= ratio <= 1.2):
            failures.append(
                f"{key}: PBF={pbf_count}, Overpass={op_count}, ratio={ratio:.2f} "
                f"(expected 0.8-1.2)"
            )

    if failures:
        pytest.fail("Parity failures:\n  " + "\n  ".join(failures))
