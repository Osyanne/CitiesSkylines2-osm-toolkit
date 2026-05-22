# Landing Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current landing page (visualizer/index.html) with a redesigned Linear/Cal.com-style page generated from `src/shared/landing.py`, including hero with stats banner, region-filtered card grid with search, lazy-loaded thumbnails, and a discreet Patreon footer link.

**Architecture:** `landing.py` keeps the template responsibility but the CSS moves out to a sibling stylesheet `visualizer/assets/landing.css`. The HTML structure becomes richer (header / hero / stats / filter bar / grid / footer) and is computed from `cities.json` + per-city manifests as before. Filtering and search run client-side via ~30 lines of inline vanilla JS. `cities.json` gains an optional `country_code` field used by a Python helper to render flag emojis.

**Tech Stack:** Python 3.11+ (existing toolkit code), HTML/CSS/vanilla JS (no frontend framework, no npm), uv for task running, pytest for tests, Playwright for thumbnail generation (already wired in `[dependency-groups.thumbnails]`).

**Spec reference:** `docs/specs/2026-05-22-landing-redesign-design.md` (commit `d35e33b`).

**Working directory:** `C:/Users/osyanne/Documents/Claude/Projects/Proyecto mineapolis/cs2-minneapolis-zoning`. Branch: `main`. Starting commit: `d35e33b`.

**Note on existing CLI:** entry point is `generate-landing` (not `landing`). Per `src/pyproject.toml`. All commands below use the correct entry point.

---

## Task 1: Pre-flight checks

**Files:** None modified.

**Goal:** Verify environment is clean and existing tests pass before any changes.

- [ ] **Step 1.1: Verify clean working tree**

Run:
```bash
git status
```

Expected: working tree clean OR only the pre-existing `visualizer/cities/trondheim/` modifications from before this work started. No untracked files in `src/`, `docs/specs/`, `docs/superpowers/`, `visualizer/assets/`.

If there are unrelated modifications, stash them: `git stash push -m "pre-landing-redesign"`.

- [ ] **Step 1.2: Verify existing landing tests pass**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v
```

Expected: all 9 tests pass. (`test_landing_html_has_one_card_per_city`, `test_landing_html_shows_module_badges`, `test_landing_html_shows_feature_counts`, `test_landing_html_handles_city_without_manifest`, `test_landing_html_includes_request_city_cta`, plus 4 `test_format_count_*`.)

If any fail, STOP and investigate before modifying anything.

- [ ] **Step 1.3: Verify branch starting point**

Run:
```bash
git log --oneline -1
```

Expected: `d35e33b docs: landing redesign design spec + exploratory mockups`.

If different, STOP — the plan assumes this baseline.

---

## Task 2: Add `country_code` field to `cities.json`

**Files:**
- Modify: `cities.json` (root of repo)
- Test: `tests/shared/test_landing.py` (new test added)

**Goal:** Add ISO 3166-1 alpha-2 country codes to all 10 existing cities. Optional field — `registry.py` does not require it.

- [ ] **Step 2.1: Write the failing test**

Add to the END of `tests/shared/test_landing.py`:

```python
def test_cities_json_has_country_code_for_all_cities():
    """Every city in cities.json must have a valid ISO 3166-1 alpha-2 country_code."""
    import json
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    cities = json.loads((repo_root / "cities.json").read_text(encoding="utf-8"))
    for slug, entry in cities.items():
        assert "country_code" in entry, f"Missing country_code in {slug}"
        code = entry["country_code"]
        assert isinstance(code, str), f"{slug}: country_code must be string"
        assert len(code) == 2, f"{slug}: country_code must be 2 chars, got {code!r}"
        assert code.isupper() and code.isalpha(), f"{slug}: country_code must be uppercase letters, got {code!r}"
```

- [ ] **Step 2.2: Run the new test to verify it fails**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py::test_cities_json_has_country_code_for_all_cities -v
```

Expected: FAIL with `Missing country_code in minneapolis`.

- [ ] **Step 2.3: Add `country_code` to all 10 cities in `cities.json`**

Edit `cities.json`. For each city entry, add `"country_code"` field right after `"country"`. Mapping:

| Slug | country | country_code |
|------|---------|--------------|
| minneapolis | USA | US |
| amsterdam | Netherlands | NL |
| madison | USA | US |
| charleston | USA | US |
| mafra_sc_brazil | Brazil | BR |
| trondheim | Norway | NO |
| bacau_ro | Romania | RO |
| fayetteville_nc | USA | US |
| sacramento | USA | US |
| new_york | USA | US |

Example diff for first entry:
```diff
   "minneapolis": {
     "display_name": "Minneapolis, MN",
     "country": "USA",
+    "country_code": "US",
     "bbox": [44.86, -93.38, 45.05, -93.17],
```

- [ ] **Step 2.4: Run the test to verify it passes**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py::test_cities_json_has_country_code_for_all_cities -v
```

Expected: PASS.

- [ ] **Step 2.5: Run the full landing test suite to verify nothing else broke**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 2.6: Commit**

```bash
git add cities.json tests/shared/test_landing.py
git commit -m "feat(cities): add ISO country_code field to all 10 cities

Optional field used by landing.py to render flag emojis. registry.py
REQUIRED_CITY_FIELDS unchanged — country_code is forward-compatible."
```

---

## Task 3: Add `country_to_flag()` helper

**Files:**
- Modify: `src/shared/landing.py` (add function)
- Test: `tests/shared/test_landing.py` (add tests)

**Goal:** Convert ISO 3166-1 alpha-2 code to flag emoji using Unicode regional indicator symbols.

- [ ] **Step 3.1: Write failing tests**

Append to `tests/shared/test_landing.py`:

```python
def test_country_to_flag_usa():
    from shared.landing import country_to_flag
    assert country_to_flag("US") == "🇺🇸"


def test_country_to_flag_lowercase_normalized():
    from shared.landing import country_to_flag
    assert country_to_flag("us") == "🇺🇸"


def test_country_to_flag_netherlands():
    from shared.landing import country_to_flag
    assert country_to_flag("NL") == "🇳🇱"


def test_country_to_flag_empty_returns_empty():
    from shared.landing import country_to_flag
    assert country_to_flag("") == ""
    assert country_to_flag(None) == ""
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k country_to_flag
```

Expected: 4 tests FAIL with `ImportError: cannot import name 'country_to_flag'`.

- [ ] **Step 3.3: Implement the helper**

Add to `src/shared/landing.py` right after the `_format_count` function (around line 28):

```python
def country_to_flag(code: str | None) -> str:
    """ISO 3166-1 alpha-2 code → flag emoji via regional indicator chars.

    Returns empty string for falsy or invalid input (graceful fallback for
    cities without a country_code field).
    """
    if not code or len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in code)
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k country_to_flag
```

Expected: 4 tests PASS.

- [ ] **Step 3.5: Commit**

```bash
git add src/shared/landing.py tests/shared/test_landing.py
git commit -m "feat(landing): add country_to_flag() helper

