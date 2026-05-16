# CS2 Minneapolis OSM Toolkit — v3.1

> Real-world GIS data from OpenStreetMap → Cities: Skylines 2
> Modular toolkit · 100% open source · Zero API keys · Interactive dark map

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/License-MIT-green)
![OSM Data](https://img.shields.io/badge/Data-OpenStreetMap-orange)
![Tests](https://img.shields.io/badge/tests-73%20passing-success)

> 🇪🇸 Versión en español: [README.es.md](README.es.md)

## What This Does

A modular toolkit that extracts real-world infrastructure data from OpenStreetMap via the Overpass API and renders it on an interactive dark-mode Leaflet map. Built as a reference layer for players recreating Minneapolis 1:1 in Cities: Skylines 2.

Currently includes **two modules**, each with its own extractor and visualization layer:

### 🗺 Zoning Module
Classifies all building polygons into the **11 official Cities: Skylines 2 zone types** (Low/Medium/High Density Residential, Row Housing, Mixed Housing, Low Rent Housing, Low/High Density Business, Low/High Density Offices, Industrial Manufacturing). 81,732 polygons in the Minneapolis bbox.

Run: `cd src && uv run extract-zoning`
Output: `visualizer/datos_zonificacion.js` (~28 MB)

### 🛣 Road Network Module
Classifies all OSM roads into the **6 CS2 road categories** (Highway, Major Road, Minor Road, Local Street, Pedestrian Path, Bike Lane). Renders as LineString overlay. 108,825 features.

Run: `cd src && uv run extract-vial`
Output: `visualizer/datos_vial.js` (~25 MB)

### Coming next
- 🏥 Services Module (health, education, parks, police, fire, energy, water) — Sesión 3
- 🚌 Transit Module (Blue/Green Line, BRT, bus routes, bikeways) — Sesión 4

## Visualizer features

- **Module pills (top right)**: toggle entire modules on/off in one click
- **Master toggles in legend**: same effect, mirrored in the sidebar
- **Background mode** (when modules are off): Hidden / Faded / Full
- **Layer Control** (top right): granular per-zone / per-road-category toggles
- **Canvas renderer**: smooth pan/zoom with 80k+ polygons + 108k linestrings
- **Tier-based hiding**: individual houses hide at zoom <14, blocks stay visible
- **CS2-faithful color palette**: 4 families (green/blue/purple/yellow) aligned to the game HUD
- **Dark theme**: CartoDB Dark Matter basemap
- **Persistence**: view state saved to localStorage (`cs2-mineapolis-view-state-v1`)

## Quick start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (faster pip+venv replacement)

### Setup

```bash
git clone https://github.com/Osyanne/cs2-minneapolis-osm-toolkit.git
cd cs2-minneapolis-osm-toolkit/src
uv sync
```

### Get prebuilts

The prebuilt `datos_*.js` files (~53 MB total) are **not** in this repo. Two ways to get them:

**Option A — Download from GitHub Releases** (recommended):
1. Go to https://github.com/Osyanne/cs2-minneapolis-osm-toolkit/releases
2. Download `datos_zonificacion.js` and `datos_vial.js` from the latest release
3. Place them in `visualizer/`

**Option B — Regenerate locally**:
```bash
cd src
uv run extract-zoning    # ~3-5 min
uv run extract-vial      # ~30s
```

### Serve the visualizer

```bash
cd visualizer
python -m http.server 8080
# Open http://localhost:8080/index.html
```

## Project structure

```
src/
├── shared/
│   └── overpass_client.py    # Overpass API client with retry + endpoint rotation
├── zoning/
│   ├── zones.py              # CS2 zone model + Overpass queries
│   ├── classifiers.py        # OSM tag → CS2 zone classifier
│   ├── extract.py            # CLI pipeline (entry: extract-zoning)
│   ├── patch_colors.py       # Color palette utility
│   └── extract_msbuildings.py  # Experimental MS Buildings augmentation
└── vial/
    ├── zones.py              # CS2 road model + Overpass query
    ├── classifiers.py        # OSM highway tag → CS2 road category
    └── extract.py            # CLI pipeline (entry: extract-vial)

tests/
├── zoning/                   # 61 tests (50 classifiers + 11 query sanity)
└── vial/                     # 12 tests

visualizer/
├── index.html                # Single-file Leaflet visualizer with module pills
└── README.md                 # How to get prebuilts

docs/
├── plans/                    # Session implementation plans
├── specs/                    # Design specs
└── adapting-to-other-cities.md
```

## Project stats

| | |
|---|---|
| **Modules** | 2 (Zoning, Road Network) — 2 more pending (Services, Transit) |
| **Bounding box** | `44.86,-93.38,45.05,-93.17` (Minneapolis + immediate borders) |
| **Total features** | 190,557 (81,732 zoning polygons + 108,825 road LineStrings) |
| **Tests** | 73 passing (50 zoning classifiers + 11 zoning queries + 12 vial sanity) |
| **Last extracted** | 2026-05-15 |

## Adapting to other cities

The bbox is parametric — point the extractors at a different `--bbox` and you get the same map for any city. See [`docs/adapting-to-other-cities.md`](docs/adapting-to-other-cities.md) for guidance.

## License

MIT. OSM data via OpenStreetMap contributors under ODbL.
