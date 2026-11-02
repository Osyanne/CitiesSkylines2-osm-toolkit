# CS2 OSM Toolkit: map viewer

This folder is the toolkit's map viewer: a static site, with no build step, that shows the CS2 zoning of each city on a dark map. GitHub Pages publishes it at https://osyanne.github.io/CitiesSkylines2-osm-toolkit/visualizer/.

- `index.html`: the city list. `uv run generate-landing` (from `src/`) writes it from the root `cities.json` and the city manifests, so don't edit it by hand.
- `map.html`: the map of one city, opened as `map.html?city=<slug>`. It uses MapLibre GL (WebGL) to draw zoning and roads from vector tiles, over Esri's Dark Gray Canvas or satellite imagery.
- `cities.json`: the copy of the root `cities.json` that the map reads, also written by `generate-landing`. A slug that isn't in it, or no `?city=`, sends you back to the city list.
- `search-config.json`: the place search service (Nominatim). `"enabled": false` turns the search off.
- `cities/<slug>/`: the data of each city (below). `assets/`: styles, icons, images and the city card pictures.

## Run it locally

Browsers block the map's data requests from a page opened as a file (`file://`), so serve this folder over HTTP:

    cd CitiesSkylines2-osm-toolkit/visualizer
    python -m http.server 8000

Then open http://localhost:8000/ (the city list) or http://localhost:8000/map.html?city=minneapolis. Every city's data is already in the repo, so there's nothing to download. Any static server works.

## What it reads for each city

`map.html` reads `cities/<slug>/manifest.json` first. The manifest lists the modules the city has and its tiles, with a hash for each module and one for the tiles. The hash goes in the request, so the browser doesn't serve an old copy after a new extraction. The map then loads only what the manifest lists:

| Files | What | Written by |
|---|---|---|
| `tiles/tiles.json` and `tiles/<z>/<x>/<y>.mvt.gz` | Zoning, roads and Google buildings, cut by zoom. The browser fetches only the tiles on screen. | `extract-zoning`, `extract-vial` and `extract-google-buildings` when they finish, or `uv run build-tiles --city <slug>` |
| `datos_servicios.js` | Services | `extract-services` |
| `datos_transporte.js`, `datos_infraestructura.js` | Transit and infrastructure | `extract-transporte`, `extract-infraestructura` |
| `datos_zonificacion_official.js` | The official plan | `extract-official-zoning` |
| `datos_zonificacion.json`, `datos_vial.json`, `datos_external_buildings.json` | The full data behind the tiles, downloaded only for a city without tiles | `extract-zoning`, `extract-vial`, `extract-google-buildings` |

Every city has zoning; only a few have the other modules. The transit, infrastructure and official plan files load after the map first appears.

GitHub Pages doesn't publish the files in the last row (`_config.yml` leaves them out), because the tiles already cover them. They stay in the repo because `build-tiles` reads them.

The view (camera, basemap, zoning source, layers, hidden categories and playable area) lives in the URL hash. Each city also remembers its layer states, zoning source, basemap and playable area in `localStorage` (`cs2-view-state-<slug>-v2`). The formats are in the specs of [stage 4](../docs/plans/2026-09-26-layout-visor/08-etapa-4-spec.md) and, for the playable area, [stage 6a](../docs/plans/2026-09-26-layout-visor/09-etapa-6a-spec.md).

## Everything else

The [main README](../README.md) covers the rest: what each control does ([Visualizer Features](../README.md#visualizer-features)), how to get your city on the site ([Adding your city](../README.md#adding-your-city)) and how to extract one yourself ([docs/QUICKSTART.md](../docs/QUICKSTART.md)).
