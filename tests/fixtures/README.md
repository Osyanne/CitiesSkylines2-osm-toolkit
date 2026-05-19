# Test fixtures

## monaco-latest.osm.pbf

Tiny Geofabrik regional PBF (~664 KB), used to test `shared.pbf_client`
end-to-end without large downloads in CI.

Vatican City was the original target (~600 KB) but Geofabrik does not
publish a Vatican extract (its URL 302-redirects to the index — Vatican
data is included in the Italy extract). Monaco is the next-smallest
country-level extract and fits the same purpose.

**Source:** https://download.geofabrik.de/europe/monaco-latest.osm.pbf

**Refresh:**

```bash
cd tests/fixtures
curl -o monaco-latest.osm.pbf https://download.geofabrik.de/europe/monaco-latest.osm.pbf
```

**Bbox (approx):** `[43.7236, 7.4090, 43.7521, 7.4395]` (south, west, north, east)

Monaco has ~5,000 buildings, ~1,500 highways, and a dense mix of amenities,
leisure POIs, and landuse polygons — enough to exercise every filter spec
branch (way + node + relation, exact + presence + one-of tag matchers,
spatial joins for the mixed-apartments pattern).
