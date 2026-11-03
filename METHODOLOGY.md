# Methodology — CS2 OSM Toolkit

Technical documentation for every design decision in this toolkit.

> **Version 3.6.1** (2026-11-02). Sections were added as the toolkit grew, so the early ones describe the first Minneapolis pipeline and say where it changed later. For the original v1.0 design, see git history.

---

## 1. The Problem: Overpass API 504 Timeouts

> Since v3.4.0, zoning, roads, services and Google buildings read a local OSM extract (`.osm.pbf`) by default: see §23. §1, §2 and §7 describe the Overpass mode. It still runs with `--source overpass`, and transit and infrastructure only read Overpass.

The Overpass API is a free, community-run service that allows querying OpenStreetMap data by geographic area. The natural first approach — one query that fetches all zoning types at once — fails consistently for city-sized bounding boxes:

```
HTTP 504 Gateway Timeout
```

This happens because:
- The Minneapolis bbox (`44.86,-93.38,45.05,-93.17`) covers ~350 km²
- A single query requesting all landuse types returns 5-10 MB of JSON
- Public Overpass instances enforce strict timeouts (120-180s) to prevent abuse
- Large queries hit those timeouts even when the server isn't under heavy load

## 2. Solution: Chunked Source Queries

Instead of one mega-query, this pipeline runs one source query per landuse/building category, in sequence:

```
mixed_apartments → apartments → landuse_residential → residential_subtypes
→ commercial → office → industrial → parking
```

Later versions added four more: `generic_buildings` (§17), `civic_amenities`, and `morphology_buildings` and `morphology_commercial_nodes` for §19.

**Why this works:**
- Each category returns 200-800 KB instead of 5+ MB
- Smaller payloads complete well within the timeout window
- If one category fails, only that category is retried (not everything)
- Progress is visible: users can see each category download in real time

**Trade-off:** one round-trip per category instead of 1, which added ~2-3 minutes of network overhead with the first eight. This is acceptable because the alternative is unreliable failures.

## 3. The 13-Zone Model (CS2 Oficial Alignment)

Originally (v1.0) the pipeline output ~10 zone types loosely mapped to CS2. In Session 1.6 (2026-05-13) the model was realigned to match the **exact 11 zones** present in CS2 oficial + 2 parking categories for reference.

### Why this realignment matters

CS2 has these zones in the game's painter:

- **Residential (6):** Low Density Housing, Medium Density Row Housing, Medium Density Housing, Mixed Housing, Low Rent Housing, High Density Housing
- **Commercial (2):** Low Density Business, High Density Business
- **Offices (2):** Low Density Offices, High Density Offices
- **Industrial (1):** Industrial Manufacturing

The pre-v1.6 model had only 3 residential tiers (high/med/low), didn't split offices by density, and had no "Mixed Housing" specifically. Now the map reflects what a CS2 player would actually zone in-game.

### The Heuristics

**Residential subtypes — distinguishing Low Rent from Medium/High Density:**

OSM doesn't tag "rent." The pipeline uses a combination of explicit tags + footprint area:

```python
if (tags["building"] in {"public_housing", "council_house"} or
    tags["social_housing"] == "yes"):
    return "low_rent"  # explicit
if 4 <= floors <= 6 and area_m2 >= 1500:
    return "low_rent"  # heuristic: mid-rise + large footprint
if floors >= 7 or building in {"tower", "residential_tower", "skyscraper"}:
    return "high"
```

This isn't perfect — OSM has no canonical "low rent" tag — but it captures the main patterns: large mid-rise apartment blocks (typical low-rent profile) vs. tall residential towers (typical luxury high-density).

Since v3.4.14, `building=house` and untyped residential buildings can also move up from Low Density by their height or their shape: see §19.

**Commercial high-vs-low density:**

Based on the most common patterns in OSM:
- `shop=mall` → always high (a mall is a big-box anchor)
- `tourism=hotel` with ≥4 floors or ≥2000 m² → high
- `amenity` ∈ {cinema, theatre, casino, conference_centre} → high
- `building=commercial` with ≥4 floors, or anything with ≥5 floors → high
- Everything else (shops, cafés, restaurants, small commercial) → low

**Office high-vs-low density:**

Simple threshold based on `building:levels` or `building=skyscraper`. ≥4 floors → high.

## 4. Spatial Join for Mixed Housing (Session 1.6.1)

The original Mixed Housing detection (Session 1.6) was tag-based:

```overpass
way["building"="apartments"]["shop"](bbox);
```

This required `shop` and `building=apartments` to be on the **same way** in OSM. In reality, OSM tags commercial POIs as separate **nodes inside** the building polygon — not on the way itself. Result: only 3 Mixed Housing polygons in Minneapolis (clearly wrong).

### The fix: spatial join via `around.set:radius`

Session 1.6.1 added a new source query that uses Overpass's `around.set` spatial operator:

```overpass
[out:json][timeout:120];
(
  node["shop"](bbox);
  node["amenity"~"^(restaurant|cafe|bar|pub|fast_food)$"](bbox);
  node["tourism"="hotel"](bbox);
)->.comm;
(
  way["building"="apartments"](around.comm:5);
  way["building"="residential"](around.comm:5);
  way["building"="mixed_use"](bbox);
);
out body geom;
```

The `(around.comm:5)` filter finds apartment buildings within 5 meters of any commercial POI node. Result: **123 Mixed Housing polygons** detected — a 41× improvement.

### Important syntax note

The query uses **named set** syntax (`->.comm`). The naive `(around:5)` with the implicit `_` set returns 0 results — this was a non-obvious bug we hit during development. Always use named sets for spatial operations spanning multiple statements.

In PBF mode (§23) the same join is a `SpatialJoin` of 5 m in `build_pbf_filters` (`src/zoning/zones.py`), applied by `pbf_client`.

## 5. Footprint Area Computation (Equirectangular Approximation)

To distinguish "block-scale" polygons (50,000 m² landuse) from "individual building" polygons (~150 m²), the pipeline computes polygon area using an equirectangular projection at the centroid:

```python
def polygon_area_m2(coords):
    lat0 = sum(c[0] for c in coords) / len(coords)
    cos_lat0 = math.cos(math.radians(lat0))
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * cos_lat0
    pts = [(c[1] * m_per_deg_lon, c[0] * m_per_deg_lat) for c in coords]
    # Shoelace formula
    n = len(pts); s = 0.0
    for i in range(n):
        x0, y0 = pts[i]; x1, y1 = pts[(i+1) % n]
        s += x0*y1 - x1*y0
    return abs(s) / 2.0
```

Sufficient accuracy at urban scale (city of ~20 km tall). For continent-scale work, use a proper projected CRS via Shapely.

## 6. OSM Element Deduplication Between Categories

OSM has overlapping semantics — a downtown apartment building might appear in multiple source queries simultaneously:
- `apartments` (because `building=apartments`)
- `residential_subtypes` (because also tagged `building=residential`)
- `mixed_apartments` (because near a shop)

If we render all three, the same polygon stacks visually.

