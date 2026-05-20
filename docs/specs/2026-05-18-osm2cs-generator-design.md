# v3.5 — Browser-based City Generator (OSM2CS) — Design Spec

> **Date:** 2026-05-18
> **Status:** Design approved (8 sections), implementation pending
> **Authors:** Imanol Miranda (`@Osyanne`)
> **Repo:** `CitiesSkylines2-osm-toolkit`
> **Predecessor:** v3.4.0 (PBF migration shipped 2026-05-20)

---

## 1. Summary

Add `visualizer/generate.html` to the existing hosted viewer — a free, no-auth web tool that lets any CS2 creator generate a CS2-ready map bundle from any city in the world directly in their browser.

**User flow:** type city name → autocomplete picks via Nominatim → confirm 14.336km tile (CS2 native size) → click "Generate" → browser downloads ZIP containing heightmap PNG + GeoJSON layers + offline viewer + import instructions.

**Architecture:** 100% client-side. SRTM elevation data, Overpass queries, image processing, and ZIP packaging all happen in the user's browser. Zero backend, zero auth, zero billing. Hosted on GitHub Pages alongside the existing toolkit.

**Why now:** Phase 3 validation is complete (Giscolab fork = Tier 0 demand signal + 7 city requests processed). Patreon LIVE at https://www.patreon.com/c/CS2OSMToolkit. The downstream-builder demand pattern indicates a generic OSM→CS2 generator is the next logical product step.

---

## 2. Context & validation status

### What's already been validated

