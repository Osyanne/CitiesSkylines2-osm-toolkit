# CS2 OSM Toolkit

> Real-world GIS data from OpenStreetMap → Cities: Skylines 2
> Modular toolkit · 100% open source · Zero API keys · Interactive dark map

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/License-MIT-green)
![OSM Data](https://img.shields.io/badge/Data-OpenStreetMap-orange)
![Tests](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/actions/workflows/test.yml/badge.svg)

> 🇪🇸 Versión en español: [README.es.md](README.es.md)

---

## Cities

**28 cities** across 14 countries, ready to explore in the browser with nothing to install:

**https://osyanne.github.io/CitiesSkylines2-osm-toolkit/**

| City | Country | Layers |
|------|---------|--------|
| Amsterdam | Netherlands | Zoning |
| Antwerp | Belgium | Zoning |
| Atlanta, GA | USA | Zoning |
| Bacău | Romania | Zoning |
| Beverlo | Belgium | Zoning |
| Butterworth, Penang | Malaysia | Zoning |
| Charleston, SC | USA | Zoning |
| Chicago, IL | USA | Zoning, roads, services |
| Cincinnati, OH | USA | Zoning |
| Denton, TX | USA | Zoning |
| Drammen | Norway | Zoning |
| Fayetteville, NC | USA | Zoning |
| Hollister, CA | USA | Zoning |
| Hong Kong | Hong Kong | Zoning |
| Kiel | Germany | Zoning |
| Køge | Denmark | Zoning |
| Kursk | Russia | Zoning |
| Little Rock, AR | USA | Zoning |
| Łódź | Poland | Zoning |
| Madison, WI | USA | Zoning |
| Mafra, SC | Brazil | Zoning, Google building footprints |
| Minneapolis, MN | USA | Zoning, roads, services, transit, official zoning, infrastructure |
| New York, NY | USA | Zoning |
| Pittsburgh, PA | USA | Zoning |
| Sacramento, CA | USA | Zoning |
| Trondheim | Norway | Zoning |
| Valparaíso | Chile | Zoning |
| Yogyakarta | Indonesia | Zoning |

Every city has zoning. Minneapolis and Chicago also have roads and services, and Minneapolis adds transit, official zoning and infrastructure on top.

### Adding your city

Open a [City Request issue](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues/new?template=city-request.yml) with the bbox + name. We'll generate the zoning and publish it, and you'll get a reply in the issue once it's live.

---

## Quick Start — Pick Your Path

### Path A: Just look at the maps

Two options:

**Option 1 — Hosted (zero setup, no install):** Visit https://osyanne.github.io/CitiesSkylines2-osm-toolkit/ in your browser. Click any of the 5 city cards to open the map.

**Option 2 — Local clone (need any tiny HTTP server):** Clone the repo, then serve the `visualizer/` folder over HTTP:

```bash
cd cs2-osm-toolkit/visualizer
python -m http.server 8000
```

Open `http://localhost:8000/` in your browser. Every city's data is included in the repo, so there's nothing extra to download.

> **Why HTTP and not just double-click?** The map viewer uses `fetch()` to load the city registry and per-city manifest. Browsers block `fetch()` from `file://` URLs by default (CORS policy), so opening `index.html` directly with double-click shows the landing but city maps fail to load. Any tiny HTTP server works — Python's built-in (above), Node's `http-server`, or VS Code's Live Server extension.

### Path B: Use it for your city (15–20 minutes, requires Python)

Full step-by-step walkthrough: [docs/QUICKSTART.md](docs/QUICKSTART.md).

The short version:
1. Install Python 3.11+ with "Add to PATH" checked, then install uv
2. Open a terminal in the `src/` folder and run `uv sync`
3. Add your city to `cities.json` at repo root with bbox, then run:

        uv run extract-zoning --city your_slug
        uv run extract-vial --city your_slug      (optional)
        uv run extract-services --city your_slug  (optional)

4. Run `uv run generate-landing` to update the landing page

5. (Optional) Generate a city card thumbnail for the landing page:

        uv sync --group thumbnails               # one-time install (~300 MB Chromium)
        uv run --group thumbnails playwright install chromium   # one-time
        uv run --group thumbnails generate-thumbnails           # auto-detects missing

   `generate-thumbnails` reads `cities.json`, navigates to the deployed map URL per city, hides UI chrome, and saves a 1200×800 PNG to `visualizer/assets/thumbnails/<slug>.png`. Run with `--city <slug>` for a specific one, `--force` to regenerate all, or `--base-url http://localhost:8080` to target a local dev server.

For ad-hoc one-off extracts without modifying `cities.json`, use the escape hatch: `uv run extract-zoning --bbox "south,west,north,east" --slug your_slug` (both flags required together).

**Common issues?** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

---

## Data source: PBF (default in v3.4+) vs Overpass (legacy)

Starting with **v3.4.0**, all extractors read from local `.osm.pbf` files
downloaded from [Geofabrik](https://download.geofabrik.de/) by default,
instead of the Overpass API.

**Why:** PBF extraction is faster per city, has no rate limits, is fully
reproducible (same PBF + same bbox = same output), and doesn't consume shared
community resources. The OSM community explicitly discourages using Overpass
for bulk extraction; Geofabrik PBFs are the recommended path.

**How it works:**

1. Each city in `cities.json` declares its Geofabrik region:

   ```json
   "minneapolis": {
       ...existing fields...,
       "pbf_region": "north-america/us/minnesota"
   }
   ```

2. The first extraction of a city downloads the regional PBF to
   `~/.cache/cs2-osm-toolkit/pbf/` (cached for 7 days, then refreshed).

3. Subsequent extractions of any city in the same region reuse the cache.

**Storage:** A US state PBF is ~30 MB; a country is 100 MB – 2 GB. Plan
accordingly.

**Refresh cache manually:**

```bash
uv run extract-zoning --city minneapolis --refresh-pbf
```

**Force the legacy Overpass mode** (not recommended; will be removed in v4.0.0):

```bash
uv run extract-zoning --city minneapolis --source overpass
```

**Performance (measured, v3.4.0):** Single-pass batched extraction via
`query_batch` (introduced mid-v3.4 dev). Minneapolis zoning extraction
(`extract-zoning --city minneapolis --source pbf`) on a cached 262 MB Minnesota
PBF: **~19 minutes** for 10 source categories producing 204k classified
polygons. Compare to Overpass which typically runs 5-15 min but is more
variable (retries, throttling, timeouts) and consumes shared OSM community
infrastructure. First-run adds ~30-60 sec for the PBF download.

### Path C: Develop or contribute

Clone the repo, run `uv sync` inside `src/`, run tests with `uv run pytest`. All technical details below.

---

## What This Does

A modular toolkit that extracts real-world infrastructure data from OpenStreetMap via the Overpass API and renders it on an interactive dark-mode map (MapLibre GL, drawn from vector tiles on the GPU). Built as a reference layer for players recreating Minneapolis 1:1 in Cities: Skylines 2. Three modules, ~192k total features.

### 🗺 Zoning Module
Classifies all building polygons into the **11 official Cities: Skylines 2 zone types** (Low/Medium/High Density Residential, Row Housing, Mixed Housing, Low Rent Housing, Low/High Density Business, Low/High Density Offices, Industrial Manufacturing). 81,732 polygons in the Minneapolis bbox.

Run: `cd src && uv run extract-zoning --city minneapolis`
Output: `visualizer/cities/minneapolis/datos_zonificacion.json` (~12 MB, compact format)

### 🛣 Road Network Module
Classifies all OSM roads into the **6 CS2 road categories** (Highway, Major Road, Minor Road, Local Street, Pedestrian Path, Bike Lane). Renders as LineString overlay. 108,825 features.

Run: `cd src && uv run extract-vial --city minneapolis`
Output: `visualizer/cities/minneapolis/datos_vial.json` (~6 MB, compact format)

### 🏥 Services Module
5 layers aligned to the base service tabs of Cities: Skylines 2 with good OpenStreetMap coverage:

- **H** Healthcare & Deathcare — hospitals, clinics, doctors, funeral directors, crematoriums, cemeteries
- **E** Education & Research — schools, universities, colleges, kindergartens, research institutes
- **B** Fire — fire stations
- **A** Police & Administration — police HQ, city hall, courthouses, prison + cultural landmarks (libraries, museums, theatres, arts centres, cinemas) + government offices
- **P** Parks — parks, nature reserves, gardens, playgrounds, sports centres

Run: `cd src && uv run extract-services --city minneapolis`
Output: `visualizer/cities/minneapolis/datos_servicios.js` (~1.3 MB)

**Notes:**
- Libraries, museums, theatres, arts centres, cinemas share the `admin` bucket with police and government offices. They differ only by name + subtype in the popup.
- Places of worship intentionally excluded (not in CS2 base game structure).
- Electricity, water & sewage, waste management deferred to Session 4 (require EIA + MN GIS Commons + opendata.minneapolismn.gov sources, not OSM).
- Minneapolis bbox typically returns ~2,300 features. Async chunked rendering prevents browser blocking during init.

### Coming next
- 🚌 Transit Module (Blue/Green Line, BRT, bus routes, bikeways) — Session 4

---

## Visualizer Features

- **Module pills (top right)**: toggle entire modules on/off in one click
- **Master toggles in legend**: same effect, mirrored in the sidebar
- **Background mode** (when modules are off): Hidden / Faded / Full
- **Layer Control** (top right): granular per-zone / per-road-category toggles
- **Canvas renderer**: smooth pan/zoom with 80k+ polygons + 108k linestrings
- **Tier-based hiding**: individual houses hide at zoom <14, blocks stay visible
- **CS2-faithful color palette**: 4 families (green/blue/purple/yellow) aligned to the game HUD
- **Dark theme**: CartoDB Dark Matter basemap
- **Persistence**: view state saved to localStorage (`cs2-view-state-{slug}-v1`, scoped per city)

## Official zoning overlay (experimental)

For cities with public planning data, the visualizer offers an authoritative
zoning overlay sourced from the city's open data portal — selectable via a
sub-toggle inside the Zoning legend (OSM-derived ↔ Official ↔ Comparison).

| City | Source | Categories |
|---|---|---|
| Minneapolis | City of Minneapolis Planning | ~25 |
| New York | NYC Department of City Planning (ZoLA) | ~70 |

### Generating official zoning data

The pipeline is implemented and tested, but the upstream `DATA_URL` constants
in `src/official_zoning/sources/<city>.py` need verification against the live
portal before extraction works (portal CDNs block automated discovery).

Quick start:

1. Open the city's open data portal in a browser:
   - Mpls: https://opendata.minneapolismn.gov/datasets/planning-primary-zoning
   - NYC: https://www1.nyc.gov/site/planning/data-maps/open-data/dwn-gis-zoning.page
2. Click the shapefile download link; capture the resolved URL via DevTools Network tab.
3. Update `DATA_URL` in `src/official_zoning/sources/<city>.py`. Bump `last_validated` in `src/official_zoning/mappings/<city>.yaml`.
4. Run extraction:
   ```bash
   cd src
   uv run extract-official-zoning --city minneapolis
   ```
5. Manifest auto-updates with the new module entry. Re-run `uv run generate-landing` to refresh the landing.

Adding a new city = one source module in `src/official_zoning/sources/<slug>.py` + one mapping YAML in `src/official_zoning/mappings/<slug>.yaml` + `official_source` entry in `cities.json`. See Minneapolis as the reference pattern.

## Transit overlay (Minneapolis)

The Mpls visualizer renders the Metro Transit network as a 4-category overlay,
sourced from OSM route relations:

| Category | Source | Mpls routes |
|---|---|---|
| LRT | OSM `route=light_rail` | METRO Blue Line, Green Line |
| Commuter Rail | OSM `route=train` | Northstar |
| BRT | OSM `route=bus` + METRO Rapid pattern | METRO A/C/D/E/F Line |
| Bus | OSM `route=bus` (rest) | ~140 local Metro Transit routes |

Generate transit data for a city (Mpls works out of the box; other cities depend on
their OSM transit coverage):

```bash
cd src
uv run extract-transporte --city minneapolis
```

The visualizer auto-detects the new module via the manifest and activates the
"Transporte" tile in the HUD.

**Update (2026-05-31):** The BRT classifier originally keyed on `network=METRO`
/ name `METRO X Line`, but real OSM data tags everything `network=Metro Transit`
and names the lines `Metro Transit A Line` / `Orange`. Fixed by detecting BRT via
name/ref shape (`" Line"` + colour names) — METRO A-E + Orange now classify as BRT.

## Infrastructure overlay (Minneapolis)

The Mpls visualizer renders real utility infrastructure as a 4-category overlay,
sourced from OSM (`power=*`, `man_made=*`, `landuse=landfill`, `amenity=recycling`),
mirroring the utilities section of Cities: Skylines 2:

| Category (label) | OSM source | Geometry |
|---|---|---|
| `power` / Electricidad | `power=plant` (generación) · `power=substation`/`transformer` (subestaciones) · `power=line`/`minor_line` (transmisión) | points · polygons · **lines** |
| `water` / Agua y Alcantarillado | `man_made=water_tower`/`water_works`/`pumping_station`/`water_well`/`reservoir_covered` · `wastewater_plant` | points · polygons |
| `waste` / Basura | `landuse=landfill` · `amenity=waste_transfer_station` · `man_made=incinerator` · `amenity=recycling` (`recycling_type=centre`) | points · polygons |
| `telecom` / Comunicaciones | `man_made=communications_tower` · `mast`/`tower` con `tower:type=communication` · `telecom=data_center` | points |

Generate infrastructure data for a city (Mpls works out of the box):

```bash
cd src
uv run extract-infraestructura --city minneapolis
```

The visualizer auto-detects the new module via the manifest and activates the
"Infraestructura" tile in the HUD. Excluded as clutter: pylons/poles
(`power=tower`/`pole`), individual rooftop solar (`power=generator`), street
recycling bins (`recycling_type=container`), and underground cables.

---

## Technical Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (faster pip+venv replacement)

### Setup

```bash
git clone https://github.com/Osyanne/CitiesSkylines2-osm-toolkit.git
cd cs2-osm-toolkit/src
uv sync
```

### Prebuilts (already in the repo)

The prebuilt `datos_*` files for every city are **committed in `visualizer/cities/<slug>/`**. No download needed.

Zoning, roads and Google buildings use a compact, lossless JSON format (`datos_*.json`, about a quarter of the old `.js` size — see [METHODOLOGY.md §9](METHODOLOGY.md)). If you have cities generated with an older version, convert them once with `cd src && uv run convert-legacy-data` (or `--city <slug>`).

The map does not download those files whole: it draws zoning and roads from **vector tiles** in `visualizer/cities/<slug>/tiles/`, so the browser only fetches what is on screen, simplified for the current zoom. `extract-zoning`, `extract-vial` and `extract-google-buildings` rebuild the tiles on their own; to rebuild them by hand run `cd src && uv run build-tiles` (or `--city <slug>`). Cities without tiles still open — the viewer falls back to the full data files. See [METHODOLOGY.md §8](METHODOLOGY.md).

**To regenerate fresh data** (e.g., after OSM updates):

```bash
cd src
uv run extract-zoning --city minneapolis    # ~3-5 min
uv run extract-vial --city minneapolis      # ~30s
uv run extract-services --city minneapolis  # ~1 min
```

Replace `minneapolis` with any slug from `cities.json` (`chicago`, `amsterdam`, `new_york`, `lodz`). Each extract updates the manifest preserving other modules.

### Serve the visualizer

```bash
cd visualizer
python -m http.server 8000
# Open http://localhost:8000/ (landing) or http://localhost:8000/map.html?city=minneapolis (direct map)
```

### Run tests

```bash
cd src
uv run pytest
```

171 tests passing across zoning, vial, and services modules.

---

## Project Structure

```
cities.json                   # Multi-city registry (bbox, center, zoom, metadata)

src/
├── shared/
│   ├── overpass_client.py    # Overpass API client with retry + endpoint rotation
│   ├── registry.py           # Reads cities.json; resolves --city <slug> to bbox
│   └── landing.py            # generate-landing CLI (rebuilds visualizer/index.html)
├── zoning/
│   ├── zones.py              # CS2 zone model + Overpass queries
│   ├── classifiers.py        # OSM tag → CS2 zone classifier
│   ├── extract.py            # CLI pipeline (entry: extract-zoning)
│   └── patch_colors.py       # Color palette utility
├── vial/
│   ├── zones.py              # CS2 road model + Overpass query
│   ├── classifiers.py        # OSM highway tag → CS2 road category
│   └── extract.py            # CLI pipeline (entry: extract-vial)
└── services/
    ├── zones.py              # CS2 service model + Overpass queries (5 buckets)
    ├── classifiers.py        # OSM tags → H/E/B/A/P bucket classifier
    └── extract.py            # CLI pipeline (entry: extract-services)

tests/
├── zoning/                   # 84 tests
├── vial/                     # 33 tests
└── services/                 # 54 tests
                              # 171 total

visualizer/
├── index.html                # Landing page, gallery of city cards
├── map.html                  # Map viewer — loaded as map.html?city=<slug>
├── cities.json               # Deployment artifact (copy of root cities.json)
├── cities/
│   ├── minneapolis/          # every module: zoning, roads, services, transit, official zoning, infrastructure
│   ├── chicago/              # datos_zonificacion.json + datos_vial.json + datos_servicios.js + tiles/ + manifest.json
│   └── <slug>/               # datos_zonificacion.json + tiles/ + manifest.json (one folder per city in cities.json)
└── assets/
    └── thumbnails/           # <slug>.png, one per city

docs/
├── QUICKSTART.md             # ELI5 guide for non-technical users
├── TROUBLESHOOTING.md        # Common errors and fixes
├── adapting-to-other-cities.md
├── bbox-mcp-server.md
├── cs2-zone-reference.md
├── github-publishing.md
├── plans/                    # Session implementation plans
└── specs/                    # Design specs

.github/
└── ISSUE_TEMPLATE/
    └── city-request.yml      # City request issue template
```

---

## Project Stats

| | |
|---|---|
| **Modules** | Zoning in all 28 cities. Roads and services in Minneapolis and Chicago. Transit, official zoning and infrastructure in Minneapolis. Google building footprints in Mafra. |
| **Bounding box** | 28 cities, see `cities.json` |
| **Total features** | ~1.67M across all cities |
| **Tests** | Run on every push, see the badge at the top |
| **Last extracted** | Varies per city, see each `manifest.json` |

---

## Adapting to Other Cities

The pipeline is multi-city via `cities.json` registry at the repo root. To add a city:

1. Add an entry to `cities.json` with `display_name`, `country`, `bbox`, `center`, `zoom`, `tagline`, `locale`
2. Run `uv run extract-zoning --city <your_slug>` (and optionally `extract-vial` / `extract-services`)
3. Run `uv run generate-landing` to update the landing
4. Open a PR to the upstream repo if you want it included for everyone

For one-off extracts without modifying `cities.json`: `uv run extract-zoning --bbox "s,w,n,e" --slug your_city`.

See [docs/adapting-to-other-cities.md](docs/adapting-to-other-cities.md) for city-specific guidance, example bboxes, and density threshold calibration.

---

## Credits

Every city on the site past the first few is here because someone asked for it.

| City | Requested by |
|------|--------------|
| Charleston, SC | [@MrWicK95](https://github.com/MrWicK95) |
| Mafra, SC | [@arthuregood](https://github.com/arthuregood) |
| Trondheim | [@SvenErik1968](https://github.com/SvenErik1968) |
| Bacău | [@VasileStelian](https://github.com/VasileStelian) |
| Fayetteville, NC | [@brooklyn85knight-sys](https://github.com/brooklyn85knight-sys) |
| Sacramento, CA | [@jwkueb](https://github.com/jwkueb) |
| New York, NY | [@ooo-89S](https://github.com/ooo-89S) |
| Hollister, CA | [@gileslcaleb-67](https://github.com/gileslcaleb-67) |
| Butterworth, Penang | [@ansehelm](https://github.com/ansehelm) |
| Antwerp | [@tomdelamontagne](https://github.com/tomdelamontagne) |
| Łódź | [@Telduu](https://github.com/Telduu) |
| Kiel | [@bamboucha1](https://github.com/bamboucha1) |
| Kursk | [@gandonuebanovic14-spec](https://github.com/gandonuebanovic14-spec) |
| Cincinnati, OH | [@caleb2656](https://github.com/caleb2656) |
| Pittsburgh, PA | [@WARning296](https://github.com/WARning296) |
| Hong Kong | [@Tableisnottable](https://github.com/Tableisnottable) |
| Little Rock, AR | [@rlprice5525](https://github.com/rlprice5525) |
| Beverlo | [@Hobbel1968](https://github.com/Hobbel1968) |
| Chicago, IL | [@Alan-March](https://github.com/Alan-March) |
| Atlanta, GA | [@BluMan142](https://github.com/BluMan142) |
| Yogyakarta | [@Nazvix](https://github.com/Nazvix) |
| Drammen | [@gwicz](https://github.com/gwicz) |
| Køge | [@gwicz](https://github.com/gwicz) |
| Valparaíso | [@lylesnake](https://github.com/lylesnake) |
| Denton, TX | [@zenful6219](https://github.com/zenful6219) |

The toolkit and its data are free. If it's useful to you, you can support it on
[Ko-fi](https://ko-fi.com/osyanne) (one-off tip),
[GitHub Sponsors](https://github.com/sponsors/Osyanne) or
[Patreon](https://www.patreon.com/c/CS2OSMToolkit) (monthly).

Supporters are credited here as well. Nobody is listed without asking first — if
you support the project and want to appear, send a message and say how you'd
like to be named.

---

## License

MIT. OSM data via OpenStreetMap contributors under ODbL.
