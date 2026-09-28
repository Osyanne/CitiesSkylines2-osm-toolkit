# Changelog

All notable changes to the cs2-osm-toolkit. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Seattle, WA** — zoning for downtown, Lake Union and the neighborhoods
  along Lake Washington: 160,010 polygons and 187 vector tiles. Requested
  by @lightningbolts (#66).
- **Sioux Falls, SD** — zoning for downtown and the neighborhoods around
  the Big Sioux River: 48,546 polygons and 164 vector tiles. Requested by
  @DekiDeveloper (#58).
- Both maps use the requested bounding boxes. The collection now covers
  **40 cities in 17 countries**.

## [v3.4.12] — 2026-09-27 — Point at a building to see its zone

### Added

- **Point at a building to see its CS2 zone.** On a computer, the building
  under the cursor gets an outline and a small label with its zone, plus
  "Guessed from size" when that's how it was classified. Its row lights up in
  the layers column.
- **Click to pin it.** A "Selected" card in the column shows the zone and
  where it comes from: OSM tags, OSM land use, guessed from size, Google or
  Microsoft footprints, or the official plan. It has `Only this zone` and
  `Explore on OSM ↗`. "Also here" lists the roads, services, transit lines
  and utilities at the same spot. `Esc`, `✕` or a click on an empty spot
  clears it. With the column folded the card floats at the bottom left; on
  phones the tray's line shows the zone you tapped.

### Removed

- The map popups: the "Selected" card replaces them.

## [v3.4.11] — 2026-09-27 — One layers column, with On, Dim and Off

### Changed

- **One layers column replaces the legend, the layers panel, the buttons at
  the top and "Switched off".** On a computer it sits on the left and the map
  shrinks beside it instead of being covered. `«` folds it away and
  `☰ Layers` brings it back; small windows start with it folded, and it
  remembers your choice. The basemap switch (Dark / Satellite) is at its
  foot. While you scroll through the zones, the other layers (Roads,
  Services…) stay pinned at the bottom of the column with their `On` / `Dim`
  / `Off`, and the confidence key ("How sure is the zone?") folds into one
  line.
- **Each layer is `On`, `Dim` or `Off`.** Dim keeps it on the map, faded, as a
  reference under the zones. It replaces "Switched off", a single setting for
  every switched-off layer at once.
- **`Only` shows a single zone or road type**, or a whole group (Residential,
  Main roads…), in one click, and `Restore` brings back what you had before.
  A line at the top of the layer says what is showing ("Showing 1 of 13
  zones"). Every zone, road type, service, transit line and utility network
  has its own checkbox; transit and utilities couldn't be filtered before.
- **Quieter counts**: small and grey, next to each name. With the official
  plan selected they count the plan's areas instead of the OSM buildings.
  Zones a city doesn't have are folded into "N not in this city" at the end
  of the list instead of a column of zeros.
- **A calmer first visit**: zoning on, roads dimmed, everything else off. The
  map remembers your layers and basemap for each city (settings saved by
  earlier versions start over).
- **On phones the layers live in a tray at the bottom**, folded to one line
  that says what is on ("Zoning · Roads dimmed"). Tap it to open half the
  screen; rows are finger-sized and `Only` is always visible. With the phone
  sideways it opens as a full-height drawer on the left instead.
- If Transit or Utilities can't download, their row says "Couldn't load —
  reload to retry" instead of a red padlock.

## [v3.4.10] — 2026-09-26 — The map in English, with a way back to the city list

### Added

- **A way back to the city list** from the map: the `‹ Cities` button next
  to the city name. Until now a map opened from Reddit was a dead end.
- **`Fit city`** under the zoom buttons brings the whole city back into view.
- **A scale bar in metres**, the unit CS2 uses.

### Changed

- **The map is in English throughout.** Layer names, the loading screen,
  popups and the legend still had Spanish text ("Fondo", "Red vial",
  "Servicios", "Sin nombre"…). Services use their CS2 names (Healthcare &
  Deathcare, Fire & Rescue, Police & Administration…), and their map markers
  now read F for Fire and P for Police, with a tree for Parks & Recreation.
- **The confidence legend matches what the map draws**: solid areas come from
  OSM tags or land use, faint dashed ones are guessed from their size. It used
  to show blue, green and brown swatches that appear nowhere on the map.
- Street and neighbourhood names on the dark basemap are easier to read.
- Numbers use the same format for everyone (161,815).

### Removed

- The bar at the bottom of the map ("295,854 polígonos · datos OSM"): it
  added roads and services to the polygon count and repeated the city name.

### Fixed

- **The map shows buttons only for the layers a city has.** Transit and
  Utilities used to appear with a padlock in every city, and only Minneapolis
  has them: in the other 37 the padlock never opened.
- **Transit and Utilities remember being switched off.** They load after the
  rest of the map, and when they arrived they turned themselves back on.
- **The layer buttons show their names** on desktop, instead of icons you had
  to guess.
- **The layer buttons stay put** when you switch one off: the "Fondo" control
  that appears then used to push them sideways, so a second click could land
  on the wrong button.
- If Transit or Utilities fail to download, their button says so instead of
  staying locked.
- **City thumbnails show only the map.** The script that takes them was
  meant to hide the title, layer buttons and legend, but looked for an element
  that doesn't exist, so every card showed the viewer's controls. All 38
  thumbnails were retaken.

## [v3.4.9] — 2026-09-26 — Six more cities, and the first in India

### Added

- **Six new cities from the request queue** (zoning), 38 in total, in 17 countries:
  - Lübeck, Germany (#52), 76,080 polygons. The box reaches north-east to
    take in Travemünde and its ferry port, which the request mentions. Its
    east side crosses into Mecklenburg-Vorpommern, so it reads both state
    extracts.
  - Pune, India (#53), 128,407 polygons, the first Indian city.
  - Recife, Brazil (#54), 107,747 polygons, with Olinda to the north.
  - Buenos Aires, Argentina (#55), 43,282 polygons. OSM maps only about
    33,000 buildings there, so most of the city shows as whole residential
    blocks.
  - Carmel, IN (#56), 24,517 polygons.
  - Kansas City, MO (#57), 120,931 polygons, with Kansas City, KS across
    State Line: it reads the Missouri and Kansas extracts, like Cincinnati.
- India maps to the Asia filter on the landing.

## [v3.4.8] — 2026-09-26 — Scranton, and a star button

### Added

- **Scranton, PA** (#51), from the request queue (zoning), 32 cities in total.
  The request carried a single point downtown, so the box is a 14.3 km square
  (the playable area of a CS2 map) centred on it. It takes in Dunmore, Taylor
  and Old Forge around the city.
- The map, landing page and city request form now invite players to star the GitHub repo.

## [v3.4.7] — 2026-09-26 — The dark basemap holds up close

### Fixed

- Zooming in on the dark Esri basemap showed "Map data not yet available"
  because its tiles stop at z16. The map now stretches the last available tile.

## [v3.4.6] — 2026-09-26 — Roscommon, Philadelphia and La Plata

### Added

- **Three new cities from the request queue** (zoning), 31 in total:
  - Roscommon, Ireland (#43).
  - Philadelphia, PA (#44).
  - La Plata, Argentina (#45): the planned 1882 core, grid, diagonals and
    plazas. OSM maps only about 2,300 buildings there, so it also gets Google
    Open Buildings like Valparaíso: +49,853 footprints, with 2,260 that OSM
    already had left out.
- Ireland maps to the Europe filter on the landing.

## [v3.4.5] — 2026-09-26 — Valparaíso fills in, and releases publish themselves

### Added

- **Releases publish themselves.** `.github/workflows/release.yml` runs on
  every push to `main` that touches `CHANGELOG.md` or `src/pyproject.toml`. Each
  CHANGELOG version without a tag gets an annotated tag on the first `main`
  commit where `src/pyproject.toml` had that version, and a GitHub release
  titled and filled from its section. It can also be run by hand from Actions
  (`workflow_dispatch`, tag + commit).

- **Valparaíso gets Google Open Buildings.** OSM maps about 36k buildings for
  Valparaíso, Viña del Mar and Concón, a metro area of ~700k people, so the
  hills showed residential zones with nothing inside. Google's ML footprints add
  111,028 buildings (confidence ≥ 0.75, ≥ 50 m²); the city goes from 29,173 to
  140,201 polygons.

### Fixed

- `extract-google-buildings` added buildings that OSM already had, and the map
  drew them twice. It now reads every OSM building in the bbox and skips a
  Google building when its centroid falls inside one, or when it contains an OSM
  building's centroid. In Valparaíso that is 27,712 duplicates left out.
- The PBF reader emitted every closed way twice: once as a way and once as the
  area osmium builds from it, typed as a relation with the same id. Each
  building was classified twice and the logged counts were inflated (Valparaíso:
  54,600 elements for 27,331 buildings); the outputs were only right because
  the extractors dedup by id. Now only multipolygon relations come out as areas,
  and a closed way still takes osmium's cleaned ring when its own has spikes or
  repeated nodes (#39).
- With that fixed, `extract-google-buildings` no longer dedups OSM buildings by
  bare id, which could drop a real building when a way and a relation share a
  number (#39).
- The tile tests compare paths with `/`, so they pass on Windows too (#39).

## [v3.4.4] — 2026-09-25 — Six new cities, and the map works on phones

### Added

- **Six new cities from the request queue** (zoning), 28 in total:
  - Atlanta, GA (#24): the request carried a single point in Midtown, so the
    box is a 14.3 km square (the playable area of a CS2 map) centred on it,
    from Downtown and the West End up to Buckhead and east to Decatur.
  - Yogyakarta, Indonesia (#26): the bbox arrived longitude-first and was
    flipped.
  - Drammen, Norway (#29).
  - Køge, Denmark (#30).
  - Valparaíso, Chile (#31): Valparaíso, Viña del Mar and Concón.
  - Denton, TX (#32).
- Denmark and Indonesia map to the Europe and Asia filters on the landing.

### Fixed

- **The map is usable on phones.** The legend covered most of the screen and
  could not be closed (reported on Reddit). It now has a **Legend** button that
  folds it away. On phones (≤ 640 px wide, or ≤ 500 px tall in landscape) it
  starts folded. Each browser remembers whether the legend was left open or
  folded. When open on a phone, the legend stops below the module toolbar and
  scrolls inside.
- On phones the module toolbar no longer covers the zoom-out button, the status
  bar (which sat on top of the legend and the layers button) is hidden, and the
  map attribution wraps instead of running over the legend button. Between
  641 and 1000 px wide the legend sits above the status bar instead of under it.
- The map height uses `100dvh`, so the bottom controls aren't hidden behind
  the mobile browser's address bar.

## [v3.4.3] — 2026-09-25 — Cities open fast

Big cities used to freeze the tab: Minneapolis took ~18 s to open, used
~950 MB of memory and froze for 3-8 s on every zoom. The work went in three
steps, each one usable on its own.

### Changed

- **Vector tiles + MapLibre GL.** The viewer no longer builds one Leaflet
  object per building and road. `src/shared/tiles.py` cuts zoning (plus
  Google buildings) and roads into Mapbox Vector Tiles
  (`visualizer/cities/<slug>/tiles/<z>/<x>/<y>.mvt.gz` + `tiles.json`). MapLibre
  draws them on the GPU and downloads only what is on screen. Small modules
  (services, transit, infrastructure, official zoning) load as GeoJSON. Every
  UI piece carries over: module pills, background modes, legend, layer
  control, official/OSM source switch, popups, persisted state.
- **Compact data format.** `datos_zonificacion`, `datos_vial` and
  `datos_external_buildings` are now lossless compact JSON
  (`src/shared/compact.py`): delta-encoded integer coordinates and properties
  stored per column. `visualizer/cities/` went from 435 MB to 119 MB of data,
  plus 74 MB of tiles.
- The extractors for zoning, roads and Google buildings write the compact
  format and rebuild the city's tiles when they finish.
- `thumbnails.py` hides the MapLibre controls and launches Chromium with
  software WebGL allowed.

### Added

- `uv run build-tiles [--city <slug>]` and
  `uv run convert-legacy-data [--city <slug>]` (migrates old `.js` data and
  verifies the round trip before deleting anything).
- Manifest fields: `modules.<m>.file` (which file to load) and `tiles`.
- Fallback: a city without tiles (data from an older toolkit) still opens,
  drawn from its full data files.
- Support links: the landing's **Support ▾** button opens a menu with Ko-fi,
  GitHub Sponsors and Patreon, and the footer and READMEs list all three.
  `.github/FUNDING.yml` adds the **Sponsor** button to the GitHub repo.

### Fixed

- Zoning and road popups never opened in cities with services: a second
  canvas sat on top and swallowed every click.
- OSM names in zoning popups were inserted without escaping.
- "Fondo: Atenuado" overwrote the dashed style of low-confidence polygons.
- Switching the zoning source (OSM / official) showed zoning again while its
  pill was off.
- `extract-official-zoning` rewrote Minneapolis' manifest on every test run,
  pointing it at a file that doesn't exist. It now only updates the manifest
  of the city folder it writes to (new `--visualizer-root` option).

### Performance

Minneapolis, headless Chromium, local files. Main-thread JavaScript time is
the part that freezes the page on any machine. The container has no GPU, so
MapLibre's wall-clock times here include software rendering and are not
representative.

| | Before | Off-map build + zoom gates | + compact data | Vector tiles |
|---|---|---|---|---|
| JS time to open | 14.3 s | 4.2 s | 3.9 s | 1.2 s |
| JS time, 6 zooms + 3 pans | 29.3 s | 25.6 s | 24.0 s | 1.1 s |
| JS heap | 949 MB | 782 MB | 556 MB | 125 MB |
| Zoning + roads download (gzip) | 8.8 MB | 8.8 MB | 4.9 MB | 0.6 MB (6 tiles) |

Madison: memory 190 MB → 12 MB, download 1.9 MB → 0.2 MB.

## [v3.4.1] — 2026-05-22 — Landing redesign

### Added

- New visual identity for the hosted landing page (Linear/Cal.com inspired):
  hero with gradient headline + animated v3.5 badge, 4-column stats banner,
  region filter pills + search input, 3-column card grid with module dots,
  dedicated "Request your city" card at end of grid, empty-state with
  conversion fallback.
- `country_code` field (optional ISO 3166-1 alpha-2) added to all 10 cities
  in `cities.json` for flag emoji rendering in the gallery.
- Region-based filtering helpers in `src/shared/landing.py`:
  `COUNTRY_TO_REGION` map, `country_to_flag()`, `region_counts()`,
  `build_stats()`, `_read_version_short()`.
- New `visualizer/assets/landing.css` extracted from the inline styles
  (cacheable, ~400 lines).
- Inline vanilla JS (~30 lines) for client-side filter + search across
  the card grid.
- Missing thumbnails generated for Fayetteville NC, Sacramento CA, and
  New York — city requests #8/#9/#10 were merged on 2026-05-20 without
  their thumbs; checklist documented in Obsidian to prevent recurrence.

### Changed

- `_card_html()` rewritten: `<img loading="lazy">` instead of
  `background-image`, flag emoji from `country_code`, module dots replace
  text badges, precomputed `data-search` attribute for fast client filter.
- `build_landing_html()` rewritten with new full-page structure.
- `cities.json` deployed mirror (`visualizer/cities.json`) carries the new
  `country_code` field.

### Accessibility

- WCAG AA contrast verified (text 17.5:1, muted 7.1:1, dim 4.3:1).
- `prefers-reduced-motion` disables pulse + hover transforms.
- `:focus-visible` rings on all interactive elements.
- `aria-pressed` on filter pills, `aria-label` on module dots,
  `<label class="sr-only">` for the search input.

### Performance

- Thumbnails lazy-loaded via `<img loading="lazy">` — page weight on
  initial load drops from ~3–4 MB to ~1.5 MB.
- Google Fonts via `<link rel="preconnect">` + `font-display: swap`.

### Docs

- Design spec: `docs/specs/2026-05-22-landing-redesign-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-05-22-landing-redesign.md`.
- Mockups (3 explored directions): `docs/mockups/landing-redesign/`.
- Thumbnail generation checklist for future city requests in Obsidian.

## [v3.4.0] — 2026-05-19

### Added

- **PBF-based extraction (default):** All four `extract-*` commands now read
  from local `.osm.pbf` files downloaded from Geofabrik by default, instead
  of the Overpass API. Faster per city, no rate limits, fully reproducible,
  and aligned with OSM community guidance against bulk-extracting from
  Overpass.
- New `pbf_region` field in `cities.json` per city (e.g.
  `"north-america/us/minnesota"`).
- New `src/shared/pbf_cache.py`: downloads + caches regional PBFs in
  `~/.cache/cs2-osm-toolkit/pbf/` with a 7-day TTL. `--refresh-pbf` flag
  forces a re-download.
- New `src/shared/pbf_filters.py`: structured filter spec types
  (`FilterSpec`, `Clause`, `TagMatcher`, `SpatialJoin`) that replace
  Overpass QL strings as the filter contract.
- New `src/shared/pbf_client.py`: PBF reader using `pyosmium 4.x`
  `FileProcessor` API. Emits Overpass-compatible JSON so existing
  classification + output code is unchanged. Exposes both `query()`
  (single FilterSpec) and `query_batch()` (multiple specs, single pass).
- `build_pbf_filters()` siblings in `zoning/zones.py`, `vial/zones.py`,
  `services/zones.py` — return structured filter specs equivalent to the
  existing `build_queries()` / `build_*_query()` Overpass QL builders.
- `--source pbf|overpass` and `--refresh-pbf` CLI flags on
  `extract-zoning`, `extract-vial`, `extract-services`, and
  `extract-google-buildings`.
- Opt-in parity integration test (`tests/integration/test_pbf_overpass_parity.py`)
  comparing PBF and Overpass element counts per source key (±20%
  tolerance). Run with `CS2_PARITY_TEST=1`.

### Changed

- Default extraction source is now `pbf` for every `extract-*` command.
- Added `osmium>=3.7.0` (pyosmium) to dependencies. Resolves to 4.3.1 in
  practice; use the 4.x API surface.
- Bumped `version` to `3.4.0` in `src/pyproject.toml`.
- Test suite grew from 184 to 281 passing tests (+97), all green.

### Deprecated

- `--source overpass` mode is kept as a fallback but will be removed in
  v4.0.0.
- `src/shared/overpass_client.py` will be removed in v4.0.0.

### Performance

Single-pass extraction via `query_batch()` (added late in v3.4.0
development after the per-source re-read approach was measured at 100+
min for Minneapolis). Measured Minneapolis zoning:
**1169 s (19 min 29 s)** for 10 source categories on a cached 262 MB
Minnesota PBF, producing 204,493 classified polygons. Subsequent cities
in the same region (e.g., Madison) skip the download and reuse the PBF.

### Known Limitations

- **Longitude buffer approximation in spatial join:** 1° latitude ≈ 111 km
  is used for both axes, overstating longitude at non-equatorial latitudes
  (~40% at 45°N). Acceptable for 5–10 m "around" semantics used in the
  mixed-apartments matcher; revisit if larger buffers are introduced.
- **Compound-tag regex approximation:** Overpass patterns like
  `["building:use"~"residential"]` are approximated as list-equality in
  PBF filters (`["residential", "residential;commercial"]`). Some rare
  multi-value `building:use` tags may go unmatched.

### Migration Notes

Existing users: re-run any `extract-*` command — it will auto-download the
regional PBF for your city's `pbf_region` on first use, then reuse the
cache. To opt back into Overpass temporarily: append `--source overpass`.

If your city in `cities.json` does not have `pbf_region`, the extractor
will exit with a clear error telling you to add it or fall back to
`--source overpass`. The seven default cities (Minneapolis, Amsterdam,
Madison, Charleston, Mafra, Trondheim, Bacau) all have `pbf_region`
preconfigured.

---

## [v3.3.x] and earlier

See git history (`git log --oneline`) for changes prior to v3.4.0. The
toolkit was renamed from `cs2-minneapolis-osm-toolkit` to
`CitiesSkylines2-osm-toolkit` in May 2026, and the multi-city architecture
landed across the v3.x series.
