# Test fixtures

## liechtenstein-latest.osm.pbf

Small Geofabrik regional PBF (~3.3 MB), used to test `shared.pbf_client`
end-to-end without large downloads in CI.

Vatican City was the original target (~600 KB) but Geofabrik does not
publish a Vatican extract (the URL 302-redirects to the index), so we fall
back to Liechtenstein as documented in the migration plan.

**Source:** https://download.geofabrik.de/europe/liechtenstein-latest.osm.pbf

**Refresh:**

```bash
cd tests/fixtures
curl -o liechtenstein-latest.osm.pbf https://download.geofabrik.de/europe/liechtenstein-latest.osm.pbf
```

**Bbox (approx):** `[47.048, 9.471, 47.270, 9.636]` (south, west, north, east)

Liechtenstein has a few thousand buildings, amenities, and ways — enough to
exercise all filter spec branches.