- **Tier 0 demand signal:** Franck Da Costa (`Giscolab`) built `CityTimelineMod` (C# CS2 mod) on a fork of the toolkit (2026-05-18 discovery). His fork adds multi-bundle workflow, MapTiler raster integration, water layer, and multi-country normalization — all features that confirm Phase 3 territory.
- **7 city requests processed** via the GitHub Issue template (Charleston #4, Mafra #5, Trondheim #6, Bacau #7, Fayetteville NC #8, Sacramento #9, New York #10) — 4× the original Phase 3 threshold (>5 requests).
- **Patreon LIVE 2026-05-20** with 3 tiers ($3 Supporter / $10 City Builder / $25 Founding Pro Beta). The Pro Beta tier locks in early access to the upcoming SaaS at the current rate.

### Why this specific shape

Out of the original 3 product forms considered (CLI extension, free hosted tool, full SaaS with tiers + auth), this spec implements **the middle option (free hosted tool, no auth, no billing)** because:

1. Aligns with the "no recurring cost commitment" principle from initial brainstorm.
2. The Patreon already provides a monetization path without coupling it to the tool's usage.
3. The client-side architecture means hosting cost is exactly $0 forever (GitHub Pages handles static delivery).
4. Forward-compatible: if a future SaaS Pro tier ships (Phase 4), the free tool stays available as the entry point.

---

## 3. User experience flow

```
State 0: Landing                  (existing page, modified)
└─→ "⚡ Generate your own city →" CTA added next to 10 city cards

State 1: /generate.html           (NEW page)
└─→ Empty Leaflet world map + search input

State 2: User types "Tokyo"
└─→ Nominatim autocomplete dropdown (3-5 results)

State 3: User picks "Tokyo, Japan"
└─→ Map centers on city, 14.336km tile drawn (green outline, draggable)
└─→ "✓ Generate ZIP" button enabled

State 4: Generation in progress   (modal or sticky panel)
└─→ Progress steps (each with elapsed time):
    ✓ Fetching elevation data (SRTM)
    ✓ Resampling to 4096×4096
    ✓ Encoding 16-bit PNG
    ⟳ Fetching OSM layers (zoning/roads/services/water in parallel)
    ○ Building ZIP

State 5: Download ready
└─→ "🎉 tokyo-osm2cs.zip generated (12.4 MB)" + [⬇ Download] + [Generate another]
└─→ Import instructions snippet + link to Patreon
```

### UX principles

- **Search-first, no map-pick UX** in v1 — 90% of users only know their city's name. Map-pick adds complexity for power users who can wait until v1.1.
- **Tile size locked to 14.336km × 14.336km** (CS2 native single-tile size). No custom sizes in v1.
- **Progress per-step, not percentage** — step times vary by 10× (PNG encode = 3s, SRTM download = 30s). Honest reporting > misleading percentage.
- **Cancel button uses AbortController** on all in-flight fetches. No backend cleanup needed.
- **Tab inactive is OK** but warned upfront ("Keep tab open during generation").

---

## 4. Architecture

100% client-side. No backend, no database, no authentication.

### Frontend stack

| Layer | Technology | Notes |
|---|---|---|
| HTML/CSS/JS | Vanilla, no framework | Consistent with existing visualizer pattern |
| Map | Leaflet 1.x | Already in the repo |
| Search | Nominatim API (OSM-hosted, free) | 1 req/sec rate limit → debounce to 500ms client-side |
| Elevation | OpenTopography SRTM v3 + NASA mirror fallback | Free, CORS-enabled public CDNs |
| OSM layers | Overpass API (multi-endpoint rotation) | Pattern already implemented in toolkit's JS — reuse |
| Image processing | Canvas API (bilinear resample) + UPNG.js (16-bit PNG encode) | UPNG.js vendored locally |
| ZIP packaging | JSZip | Vendored locally |

### External services (all free, all public)

```
                Browser (do everything)
                       │
       ┌───────────────┼────────────────┐
       ↓               ↓                ↓
  Nominatim       OpenTopography    Overpass API
  (city search)   (SRTM tiles)     (OSM layers)
  
  rate limit:     rate limit:       rate limit:
  1 req/sec       no documented     community-funded,
                                    multi-endpoint rotation
```

### Hosting

- **GitHub Pages** at `https://osyanne.github.io/CitiesSkylines2-osm-toolkit/generate.html`
- Zero new deploy pipeline. Push to `main` = live in ~1-2 min.

### Explicitly NOT in stack

- ❌ Node.js runtime — no build step (browser ES modules served directly)
- ❌ React / Vue / Svelte — vanilla DOM manipulation
- ❌ TypeScript in v1 — plain JS for consistency with rest of repo (revisit in v2.0)
- ❌ Service Worker / PWA — overkill for single-page tool
- ❌ Telemetry / analytics — privacy-first, no user tracking

---

## 5. Component structure

```
CitiesSkylines2-osm-toolkit/        (existing repo, name finalized 2026-05-18)
├── visualizer/
│   ├── index.html                  ✏ UPDATE: add "⚡ Generate yours" CTA
│   ├── map.html                    ✓ unchanged
│   ├── generate.html               ★ NEW
│   ├── cities/                     ✓ unchanged (10 prebuilt cities)
│   ├── js/                         ★ NEW directory
│   │   ├── search.js               Nominatim autocomplete + debounce
│   │   ├── tile-picker.js          Leaflet integration, 14.336km lock
│   │   ├── srtm-fetcher.js         SRTM tile download + mosaic + clip
│   │   ├── heightmap.js            Canvas bilinear resample + UPNG encode
│   │   ├── overpass-client.js      ↻ REFACTOR: extract from map.html
│   │   ├── classifiers.js          ↻ REFACTOR: extract from map.html
│   │   ├── water-extractor.js      ★ NEW: Overpass query for water polygons (Giscolab inspiration)
│   │   ├── bundler.js              JSZip packaging (permalink deferred to v1.1)
│   │   ├── progress-ui.js          Step indicator state machine
│   │   └── readme-gen.js           Templates README.md for ZIP
│   └── lib/                        ★ NEW directory (vendored 3rd party)
│       ├── jszip.min.js            ~95 KB
│       └── upng.min.js             ~30 KB
├── src/                            ✓ Python toolkit unchanged
├── tests/                          ✓ pytest unchanged (292 tests + 1 skip)
├── tests-js/                       ★ NEW: JS tests parallel to Python
│   ├── search.test.js
│   ├── srtm-fetcher.test.js
│   ├── heightmap.test.js
│   ├── overpass-client.test.js
│   ├── water-extractor.test.js
│   └── bundler.test.js
└── docs/specs/                     ✓ this file goes here
```

### Key structural decisions

**Refactor of `overpass-client.js` + `classifiers.js` from `map.html`**

Currently these live as inline `<script>` tags in `map.html` (~200-300 lines embedded). The refactor moves them to `visualizer/js/` so both `map.html` AND `generate.html` can share them.

- Cost: ~2-3 hours.
- Risk: low — regression tests via Playwright verify all 10 cities still render post-refactor.
- Benefit: avoid duplicating Overpass+classification logic.

**Plain ES modules, no build step**

```html
<!-- generate.html -->
<script type="module" src="js/main.js"></script>
```

```javascript
// js/main.js
import { searchCity } from './search.js';
import { fetchSRTM } from './srtm-fetcher.js';
```

The browser handles module loading natively. No Webpack/Vite/bundler needed.

**Vendored 3rd-party libs**

`lib/jszip.min.js` and `lib/upng.min.js` are checked into the repo (~125 KB total). No runtime CDN dependency. Updates are explicit commits.

---

## 6. Data flow

```
User types "Tokyo" → search.js → Nominatim API
                            ↓
                  [returns: lat, lon, bbox]
                            ↓
            tile-picker.js: lock 14.336km tile around (lat, lon)
                            ↓
                  [output: bbox = {south, west, north, east}]
                            ↓
                  User clicks "Generate"
                            ↓
            Promise.all([
              pipelineHeightmap(bbox),      ← runs in parallel
              pipelineLayers(bbox)
            ])
              ↙                  ↘
   ┌──────────────────┐    ┌──────────────────────────────┐
   │ srtm-fetcher.js  │    │ overpass-client.js           │
   │ + heightmap.js   │    │ (parallel Promise.all):      │
   │                  │    │   → zoning                   │
   │ 1. Compute       │    │   → roads                    │
   │    overlapping   │    │   → services                 │
   │    SRTM tiles    │    │   → water                    │
   │ 2. Fetch (CDN)   │    │                              │
   │ 3. Mosaic + clip │    │ + classifiers.js (zoning)    │
   │ 4. Bilinear      │    │                              │
   │    resample to   │    │ Output: GeoJSON              │
   │    4096×4096     │    │ FeatureCollections           │
   │ 5. UPNG encode   │    │                              │
   │    16-bit PNG    │    │                              │
   │                  │    │                              │
   │ ~20-30s          │    │ ~5-15s                       │
   └──────────────────┘    └──────────────────────────────┘
            ↘                          ↙
              ↘                      ↙
                bundler.js (JSZip)
                  Add:
                  /heightmap.png       (~12 MB)
                  /zoning.geojson      (~2-5 MB)
                  /roads.geojson       (~2-5 MB)
                  /services.geojson    (~1-2 MB)
                  /water.geojson       (~500 KB - 1 MB)   ← Giscolab insight
                  /preview.html        (~8 KB, templated)
                  /README.md           (~3 KB, templated with city name + bbox + date)
                Compress → Blob
                            ↓
                  ~2-5s · ~25-45 MB ZIP
                            ↓
                  Browser download
                  <a download="tokyo-osm2cs.zip">
```

### Wall-clock total

- Serial worst-case: ~55s (sum of all steps)
- Parallel (real): **~25-40s** (max of SRTM+heightmap vs Overpass parallel, + bundling)

### Peak memory profile

| Component | Memory peak |
|---|---|
| SRTM raw tiles in memory | 50-200 MB |
| Mosaic Uint16Array (4096²) | ~33 MB |
| Resampled buffer | ~33 MB |
| PNG encode workspace | ~25 MB |
| GeoJSON parsed (4 layers) | ~5-25 MB |
| ZIP buffer (uncompressed) | ~50 MB |
| **Total simultaneous** | **~250-400 MB** |

Desktop browsers (2-4 GB per tab): ✅ works comfortably. Mobile (256-512 MB tabs): ❌ likely OOM. Mitigation: warn user upfront via UserAgent detection.

---

## 7. Error handling

Four categories, each with specific UI strategy.

### Category 1: Recoverable (automatic retry, invisible to user)

| Error | Cause | Strategy |
|---|---|---|
| SRTM tile timeout | CDN slow | Retry 3× with backoff 2s/4s/8s, fallback to NASA mirror |
| Overpass 504 | Endpoint overload | Rotate next endpoint (existing pattern: 4 endpoints) |
| Overpass returns `{"elements": []}` | Silent failure under load | Detect (response.length === 0 with valid bbox), treat as timeout, rotate |
| Nominatim 429 rate limit | >1 req/sec | Debounce to 500ms between keystrokes |

UI: nothing visible. Console.warn logging only.

### Category 2: Partial failure (recoverable, soft warning)

| Error | Cause | Strategy | UI |
|---|---|---|---|
| Overpass returns 0 features for `zoning` | Rural area, no OSM tagging | Skip layer, mark in ZIP manifest | Yellow banner: "Limited OSM data: zoning layer empty" |
| Some SRTM tiles missing | Coverage gap (rare, polar/oceanic) | Fill with sea-level (0) | Yellow banner: "Some elevation data filled with sea level" |
| Single OSM feature has invalid geometry | Bad upstream tagging | Skip feature, continue | Silent (log only) |

UI: progress step shows ⚠ instead of ✓. Final screen has explanation banner. ZIP still downloads.

### Category 3: Fatal (stop, no ZIP)

| Error | Cause | UI |
|---|---|---|
| All SRTM CDNs unavailable | NASA + mirror outage | Modal: "Elevation data unavailable. Try again in a few minutes." [Retry] [Cancel] |
| Browser OOM during resample | Insufficient RAM | Modal: "This area is too large for your device. Try desktop with 4 GB+ RAM." |
| Canvas API missing | Ancient browser | Upfront detection: "Use Chrome, Firefox, Safari, or Edge (modern versions)." |
| Mobile detected via UserAgent | Mobile/tablet device | Upfront warning: "This tool works best on desktop." [Continue anyway] [OK] |

UI: blocking modal. Primary CTA "Retry" when applicable.

### Category 4: User-driven (no recovery needed)

| Action | Behavior |
|---|---|
| User closes tab mid-generation | Zero cleanup (no backend state). Refresh = start fresh. |
| User clicks Cancel | `AbortController.abort()` on all in-flight fetches. UI returns to State 3 (tile selected). |
| User refresh during generation | Loses state, returns to State 1. |
| Popup blocker blocks download | Fallback button "Download blocked. [Click to retry]" |

### Implementation pattern

Every pipeline step returns:

```javascript
{
  ok: boolean,
  data?: any,
  error?: 'recoverable' | 'partial' | 'fatal',
  message?: string,
  details?: object
}
```

The orchestrator (`main.js`) decides:
- `recoverable` → retry (max 3×)
- `partial` → log warning, add to `warnings[]`, continue
- `fatal` → show modal, halt pipeline

---

## 8. Testing strategy

Three layers, all integrated with existing CI.

### Layer 1: JS unit tests (Node.js native, no external deps)

Framework: `node --test` (Node 20+). Zero new dependencies.

Coverage targets:
- Core logic (heightmap, srtm-fetcher, classifiers, water-extractor): **80%+**
- UI glue (progress-ui, search): **40-60%**
- Pipeline integration paths: **1 happy path + 2-3 error paths**

```javascript
// tests-js/heightmap.test.js
import { test } from 'node:test';
import assert from 'node:assert';
import { resampleBilinear } from '../visualizer/js/heightmap.js';

test('resample 1024×1024 input → 4096×4096 output', () => {
  const input = new Uint16Array(1024 * 1024).fill(100);
  const output = resampleBilinear(input, 1024, 1024, 4096, 4096);
  assert.equal(output.length, 4096 * 4096);
});
```

### Layer 2: Integration tests

Full pipeline with mocked external services. ~5 tests:

1. Happy path: Mpls bbox → ZIP with 6 files
2. Partial Overpass failure: zoning empty → ZIP with heightmap + warning
3. SRTM gap: missing tile → partial heightmap + warning
4. All Overpass endpoints down: ZIP with heightmap only
5. Large bbox OOM simulation: fatal error returned correctly

### Layer 3: E2E with Playwright

Reuse existing Playwright setup. Tests against real browsers (Chrome, Firefox, Safari, Edge):

```javascript
// tests-js/e2e/generate-flow.spec.js
test('full generation flow for Minneapolis', async ({ page }) => {
  await page.goto('http://localhost:8000/generate.html');
  await page.fill('[data-testid=city-search]', 'Minneapolis');
  await page.click('text=Minneapolis, MN, USA');
  await page.click('[data-testid=generate-btn]');
  
  await page.waitForSelector('[data-testid=download-ready]', { timeout: 90000 });
  
  const downloadPromise = page.waitForEvent('download');
  await page.click('[data-testid=download-btn]');
  const download = await downloadPromise;
  
  // Verify ZIP contents
  const path = await download.path();
  assert(await zipContains(path, [
    'heightmap.png', 'zoning.geojson', 'roads.geojson',
    'services.geojson', 'water.geojson', 'preview.html', 'README.md'
  ]));
});
```

### Critical non-obvious tests

**Refactor regression for `map.html`**

When extracting `overpass-client.js` + `classifiers.js` from `map.html`, all 10 existing cities must still render correctly.

```javascript
test('all 10 cities still render post-refactor', async ({ page }) => {
  for (const slug of [
    'minneapolis', 'amsterdam', 'madison', 'charleston', 'trondheim',
    'bacau_ro', 'mafra_sc_brazil', 'fayetteville_nc', 'sacramento', 'new_york'
  ]) {
    await page.goto(`http://localhost:8000/map.html?city=${slug}`);
    await page.waitForSelector('.leaflet-overlay-pane svg', { timeout: 10000 });
    const polygonCount = await page.locator('.leaflet-overlay-pane path').count();
    assert(polygonCount > 100, `${slug}: expected polygons, got ${polygonCount}`);
  }
});
```

**Python ↔ JS classifier parity**

Both Python (`src/classifiers.py`) and JS (`visualizer/js/classifiers.js`) must produce identical zone classifications for the same OSM input. Test using shared fixtures.

### CI integration

Update `.github/workflows/test.yml` to add 2 new jobs (in parallel with existing pytest):

```yaml
jobs:
  python-tests:                  # existing, 292 tests
  js-unit-tests:                 # NEW
    - run: node --test tests-js/
  e2e-tests:                     # NEW
    - run: npx playwright test tests-js/e2e/
