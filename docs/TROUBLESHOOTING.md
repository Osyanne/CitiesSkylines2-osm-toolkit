# Troubleshooting

Quick fixes for the most common issues. If yours isn't here, open a GitHub Issue — see the bottom of this page.

---

## "Python is not recognized" or "python: command not found"

You didn't check "Add Python to PATH" during installation (easy to miss — it's unchecked by default).

Fix: Reinstall Python from [python.org/downloads](https://www.python.org/downloads/). On the first screen of the installer, check the box that says **"Add Python to PATH"** before clicking Install Now. Then open a new terminal and try again.

If you'd rather not reinstall, you can add Python to PATH manually — search "Edit the system environment variables" in Windows, go to Environment Variables, find PATH under System variables, and add the folder where Python is installed (usually `C:\Users\<you>\AppData\Local\Programs\Python\Python311\` and the `Scripts\` subfolder inside it). Restart your terminal after.

On macOS and Linux, the command is often `python3` instead of `python`.

---

## "uv: command not found" or "uv is not recognized"

Either uv didn't install or your terminal still has the old PATH.

First try: close all terminal windows and open a fresh one. Then run `uv --version`.

If that still fails, reinstall uv:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

On macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

After installing, close and reopen the terminal. Run `Get-Command uv` (Windows) or `which uv` (Mac/Linux) to confirm it's found.

---

## `uv sync` fails

Three most common causes:

**Wrong directory.** You must be inside the `src/` folder when you run `uv sync`, not the root of the repo. Check that your terminal prompt ends with `\src>`. If it doesn't, navigate there first.

**No internet connection.** uv downloads packages from the internet. Check your connection and try again.

**Python version too old.** This toolkit requires Python 3.11 or newer. Run `python --version` and check the number. If it's 3.10 or earlier, install a newer version from [python.org](https://www.python.org/downloads/).

---

## "Failed to spawn: `extract-zoning`" (or another command)

You ran the command outside the `src/` folder. The toolkit's commands are defined in `src/pyproject.toml`, so uv only finds them from inside `src/`. Check that your terminal prompt ends with `\src>` and try again.

Run them through `uv run`, too. Running a file inside `src/` with `python` skips the toolkit's setup and ends in errors like `ModuleNotFoundError`.

---

## Errors about cities.json

The extractors read `cities.json` before anything else and stop if something is wrong. Their messages are in Spanish:

- **`cities.json no es JSON válido`**: a typo in the file. The message gives the line and column. Look for a missing comma between two entries, a comma after the last one, or a missing quote.
- **`Entry 'your_slug' le faltan campos: [...]`**: the entry lacks the fields in the list. Every city needs `display_name`, `country`, `bbox`, `center`, `zoom`, `tagline` and `locale` (see [Step 7 of the Quick Start](QUICKSTART.md#step-7-add-your-city-to-citiesjson)).
- **`bbox debe ser [s,w,n,e] de 4 floats`** or **`bbox inválido`**: the box must be four numbers, `[south, west, north, east]`, with south below north and west below east.
- **`Slug 'your_slug' no está en el registro`**: no entry has that slug. Check the spelling, and that you edited `cities.json` in the main folder, not the copy in `visualizer/`.

The `--bbox` and `--slug` options that `--help` and older guides mention don't get around this. Reading the extract, they stop with that same error and leave an empty folder in `visualizer/cities/`. Whatever they write, the map only opens cities that are in `cities.json`. Delete that folder and add an entry instead.

---

## "City 'your_slug' has no 'pbf_region' in cities.json"

Zoning, roads and services read a regional extract from Geofabrik, and `pbf_region` says which one. Add it to the entry. It's the path of the extract on [download.geofabrik.de](https://download.geofabrik.de/) without the ending: `https://download.geofabrik.de/north-america/us/minnesota-latest.osm.pbf` is `"pbf_region": "north-america/us/minnesota"`. If the box crosses into a second region, list both, as Amersfoort does: `["europe/netherlands/utrecht", "europe/netherlands/gelderland"]`.

The message also offers `--source overpass`, which works without `pbf_region` but depends on the public Overpass servers (see the timeouts below).

---

## "404 Client Error: Not Found for url: https://download.geofabrik.de/…"

Geofabrik has no extract with that `pbf_region`. Find your region on [download.geofabrik.de](https://download.geofabrik.de/) and copy its path exactly, in lowercase and with hyphens: `north-america/us/new-york`, `europe/germany/schleswig-holstein`. `process-cities` catches this before downloading any extract: `Geofabrik no tiene la región …`.

Downloads land in `~/.cache/cs2-osm-toolkit/pbf/` and are reused for 7 days. If one stops halfway, run the command again: the unfinished file is deleted, never used. `--refresh-pbf` forces a fresh download.

---

## "AttributeError: 'list' object has no attribute 'strip'"

`extract-vial`, `extract-services` and `extract-google-buildings` read a single extract. They stop with this error on a city whose `pbf_region` is a list, like New York or Amersfoort. Only `extract-zoning` reads several extracts.

---

## Overpass timeout / "Gateway Timeout" / "504"

Only `extract-transporte` and `extract-infraestructura` use the Overpass API. Zoning, roads and services read the Geofabrik extract, unless you run them with `--source overpass`.

The Overpass API is a public service and sometimes struggles with large requests.

**Bbox too large.** Try a smaller bounding box in `cities.json`: just the core urban area rather than the whole metro region. A smaller bbox means fewer features to download and is less likely to time out.

**All endpoints are down.** Rare but happens. The toolkit rotates between three public Overpass endpoints automatically. If they're all struggling, wait 5 minutes and try again. You can check their status on the OSM wiki's [Platform Status](https://wiki.openstreetmap.org/wiki/Platform_Status) page.

---

## Empty output or very few features

The extraction ran without errors but your visualizer looks mostly empty.

First rule out the box: see the next section. If the box is right, this usually means your city has sparse OSM data. OSM is a volunteer-built map — coverage varies a lot by region. Some cities have extremely detailed building and land use data; others have barely the roads.

Check your city's OSM coverage at [osmstats.neis-one.org](https://osmstats.neis-one.org/). If the contributor and edit counts are low, that's why.

The best long-term fix is to contribute to OSM for your area — add building footprints, building levels, land use polygons. The OSM wiki has guides for getting started. After contributing, re-run the extractor.

Also check that the whole box falls inside its `pbf_region`. A city on the edge of an extract loses everything past the edge. List the neighboring extract too: `extract-zoning` reads them all.

---

## The extraction finds nothing, or the map opens over the wrong place

Check the order of the box. The toolkit wants `[south, west, north, east]`, latitude first. Many tools give longitude first (`west,south,east,north`), and [bboxfinder.com](http://bboxfinder.com/) does by default: choose **Lat / Lng** under Coordinate Format before you draw the rectangle.

`extract-zoning` can't always tell. A box in the wrong order often looks valid, so the extraction runs and finds nothing, and the map opens over the sea or says `Invalid LngLat latitude value`. `process-cities` checks harder before downloading any extract. It stops with `fuera de rango: ¿está en metros o en orden lon/lat?`, `el centro … queda fuera de la caja` or `solo el N% de la caja cae en …`.

A lost minus sign does the same, or trips `bbox inválido`. West of Greenwich, longitudes are negative; south of the equator, latitudes are.

---

## The map won't open, or the page is blank

**The address starts with `file://`.** You opened the page with a double-click. Browsers block the map's data requests from files, so the city list may show but no city loads: the map page says `Failed to load city`. Serve the folder over HTTP instead:

    cd CitiesSkylines2-osm-toolkit/visualizer
    python -m http.server 8000

(The folder is `CitiesSkylines2-osm-toolkit-main` if you downloaded the ZIP.) Then open `http://localhost:8000/`. Any static server works, like Node's `http-server` or VS Code's Live Server.

**`Failed to initialize WebGL`.** The map draws with your graphics card, through WebGL. Turn on hardware acceleration in the browser's settings, or try another browser.

**Something else.** Open browser developer tools (press **F12**), click the **Console** tab, and look for red error messages.

**Browser cache showing old version.** Press **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac) to force a full reload.

---

## The map sends me back to the city list, or my city isn't in it

Run `uv run generate-landing` from `src/`. It rewrites the city list (`visualizer/index.html`) and `visualizer/cities.json`, the copy of the registry that the map reads. `map.html` sends any slug that isn't in that copy back to the city list, and so does a `map.html` without `?city=`.

---

## "City data corrupted: manifest.json missing"

The city is in `cities.json`, but it was never extracted, or the extraction stopped before the end. Run `uv run extract-zoning --city <slug>` from `src/` and read the last lines it prints.

---

## `process-cities` fails at the city card pictures

The pictures need Playwright's Chromium. If the summary says `failed: falta Playwright`, or the run stops with Playwright's `Executable doesn't exist`, install it once:

    uv run --group thumbnails playwright install chromium

and start `process-cities` with `uv run --group thumbnails`, as in the [Quick Start](QUICKSTART.md#several-cities-at-once). The extraction and the city list are done before the pictures, so you can take just the pictures afterwards, while the local server runs:

    uv run --group thumbnails generate-thumbnails --city <slug> --base-url http://localhost:8000

---

## Things disappear when I zoom out

That's intentional, so a whole city stays fast to draw:

- Services markers (H, E, F and P, and a tree for parks) show from zoom 11. Polygon features (hospital campuses, parks, university grounds) are always visible.
- Low density houses and surface parking lots under 3,000 m² show from zoom 13.
- Local streets show from zoom 11, bike lanes from 12 and pedestrian paths from 13.
- Anything smaller than a pixel is left out until you zoom in.

The zoom is the first number after `map=` in the address bar.

---

## Colors are hard to tell apart

Known limitation. The color palette is designed to match the in-game CS2 zone HUD, which uses several similar shades of green for the residential zones (Low Density, Medium Density Row, Medium Density, Low Rent and High Density Housing). They're distinct in the layers column but can look similar on the map at medium zoom.

Zooming in helps. Point at a building to see the name of its zone, or press **Only** next to a zone in the layers column to show just that one (**Restore** brings the others back).

---

## Still stuck?

Open an issue at [github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues).

Include: what step you were on, the exact error message (copy-paste it, don't screenshot if you can help it), your OS and Python version, and your bbox if relevant. The more detail, the faster it gets resolved.
