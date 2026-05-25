# Official Zoning Module — Design Spec

**Date:** 2026-05-24
**Status:** Approved, ready for implementation plan
**Scope:** Sprint 1 — Minneapolis + New York City
**Predecessor context:** v3.2 Reddit feedback (Gap #1: "this is land use detection, not zoning"), validated by urban planner comments on r/CitiesSkylines2

## 1. Motivation

The current zoning map in the visualizer is **derived from OSM tags** (e.g., `building=apartments`, `landuse=commercial`). Real urban planners flagged two limitations in v3.2 community feedback:

1. **OSM measures what physically exists, not what is legally planned.** An empty lot zoned R4 has no OSM tags → invisible. A legacy industrial building zoned for mixed-use redevelopment is misrepresented.
2. **It's land use detection, not zoning.** Three separate r/CitiesSkylines2 comments (one from a working planner) said: "Cities like Minneapolis publish their official zoning. Integrate it."

This module adds an **official zoning overlay** sourced from each city's planning department open data portal, available as a sub-toggle inside the existing Zoning tile in the visualizer HUD.

## 2. Goals

- Integrate the **legal/institutional zoning data** for selected US cities into the visualizer.
- Provide a **side-by-side comparison** mode so the user can decide whether to keep both, consolidate, or default to one source per city.
- Establish a **pluggable architecture** so adding a new US city only requires one source module + one mapping table.
- Mitigate the "AI slop" critique by anchoring zoning data in authoritative sources.

## 3. Non-goals (v1)

- **Future Land Use (FLUM)** — Minneapolis publishes a 20-year planning vision; this is a separate dataset, deferred to Phase 2.
- **Parcels / tax lots** — different granularity; not zoning.
- **Other cities beyond Mpls + NYC in this sprint** — the pattern is built to scale, but each new city requires its own source module + mapping table written manually.
- **Auto-update from upstream portals** — snapshot one-time per city; manual refresh via `--force-refresh` flag.
- **OSM-derived removal** — keep both sources working in parallel. Consolidation decision (keep both, remove one, default to one) is **deferred until after the user reviews the comparison mode** for Mpls and NYC. That decision is its own follow-up — not part of this sprint.
- **Overlay districts / multi-zone polygons** — some shapefiles encode primary zoning + overlay district (e.g., historic, transit) as separate fields. v1 uses only the primary zoning field declared in `source_field`. Overlay districts can be added in a follow-up via additional source_field entries.

## 4. Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| City scope sprint 1 | Mpls + NYC | NYC = highest demand signal (Issue #10); MapPLUTO is the gold standard zoning dataset in US; Mpls = hero city with most user familiarity |
| Module placement | New top-level package `src/official_zoning/` | Mirrors existing `src/zoning/`, `src/vial/`, `src/services/` convention |
| City source pattern | Plugin: `src/official_zoning/sources/<slug>.py` + registry | Adding a new city = 1 source module + 1 mapping YAML; no core refactor |
| Mapping strategy | Hardcoded translation tables per city (YAML files) | Max precision over heuristic genericity; mappings reviewable by humans; one-time research per new city |
| Visualizer integration | Sub-toggle inside existing Zoning tile (no new top-bar tile) | Avoids HUD bloat; only the cities that opt in show the toggle |
| Data flow | Both sources loaded, swap instantáneo (Approach B) | Matches phased "compare → decide" intent; zero latency on toggle; isolated load impact (only Mpls + NYC affected) |
| Output files | Separate `datos_zonificacion.js` (OSM) + `datos_zonificacion_official.js` (new) per city | Independent regeneration; un-coupled schemas; clean to drop one later if consolidated |

## 5. Architecture

### Python package layout

```
src/official_zoning/
├── __init__.py
├── extract.py              # CLI entrypoint: extract-official-zoning --city <slug>
├── pipeline.py             # Orchestrator: download → parse → reproject → spatial filter → map → emit
├── sources/
│   ├── __init__.py         # Registry: explicit SOURCES dict {slug: module} populated via imports
│   ├── minneapolis.py      # Mpls Planning shapefile downloader + parser
│   └── new_york.py         # NYC ZoLA / Department of City Planning shapefile downloader + parser
└── mappings/
    ├── minneapolis.yaml    # Mpls zoning codes (~25) → 13 CS2 zones
    └── new_york.yaml       # NYC zoning codes (~70) → 13 CS2 zones
```

The `sources/__init__.py` registry is an explicit dict (not auto-discovery) to keep imports static and traceable:

```python
from official_zoning.sources import minneapolis, new_york
SOURCES = {"minneapolis": minneapolis, "new_york": new_york}
```

Each source module exposes `download(cache_dir)` and `read(cache_path) -> geopandas.GeoDataFrame`. The pipeline orchestrator delegates to the registered source via the city slug.

### New CLI entry-point

In `pyproject.toml`:

```toml
[project.scripts]
extract-official-zoning = "official_zoning.extract:main"
```

Usage:

```
cd src && uv run extract-official-zoning --city minneapolis
cd src && uv run extract-official-zoning --city new_york --force-refresh
```

### New dependencies

| Dep | Purpose | Notes |
|---|---|---|
| `geopandas` | Read shapefiles / GeoJSON | Use `pyogrio` engine (pure Python, no GDAL system dep) |
| `pyproj` | Reproject MN State Plane (EPSG:26915), NY State Plane Long Island (EPSG:2263) → WGS84 (EPSG:4326) | Standard CRS library |
| `pyogrio` | Backing engine for geopandas | Avoids GDAL install pain on Windows |
| `pyyaml` | Already present | Mapping table parsing |

## 6. Data pipeline

For each city declared in `cities.json` with `official_source`:

1. **Download** shapefile or GeoJSON from the city's open data portal → cache in `~/.cache/cs2-osm-toolkit/official_zoning/<slug>/` (TTL 30 days, override via `--force-refresh`).
2. **Parse** with `geopandas` (`gpd.read_file()` handles `.zip` + nested shapefile transparently).
3. **Reproject** geometries to WGS84 (EPSG:4326) with `pyproj`.
4. **Spatial filter** by the city bbox declared in `cities.json` (drop polygons outside CS2 build scope).
5. **Map** each polygon's zoning code (read from `source_field` declared in the YAML) through the city's translation table → one of 13 CS2 zone keys.
6. **Emit** `visualizer/cities/<slug>/datos_zonificacion_official.js` with the same shape as `datos_zonificacion.js` but variable names prefixed: `DATA_OFFICIAL_RES_LOW_HOUSE`, `DATA_OFFICIAL_COM_HIGH`, etc.
7. **Update** `manifest.json` for the city to declare the `official_zoning` module with a fresh hash.

## 7. Mapping schema

Each city's mapping table lives in `src/official_zoning/mappings/<slug>.yaml`:

```yaml
# Example: minneapolis.yaml
city: minneapolis
source_url: https://opendata.minneapolismn.gov/datasets/zoning.zip
source_field: ZONE_CODE       # property of the shapefile carrying the zoning code
crs_in: EPSG:26915            # source CRS (MN State Plane South)
last_validated: 2026-05-24
mappings:
  R1:   res_low_house         # Single-family
  R1A:  res_low_house
  R2:   res_low_house
  R2B:  res_row
  R3:   res_med
  R4:   res_med
  R5:   res_high
  R6:   res_high
  OR1:  res_mixed
  OR2:  res_mixed
  OR3:  office_low
  B1:   com_low               # Neighborhood Business
  B2:   com_low
  B3:   com_high
  B4:   com_high              # Downtown Business
  B4-1: com_high
  C1:   com_low               # Commercial corridor
  I1:   industrial
  I2:   industrial
  I3:   industrial
unmapped: skip                # alternatives: "default: <zone_key>"
```

Mapping research sources:

- **Minneapolis**: Mpls Municipal Code Chapter 530 (Zoning Code) + opendata.minneapolismn.gov dataset metadata.
- **New York**: NYC Zoning Resolution + NYC Department of City Planning ZoLA documentation.

Each mapping table will be validated against the actual codes present in the downloaded shapefile during the test suite. Codes present in the shapefile but not in the YAML emit a warning; codes in the YAML but not in the shapefile emit an info log.

## 8. Visualizer integration

### Manifest extension

`visualizer/cities/<slug>/manifest.json` gains a new optional module entry:

```json
{
  "modules": {
    "zoning":           { "hash": "abc123" },
    "vial":             { "hash": "..." },
    "services":         { "hash": "..." },
    "official_zoning": {
      "hash": "def456",
      "source_name": "City of Minneapolis Planning",
      "source_url": "https://opendata.minneapolismn.gov/datasets/zoning",
      "category_count": 25,
      "last_extracted": "2026-05-24"
    }
  }
}
```

### Loading flow in `map.html`

1. Primary render of OSM zoning proceeds exactly as today.
2. After `loadAll()` resolves, if `CITY_MANIFEST.modules.official_zoning` exists, lazy-load `datos_zonificacion_official.js` in the background via dynamic `<script>` injection (non-blocking).
3. On load, populate parallel layer groups (`groupsOfficial[]`) mirroring `groups[]`. Initially hidden.
4. Sub-toggle in the Legend header chooses which source renders.

### Sub-toggle UI

Rendered inside the Legend panel header for cities with `official_zoning`:

```
┌─ CS2 Zonificación ────────────┐
│ Source:                       │
│   ⦿ OSM-derived               │
│   ◯ Official (Mpls Planning)  │
│   ◯ Comparison (split)        │
├───────────────────────────────┤
│ Residencial                   │
│   Low Density Housing  161,015│
│   ...                          │
```

- Default selection: **OSM-derived** (current behavior preserved).
- Selecting **Official** hides OSM layer groups and shows Official ones.
- Selecting **Comparison** activates split-screen mode (next section).

Cities without `official_zoning` in their manifest show the legend header without the toggle.

### Comparison mode

Vertical split-screen using `L.gridLayer` with CSS clip-path:

- Left half of map renders OSM zoning layer groups.
- Right half renders Official zoning layer groups.
- A draggable vertical divider in the middle lets the user wipe between sources.
- Legend counts adapt to show both columns side-by-side when in comparison mode.

This is the primary tool for the user's phased "compare and decide" workflow.

## 9. Testing strategy

Framework: pytest (existing project convention; same configuration applies).

| Test type | Coverage | Target count |
|---|---|---|
| Unit (per source module) | Mock shapefile bytes → parse + reproject + filter + map → expected output | ~6 |
| Mapping coverage | YAML mapping covers 100% of codes seen in downloaded shapefile (warn on gaps) | ~2 (one per city) |
| Pipeline integration | End-to-end `extract-official-zoning --city minneapolis` produces expected file count + schema | ~4 |
| Visualizer (Playwright) | Sub-toggle swap renders correct dataset, no console errors | ~3 |
| Comparison mode | Split-screen render + draggable divider | ~2 |
| Manifest schema | Existing tests don't break with new optional field | (regression coverage) |

Network-touching tests (download from open data portal) are marked with `@pytest.mark.network` and run opt-in via `pytest -m network` to keep the default test run offline-safe.

Target: **+20-25 tests**. Total project suite goes from 292 to ~317.

## 10. Out of scope (deferred to future phases)

- Future Land Use (FLUM) overlay
- Parcels / tax lots
- Other US cities (pattern is ready; each requires manual research + YAML)
- Auto-update from upstream portals
- Removing OSM-derived zoning (kept until comparison phase decides)
- Per-zone reliability/confidence encoding (the existing OSM uncertainty layer stays; official is treated as authoritative without confidence ranking)

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Open data portals change schema or URL | Mapping coverage tests + pipeline integration tests fail loudly in CI; `last_validated` field in YAML signals staleness |
| Mapping table incomplete or incorrect | Comparison mode is the explicit review tool before declaring "approved"; per-zone code count logged on extract |
| NYC shapefile is ~40k polygons → JS file 70+ MB | Approach B lazy-loads the second source after primary render; GH Pages serves gzip-compressed |
| `geopandas` install pain on Windows | Use `pyogrio` engine (pure Python wheels, no GDAL system dependency) |
| User confusion with two zoning sources | UX explicitly labels the source in the toggle; comparison mode shows both; phased plan is to consolidate after review |
| Mpls + NYC zoning shapefiles change post-extract | TTL 30 days on cache; `--force-refresh` flag for manual regen |

## 12. Effort estimate

**Sprint 1 (this design):** Mpls + NYC end-to-end with sub-toggle + comparison mode.
- 8-15 hours of focused work.
- Subagent-driven viable: spec → plan (TDD, 18-22 tasks) → execution with fresh subagent per task.

## 13. Success criteria

- `extract-official-zoning --city minneapolis` produces `datos_zonificacion_official.js` deployable via the existing build pipeline.
- Same for `--city new_york`.
- Manifest carries the new `official_zoning` module entry; visualizer detects it and renders the sub-toggle.
- Sub-toggle swap is instant (no network on switch).
- Comparison mode shows side-by-side render with draggable divider.
- All existing tests pass; new tests added land green in CI.
- After review, user makes a decision on consolidation strategy for Mpls and NYC.

## 14. References

- v3.2 Reddit feedback summary: Obsidian `📊 Lessons — Reddit Launch v3.2.md` (gap #1 detail)
- HUD redesign that paved the way: `docs/specs/2026-05-22-landing-redesign-design.md`
- Current zoning pipeline: `src/zoning/extract.py` + `src/zoning/classifiers.py`
- 13 CS2 zone reference: `docs/cs2-zone-reference.md`
- Mpls Planning data portal: https://opendata.minneapolismn.gov
- NYC Department of City Planning: https://www1.nyc.gov/site/planning/data-maps/open-data.page