```

### Excluded from v1 tests

- Visual regression screenshot diffing (overkill)
- Load/stress tests (no backend)
- Real Overpass/SRTM in CI (flaky external deps — manual smoke test pre-release only)
- Mutation testing
- Automated accessibility audits (manual checks suffice for v1)

---

## 9. Out of scope (deliberately deferred)

### Out: Features

| Feature | Why deferred | Future home |
|---|---|---|
| User accounts / auth | Contradicts free-hosted-no-billing principle | Phase 4 (Pro SaaS) |
| Pro tier / billing | Patreon already provides monetization path | Phase 4 |
| Saved cities / history | Adds complexity for marginal value | v1.1 with localStorage |
| Map-pick UX | UX-A search-first is sufficient for 90% | v1.1 if feedback requests |
| Coordinate paste UX | Filters out 99% non-dev target market | v1.1 |
| CS2 mod-importable `.crp` bundle | Format undocumented | Phase 5 if Colossal publishes |
| Multi-tile regions (stitching) | Single 14.336km is CS2 native | v2.0 |
| Custom tile sizes | Locked to CS2 native | v2.0 |
| Mobile support | OOM probable, warn upfront | Probably never (hardware) |
| i18n / multi-language | English only in v1 | v1.1 once flow proven |
| Email notifications | No backend | Phase 4 |
| **Bbox permalink URL** (Giscolab inspiration) | Nice for sharing, not critical for MVP | v1.1 |
| **Multi-bundle batch workflow** (Giscolab) | Single-bbox UX by design | Phase 4 Pro feature |
| **MapTiler raster integration** (Giscolab) | MapTiler paid; stick with free OpenTopography | v2.0 if elevation quality complaints |

### Out: Technical

| Item | Why deferred | Future home |
|---|---|---|
| Server-side SRTM caching | Implies backend | Phase 4 if latency complaints |
| Service Worker / PWA | Overkill for single-page tool | v1.1 if daily usage emerges |
| TypeScript | JS plain matches repo conventions | v2.0 if codebase >2k LOC |
| Build pipeline (Vite/Webpack) | Not needed without TS/React | v2.0 |
| React/Vue/Svelte | Overkill for one page | Probably never |
| Visual regression tests | Flaky for v1 | v1.1+ if visual bugs surface |
| Real Overpass/SRTM in CI | External dependency = flaky | Manual smoke test pre-release |
| Analytics / telemetry | Privacy-first, no tracking | Probably never |
| Heightmap >30m resolution (LIDAR) | Per-country complexity massive | v1.1 if demand significant |
| Water masking / ocean-flat | Raw output OK for v1 | v1.1 if feedback requests |

---

## 10. Open questions (resolve during implementation)

1. **Exact SRTM CDN endpoint** — OpenTopography vs NASA SRTM v3 S3 vs USGS Earth Explorer. Recommended start: OpenTopography (CORS open, free, no key). Fallback: NASA mirror.
2. **UPNG.js version pinning** — Vendor at latest stable, pin to specific commit SHA when shipping.
3. **Leaflet tile-picker plugin or custom?** — Custom rectangle locked to 14.336km is ~30 lines; Leaflet.Draw is overkill. Recommendation: custom.
4. **ZIP filename convention** — Proposed: `<city-slug>-<bbox-hash>-osm2cs.zip` (e.g., `tokyo-japan-a3f2c1-osm2cs.zip`). Confirm during implementation.
5. **Should `generate.html` link to Patreon?** — Subtle "Support Phase 4" footer link makes sense given Patreon launched. Tone: not pushy, similar to existing README phrasing.

---

## 11. Pre-requisites before starting build

- ☐ Confirm with current backlog priority (depends on what's after v3.4.0 stabilization)
- ☐ Decide if Reddit posts (v3.4 refresh) happen before or after this build starts
- ☐ Validate that hosted-viewer URL changes won't break Giscolab fork (already broken by repo rename; offer help to him if he reaches out via Issue #1)
- ☐ Optional: Migrate the existing `map.html` inline JS to `visualizer/js/` modules as a preparatory commit (decouples the refactor from the new feature, reducing risk)

---

## 12. References

- **Repo:** https://github.com/Osyanne/CitiesSkylines2-osm-toolkit
- **Hosted (current):** https://osyanne.github.io/CitiesSkylines2-osm-toolkit/
- **Patreon:** https://www.patreon.com/c/CS2OSMToolkit
- **v3.4.0 PBF Migration spec:** `docs/superpowers/plans/2026-05-18-pbf-migration.md`
- **v3.3 Featured Cities Pack spec:** `docs/specs/2026-05-17-featured-cities-pack-design.md`
- **Toolkit reorg spec:** `docs/specs/2026-05-15-toolkit-reorg-design.md`
- **Giscolab fork analysis:** `Obsidian: 01-Proyectos/CS2-Mineapolis/🍴 Giscolab Fork — First Downstream Builder.md`
- **CityTimelineMod (Giscolab's downstream product):** https://github.com/Giscolab/CityTimeline-Mod
- **Giscolab's fork of toolkit:** https://github.com/Giscolab/cs2-minneapolis-zoning (12 commits ahead, refs to MapTiler, multi-bundle, water layer)
- **OpenTopography SRTM:** https://portal.opentopography.org/raster?opentopoID=OTSRTM.082016.4326.1
- **UPNG.js:** https://github.com/photopea/UPNG.js
- **JSZip:** https://stuk.github.io/jszip/
- **Nominatim API:** https://nominatim.openstreetmap.org/
- **Overpass API endpoints (rotation pool):**
  - https://overpass-api.de/api/interpreter
  - https://overpass.kumi.systems/api/interpreter
  - https://overpass.openstreetmap.ru/api/interpreter
  - https://maps.mail.ru/osm/tools/overpass/api/interpreter

---

## Appendix A: README.md template for the generated ZIP

```markdown
# Your City — Generated by OSM2CS