**Solution:** Process queries in priority order, maintain a global `seen_ids` set, skip any element already classified. The key is the OSM type plus the id, because a way and a relation can share a number:

```python
seen_ids = set()
def add(el, cs2_key):
    ref = (el["type"], el["id"])
    if ref in seen_ids: return False
    seen_ids.add(ref)
    output[cs2_key].append(make_item(el))
    return True

# Priority order: most specific wins
for el in raw["mixed_apartments"]:    add(el, "res_mixed")
for el in raw["apartments"]:          add(el, classify_apartment(...))
for el in raw["residential_subtypes"]: add(el, ...)
# etc.
```

The first viewer mirrored this logic for its live mode (no prebuilt data). The current viewer doesn't query Overpass: it draws what the extractors wrote.

## 7. Multi-Endpoint Rotation with Exponential Backoff

The pipeline rotates across 3 community Overpass endpoints:

| Endpoint | Operator |
|---|---|
| `overpass-api.de` | Official OpenStreetMap Foundation |
| `overpass.kumi.systems` | Kumi Systems (community) |
| `maps.mail.ru/osm/tools/overpass` | Mail.ru Group |

**Retry strategy (first viewer, in JS):** the first viewer also queried Overpass from the browser, with 3 retries (backoff 2s / 4s / 8s), two queries in parallel and a final fallback to `corsproxy.io` to bypass CORS limits. The current viewer doesn't query Overpass.

**Retry strategy (in Python `src/shared/overpass_client.py`):**
- 4 rounds × 3 endpoints = 12 attempts max per query
- Round backoff: 5s / 15s / 30s

These strategies converge on 100% success rate in normal conditions. The one known failure mode: Overpass returning HTTP 200 with an empty `elements` array (silent overload). This is undetectable client-side without semantic validation, which we don't currently do.

## 8. Performance: Vector Tiles + WebGL

**History.** The first viewer used Leaflet's SVG renderer (one DOM node per polygon, ~30 s to render 81k polygons). The canvas renderer (`preferCanvas: true`) and tier-based hiding (small houses only from zoom 14) brought it down to a few seconds. But Minneapolis grew to 184k zoning polygons plus 109k road segments, and Leaflet keeps one JS object per feature: it re-projects and redraws all of them on every zoom. Measured in headless Chromium with local files: ~18 s to open, ~950 MB of JS heap, and 3-8 s frozen per zoom level.

**Now.** Zoning (plus Google buildings) and roads are cut into Mapbox Vector Tiles by `src/shared/tiles.py` (`uv run build-tiles`, also run by the extractors) and drawn by MapLibre GL on the GPU:

