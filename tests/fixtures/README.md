# Test fixtures

## goatcounter/count.v5.js

The GoatCounter script that `visualizer/assets/visits.js` loads, byte for byte
(ISC license, see its header). The tests check that its SHA-384 is the
`integrity` hash in `visits.js`, and the browser test serves it in place of
`gc.zgo.at` so the real script runs without network. `.gitattributes` keeps
Git from changing its line endings.

**Source:** https://gc.zgo.at/count.v5.js (hash listed at
https://www.goatcounter.com/help/countjs-versions)

**Refresh:** only when `visits.js` moves to a newer stable version. Download
that version here, put its hash from the page above in `visits.js`, and point
the tests (`VISITS_SCRIPT_FIXTURE`) at the new file:

```bash
cd tests/fixtures/goatcounter
curl -O https://gc.zgo.at/count.v5.js
```

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