**City:** {{ city_name }}
**Bbox:** {{ south }}, {{ west }}, {{ north }}, {{ east }}
**Generated:** {{ ISO_timestamp }}
**Tool version:** v3.5.0 (browser-based generator)
**Source data:** OpenStreetMap (Overpass API) + SRTM v3 elevation

## What's inside

- `heightmap.png` — 16-bit PNG, 4096×4096px, 14.336km tile. Import into Cities Skylines 2 → Map Editor → Terrain → Import Heightmap.
- `zoning.geojson` — Real-world land use, classified into 11 CS2 zone types.
- `roads.geojson` — Real-world road network, classified into 6 CS2 road tiers.
- `services.geojson` — Hospitals, schools, fire stations, police, libraries, parks.
- `water.geojson` — Rivers, lakes, ocean polygons (visual reference).
- `preview.html` — Offline Leaflet viewer. Double-click won't work due to CORS; serve via any HTTP server, or open in a browser with `--allow-file-access-from-files`.

## How to use

1. Copy `heightmap.png` to your CS2 heightmaps folder (varies by OS, see [official CS2 docs](https://www.paradoxinteractive.com/games/cities-skylines-ii/about)).
2. Open CS2 → Map Editor → Terrain → Import Heightmap → select the PNG.
3. While building, keep `preview.html` open in a browser tab to reference real-world zoning, roads, services, and water.

## License

OSM data is © OpenStreetMap contributors, licensed under [ODbL](https://www.openstreetmap.org/copyright). Derived data in the GeoJSON files inherits this license. The heightmap PNG is derived from SRTM (public domain, NASA).

This bundle was generated by https://github.com/Osyanne/CitiesSkylines2-osm-toolkit — free, MIT-licensed.
```

---

**End of design spec — v3.5 browser-based city generator.**