- Tiles cover zoom 9-14 (MapLibre zooms, one less than Leaflet's). Beyond 14 MapLibre over-zooms the z14 tiles (~0.4 m per unit).
- **Level of detail is baked in.** Below z14, geometry is simplified by 0.5 px and anything under 1 px is dropped. Houses and parking lots under 3,000 m² start at z13 (the old tier rule). Local streets start at z11, bike lanes at z12, footpaths at z13.
- **Storage.** Tiles are stored as `tiles/<z>/<x>/<y>.mvt.gz` plus a `tiles/tiles.json` index (bounds, zooms, per-category counts, list of non-empty tiles, content hash). They are separate files rather than a single `.pmtiles` because PMTiles needs HTTP range requests, and `python -m http.server` (what `start-visualizer.bat` runs) does not support them. The viewer fetches tiles through a small `cs2tiles://` protocol that gunzips them with `DecompressionStream`.
- **Deterministic output.** The encoder is written in plain Python (shapely + numpy), so it runs on Windows without extra native dependencies, and gzip runs with `mtime=0`. Rebuilding unchanged data gives byte-identical files, so git sees no spurious changes.
- **Small modules stay GeoJSON.** Services, transit, infrastructure and official zoning are small, so they are loaded whole and handed to MapLibre as GeoJSON sources.
- **Fallback.** A city whose manifest has no `tiles` entry (data from an older toolkit) is drawn from the full data files through GeoJSON sources, with the same zoom rules applied as filters. GitHub Pages does not publish the full files of the tiled layers (`_config.yml`): they were half of a site capped at 1 GB. So a published city needs its tiles, which `tests/shared/test_tiles.py` checks.
- **Category filters.** A checkbox, `Only` or `Restore` is a `setFilter`, and MapLibre then re-parses every loaded tile of that source in its workers (zoning and roads share the tile source). A hidden layer (a module that is Off, or the zoning source that isn't selected) gets its filter only when it is shown. While a source is re-parsing, further clicks wait and are applied together when it finishes: a burst of clicks costs at most two passes, and the map never settles on an in-between state. `Dim` only changes a constant opacity, which needs no re-parse; that is why zone fills carry their transparency in the fill colour rather than in a per-polygon `fill-opacity`. Headless Chromium on a laptop GPU, until MapLibre's `idle`: `Only` takes 0.3-0.6 s in Yogyakarta (520,689 zoning features) and about 0.6 s in Minneapolis. With software rendering it is 0.4-1.5 s and 2.4-3.5 s, and zoning `Dim` in Minneapolis went from 3.0 s to 0.7 s with the colour change.

Minneapolis, headless Chromium, local files. Main-thread JS time is what freezes the page on any machine. Wall-clock times for MapLibre in a GPU-less container include software rendering, so they are left out:

| | Leaflet (before) | + off-map build, zoom gates | + compact data | Vector tiles + MapLibre |
|---|---|---|---|---|
| JS time to open | 14.3 s | 4.2 s | 3.9 s | 1.2 s |
| JS time, 6 zooms + 3 pans | 29.3 s | 25.6 s | 24.0 s | 1.1 s |
| JS heap | 949 MB | 782 MB | 556 MB | 125 MB |
| Zoning + roads download (gzip) | 8.8 MB | 8.8 MB | 4.9 MB | 0.6 MB (6 tiles) |

## 9. Prebuilt Data Format (`datos_*.json`)

`extract-zoning`, `extract-vial` and `extract-google-buildings` write a compact JSON file per module (`datos_zonificacion.json`, `datos_vial.json`, `datos_external_buildings.json`). The format lives in `src/shared/compact.py` and is lossless: decoding gives back exactly the items the extractor produced.

```json
{
  "format": "cs2-compact", "version": 1, "module": "zoning",
  "precision": 5,
  "meta": {"bbox": "...", "generated_at": "..."},
  "layers": {
    "res_low_house": {
      "ids":  [38932348, ...],
      "geom": [[4498737, -9324109, -6, 17, ...], ...],
      "props": {"name":   {"default": "", "sparse": {"5": "Old Muskego Church"}},
                "method": {"dict": ["landuse", "area"], "codes": [0, 1, -1, ...]}}
    }
  }
}
```

- **Layer key = `cs2_key`**, so it is not repeated in every item.
- **Coordinates** are integers scaled by 10^5 (the same ~1.1 m precision `round_coords` already applies). The first point of each ring is absolute and the rest are deltas, so most numbers are 1-3 digits.
- **Properties are stored per column.** The encoder picks the shortest form: a default plus sparse exceptions (names, bridges), a small dictionary plus codes (`method`), or a plain list (Google `conf`).

Minneapolis zoning went from 47 MB to 12 MB (5.6 → 3.1 MB gzipped), and the whole `visualizer/cities/` folder from 435 MB to 119 MB. The visualizer fetches the file, decodes it into the same `DATA_<ZONE>` / `DATA_EXT_<ZONE>` / `DATA_VIAL` globals the old `.js` files defined, and reads the filename from the manifest (`modules.<module>.file`). Manifests without that field still load the old `.js` names.

`uv run convert-legacy-data [--city <slug>]` migrates old `.js` files. It checks the round trip before deleting each original.

## 10. Session 1.8 Caveat: Microsoft Building Footprints

A future-experimental script `src/zoning/extract_msbuildings.py` was added to augment OSM data with Microsoft's [USBuildingFootprints](https://github.com/microsoft/USBuildingFootprints) dataset (5M+ buildings detected from satellite imagery in Minnesota). The goal: fill OSM coverage gaps in suburbs/edge neighborhoods.

**Known issues (rolled back from production):**

1. **Misclassification**: The script uses any polygon ≥3000 m² as a "landuse anchor" for nearest-neighbor classification. But OSM has many large *individual buildings* (a Target store, an industrial warehouse) that are ≥3000 m². Those get used as if they were landuse zones, pulling nearby MS buildings into the wrong classification (houses near Hiawatha Avenue ending up colored as commercial/industrial).

2. **Suggested fix (not yet applied):** Re-query Overpass for ONLY `landuse=*` polygons (pure zoning, no buildings) and use only those as classification anchors. Tighten the "nearest" radius from 500m → 100m.

The script remains in the repo for future improvement. No published map uses it: they run on OSM data, plus Google Open Buildings in three cities (§18).

## 11. Why Not QGIS or PostGIS?

The original v1.0 considered alternatives:

- **QGIS:** GUI-based, excellent for visual workflows, but not scriptable in a reproducible way
- **PostGIS:** Industrial-strength spatial queries, but requires a PostgreSQL server setup
- **GeoPandas:** Python library for geospatial DataFrames, but adds ~500 MB of dependencies (GDAL, Shapely, Fiona)

This pipeline chose none of them for a specific reason: **zero barrier to entry**.

The goal was a tool any CS2 player could run without installing a database. v1.0 only needed `requests` + `tqdm`. Since then the toolkit added shapely (spatial joins, §17 and §19), pyosmium (PBF extracts, §23) and geopandas (official zoning, §20). `uv sync` installs them all, and there is still no database to set up.

v1.0 used OSM element IDs as proxies for spatial containment, and Overpass's `around.set` for the one place where it really mattered (Mixed Housing). Later passes do real spatial joins with shapely: buildings inside land use polygons (§17) and walls shared between buildings (§19).

## 12. Adapting to Any City

The pipeline is city-agnostic. Any city with reasonable OSM coverage will work.

**Step 1: Get the bounding box**

Use [Nominatim](https://nominatim.openstreetmap.org/):
```
https://nominatim.openstreetmap.org/search?q=Chicago,IL&format=json&limit=1
```

The response includes a `boundingbox` field: `[south, north, west, east]`.

Note: `cities.json` and Overpass QL use `south,west,north,east` order: swap accordingly.

**Step 2: Add the city to `cities.json`**

The entry needs `display_name`, `country`, `bbox`, `center` (`[lat, lon]`), `zoom`, `tagline` and `locale`, plus `pbf_region`: the Geofabrik region (`"north-america/us/illinois"`), or a list when the box crosses the border of an extract (§23). Then, from `src/`, run `uv run extract-zoning --city <slug>` and `uv run generate-landing`. The map only opens cities listed in `cities.json`.

**Step 3: Consider OSM coverage quality**

North American and Western European cities have excellent OSM coverage including building heights. Cities in other regions may have fewer `building:levels` tags, which will cause most residential to fall back to "low density." This is a data limitation, not a pipeline limitation. Without heights, the shape pass of §19 still lifts houses and untyped buildings that share walls in built-up blocks.

**Step 4: Calibrate thresholds**

Run the pipeline once, open the visualizer, and visually compare against Google Maps satellite view. Adjust thresholds in `src/zoning/classifiers.py` if your city has different building patterns:
- `effective_levels` cutoffs for high/med density
- `area_m2` threshold for Low Rent detection
- Commercial high-density signals (mall, hotel, etc.)

The density pass of §19 keeps its thresholds in `src/zoning/morphology_config.py`. Every threshold applies to all the cities you extract afterwards.

See [docs/adapting-to-other-cities.md](docs/adapting-to-other-cities.md) for a complete walkthrough.

## 13. Test Coverage

The tests live in `tests/`, one folder per module (`zoning`, `vial`, `services`, `transporte`, `infraestructura`, `official_zoning`, `shared`), plus `visualizer` (the map in Chromium) and `integration`.

Run with:
```bash
cd src
uv sync
uv run pytest ../tests/ -m "not network"
```

`pytest.ini` sits at the repo root, so the `../tests/` path is needed: a bare `uv run pytest` from `src/` collects nothing. Tests marked `network` are opt-in (`-m network`): the official zoning portals, and the map tests in Chromium, which are also marked `browser` and run with `uv run --group thumbnails pytest ../tests/visualizer -m browser`. The PBF/Overpass parity test only runs with `CS2_PARITY_TEST=1`.

## 14. Red Vial (Sesión 2)

### Modelo

6 categorías mapeadas 1:1 desde `highway=*`:

| Categoría | Tags OSM |
|---|---|
| Highway | motorway, trunk (+ _link) |
| Major Road | primary, secondary (+ _link) |
| Minor Road | tertiary (+ _link), residential, unclassified |
| Local Street | living_street, service |
| Pedestrian Path | pedestrian, footway, path, steps |
| Bike Lane | cycleway |

### Pipeline

- **Una sola pasada** sobre `highway=*` trae todas las categorías: un filtro sobre el PBF (por defecto, §23) o 1 query Overpass con regex (`--source overpass`)
- `vial.classifiers.classify_highway(tags)` → lookup en dict puro
- `linestring_from_way(element)` → coords [[lat, lon], ...] (mínimo 2 puntos)
- Output: `datos_vial.json` (formato compacto, §9), una capa por categoría

### Render

Las calles van en las teselas vectoriales, en la misma fuente que la zonificación (§8), y MapLibre las dibuja como líneas. Ancho por categoría (3.5px highway → 0.6px pedestrian). `bridge=yes` suma 0.5px para destacar puentes del Mississippi. Las calles locales aparecen desde z11, las bicisendas desde z12 y los senderos desde z13.

## 15. Servicios públicos (Sesión 3)

### Extracción

Una sola pasada (sobre el PBF por defecto, §23, o una query Overpass) cubre 5 categorías alineadas a las solapas de servicios base de Cities: Skylines 2:

| Bucket | Tags OSM | Geometría esperada |
|---|---|---|
| `health` | `amenity=hospital\|clinic\|doctors\|funeral_directors\|crematorium` + `landuse=cemetery` | Mix polígono + punto |
| `education` | `amenity=school\|university\|college\|kindergarten\|research_institute` + `office=research` | Mayormente polígono |
| `fire` | `amenity=fire_station` | Mix |
| `admin` | `amenity=police\|townhall\|courthouse\|prison\|library\|theatre\|arts_centre\|cinema` + `office=government` + `tourism=museum` | Mix |
| `parks` | `leisure=park\|nature_reserve\|garden\|playground\|sports_centre` | Mayormente polígono |

En modo Overpass: timeout 90s, `out body geom` para extraer geometría completa en una sola pasada.

Electricidad, agua, basura y comunicaciones no están acá: son el módulo de infraestructura (§22).

### Filtros aplicados

- **`landuse=cemetery` solo cuenta como `way`.** Los nodes con landuse=cemetery se rechazan — un cementerio sin polígono no aporta información geográfica útil.
- **Subtypes culturales en `admin` requieren `name=*`.** Bibliotecas, teatros, museos, cinemas, arts centres anónimos se filtran para reducir ruido (OSM tiene muchas entradas placeholder sin nombre real).
- **Resto sin filtro adicional.** Hospitales, escuelas, parques se incluyen tal cual.

### Geometría: polígono-preferido + punto-fallback

Cada entidad OSM aparece **una vez** en el output. La función `infer_geometry_kind(element)`:

1. Si `element.type === "node"` → `"point"` (usa lat/lon directo)
2. Si `element.type === "way"` con geometría ≥4 nodos Y primer==último → `"polygon"`
3. Sino → `"point"` (usa primer nodo como anchor)

Esto evita duplicación cuando la misma entidad tiene representación tanto como node como way en OSM, y elige la representación más informativa (polígono > punto).

### Rendering

Los servicios se cargan enteros como fuente GeoJSON de MapLibre (§8):

- **Polígonos:** fill opacity 0.35, stroke 1.5px opacity 0.9, con el color de la categoría. **Siempre visibles** independiente del zoom.
- **Puntos:** un ícono por categoría (círculo de color con H, E, F o P en blanco, o un árbol para parques), desde el zoom 11 de MapLibre (12 de Leaflet).
- **Detalle:** desde la v3.4.12 no hay popups. Al hacer click, la ficha muestra el nombre, la categoría, el subtipo y los tags OSM; si debajo hay una zona, la ficha es de la zona y el servicio sale en «Also here».

Con Leaflet, los ~2273 features de Minneapolis (1573 son parques: playgrounds, gardens, sports centres) se dibujaban de a 250 para no bloquear la página. Con MapLibre ese paso ya no hace falta.

### Decisiones documentadas

- **Design spec:** [`docs/plans/2026-05-16-modulo-servicios.md`](docs/plans/2026-05-16-modulo-servicios.md)
- **Implementation plan:** [`docs/plans/2026-05-16-modulo-servicios-implementation.md`](docs/plans/2026-05-16-modulo-servicios-implementation.md)
- **Tests:** `tests/services/`

---

## Sección 16 — Multi-city architecture (v3.3, mayo 2026)

Tras Sesiones 1-3 con scope Minneapolis-only, el toolkit se generalizó para
soportar múltiples ciudades via Featured Cities Pack.

### Cambios estructurales

- **Registro `cities.json`** (raíz del repo): single source of truth para qué
  ciudades existen, con bbox + center + zoom + tagline + locale por entry.
- **Manifest per-city** (`visualizer/cities/<slug>/manifest.json`): declara qué
  módulos están generados para esa ciudad y sus hashes (sha256 trunco para
  cache busting). Se actualiza automáticamente cada vez que un extract corre.
- **Pipeline `--city` flag**: los extracts aceptan `--city <slug>`, que
  resuelve el bbox (y la región del PBF, §23) desde el registro. Una ciudad
  nueva necesita su entrada en `cities.json`: el visor solo abre los slugs que
  están ahí (`generate-landing` los copia a `visualizer/cities.json`).
- **Visualizer refactor**: `index.html` legacy → `map.html` (lee `?city=`,
  inyecta scripts dinámicamente desde `manifest.json`). Nueva `index.html` es
  landing page generada por `generate-landing` script.

### Scope Phase 1

- Minneapolis preserva los 3 módulos (hero/legacy).
- 3 ciudades adicionales (Amsterdam, Madison, Charleston) entran solo con
  zoning. Vial y services on-demand vía GitHub Issues post-launch.
- Manhattan y Tokyo se incluyeron originalmente en v3.3 pero se removieron
  en v3.3.2 (2026-05-18) para enfocar el set en cities con request real de la
  community + Amsterdam como referencia de fine-grained EU tagging.
- En v3.3.3 (2026-05-18 PM) se incorporan **Trondheim (Norway)** y
  **Mafra, SC (Brazil)** como las primeras dos cities entrantes por
  community city-request (Issues #5 y #6). A partir de v3.3.3 el template
  de city-request limita el scope a **zoning-only** mientras se amplía
  la cobertura geográfica; vial/services para nuevas cities quedan pausados.

### Deferreds (Phase 2+)

- Rename del repo a `cs2-osm-toolkit` (espera caída de tráfico Reddit v3.2).
- Heightmap generation pipeline (Phase 3 — valida demanda con Featured
  Cities primero; CityTimelineMod fork confirma demanda implícita).
- Reapertura de vial/services para nuevas city-requests cuando la cobertura
  de zoning alcance ≥10 cities.
- Promoción de cities zoning-only a fully-featured (cuando acumulen 5+
  requests por vial/services).

---

## Sección 17 — Generic buildings: spatial-join + heurística (v3.3.4)

### Problema

Al procesar Mafra, SC (Brasil) en v3.3.3 quedó claro que el extractor de zoning
solo recogía **24%** de los buildings tagged en OSM (105 / 427 ways). El resto
estaba como `building=yes` sin más contexto — el extractor los ignoraba porque
no encajaban en ninguna categoría específica (apartments, residential_subtypes,
commercial, office, industrial).

Esto reflejaba un patrón conocido de OSM: en regiones con cobertura sparse
(small-town LATAM, África, parte de Asia) la mayoría de los building footprints
están como `building=yes` por imports masivos sin enriquecimiento posterior.
Para esas zonas, una visualización de zoning honesta requería poder **inferir**
la zona de los footprints sin tipificar.

### Solución

Nuevo paso 8 del pipeline `extract-zoning`:

1. **Nueva query `generic_buildings`** que recoge `way["building"="yes"]` y
   `relation["building"="yes"]` del bbox.
2. **Dedup global por OSM id** — buildings ya capturados por queries
   específicas se ignoran (los tags específicos siempre ganan).
3. **Spatial join contra landuse polygons** — para cada generic building:
   - Construir un `STRtree` con los polígonos `landuse=*` ya extraídos por
     queries existentes (residential, commercial, retail, industrial, office).
   - Buscar el polígono que contiene el centroide del building.
   - Si hay match → clasificar por `LANDUSE_TO_CS2_KEY` (mapa landuse→CS2 key).
4. **Heurística de área como fallback** — si no hay landuse que lo contenga:
   - `< 300 m²`   → `res_low_house` (casa pequeña)
   - `300–1500 m²` → `res_med` (edificio mediano)
   - `≥ 1500 m²` → `industrial` (footprint grande sin contexto = nave/galpón)
   - Con pisos conocidos (`height` menos 2,5 m de techo, o `building:levels`), la
     altura manda (2026-11-02): mediano de 7+ pisos → `res_high`; grande de 4 a 6
     → `office_low`; grande de 7+ → `office_high`. Si el contorno no trae altura, se
     usa la `building:part` más alta cuyo punto interior cae dentro (las torres
     mapeadas en 3D llevan la altura en las partes). Sin esto, en Nueva York la Bolsa,
     el Woolworth y la Reserva Federal salían industria.

### Impacto medido (re-extract 2026-05-18 PM)

| City | v3.3.3 polygons | v3.3.4 polygons | Δ | generic+ (landuse / area) |
|------|-----------------|-----------------|---|---------------------------|
| Minneapolis | 81,825 | 204,470 | +150% | 122,633 (57k / 66k) |
| Amsterdam | 89,228 | 137,559 | +54% | 48,331 (42k / 6k) |
| Madison | 36,738 | 55,889 | +52% | 19,151 (17k / 2k) |
| Charleston | 14,495 | 31,957 | +120% | 17,461 (9k / 8k) |
| Trondheim | 40,339 | 43,499 | +8% | 3,160 (1.4k / 1.8k) |
| Mafra | 105 | 431 | +310% | 326 (4 / 322) |

**Lectura:** ciudades con landuse polygons granulares (US/EU) ganan
clasificación por spatial join (lo más confiable). Ciudades con landuse
sparse (LATAM small-town) dependen más de la heurística de área. En todas
las ciudades el delta es positivo — el algoritmo es defensivo (solo añade
buildings no clasificados antes; nunca sobreescribe).

### Diseño defensivo

- **Tags específicos siempre ganan**: si una way tiene `building=apartments`,
  pasa por `classify_apartment` y nunca llega al paso generic.
- **Cero falsos positivos en cities granulares**: en Mpls los apartments,
  houses, terraces, etc. ya están bien clasificados por su tag específico.
- **Honestidad de signal**: el output incluye `generic+` con breakdown
  landuse vs área heurística — el usuario puede ver qué fracción del map
  viene de inferencia.

Ver implementación: `src/zoning/extract.py` (`_process_generic_buildings`),
`src/zoning/classifiers.py` (`classify_generic_building_by_area`,
`LANDUSE_TO_CS2_KEY`).

---

## Sección 18 — External buildings augmentation: Google Open Buildings (v3.3.5)

### Problema

El generic-buildings pass de v3.3.4 extrajo el 100% de los `building=yes`
en Mafra (326 polygons clasificados) — y aun así la ciudad quedó con apenas
431 polygons totales. Causa: **OSM literalmente solo tiene 427 buildings
tagged en el bbox**. Mafra tiene ~55k habitantes; era estructuralmente
imposible que OSM contara más buildings sin contribución upstream.

### Solución: ingest ML-detected footprints

Las fuentes globales de building footprints ML-detectados (Microsoft, Google,
Overture) tienen **>1 billón de buildings** que NO están en OSM. Para zonas
con OSM sparse, son el complemento natural — geometrías sin tipo, exactamente
el input para el algoritmo v3.3.4.

Se elige **Google Open Buildings v3** sobre Microsoft Global por:
- Modelo ML más reciente (1.8B globales vs 1B de MS)
- Foco explícito en LATAM/África/SE-Asia (target del lanzamiento humanitario)
- Confidence scores por building (0.65–1.0) → permite filtrar ruido
- Licencia dual CC BY 4.0 + ODbL (más permisiva que solo ODbL)

### Pipeline (`extract-google-buildings`)

1. **S2 cell lookup**: calcula con `s2sphere` qué S2 cell L6 (~50–100k km²)
   toca el bbox. Para bboxes urbanos típicos, 1 cell suele bastar.
2. **Download cacheado**: trae los `<token>_buildings.csv.gz` de
   `storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header/`.
   Cache vive en `.cache/google_open_buildings/` (gitignored).
3. **Landuse polygons**: lee los polígonos de landuse
   (residential/commercial/industrial/office), las amenities cívicas y los
   buildings OSM para construir el STRtree del spatial join. Por defecto salen
   del PBF de la ciudad en una sola pasada (§23, `zoning.zones.build_pbf_filters`);
   con `--source overpass`, de las queries de `zoning.zones.build_queries`.
4. **Stream + filter**: parsea el CSV.gz línea por línea, descarta
   buildings fuera del bbox o con confidence < threshold (default 0.75), y
   los que ya están en OSM: su centroide cae dentro de un building OSM, o él
   contiene el centroide de uno (Google unió casas que OSM tiene separadas).
5. **Classify**: mismo algoritmo que `_process_generic_buildings` —
   spatial join contra landuse, fallback heurística de área.
6. **Output**: `visualizer/cities/<slug>/datos_external_buildings.json`
   (formato compacto, §9), con una capa por zona como zoning. Manifest
   gana entry `external_buildings` y se regeneran las teselas.

### Integración con el visualizer

Los edificios de Google van en las teselas de zonificación junto con los de
OSM (§8); sin teselas, `map.html` junta `DATA_<ZONE>` (OSM) y
`DATA_EXT_<ZONE>` (Google) por zona. Los polígonos Google llevan su fuente y
`conf`: el tip dice "Google Open Buildings" y la ficha le suma la confianza.
Los filtros de capas funcionan igual para los dos.

### Impacto medido (Mafra primero, 2026-05-18 PM)

| Métrica | OSM-only (v3.3.4) | + Google augment (v3.3.5) | Δ |
|---|---|---|---|
| Polygons totales | 431 | **35,552** | **+82×** |
| res_low_house | 182 | 33,428 | +33,246 |
| res_med | 113 | 1,798 | +1,685 |
| industrial | 51 | 241 | +190 |
| Por landuse spatial join | 4 (de 326) | +96 (de 35,121) | |
| Por área heurística | 322 | +35,025 | |
| File size | 28 KB | **11.8 MB** | 420× |
| OSM building density | 5.8/km² | 480/km² | 82× |

**Lectura:** Mafra ahora se ve poblada. El mapa muestra ~35.5k footprints
ML-clasificados, dominados por low-density housing (consistente con
small-town brasileña de viviendas <300 m²). Sin contribución a OSM,
la ciudad pasó de "casi vacía" a "densamente poblada" en 2 minutos de
runtime.

### Diseño defensivo

- **OSM siempre gana**: si una way tiene un building en OSM (cualquier
  valor de `building=*`), el módulo zoning ya lo capturó y Google no lo repite:
  el extractor lee los buildings OSM del bbox y descarta los de Google que caen
  sobre uno (paso 4). Hasta v3.4.4 este chequeo no existía; en Mafra no se
  notaba porque OSM tenía 431 polígonos, pero en Valparaíso habría dibujado
  27.7k edificios dos veces.
- **Confidence threshold opt-in**: el flag `--min-confidence` permite
  ajustar el filtro de ruido. Default 0.75 es conservador.
- **Source visible en la ficha**: el usuario puede distinguir OSM-derived
  de Google-ML en cualquier polígono. Honestidad sobre la incertidumbre.

### Casos de uso futuros

Cualquier city-request en zona OSM sparse:
- Latin America small-town
- Africa subsaharian urbanism
- SE Asia secondary cities
- Rural areas anywhere

El operador run-once `extract-google-buildings --city <slug>` añade el
módulo de ML buildings. El visualizer detecta el manifest y los renderiza.

Ver implementación: `src/zoning/extract_google_buildings.py` (script
nuevo + entry point `extract-google-buildings`).

Ver spec: `docs/specs/2026-05-17-featured-cities-pack-design.md`
Ver plan: `docs/plans/2026-05-17-featured-cities-pack.md`

---

## Sección 19 — Densidad residencial por altura y morfología (2026-10)

### Problema

En ciudades europeas casi todo salía `res_low_house`: en Amberes, el 93% de los
items. Los edificios residenciales sin tipo (`building=yes` dentro de
`landuse=residential`, los chicos clasificados por área) y los `building=house`
caían a casa baja sin mirar la altura ni si estaban pegados a otros. En Amberes
(import GRB) las casas en hilera y los edificios del casco antiguo son
`building=house` o `building=yes`. Lo señaló u/Pamani_ en r/CitiesSkylines2.

### Solución

Dos pasadas al final de la clasificación, solo sobre esos candidatos
(`_refine_residential_density` en `src/zoning/extract.py`, geometría en
`src/zoning/morphology.py`, umbrales en `src/zoning/morphology_config.py`):

1. **Altura** (`method="height"`). Niveles efectivos = max(`building:levels`,
   (`height` − 2,5 m) / 3, al menos 1): la altura medida llega a lo alto del techo
   (ver «Calibración de la altura con catastro»). `building=yes`: 3 o más → `res_med`;
   `building=house`: 4 o más (una casa de 3 pisos sigue siendo casa); 7 o más →
   `res_high`. Con un comercio adentro, `res_mixed` en vez de `res_med`. Un edificio
   pegado a sus vecinos (`shared_frac` ≥ 0,25, con el contexto completo), de hasta 3
   pisos y hasta 150 m², va a `res_row` (`method="morphology"`) aunque la altura llegue
   a media.
2. **Morfología** (`method="morphology"`), para los que no tienen altura. Se mide
   sobre la geometría original de OSM, no la publicada (que se redondea a ~1,1 m):
   - `shared_frac`: fracción del contorno a menos de 0,5 m de otro edificio, con
     tramos de al menos 3 m (una esquina que se toca en un punto no cuenta). Los
     garajes, cobertizos y similares no cuentan como pared compartida.
   - `coverage`: área de los edificios cuyo punto representativo cae a 60 m o menos
     del centroide, sobre el área del círculo (aproximación sin recorte, mucho más
     rápida que recortar cada círculo). Solo se calcula para los adosados.
   - Adosado (`shared_frac` ≥ 0,25) con `coverage` ≥ 0,45 → `res_med` (`res_mixed`
     si hay un nodo `shop`/`amenity` comercial adentro); con `coverage` entre 0,20 y
     0,45 → `res_row` si el footprint mide hasta 250 m², `res_med` si es más grande.
     Si no, no cambia.
   - Con altura conocida pero baja (por ejemplo, una casa de 2 pisos), la morfología
     solo puede llevarla a `res_row`.

Para el contexto se leen dos fuentes nuevas que no agregan items:
`morphology_buildings` (todo `building=*`, para que escuelas, galpones y
comercios cuenten como suelo construido) y `morphology_commercial_nodes`.

**Protecciones:** `detached` y `bungalow` nunca cambian, tampoco lo que ya tenía otra
clave por tag, los polígonos de landuse ni los items con `method="amenity"`. La
morfología se abstiene a menos de 60 m del borde del bbox (contexto incompleto) y en
relaciones cuyos anillos no se pueden reconstruir; la altura no, porque no depende
de los vecinos.

`pbf_client` ahora entrega todos los anillos de una relación (el exterior más grande
primero), así los consumidores que leen el primer `outer` siguen viendo la misma forma.

### Calibración

`extract-zoning --morphology-report <csv>` escribe una fila por candidato con las
métricas, la clave vieja y la nueva y el motivo. Los umbrales iniciales no hicieron
falta moverlos. Reparto residencial antes/después sobre el mismo extracto de OSM
(baja / hilera / media / mixta / alta):

| Ciudad | Antes | Después | Casa baja |
|---|---|---|---|
| Amberes | 116.857 / 470 / 3.139 / 114 / 140 | 23.064 / 51.558 / 43.164 / 2.587 / 347 | 93% → 18% |
| Beverlo | 44.119 / 7 / 887 / 12 / 0 | 40.009 / 3.657 / 1.276 / 83 / 0 | 94% → 85% |
| Kiel | 38.096 / 3.175 / 16.096 / 344 / 227 | 33.526 / 7.512 / 16.296 / 371 / 233 | 59% → 52% |
| Minneapolis (control) | 165.371 / 1.986 / 6.715 / 43 / 147 | 164.874 / 2.348 / 6.834 / 47 / 159 | 87% → 87% |

En Amberes, a 400 m de la Grote Markt quedan 691 de densidad media y 311 mixtos
sobre 1.168 candidatos; en Wilrijk (suburbio), 628 en hilera y 155 casas bajas sobre
867. En Minneapolis cambia el 0,3% de los candidatos.

### Calibración de la altura con catastro (2026-10-30)

Al volver a extraer Filadelfia, la pasada de altura mandó a `res_med` el 82% de lo
residencial. Son `building=yes` con `height` LiDAR y sin `building:levels`, y
`height / 3` contaba un piso de más: la altura medida llega a lo alto del techo. Se
midió contra el catastro de cada ciudad, cruzando cada candidato con el lote más cercano
a 15 m o menos: OPA en Filadelfia (tipo de construcción, como "ROW 2 STY" o "SEMI/DET")
y PLUTO en Nueva York (clase de edificio, pisos y si está pegado). Cuenta como acierto
que una hilera o un mellizo salga `res_row` (`semi` ya va a hilera), una casa aislada
`res_low_house`, un edificio de 5 o más departamentos `res_med` y uno con local
`res_mixed`. En los dos catastros, los edificios de 2, 3 y 4 pisos miden ~8,5, ~11,7 y
~14,8 m (medianas).

| Regla | Filadelfia | Nueva York |
|---|---|---|
| Antes: `height` / 3 | 13,1% | 42,7% |
| Hilera si está pegado, con ≤ 3 pisos (`height` / 3) y ≤ 250 m² | 67,3% | 62,1% |
| La misma hilera, contando 4 m por piso | 83,9% | 61,5% |
| Solo descontar el techo: (`height` − 2,5 m) / 3 | 58,7% | 64,9% |
| Techo + hilera de ≤ 3 pisos y ≤ 150 m² (la que quedó) | 80,8% | 67,0% |

La de 4 m por piso acierta más en Filadelfia, pero deja en `res_med` las casas aisladas
de 2 pisos con techo a dos aguas y manda a hilera más edificios de departamentos de Nueva
York. Con la que quedó, las hileras de 2 pisos pasan del 14% al 88% en Filadelfia y del
31% al 92% en Nueva York; las de 3 pisos, del 5% al 69% y del 2% al 68%; las casas
aisladas de 2 pisos quedan en baja densidad en el 73% y el 80% (antes, 21% y 29%). En
Nueva York 1.945 zonas dejan de ser `res_high`, y según PLUTO el 97% tiene 6 pisos o
menos. El costo: de los edificios sin ascensor de 5 o más familias de Nueva York quedan
en `res_med` el 61% (antes, 80%). Para eso está el tope de 150 m²: las hileras miden
54–109 m² (p10–p90) y esos edificios, 92–179 m².

Reparto residencial (baja / hilera / media / mixta / alta) sobre el mismo extracto:

| Ciudad | Antes | Después |
|---|---|---|
| Filadelfia | 11.338 / 28.865 / 193.810 / 741 / 394 | 24.882 / 176.810 / 32.554 / 632 / 270 |
| Nueva York | 27.677 / 24.857 / 93.354 / 8.045 / 6.714 | 33.257 / 63.582 / 51.184 / 7.855 / 4.769 |
| Amberes | 23.085 / 51.551 / 43.188 / 2.590 / 347 | 23.093 / 51.811 / 42.954 / 2.614 / 289 |
| Kiel | 33.510 / 7.515 / 16.317 / 374 / 232 | 33.510 / 7.525 / 16.307 / 374 / 232 |

Beverlo y Minneapolis no cambian. El cruce es por cercanía, así que algún edificio queda
con el lote del vecino (distancia mediana: 2,5 m en Filadelfia y 4,4 m en Nueva York).

### Rendimiento

El paso nuevo tardó 21 s en Amberes (117 mil candidatos), 10 s en Beverlo y 14 s
en Kiel, con varias extracciones en paralelo. Benchmark sintético de 190 mil
footprints (`tests/zoning/benchmark_morphology.py`): 6 s suburbano, 21 s denso. Lo
que más tarda en una ciudad europea sigue siendo leer el PBF del país.

### Límites

Sin altura, la forma en planta no distingue una hilera de 2 pisos de una de 5: el corte
entre `res_row` y `res_med` es la cobertura del entorno. Las alturas de Copernicus GHSL
(etapa 2 del [plan](docs/plans/2026-09-24-densidad-residencial-morfologia.md)) quedan
pendientes.

El descuento del techo se usa solo en esta pasada: `classify_apartment`,
`classify_commercial` y `classify_office` siguen contando `height` / 3
(`_effective_levels` sin `roof_m`, en `src/zoning/classifiers.py`).

Los edificios de Google Open Buildings (Mafra, Valparaíso y La Plata, §18) quedan fuera
de esta pasada: `extract-google-buildings` los clasifica solo por el landuse que los
contiene, por una amenity cívica a 30 m o menos (que los manda a `com_low`) o por el
área.

Las ciudades toman cada cambio al volver a extraerlas. Esta pasada (la etapa 1 del plan)
la tienen las 43 ciudades extraídas desde el 2026-10-01, empezando por Amberes, Beverlo,
Kiel y Minneapolis; las 34 anteriores la toman al volver a extraerse. El descuento del
techo y la hilera de hasta 150 m² (v3.6.1) están en Filadelfia, Nueva York, Amersfoort y
Reston; las demás ciudades con alturas medidas los toman al actualizarse. La lista por
ciudad está en [densidad pendiente](docs/plans/2026-11-02-densidad-pendiente.md).

---

## Sección 20 — Official zoning layer (2026-05-24)

OSM-derived zoning is land use detection (what physically exists). For cities
that publish their official zoning maps, the toolkit offers an alternative
layer sourced from city open data portals. The Zoning block of the layer column
then switches between `OSM-derived` and `Official plan` and, since v3.6.0, `Compare`.
Compare keeps the OSM zones as the fill and draws the plan's districts on top
as outlines in their zone colour. The switch only appears in cities with a
published plan (today, Minneapolis).

### Pluggable architecture

Each supported city declares a Python `Source` module in
`src/official_zoning/sources/` + a YAML mapping table in
`src/official_zoning/mappings/`. Adding a new US city is one source module +
one YAML; no core refactor.

### Pipeline

1. Download shapefile from city open data portal (cached in `~/.cache/cs2-osm-toolkit/official_zoning/`)
2. Parse with geopandas + pyogrio
3. Reproject to WGS84 (EPSG:4326)
4. Spatial filter by city bbox (from `cities.json`)
5. Translate native zoning codes to 13 CS2 zone keys via YAML mapping
6. Emit `visualizer/cities/<slug>/datos_zonificacion_official.js`
7. Register module in per-city `manifest.json`

### Sources

- **Minneapolis** (published): the land use of the Minneapolis 2040 Plan
  ("Planning Primary Zoning" on the city's open data portal), not the
  Chapter 530 zoning code. `src/official_zoning/mappings/minneapolis.yaml`
  maps its 15 land use categories to CS2 zones.
- **New York**: the source module (NYC Zoning Resolution / ZoLA,
  `src/official_zoning/sources/new_york.py`) and its mapping are in the
  pipeline, but the layer is not published yet.

### Known limitation

The `DATA_URL` constants in source modules need human-loop verification
against the live portals (CDNs block automated URL discovery). On 2026-11-02
neither one downloads: Minneapolis's is a placeholder dataset id (the portal
answers HTTP 500) and New York's answers HTTP 404. To activate: open the
portal in a browser, capture the resolved shapefile URL from DevTools, update
the constant, and re-run the extraction CLI. The full pipeline is tested with
mocked GeoDataFrames; the network path is exercised opt-in via `pytest -m network`.

---

## Sección 21 — Transit overlay (2026-05-25)

A 4-category transit overlay sourced from OpenStreetMap route relations.
A single Overpass query fetches all `route=light_rail|train|tram|bus`
relations in the city bbox; each relation becomes one polyline (multi-way
relations are concatenated where members touch; disjoint segments emit the
longest continuous piece). Transit has no PBF mode (§23): it always reads Overpass.

### Category mapping

| OSM route | Name hint | CS2 category |
|---|---|---|
| `light_rail` | — | LRT |
| `tram` | — | LRT (display) |
| `train` / `commuter_rail` | — | Commuter Rail |
| `bus` | `name` contains ` Line` (`Metro Transit A Line`) or is a colour (`Red`, `Orange`, `Gold`) | BRT |
| `bus` | (other) | Bus |

Metro Transit tags every route `network=Metro Transit` in OSM (never `METRO`),
so BRT is detected by the shape of the name (`_is_metro_brt` in
`src/transporte/classifiers.py`). The first version keyed on `network=METRO` or
a `METRO X Line` name and filed the BRT lines under Bus; that was fixed on
2026-05-31.

### Sources shipped

Minneapolis: 297 route relations for the city bbox (OSM often maps each
direction as its own relation). 5 are LRT, 4 commuter rail (Amtrak's Empire
Builder), 12 BRT (the A to E Lines and the Orange Line, two relations each) and
276 bus, with 202 route numbers from Metro Transit and other operators.

### Activation

The viewer adds a Transit block to the layer column only when the city's
manifest declares the `transporte` module (today, only Minneapolis).
`datos_transporte.js` loads after the first paint. `transporteLoaded()` then
builds a GeoJSON source with one line per route, and the block starts the way
it was left last time (Off on a first visit). If the file can't load, the block
says so and asks for a reload.

### Performance note

The Mpls `datos_transporte.js` is ~4 MB (297 routes with full member geometry).
Lazy-loaded after primary render so it doesn't block initial paint. Future
optimization options: coordinate decimation, way-filtering by relevant network,
or removing routes that fall outside the visible bbox.

---

## Sección 22 — Infraestructura (2026-05-31)

`src/infraestructura/` cubre el apartado de utilities de CS2 (electricidad, agua,
basura y comunicaciones) con datos de OSM. Como transporte, no tiene modo PBF: una
sola query Overpass (`build_infraestructura_query`, en `zones.py`) trae del bbox los
nodos, ways y relaciones con los tags de la tabla de abajo, con su geometría. La query
es amplia (trae todos los `man_made=mast|tower` y todos los `amenity=recycling`) y el
clasificador filtra. Hoy lo tiene solo Minneapolis.

### Clasificación

`classify_infra(tags)` (`classifiers.py`) devuelve categoría y subtipo con una tabla
de tags, sin heurísticas:

| Categoría (en el visor) | Tags OSM → subtipo | Minneapolis |
|---|---|---|
| `power` (Electricity) | `power=plant` → `generacion`; `power=substation\|transformer` → `subestacion`; `power=line\|minor_line` → `transmision` | 253 |
| `water` (Water & Sewage) | `man_made=water_tower\|water_works\|pumping_station\|water_well\|reservoir_covered` → `suministro`; `man_made=wastewater_plant` → `aguas_residuales` | 38 |
| `waste` (Garbage) | `landuse=landfill`, `amenity=waste_transfer_station` o `man_made=incinerator` → `disposicion`; `amenity=recycling` con `recycling_type=centre` → `reciclaje` | 15 |
| `telecom` (Communications) | `man_made=communications_tower`, o `mast`/`tower` con `tower:type=communication` → `torre`; `telecom=data_center` → `data_center` | 65 |

Se descartan los pilones, los postes, los cables subterráneos y `power=generator` (en
OSM suele ser cada panel solar; las plantas son `power=plant`), los contenedores de
reciclaje de la calle y los mástiles que no son de telecomunicaciones. Las cañerías de
agua y cloacas no se piden: van bajo tierra y casi no están en OSM.

### Geometría y salida

Un nodo es un punto y un way cerrado, un polígono. Un way abierto de transmisión es una
línea (en una relación, su member way más largo); otro way abierto queda como punto en
su primer nodo, y otra relación, como el polígono de su primer anillo exterior. Sin
`name`, el nombre es el `operator` o, por ejemplo, «Electricidad sin nombre».

La salida es `datos_infraestructura.js` (`DATA_INFRA_POWER`, `_WATER`, `_WASTE` y
`_TELECOM`) más la entrada `infraestructura` del manifest. El visor lo carga después
del primer dibujo, como transporte (§21), y lo dibuja como fuente GeoJSON (§8):
polígonos al 25%, líneas de 2 px y puntos como círculos, con el color de cada
categoría. En la columna de capas, el bloque se llama Utilities.

- **Diseño:** [`docs/specs/2026-05-31-infraestructura-design.md`](docs/specs/2026-05-31-infraestructura-design.md)
- **Plan:** [`docs/superpowers/plans/2026-05-31-infraestructura.md`](docs/superpowers/plans/2026-05-31-infraestructura.md)
- **Tests:** `tests/infraestructura/`

---

## Sección 23 — Extracción desde PBF (v3.4.0)

Desde la v3.4.0, `extract-zoning`, `extract-vial`, `extract-services` y
`extract-google-buildings` leen por defecto un extracto regional de OSM (`.osm.pbf`)
en vez de consultar Overpass: lo bajan de Geofabrik, lo guardan en una caché y lo
leen en la máquina, sin los timeouts de §1. `--source overpass` sigue andando.
Transporte (§21) e infraestructura (§22) no tienen modo PBF.

### Descarga y caché

`src/shared/pbf_cache.py`. Cada ciudad declara en `cities.json` su `pbf_region`, la
región de Geofabrik (`"north-america/us/minnesota"`). `ensure_pbf()` la baja de
`download.geofabrik.de` a `~/.cache/cs2-osm-toolkit/pbf/`, con el nombre
`north-america-us-minnesota-latest.osm.pbf`, y escribe primero un `.part` para no
dejar un archivo a medias. Si el archivo de la caché tiene menos de 7 días (por fecha
de modificación), lo reusa; si no, lo vuelve a bajar. `--refresh-pbf` fuerza la
descarga. Las ciudades de una misma región comparten el archivo.

### Lectura

`src/shared/pbf_client.py`. Los `zones.py` de zonificación, calles y servicios tienen,
al lado de sus queries Overpass, filtros estructurados (`build_pbf_filters`,
`build_vial_pbf_filter` y `build_services_pbf_filter`, con los tipos de
`src/shared/pbf_filters.py`: cláusulas de tags por tipo de elemento y spatial joins
como el de §4). pyosmium recorre el archivo una vez, resuelve las coordenadas, arma
los multipolígonos y devuelve los elementos con la misma forma que Overpass, así que
la clasificación no cambia. Un way entra si tiene algún nodo dentro del bbox, y una
relación, si lo tiene alguno de sus anillos exteriores. `query_batch()` aplica todos
los filtros de la zonificación en esa única pasada.

### Varias regiones

Si la caja cruza el borde de un extracto, `pbf_region` es una lista (Amersfoort:
`["europe/netherlands/utrecht", "europe/netherlands/gelderland"]`). `extract-zoning`
lee cada PBF y `merge_batch_results()` junta los resultados: los extractos traen
enteras las vías que cruzan su borde, así que un mismo elemento puede venir de los dos,
y queda una sola vez por (tipo, id). `extract-vial`, `extract-services` y
`extract-google-buildings` todavía aceptan una sola región. Antes de bajar nada,
`process-cities` revisa que cada caja caiga dentro de sus regiones, con los contornos
del índice de Geofabrik (`index-v1.json`, cacheado como los PBF).