ISO 3166-1 alpha-2 → emoji via regional indicator chars. Graceful
empty-string fallback for missing/invalid input."
```

---

## Task 4: Add `COUNTRY_TO_REGION` map + `region_counts()`

**Files:**
- Modify: `src/shared/landing.py`
- Test: `tests/shared/test_landing.py`

**Goal:** Provide region grouping for filter pills. Region mapping lives in code, not in `cities.json` (centralized; rarely changes).

- [ ] **Step 4.1: Write failing tests**

Append to `tests/shared/test_landing.py`:

```python
def test_region_counts_basic():
    from shared.landing import region_counts
    cities = {
        "a": {"country": "USA", "display_name": "A", "tagline": "", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
        "b": {"country": "Netherlands", "display_name": "B", "tagline": "", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
        "c": {"country": "USA", "display_name": "C", "tagline": "", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
        "d": {"country": "Brazil", "display_name": "D", "tagline": "", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
    }
    counts = region_counts(cities)
    assert counts["all"] == 4
    assert counts["north-america"] == 2
    assert counts["europe"] == 1
    assert counts["south-america"] == 1


def test_region_counts_unknown_country_goes_to_other():
    from shared.landing import region_counts
    cities = {
        "x": {"country": "Atlantis", "display_name": "X", "tagline": "", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
    }
    counts = region_counts(cities)
    assert counts["all"] == 1
    assert counts.get("other", 0) == 1


def test_country_to_region_known_countries():
    from shared.landing import COUNTRY_TO_REGION
    assert COUNTRY_TO_REGION["USA"] == "north-america"
    assert COUNTRY_TO_REGION["Netherlands"] == "europe"
    assert COUNTRY_TO_REGION["Brazil"] == "south-america"
    assert COUNTRY_TO_REGION["Norway"] == "europe"
    assert COUNTRY_TO_REGION["Romania"] == "europe"
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k "region_counts or country_to_region"
```

Expected: 3 tests FAIL with `ImportError`.

- [ ] **Step 4.3: Add the constant and function to `landing.py`**

Add to `src/shared/landing.py` right after `country_to_flag()`:

```python
COUNTRY_TO_REGION = {
    # North America
    "USA": "north-america",
    "Canada": "north-america",
    "Mexico": "north-america",
    # Europe
    "Netherlands": "europe",
    "Norway": "europe",
    "Romania": "europe",
    "Germany": "europe",
    "France": "europe",
    "UK": "europe",
    "Spain": "europe",
    "Italy": "europe",
    "Portugal": "europe",
    # South America
    "Brazil": "south-america",
    "Argentina": "south-america",
    "Chile": "south-america",
    "Colombia": "south-america",
    # Asia (placeholder for future)
    "Japan": "asia",
    "China": "asia",
    "South Korea": "asia",
}


def region_counts(cities: dict) -> dict[str, int]:
    """Count cities per region for filter pills. Always includes 'all' key."""
    counts = {"all": len(cities)}
    for entry in cities.values():
        region = COUNTRY_TO_REGION.get(entry["country"], "other")
        counts[region] = counts.get(region, 0) + 1
    return counts
```

- [ ] **Step 4.4: Run tests to verify they pass**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k "region_counts or country_to_region"
```

Expected: 3 tests PASS.

- [ ] **Step 4.5: Commit**

```bash
git add src/shared/landing.py tests/shared/test_landing.py
git commit -m "feat(landing): add COUNTRY_TO_REGION map + region_counts()

Centralized country→region mapping used by filter pills. Unknown
countries map to 'other'. Pre-populated with current 5 countries +
common ones for future city requests."
```

---

## Task 5: Add `build_stats()` helper

**Files:**
- Modify: `src/shared/landing.py`
- Test: `tests/shared/test_landing.py`

**Goal:** Compute the 4 stats banner numbers (cities count, total features, countries count, version) from inputs.

- [ ] **Step 5.1: Write failing tests**

Append to `tests/shared/test_landing.py`:

```python
def test_build_stats_basic_counts():
    from shared.landing import build_stats
    cities = {
        "a": {"country": "USA", "display_name": "A", "tagline": "", "country_code": "US", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
        "b": {"country": "Netherlands", "display_name": "B", "tagline": "", "country_code": "NL", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
        "c": {"country": "USA", "display_name": "C", "tagline": "", "country_code": "US", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
    }
    manifests = {
        "a": {"modules": {"zoning": {"features": 100}, "vial": {"features": 50}}},
        "b": {"modules": {"zoning": {"features": 200}}},
        "c": {"modules": {"zoning": {"features": 1000}}},
    }
    stats = build_stats(cities, manifests)
    assert stats["cities_count"] == 3
    assert stats["features_total"] == "1.4k"  # 100+50+200+1000 = 1350 → 1.4k via _format_count
    assert stats["countries_count"] == 2  # USA + Netherlands


def test_build_stats_handles_missing_manifest():
    from shared.landing import build_stats
    cities = {
        "a": {"country": "USA", "display_name": "A", "tagline": "", "country_code": "US", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"},
    }
    manifests = {}  # missing entirely
    stats = build_stats(cities, manifests)
    assert stats["cities_count"] == 1
    assert stats["features_total"] == "0"
    assert stats["countries_count"] == 1


def test_build_stats_includes_version():
    from shared.landing import build_stats
    cities = {"a": {"country": "USA", "display_name": "A", "tagline": "", "country_code": "US", "bbox":[0,0,0,0],"center":[0,0],"zoom":12,"locale":"es"}}
    manifests = {}
    stats = build_stats(cities, manifests)
    assert "version" in stats
    assert stats["version"].startswith("v")
    assert "." in stats["version"]  # like "v3.4"
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k build_stats
```

Expected: 3 tests FAIL with `ImportError`.

- [ ] **Step 5.3: Add `build_stats()` and `_read_version_short()` to `landing.py`**

Add to `src/shared/landing.py` right after `region_counts()`:

```python
def _read_version_short(default: str = "v3.4") -> str:
    """Reads major.minor from pyproject.toml. Falls back to default on any error."""
    try:
        import tomllib  # Python 3.11+
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        full = data["project"]["version"]  # ej. "3.4.0"
        parts = full.split(".")
        return f"v{parts[0]}.{parts[1]}"
    except Exception:
        return default


def build_stats(cities: dict, manifests: dict) -> dict:
    """Compute 4 stats for the hero banner."""
    total_features = 0
    for slug, manifest in manifests.items():
        if not manifest:
            continue
        for mod in manifest.get("modules", {}).values():
            total_features += mod.get("features", 0)
    return {
        "cities_count": len(cities),
        "features_total": _format_count(total_features),
        "countries_count": len(set(c["country"] for c in cities.values())),
        "version": _read_version_short(),
    }
```

- [ ] **Step 5.4: Run tests to verify they pass**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k build_stats
```

Expected: 3 tests PASS.

- [ ] **Step 5.5: Commit**

```bash
git add src/shared/landing.py tests/shared/test_landing.py
git commit -m "feat(landing): add build_stats() + _read_version_short()

build_stats() returns the 4 numbers for the new hero banner.
_read_version_short() pulls major.minor from pyproject.toml with
defensive fallback."
```

---

## Task 6: Create `visualizer/assets/landing.css`

**Files:**
- Create: `visualizer/assets/landing.css`

**Goal:** Extract all landing styles into a single stylesheet covering nav, hero, stats banner, filter bar, card grid, request-card, empty state, footer, hover states, responsive breakpoints, accessibility (reduced motion, focus rings).

- [ ] **Step 6.1: Create the CSS file with all sections**

Create `visualizer/assets/landing.css` with the following content:

```css
/* CS2 OSM Toolkit — Landing styles
   Generated alongside index.html by src/shared/landing.py
   See docs/specs/2026-05-22-landing-redesign-design.md */

* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0e0e10;
  --bg-elevated-from: #18181b;
  --bg-elevated-to: #0f0f12;
  --border: rgba(255,255,255,0.06);
  --border-hover: rgba(94,106,210,0.4);
  --text: #fafafa;
  --text-muted: #a0a0a8;
  --text-dim: #71717a;
  --accent: #5e6ad2;
  --accent-soft: #c4b5fd;
}

html { scroll-behavior: smooth; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.5;
  overflow-x: hidden;
}

body::before {
  content: '';
  position: fixed;
  top: -20%; left: 50%; transform: translateX(-50%);
  width: 1200px; height: 800px;
  background: radial-gradient(circle, rgba(94,106,210,0.15) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

.wrap { position: relative; z-index: 1; max-width: 1280px; margin: 0 auto; padding: 0 2rem; }

.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}

/* Focus visible (keyboard only) */
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
:focus:not(:focus-visible) { outline: none; }

/* ---------- nav ---------- */
nav.top {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.2rem 0;
  border-bottom: 1px solid var(--border);
}
nav.top .brand {
  display: flex; align-items: center; gap: 0.6rem;
  font-weight: 600; font-size: 0.95rem;
}
nav.top .brand .logo {
  width: 26px; height: 26px;
  background: linear-gradient(135deg, #5e6ad2, #8b5cf6);
  border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem;
}
nav.top .brand .ver {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-dim);
  padding: 0.15rem 0.45rem;
  background: rgba(255,255,255,0.05);
  border-radius: 4px;
  margin-left: 0.4rem;
}
nav.top .links { display: flex; gap: 1.5rem; align-items: center; font-size: 0.85rem; }
nav.top .links a { color: var(--text-muted); text-decoration: none; transition: color .15s; }
nav.top .links a:hover { color: var(--text); }
nav.top .links .cta {
  background: var(--text); color: var(--bg);
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  font-weight: 500;
}
nav.top .links .cta:hover { background: #e5e5e7; color: var(--bg); }

/* ---------- hero ---------- */
.hero { padding: 5rem 0 3rem; text-align: center; }
.hero .badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.35rem 0.85rem;
  background: rgba(94,106,210,0.1);
  border: 1px solid rgba(94,106,210,0.3);
  border-radius: 999px;
  font-size: 0.8rem;
  color: var(--accent-soft);
  margin-bottom: 1.8rem;
  text-decoration: none;
}
.hero .badge .dot {
  width: 6px; height: 6px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.hero h1 {
  font-size: clamp(2.5rem, 5vw, 3.8rem);
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.05;
  margin-bottom: 1.2rem;
}
.hero h1 .grad {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-soft) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.hero .lede {
  font-size: 1.15rem;
  color: var(--text-muted);
  max-width: 560px;
  margin: 0 auto 2rem;
}
.hero .ctas { display: flex; gap: 0.8rem; justify-content: center; margin-bottom: 3rem; }
.hero .ctas a {
  padding: 0.7rem 1.4rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.9rem;
  text-decoration: none;
  transition: background .15s;
}
.hero .ctas .primary { background: var(--text); color: var(--bg); }
.hero .ctas .primary:hover { background: #e5e5e7; }
.hero .ctas .secondary {
  background: rgba(255,255,255,0.05);
  color: var(--text);
  border: 1px solid rgba(255,255,255,0.1);
}
.hero .ctas .secondary:hover { background: rgba(255,255,255,0.08); }

/* ---------- stats banner ---------- */
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  padding: 1.5rem 0;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent);
  margin-bottom: 4rem;
}
.stats > div { text-align: center; border-right: 1px solid var(--border); }
.stats > div:last-child { border-right: none; }
.stats strong {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.8rem;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 0.15rem;
  letter-spacing: -0.02em;
}
.stats span {
  font-size: 0.75rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* ---------- filter bar ---------- */
.filter-bar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap;
}
.filter-pills { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.filter-pills button {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: var(--text-muted);
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-family: inherit;
  cursor: pointer;
  transition: all .15s;
}
.filter-pills button:hover { background: rgba(255,255,255,0.08); }
.filter-pills button.active { background: var(--text); color: var(--bg); border-color: var(--text); }
.search { position: relative; }
.search input {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: var(--text);
  padding: 0.45rem 0.85rem 0.45rem 2rem;
  border-radius: 6px;
  font-size: 0.85rem;
  width: 220px;
  font-family: inherit;
  transition: border-color .15s;
}
.search input::placeholder { color: var(--text-dim); }
.search:focus-within input { border-color: var(--accent); }
.search::before {
  content: '⌕';
  position: absolute;
  left: 0.7rem; top: 50%; transform: translateY(-50%);
  color: var(--text-dim);
  font-size: 0.9rem;
  pointer-events: none;
}

/* ---------- card grid ---------- */
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 4rem;
}
.card {
  background: linear-gradient(180deg, var(--bg-elevated-from) 0%, var(--bg-elevated-to) 100%);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all .2s;
  position: relative;
  text-decoration: none;
  color: inherit;
  display: block;
}
.card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
  box-shadow: 0 12px 24px -8px rgba(94,106,210,0.15);
}
.card .thumb {
  aspect-ratio: 16/10;
  background-color: #18181b;
  position: relative;
  overflow: hidden;
}
.card .thumb img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
}
.card .thumb::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(15,15,18,0.6) 100%);
  pointer-events: none;
}
.card .body { padding: 0.9rem 1rem 1rem; }
.card h4 {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 0.1rem;
  letter-spacing: -0.01em;
}
.card .loc {
  font-size: 0.75rem;
  color: var(--text-dim);
  margin-bottom: 0.6rem;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.02em;
}
.card .tag {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-bottom: 0.9rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card .meta {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 0.7rem;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.card .modules { display: flex; gap: 0.25rem; }
.card .modules .mod {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px rgba(94,106,210,0.5);
}
.card .modules .mod.off { background: rgba(255,255,255,0.1); box-shadow: none; }
.card .count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* ---------- request city card ---------- */
.card.request {
  grid-column: span 2;
  background: transparent;
  border: 1px dashed var(--text-dim);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
}
.card.request:hover {
  border-color: var(--accent);
  border-style: solid;
  transform: none;
  box-shadow: none;
}
.card.request .plus {
  color: var(--text-dim);
  margin-bottom: 1rem;
  transition: color .15s;
}
.card.request:hover .plus { color: var(--accent); }
.card.request h4 {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 0.4rem;
  letter-spacing: -0.01em;
}
.card.request p {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  max-width: 280px;
}
.card.request .cta {
  font-size: 0.85rem;
  color: var(--accent-soft);
  font-weight: 500;
}

/* ---------- empty state ---------- */
.empty-state {
  display: none;
  padding: 3rem;
  text-align: center;
  border: 1px dashed var(--border);
  border-radius: 12px;
  color: var(--text-muted);
  margin-bottom: 4rem;
}
.empty-state.visible { display: block; }
.empty-state a { color: var(--accent-soft); text-decoration: none; font-weight: 500; }

/* ---------- footer ---------- */
footer {
  padding: 2.5rem 0 3rem;
  border-top: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  font-size: 0.82rem;
  color: var(--text-dim);
  flex-wrap: wrap; gap: 1rem;
}
footer a { color: var(--text-muted); text-decoration: none; transition: color .15s; }
footer a:hover { color: var(--text); }
footer .right { display: flex; gap: 1.5rem; }
footer .patreon-link { color: var(--accent-soft); }
footer .patreon-link:hover { color: var(--accent); }

/* ---------- responsive ---------- */
@media (max-width: 1023px) {
  .grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 767px) {
  .grid { grid-template-columns: repeat(2, 1fr); }
  .card.request { grid-column: span 1; }
  nav.top .links a[data-secondary] { display: none; }
}
@media (max-width: 639px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  .stats > div:nth-child(-n+2) { border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1rem; }
  .stats > div:nth-child(2) { border-right: none; }
  .stats > div:nth-child(3) { border-right: 1px solid var(--border); }
  .filter-bar .search { width: 100%; }
  .filter-bar .search input { width: 100%; }
}
@media (max-width: 479px) {
  .wrap { padding: 0 1rem; }
  .grid { grid-template-columns: 1fr; }
  .hero { padding: 3rem 0 2rem; }
  nav.top .links a[data-tertiary] { display: none; }
}

/* ---------- reduced motion ---------- */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
  html { scroll-behavior: auto; }
  .hero .badge .dot { animation: none; }
  .card:hover { transform: none; }
}
```

- [ ] **Step 6.2: Commit**

```bash
git add visualizer/assets/landing.css
git commit -m "feat(landing): add landing.css with full redesign styles

Linear/Cal.com style — design tokens, hero with gradient headline,
stats banner, filter pills + search, 3-col card grid, request-city
card, footer with Patreon link, responsive breakpoints, reduced-motion
support."
```

---

## Task 7: Rewrite `_card_html()` to produce the new card markup

**Files:**
- Modify: `src/shared/landing.py`
- Test: `tests/shared/test_landing.py`

**Goal:** Replace the existing card HTML generator with one that emits the new structure (img with lazy loading, flag + country in loc, module dots, count in mono, data attributes for filter/search).

- [ ] **Step 7.1: Update the existing test helper `_city_entry` to include country_code**

Edit `tests/shared/test_landing.py`. Find the `_city_entry` function (around line 11) and update:

```python
def _city_entry(name="Test", country="USA", tagline="t", country_code="US"):
    return {
        "display_name": name, "country": country,
        "country_code": country_code,
        "bbox": [44.86, -93.38, 45.05, -93.17],
        "center": [44.97, -93.27], "zoom": 12,
        "tagline": tagline, "locale": "es"
    }
```

- [ ] **Step 7.2: Write new tests for the rewritten card markup**

Append to `tests/shared/test_landing.py`:

```python
def test_card_html_has_lazy_loaded_img():
    from shared.landing import _card_html
    entry = _city_entry("Minneapolis, MN", "USA", "tag", "US")
    manifest = {"modules": {"zoning": {"features": 100}}}
    html = _card_html("minneapolis", entry, manifest)
    assert '<img' in html
    assert 'loading="lazy"' in html
    assert 'src="assets/thumbnails/minneapolis.png"' in html
    assert 'alt=' in html


def test_card_html_has_data_region_and_data_search():
    from shared.landing import _card_html
    entry = _city_entry("Minneapolis, MN", "USA", "Ciudad hero", "US")
    manifest = {"modules": {"zoning": {"features": 100}}}
    html = _card_html("minneapolis", entry, manifest)
    assert 'data-region="north-america"' in html
    # data-search should be lowercase concatenation of name/country/tagline
    assert 'data-search="' in html
    assert "ciudad hero" in html.lower()


def test_card_html_has_flag_emoji():
    from shared.landing import _card_html
    entry = _city_entry("Amsterdam", "Netherlands", "tag", "NL")
    manifest = {"modules": {"zoning": {"features": 100}}}
    html = _card_html("amsterdam", entry, manifest)
    assert "🇳🇱" in html


def test_card_html_module_dots_reflect_available_modules():
    from shared.landing import _card_html
    entry = _city_entry("M", "USA", "t", "US")

    # All 3 modules present → 3 "on" dots, 0 "off"
    manifest_full = {"modules": {"zoning": {"features": 1}, "vial": {"features": 1}, "services": {"features": 1}}}
    html_full = _card_html("m", entry, manifest_full)
    assert html_full.count('class="mod"') == 3  # substring matches ONLY on-dots (off has 'class="mod off"')
    assert "mod off" not in html_full

    # Only zoning → 1 "on", 2 "off"
    manifest_partial = {"modules": {"zoning": {"features": 1}}}
    html_partial = _card_html("m", entry, manifest_partial)
    assert html_partial.count('class="mod"') == 1
    assert html_partial.count("mod off") == 2


def test_card_html_missing_manifest_shows_pending_state():
    from shared.landing import _card_html
    entry = _city_entry("Future", "USA", "t", "US")
    html = _card_html("future", entry, None)
    assert "future" in html.lower()
    # Pending state: all 3 dots off + a "0" count or "—" placeholder
    assert html.count("mod off") == 3
    assert "0" in html or "—" in html


def test_card_html_handles_missing_country_code_gracefully():
    """Old cities.json entries without country_code should still render (no flag)."""
    from shared.landing import _card_html
    entry = {
        "display_name": "Old City", "country": "USA",
        "bbox": [0,0,0,0], "center": [0,0], "zoom": 12,
        "tagline": "t", "locale": "es"
        # No country_code
    }
    manifest = {"modules": {"zoning": {"features": 100}}}
    html = _card_html("old_city", entry, manifest)
    assert "Old City" in html  # Doesn't crash
```

- [ ] **Step 7.3: Run tests to verify they fail**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k card_html
```

Expected: 6 new tests FAIL. Existing `test_landing_html_*` may also fail depending on assertions (they reference old class names) — that's expected and fixed in Task 8.

- [ ] **Step 7.4: Rewrite `_card_html()` in `landing.py`**

Find the existing `_card_html` function in `src/shared/landing.py` (around line 30) and REPLACE it entirely with:

```python
def _card_html(slug: str, entry: dict, manifest: dict | None) -> str:
    """Generate the <a class='card'> for one city."""
    name = html.escape(entry["display_name"])
    country = html.escape(entry["country"])
    country_code = entry.get("country_code", "")
    tagline = html.escape(entry["tagline"])
    flag = country_to_flag(country_code)
    region = COUNTRY_TO_REGION.get(entry["country"], "other")

    # Precomputed lowercase search index (avoids client-side toLowerCase per keystroke)
    search_index = html.escape(
        f"{entry['display_name']} {entry['country']} {entry['tagline']}".lower()
    )

    # Module dots — fixed order: zoning, vial, services
    if manifest is None or not manifest.get("modules"):
        mods_html = (
            '<span class="mod off" aria-label="Zoning not available"></span>'
            '<span class="mod off" aria-label="Vial not available"></span>'
            '<span class="mod off" aria-label="Services not available"></span>'
        )
        total = 0
    else:
        present = manifest.get("modules", {})
        labels = {
            "zoning": "Zoning",
            "vial": "Vial",
            "services": "Services",
        }
        dot_pieces = []
        for key in ("zoning", "vial", "services"):
            label = labels[key]
            if key in present:
                dot_pieces.append(
                    f'<span class="mod" aria-label="{label} available"></span>'
                )
            else:
                dot_pieces.append(
                    f'<span class="mod off" aria-label="{label} not available"></span>'
                )
        mods_html = "".join(dot_pieces)
        total = sum(d.get("features", 0) for d in present.values())

    flag_html = f"{flag} " if flag else ""

    return (
        f'<a href="map.html?city={html.escape(slug)}" class="card"'
        f' data-region="{region}"'
        f' data-search="{search_index}">'
        f'<div class="thumb">'
        f'<img loading="lazy" src="assets/thumbnails/{html.escape(slug)}.png"'
        f' alt="Zoning map of {name}">'
        f'</div>'
        f'<div class="body">'
        f'<h4>{name}</h4>'
        f'<div class="loc">{flag_html}{country}</div>'
        f'<div class="tag">{tagline}</div>'
        f'<div class="meta">'
        f'<div class="modules">{mods_html}</div>'
        f'<span class="count">{_format_count(total)}</span>'
        f'</div>'
        f'</div>'
        f'</a>'
    )
```

- [ ] **Step 7.5: Run new tests to verify they pass**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v -k card_html
```

Expected: 6 tests PASS.

- [ ] **Step 7.6: Note tests still failing from old assertions**

Run the full test file:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v
```

Expected failures (will be fixed in Task 8):
- `test_landing_html_has_one_card_per_city` — looks for `class="city-card"` (old)
- `test_landing_html_shows_module_badges` — looks for "Zoning"/"Vial"/"Servicios" text labels (now aria-only)
- `test_landing_html_handles_city_without_manifest` — looks for "Sin datos" / "pending" text

Do NOT modify those tests yet — they validate the OLD template which we replace next task.

- [ ] **Step 7.7: Commit**

```bash
git add src/shared/landing.py tests/shared/test_landing.py
git commit -m "feat(landing): rewrite _card_html() for new design

New markup: lazy-loaded <img>, flag emoji from country_code, region
data attribute for filtering, precomputed data-search for fast client
filtering, module dots with aria-labels. Graceful fallback for missing
country_code (no flag, still renders).

Old build_landing_html assertions still failing — fixed in next commit."
```

---

## Task 8: Rewrite `build_landing_html()` with new full-page template

**Files:**
- Modify: `src/shared/landing.py`
- Modify: `tests/shared/test_landing.py` (update existing + add new tests)

**Goal:** Replace the whole HTML template with the new structure (header + hero + stats + filter bar + grid + request-card + empty state + footer + JS). Link the external CSS instead of inlining.

- [ ] **Step 8.1: Update existing test assertions for new markup**

Edit `tests/shared/test_landing.py`. Update the existing tests:

In `test_landing_html_has_one_card_per_city`, replace `'class="city-card"'` with `'class="card"`:

```python
def test_landing_html_has_one_card_per_city():
    cities = {
        "minneapolis": _city_entry("Minneapolis, MN"),
        "manhattan": _city_entry("Manhattan, NYC"),
    }
    manifests = {
        "minneapolis": {"modules": {"zoning": {"hash": "a", "features": 100},
                                     "vial": {"hash": "b", "features": 200},
                                     "services": {"hash": "c", "features": 50}}},
        "manhattan": {"modules": {"zoning": {"hash": "d", "features": 500}}},
    }
    html = build_landing_html(cities, manifests)
    # Count only city cards (not the request-city card)
    assert html.count('class="card"') == 2  # 2 cities, request-card uses class="card request"
    assert 'href="map.html?city=minneapolis"' in html
    assert 'href="map.html?city=manhattan"' in html
    assert "Minneapolis, MN" in html
    assert "Manhattan, NYC" in html
```

Replace `test_landing_html_shows_module_badges` with version that checks module dots instead of text badges:

```python
def test_landing_html_shows_module_dots():
    cities = {
        "minneapolis": _city_entry("Mpls"),
        "manhattan": _city_entry("Man"),
    }
    manifests = {
        "minneapolis": {"modules": {"zoning": {"hash":"a","features":1},
                                     "vial": {"hash":"b","features":1},
                                     "services": {"hash":"c","features":1}}},
        "manhattan": {"modules": {"zoning": {"hash":"d","features":1}}},
    }
    html = build_landing_html(cities, manifests)
    mpls_section = html[html.index("Mpls"):html.index("Man")]
    # All 3 modules → 3 "on" dots, 0 "off"
    assert mpls_section.count('class="mod"') == 3
    assert "mod off" not in mpls_section

    man_section = html[html.index("Man"):]
    # Only zoning → 1 "on", 2 "off"
    # (request-card and footer don't contain .mod elements, so counts are clean)
    assert man_section.count('class="mod"') == 1
    assert man_section.count("mod off") == 2
```

Update `test_landing_html_handles_city_without_manifest` to check for the new pending state representation:

```python
def test_landing_html_handles_city_without_manifest():
    """Ciudad en registro pero sin manifest (ej. recién agregada, no extraída aún)."""
    cities = {"future_city": _city_entry("Future")}
    manifests = {}
    html = build_landing_html(cities, manifests)
    assert "Future" in html
    # Pending state in new design = all 3 dots off + count "0"
    future_section = html[html.index("Future"):]
    assert future_section.count("mod off") == 3
```

The `test_landing_html_includes_request_city_cta` test is unchanged — the request-city card and footer still link to the issue template.

- [ ] **Step 8.2: Write NEW tests for the new template sections**

Append to `tests/shared/test_landing.py`:

```python
def test_landing_html_links_external_stylesheet():
    cities = {"minneapolis": _city_entry("M")}
    manifests = {"minneapolis": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert 'href="assets/landing.css"' in html
    assert '<style' not in html  # No inline styles


def test_landing_html_has_header_with_brand_and_version():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert "CS2 OSM Toolkit" in html
    # Version tag (auto from pyproject)
    assert "v3.4" in html or "v3.5" in html  # current or near-future


def test_landing_html_has_hero_with_headline_and_ctas():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert '<h1' in html
    assert "Cities: Skylines 2" in html
    assert 'href="#gallery"' in html  # primary CTA anchor


def test_landing_html_has_stats_banner_with_4_stats():
    cities = {
        "a": _city_entry("A", "USA", "t", "US"),
        "b": _city_entry("B", "Netherlands", "t", "NL"),
        "c": _city_entry("C", "Brazil", "t", "BR"),
    }
    manifests = {
        "a": {"modules": {"zoning": {"features": 100}}},
        "b": {"modules": {"zoning": {"features": 200}}},
        "c": {"modules": {"zoning": {"features": 300}}},
    }
    html = build_landing_html(cities, manifests)
    assert 'class="stats"' in html
    # Cities count
    assert ">3<" in html
    # Total features 600 → "600"
    assert "600" in html
    # Countries 3 → ">3<"
    # Version
    assert "v3.4" in html or "v3.5" in html


def test_landing_html_has_filter_pills():
    cities = {
        "a": _city_entry("A", "USA", "t", "US"),
        "b": _city_entry("B", "Netherlands", "t", "NL"),
    }
    manifests = {"a": {"modules": {"zoning": {"features": 1}}},
                 "b": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert 'data-region="all"' in html
    assert 'data-region="north-america"' in html
    assert 'data-region="europe"' in html
    # Counts: All · 2, North America · 1, Europe · 1
    assert "All" in html
    assert "North America" in html
    assert "Europe" in html


def test_landing_html_has_search_input():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert '<input' in html
    assert 'id="search"' in html
    assert 'type="search"' in html


def test_landing_html_has_request_city_card():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert 'class="card request"' in html
    assert "Request your city" in html
    assert "issues/new" in html  # link to issue template


def test_landing_html_has_empty_state_hidden_by_default():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert 'class="empty-state"' in html
    assert "No cities match" in html


def test_landing_html_has_footer_with_patreon_link():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert '<footer' in html
    assert "patreon" in html.lower()


def test_landing_html_includes_filter_javascript():
    cities = {"m": _city_entry("M")}
    manifests = {"m": {"modules": {"zoning": {"features": 1}}}}
    html = build_landing_html(cities, manifests)
    assert '<script' in html
    assert "addEventListener" in html
```

- [ ] **Step 8.3: Run failing tests to verify they fail**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v
```

Expected: many new tests FAIL with `class="card"` count off, missing `assets/landing.css`, missing `<h1`, etc. Some old tests may still fail.

- [ ] **Step 8.4: Add new constants + `_build_pills_html`, then rewrite `build_landing_html`**

The existing file already has `REPO_URL` and `ISSUE_NEW_URL` near the top — DO NOT redeclare them. Add `PATREON_URL` and `REGION_LABELS` right after `ISSUE_NEW_URL`. Then add `_build_pills_html` before the existing `build_landing_html`. Finally, REPLACE the body of `build_landing_html` entirely.

Add right after `ISSUE_NEW_URL` (around line 18 of the current file):

```python
PATREON_URL = "https://www.patreon.com/c/CS2OSMToolkit"

# Region display names for pills (slug → label)
REGION_LABELS = {
    "all": "All",
    "north-america": "North America",
    "europe": "Europe",
    "south-america": "South America",
    "asia": "Asia",
    "africa": "Africa",
    "oceania": "Oceania",
    "other": "Other",
}


def _build_pills_html(cities: dict) -> str:
    """Generate the filter pill buttons. 'all' is always active by default."""
    counts = region_counts(cities)
    # Always include 'all' first
    pills = [("all", counts["all"])]
    # Then any region present (in defined order)
    for slug in ("north-america", "europe", "south-america", "asia", "africa", "oceania", "other"):
        if slug in counts:
            pills.append((slug, counts[slug]))
    pieces = []
    for i, (slug, count) in enumerate(pills):
        active = ' class="active" aria-pressed="true"' if i == 0 else ' aria-pressed="false"'
        label = REGION_LABELS.get(slug, slug.title())
        pieces.append(
            f'<button{active} data-region="{slug}">{label} · {count}</button>'
        )
    return "\n        ".join(pieces)


def build_landing_html(cities: dict, manifests: dict) -> str:
    """Build the complete landing HTML."""
    cards = "\n".join(
        _card_html(slug, entry, manifests.get(slug))
        for slug, entry in cities.items()
    )
    stats = build_stats(cities, manifests)
    pills_html = _build_pills_html(cities)

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CS2 OSM Toolkit — Real-world cities for your CS2 builds</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/landing.css">
</head>
<body>
  <div class="wrap">
    <nav class="top">
      <div class="brand">
        <div class="logo">🏙</div>
        CS2 OSM Toolkit
        <span class="ver">{stats["version"]}</span>
      </div>
      <div class="links">
        <a href="{REPO_URL}#readme" data-secondary>Docs</a>
        <a href="{REPO_URL}/blob/main/METHODOLOGY.md" data-secondary>Methodology</a>
        <a href="{REPO_URL}" data-tertiary>GitHub</a>
        <a href="{PATREON_URL}" class="cta">Support →</a>
      </div>
    </nav>

    <section class="hero">
      <a class="badge" href="{REPO_URL}#roadmap"><span class="dot"></span> v3.5 — Browser generator in development</a>
      <h1>OpenStreetMap zoning<br>for <span class="grad">Cities: Skylines 2</span> builders.</h1>
      <p class="lede">Real-world cities, ready to import. Open data, open source, zero friction. Browse {stats["cities_count"]} curated maps or request your own.</p>
      <div class="ctas">
        <a href="#gallery" class="primary">Browse cities ↓</a>
        <a href="{ISSUE_NEW_URL}" class="secondary" target="_blank" rel="noopener">Request your city</a>
      </div>

      <div class="stats" role="list" aria-label="Project stats">
        <div role="listitem"><strong>{stats["cities_count"]}</strong><span>Cities</span></div>
        <div role="listitem"><strong>{stats["features_total"]}</strong><span>Features</span></div>
        <div role="listitem"><strong>{stats["countries_count"]}</strong><span>Countries</span></div>
        <div role="listitem"><strong>{stats["version"]}</strong><span>Version</span></div>
      </div>
    </section>

    <section id="gallery">
      <h2 class="sr-only">Featured cities</h2>
      <div class="filter-bar">
        <label class="sr-only" for="search">Search cities</label>
        <div class="filter-pills" role="group" aria-label="Filter by region">
        {pills_html}
        </div>
        <div class="search">
          <input id="search" type="search" placeholder="Search cities…" autocomplete="off">
        </div>
      </div>

      <div class="grid">
{cards}
        <a class="card request" href="{ISSUE_NEW_URL}" target="_blank" rel="noopener">
          <svg class="plus" viewBox="0 0 24 24" width="32" height="32" stroke="currentColor" stroke-width="1.5" fill="none" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <h4>Request your city</h4>
          <p>Open an issue with your bbox and we'll add it to the collection.</p>
          <span class="cta">Open issue template →</span>
        </a>
      </div>

      <div id="empty-state" class="empty-state">
        <p>No cities match. Try a different filter, or <a href="{ISSUE_NEW_URL}" target="_blank" rel="noopener">request your city →</a></p>
      </div>
    </section>

    <footer>
      <div>MIT licensed · OSM data © OpenStreetMap contributors · Built by <a href="https://github.com/Osyanne">@Osyanne</a></div>
      <div class="right">
        <a href="{REPO_URL}">GitHub</a>
        <a href="{PATREON_URL}" class="patreon-link">Patreon</a>
        <a href="{ISSUE_NEW_URL}" target="_blank" rel="noopener">Request a city</a>
      </div>
    </footer>
  </div>

  <script>
  (() => {{
    const cards = document.querySelectorAll('.card[data-region]');
    const pills = document.querySelectorAll('.filter-pills button');
    const search = document.getElementById('search');
    const empty = document.getElementById('empty-state');
    let region = 'all', query = '';
    function apply() {{
      let visible = 0;
      cards.forEach(c => {{
        const okRegion = region === 'all' || c.dataset.region === region;
        const okQuery = !query || c.dataset.search.includes(query);
        const show = okRegion && okQuery;
        c.style.display = show ? '' : 'none';
        if (show) visible++;
      }});
      empty.classList.toggle('visible', visible === 0);
    }}
    pills.forEach(p => p.addEventListener('click', () => {{
      pills.forEach(x => {{
        x.classList.toggle('active', x === p);
        x.setAttribute('aria-pressed', x === p ? 'true' : 'false');
      }});
      region = p.dataset.region;
      apply();
    }}));
    search.addEventListener('input', e => {{
      query = e.target.value.toLowerCase().trim();
      apply();
    }});
  }})();
  </script>
</body>
</html>
'''
```

- [ ] **Step 8.5: Run the full test suite to verify everything passes**

Run:
```bash
cd src && uv run pytest ../tests/shared/test_landing.py -v
```

Expected: all tests PASS (the existing ones updated, the 10+ new ones).

If failures remain, fix iteratively. Common issues:
- Empty state not found: check element has both `class="empty-state"` AND `id="empty-state"`.
- Test expecting Spanish text now sees English (or vice versa) — the new template is English; tests should assert against the actual generated copy.

- [ ] **Step 8.6: Verify the full test suite for the project still passes**

Run the wider test suite to catch any regressions:
```bash
cd src && uv run pytest ../tests -v
```

Expected: all tests pass (~290+ existing tests + new ones from this work).

- [ ] **Step 8.7: Commit**

```bash
git add src/shared/landing.py tests/shared/test_landing.py
git commit -m "feat(landing): rewrite build_landing_html() with new template

Full page restructure: header + hero with gradient headline + stats
banner + filter pills + search + 3-col grid + request-city card +
empty state + footer + inline JS. CSS extracted to landing.css.
Stats computed server-side. Pills generated from region_counts.

Existing tests updated for new markup. New tests cover stats banner,
filter pills, search input, request card, empty state, JS presence,
external stylesheet linking."
```

---

## Task 9: Generate the 3 missing thumbnails

**Files:**
- Create: `visualizer/assets/thumbnails/fayetteville_nc.png`
- Create: `visualizer/assets/thumbnails/sacramento.png`
- Create: `visualizer/assets/thumbnails/new_york.png`

**Goal:** Fill the gap left when city requests #8/#9/#10 were merged without their thumbs. Required because the new landing's `<img>` tags otherwise produce broken images. Documented as in-scope in spec §12.F1.

- [ ] **Step 9.1: Install Playwright if not present**

Run:
```bash
uv sync --group thumbnails
uv run --group thumbnails playwright install chromium
```

Expected: Chromium binary downloaded (~300 MB first time, cached after). If already installed, both commands are fast no-ops.

- [ ] **Step 9.2: Verify the 3 thumbs are detected as missing**

Run:
```bash
ls visualizer/assets/thumbnails/
```

Expected output (only 7 files):
```
amsterdam.png  bacau_ro.png  charleston.png  madison.png
mafra_sc_brazil.png  minneapolis.png  trondheim.png
```

NY, Sacramento, and Fayetteville should NOT be present.

- [ ] **Step 9.3: Generate the missing thumbnails**

Run:
```bash
uv run generate-thumbnails
```

This auto-detects which slugs from `cities.json` lack a `.png` and generates only those. It uses the deployed visualizer URL by default.

Expected: prints progress for `fayetteville_nc`, `sacramento`, `new_york`. Each takes ~30–60s (load + 5s settle + screenshot). Total ~2-3 min.

- [ ] **Step 9.4: Verify all 10 thumbnails now exist**

Run:
```bash
ls visualizer/assets/thumbnails/
```

Expected (10 files): amsterdam, bacau_ro, charleston, fayetteville_nc, madison, mafra_sc_brazil, minneapolis, new_york, sacramento, trondheim — all .png.

If any failed to generate, retry per-city: `uv run generate-thumbnails --city <slug>`.

- [ ] **Step 9.5: Visually verify the new thumbs look correct**

Open the 3 new PNG files in an image viewer. They should look like the existing thumbs:
- 1200×800 pixels
- Show the zoning map of the city
- No UI chrome (no header pills, no layer controls, no attribution at bottom)

If something's wrong (e.g., loading spinner still visible), the settle time may be too short for that city — retry with: `uv run generate-thumbnails --city <slug> --force`.

- [ ] **Step 9.6: Commit the 3 new thumbnails**

```bash
git add visualizer/assets/thumbnails/fayetteville_nc.png \
        visualizer/assets/thumbnails/sacramento.png \
        visualizer/assets/thumbnails/new_york.png
git commit -m "fix(thumbnails): generate missing thumbs for NY, Sacramento, Fayetteville

City requests #8 (Fayetteville NC), #9 (Sacramento CA), #10 (NY)
were merged on 2026-05-20 without their card thumbnails — production
showed empty dark rectangles for these 3 cards.

Per landing redesign spec §12.F1. Recipe documented in Obsidian:
01-Proyectos/CS2-Mineapolis/🖼 City Request — Thumbnail Checklist.md"
```

---

## Task 10: Regenerate `visualizer/index.html` and visually verify

**Files:**
- Modify: `visualizer/index.html` (regenerated)
- Modify: `visualizer/cities.json` (regenerated deployed mirror)

**Goal:** Run the landing generator with all the new code + data, verify output renders correctly in browser.

- [ ] **Step 10.1: Regenerate landing**

Run:
```bash
uv run generate-landing
```

Expected output:
```
Landing generada: <repo>/visualizer/index.html
Registro deployado: <repo>/visualizer/cities.json
Cities incluidas: [...]
```

- [ ] **Step 10.2: Sanity check the generated HTML**

Run:
```bash
head -20 visualizer/index.html
```

Expected: starts with `<!DOCTYPE html>`, includes the new `<link rel="stylesheet" href="assets/landing.css">`. NOT a redirect like the root `index.html`.

Also run:
```bash
grep -c 'class="card"' visualizer/index.html
```

Expected: `11` (10 city cards + 1 request-city card with `class="card request"` matching the substring).

Actually for exact match:
```bash
grep -c 'class="card" ' visualizer/index.html  # note trailing space
```

Expected: `10` (only city cards — the request-card is `class="card request"`).

- [ ] **Step 10.3: Start a local preview server**

The repo already has `.claude/launch.json` with config `cs2-mockups` that serves the repo root on port 5180.

Run the preview server via Claude Code's preview tooling, or manually:
```bash
python -m http.server 5180 --directory .
```

Then open `http://localhost:5180/visualizer/index.html` in a browser.

- [ ] **Step 10.4: Visual verification checklist**

Open the URL and verify:

- [ ] Header shows "CS2 OSM Toolkit" + version pill, links visible, "Support →" button visible
- [ ] Hero shows badge with pulsing dot, headline with purple gradient on "Cities: Skylines 2"
- [ ] Lede text says "Browse 10 curated maps or request your own."
- [ ] Two CTAs visible: "Browse cities ↓" (white) + "Request your city" (outlined)
- [ ] Stats banner shows 4 stats: 10 cities, ~855k features, 5 countries, v3.4
- [ ] Filter pills: All · 10, North America · 6, Europe · 3, South America · 1
- [ ] Search input visible on the right
- [ ] Grid: 3 columns, 10 city cards + 1 dashed "Request your city" card spanning 2 cols at the end
- [ ] Each card shows: thumbnail image (no broken icons!), city name, flag + country, tagline, 1-3 purple dots, feature count in monospace
- [ ] Hover on a card: lifts up + purple glow
- [ ] Click "North America" pill: only USA cities show; pill becomes white background
- [ ] Type "ams" in search: only Amsterdam shows
- [ ] Clear search + click "All": all 10 cities reappear
- [ ] Filter to a region with 0 results (impossible naturally, but if you type random junk in search): empty state appears
- [ ] Footer shows attribution + 3 links, "Patreon" link is lavender colored
- [ ] Open DevTools → Lighthouse → run audit on Accessibility: score ≥95
- [ ] Resize browser to ~600px width: grid becomes 2 columns
- [ ] Resize to ~400px: grid becomes 1 column, stats become 2×2

- [ ] **Step 10.5: If any visual issue found, debug + fix iteratively**

Common issues:
- **Broken images for the 3 new thumbs:** Task 9 didn't actually generate them. Re-run with `uv run generate-thumbnails`.
- **Module dots invisible:** check `.mod { width: 5px; height: 5px; }` — 5px is small, might be misaligned with `border-radius`.
- **Filter doesn't work:** open browser console, look for JS errors. Common: `data-region` typo in pills vs cards.
- **Fonts didn't load:** check Network tab for failed Google Fonts requests. If offline, fallback stack should still render.

Fix any issues in the relevant source file (`landing.py` for HTML/JS, `landing.css` for styles), re-run `uv run generate-landing`, refresh browser.

- [ ] **Step 10.6: Commit the regenerated output**

```bash
git add visualizer/index.html visualizer/cities.json
git commit -m "chore(landing): regenerate index.html with new design

Output of \`uv run generate-landing\` with the redesigned template,
new helpers, and country_code data. Includes deployed cities.json
mirror with new field."
```

---

## Task 11: Update CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Goal:** Document this release per the existing CHANGELOG format.

- [ ] **Step 11.1: Read existing CHANGELOG format**

Run:
```bash
head -30 CHANGELOG.md
```

Note the heading style (e.g., `## v3.4.0 — title (date)`). Match it.

- [ ] **Step 11.2: Add the new entry**

Edit `CHANGELOG.md`. Add at the TOP, below the title (if any):

```markdown
## v3.4.1 — Landing redesign (2026-05-22)

### Added
- New visual identity for landing page (Linear/Cal.com inspired): hero with gradient headline + animated v3.5 badge, 4-column stats banner, region filter pills + search input, 3-column card grid with module dots, dedicated "Request your city" card at end of grid, empty-state with conversion fallback.
- `country_code` field (optional ISO 3166-1 alpha-2) added to all 10 cities in `cities.json` for flag emoji rendering.
- Region-based filtering helpers in `src/shared/landing.py`: `COUNTRY_TO_REGION` map, `country_to_flag()`, `region_counts()`, `build_stats()`, `_read_version_short()`.
- `visualizer/assets/landing.css` extracted from inline styles (cacheable, ~250 lines).
- Inline vanilla JS (~30 lines) for client-side filter + search across the card grid.
- Missing thumbnails generated for Fayetteville NC, Sacramento CA, New York (city requests #8/#9/#10 — were merged without thumbs on 2026-05-20).

### Changed
- `_card_html()` rewritten: `<img loading="lazy">` instead of `background-image`, flag emoji from country_code, module dots replace text badges, precomputed `data-search` attribute.
- `build_landing_html()` rewritten with new full-page structure.

### Accessibility
- WCAG AA contrast verified (text 17.5:1, muted 7.1:1, dim 4.3:1).
- `prefers-reduced-motion` support disables pulse + hover transforms.
- `:focus-visible` rings on all interactive elements.
- `aria-pressed` on filter pills, `aria-label` on module dots, `<label class="sr-only">` for search input.

### Performance
- Thumbnails lazy-loaded via `<img loading="lazy">` — initial page weight ~50 KB above-the-fold.
- Google Fonts via `preconnect` + `font-display: swap`.

### Docs
- Design spec: `docs/specs/2026-05-22-landing-redesign-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-05-22-landing-redesign.md`.
- Thumbnail generation checklist: documented for future city requests in Obsidian.
```

- [ ] **Step 11.3: Update version in `src/pyproject.toml`**

Edit `src/pyproject.toml`. Change:
```diff
-version = "3.4.0"
+version = "3.4.1"
```

- [ ] **Step 11.4: Regenerate the landing once more so the stats banner version reflects 3.4.1**

Run:
```bash
uv run generate-landing
```

Expected: HTML output now contains `<span>Version</span>` paired with `<strong>v3.4</strong>` (still v3.4 since `_read_version_short` returns major.minor).

- [ ] **Step 11.5: Run full test suite once more as final safety net**

Run:
```bash
cd src && uv run pytest ../tests -v
```

Expected: all tests pass.

- [ ] **Step 11.6: Commit**

```bash
git add CHANGELOG.md src/pyproject.toml visualizer/index.html visualizer/cities.json
git commit -m "chore: bump to v3.4.1 + CHANGELOG entry for landing redesign"
```

---

## Task 12: Final verification + (optional) push

**Files:** None modified.

**Goal:** Sanity-check the work end-to-end before considering it shippable.

- [ ] **Step 12.1: Verify the git log shows clean commit history**

Run:
```bash
git log --oneline -15
```

Expected: ~10 commits on top of `d35e33b`, each with descriptive `feat()` / `fix()` / `chore()` message. No "WIP" or amended commits.

- [ ] **Step 12.2: Verify no untracked files left behind**

Run:
```bash
git status
```

Expected: working tree clean (or only the pre-existing trondheim changes from before this work).

- [ ] **Step 12.3: Run full test suite one final time**

Run:
```bash
cd src && uv run pytest ../tests -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 12.4: Visual smoke test once more**

Start the preview server (if not still running) and open the local URL. Spot-check:
- Open one card → loads `map.html?city=<slug>` (existing viewer)
- Click hero "Browse cities ↓" → smooth scroll to grid
- Type in search, clear it
- Click each pill in turn
- Mobile-resize the window
- Open browser DevTools Console — should be silent (no errors, no warnings)

- [ ] **Step 12.5: (Optional) Push to remote**

If the user confirms they want to deploy:

```bash
git push origin main
```

GitHub Pages will redeploy automatically within ~1 minute.

Then verify the deployed URL: https://osyanne.github.io/CitiesSkylines2-osm-toolkit/visualizer/

---

## Done

All sections of the spec are now implemented. Next steps (out of scope for this plan):

- When v3.5 generator ships → update the hero badge text + href (2-line change in `landing.py`)
- If Modelo A is adopted later → wire up the per-card paywall badge per spec §11.Slot 2
- Add country flags / region pills for new cities as they're requested (just update `COUNTRY_TO_REGION` and `cities.json` `country_code`)
