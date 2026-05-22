# Changelog

All notable changes to the cs2-osm-toolkit. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
follows [Semantic Versioning](https://semver.org/).

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
