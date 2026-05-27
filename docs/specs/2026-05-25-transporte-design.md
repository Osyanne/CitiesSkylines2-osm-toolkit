# Transporte Module — Design Spec

**Date:** 2026-05-25
**Status:** Approved, ready for implementation plan
**Scope:** Sprint 1 — Minneapolis (sesión 5 del roadmap original)
**Predecessor context:** Los 3 módulos OSM-derived (zoning + vial + servicios) están shipped + el módulo Official Zoning shipped esta misma fecha. Queda Sesión 5 (Transporte) y Sesión 4 (Infraestructura) en el roadmap. El HUD ya muestra un tile "Transporte" con lock SVG como "próximamente".

## 1. Motivation

Minneapolis tiene una red de tránsito robusta y bien mapeada en OSM (Metro Transit):

- **METRO Blue Line + Green Line** (light rail / LRT)
- **Northstar** (commuter rail al noroeste)
- **METRO Rapid Bus A/C/D/E/F lines** (BRT)
- **~140 rutas de bus locales**

CS2 distingue estos modos como vehículos diferenciados (Tram, Train, Bus, BRT-style lanes). Para construir Mpls 1:1 en el juego, ver dónde corre cada modo es esencial. OSM cubre transporte bien vía `route=*` relations, así que la extracción es directa.

## 2. Goals

- Renderear las **4 categorías de tránsito** de Mpls como polylines coloridas en el visualizer.
- Activar el tile "Transporte" en el top bar (actualmente disabled con lock SVG).
- Cada polyline lleva el nombre real de la línea (popup con "METRO Green Line" / "Route 5" / etc.) para fidelidad al replicarlo en CS2.
- Seguir el pattern existente de los otros módulos (`vial/`, `services/`) sin refactor del core.

## 3. Non-goals (v1)

- **Markers de paradas / estaciones** — agregable en v1.1; ~6,000 bus stops saturan el mapa, las ~30 stations de LRT/BRT son útiles pero se difieren.
- **Multi-city** — el pattern es trasladable pero cada ciudad requiere validación de la cobertura OSM de su transit. Mpls primero; NY/Amsterdam pueden activarse después agregando entry en `cities.json` (no requiere nuevo source module, transit es OSM-puro).
- **Animaciones (dashed lines, dots móviles)** — sexy pero YAGNI para v1.
- **Datos de frecuencia / horarios** — OSM no los tiene; requeriría GTFS feeds (out of scope).
- **Tránsito aéreo / náutico** — Mpls no tiene metro aéreo ni ferries relevantes.

## 4. Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Data source | Overpass relations (no PBF) | ~150 relations totales para Mpls = 3 órdenes de magnitud menos que zoning. La crítica "Overpass abuse" (tj-horner) no aplica a este uso — fue por extracciones masivas, no metadata de relaciones |
| Cobertura | 4 categorías: LRT / Commuter / BRT / Bus | Mapea limpio a CS2 (que distingue Tram/Train/Bus/BRT) |
| Output | Polylines por route relation, con nombre/ref | Una línea coherente por ruta vs fragmentos de track sin identidad |
| Module placement | `src/transporte/` | Mirrors existing `src/vial/`, `src/services/` convention |
| Scope sprint 1 | Mpls only | Pattern queda listo para escalar, pero Mpls valida el flow |
| Routes que salen del bbox | Include full route (no clip) | Mejor UX — usuario ve la red completa de tránsito conectado a Mpls |

## 5. Architecture

### Python package layout

```
src/transporte/
├── __init__.py
├── extract.py            # CLI entrypoint: extract-transporte --city minneapolis
├── classifiers.py        # classify_route(tags) -> "lrt"|"commuter"|"brt"|"bus"|None
└── zones.py              # TRANSPORT_LABELS + build_transporte_query(bbox)
```

### New CLI entry-point

In `src/pyproject.toml`:

```toml
[project.scripts]
extract-transporte = "transporte.extract:main"
```

Usage:

```
cd src && uv run extract-transporte --city minneapolis
```

### New dependencies

Ninguna. `shared.overpass_client` ya existe en el proyecto y se reutiliza.

## 6. Data pipeline

Para Minneapolis (y en el futuro para cualquier ciudad declarada en `cities.json`):

1. Leer `bbox` desde `cities.json[<slug>].bbox` (formato `[south, west, north, east]`)
2. Build query Overpass:

   ```overpass
   [out:json][timeout:120];
   (
     relation["route"~"^(light_rail|train|tram|bus)$"]({bbox});
   );
   out body geom;
   ```

3. Fetch via `shared.overpass_client.fetch()` (existing utility)
4. Para cada relation:
   - Concatenar las geometrías de sus member ways en una LineString (o MultiLineString si hay gaps)
   - Llamar `classify_route(tags)` → categoría CS2 (descartar None)
   - Extraer metadata: `name`, `ref`, `network`, `operator`, `osm_id`
5. Emit `visualizer/cities/<slug>/datos_transporte.js`
6. Update `manifest.json` con módulo `transporte`

## 7. Classifier

```python
def classify_route(tags: dict) -> str | None:
    """Map OSM route tags to a CS2 transit category."""
    route = tags.get("route", "").lower()
    network = tags.get("network", "")
    name = tags.get("name", "")
    
    if route == "light_rail" or route == "tram":
        # METRO Blue/Green Line + cualquier tram (Mpls no tiene tram real,
        # pero ciudades EU sí; mapear como LRT visualmente)
        return "lrt"
    if route in ("train", "commuter_rail", "commuter"):
        return "commuter"
    if route == "bus":
        # BRT detection: METRO Rapid uses pattern "METRO X Line" o "X Line"
        # en `name`, con `network=METRO`.
        if "METRO" in network or ("METRO" in name and " Line" in name):
            return "brt"
        return "bus"
    return None
```

## 8. Output schema

`visualizer/cities/<slug>/datos_transporte.js`:

```js
// Auto-generated by transporte.extract — <ISO timestamp>
// Source: OpenStreetMap (Overpass query route=*)

var DATA_TRANSPORT_LRT = [
  {
    "name": "METRO Green Line",
    "ref": "Green",
    "coords": [[lat, lon], [lat, lon], ...],
    "operator": "Metro Transit",
    "osm_id": "11286"
  },
  ...
];
var DATA_TRANSPORT_COMMUTER = [...];
var DATA_TRANSPORT_BRT = [...];
var DATA_TRANSPORT_BUS = [...];
```

**Uses `var` (not `const`)** — same lesson as official zoning (so `window["DATA_TRANSPORT_*"]` is accessible from the visualizer hook).

Coords truncated to 5 decimal places (~1m precision, matches project convention).

## 9. Visualizer integration

### Activate the "Transporte" tile

Currently in `map.html` `MODULE_META.transporte` is:

```js
transporte: {
  label: "Transporte (próximamente)",
  cat: "var(--cat-transport)",
  svg: `<svg class="pill-icon" ...>(bus icon)</svg>`,
}
```

Updates:
- Remove `disabled` class injection for transporte
- Remove lock SVG overlay
- Detect `manifest.modules.transporte` to auto-show the tile
- Wire toggle behavior parallel to zoning/vial/services

### Loading flow

Same lazy-load pattern as `official_zoning`:
1. Primary modules render via existing `loadAll()`
2. After `renderMap()`, if `manifest.modules.transporte` exists, lazy-load `datos_transporte.js`
3. On load, `window.transporteLoaded()` hook populates 4 parallel layer groups

### Layer groups + rendering

```js
const transporteGroups = {
  lrt:      L.layerGroup().addTo(map),
  commuter: L.layerGroup().addTo(map),
  brt:      L.layerGroup().addTo(map),
  bus:      L.layerGroup().addTo(map),
};

// Distinct palette — avoids collision with services cyan (#5bbdd0) and
// zoning greens. Matches Mpls Metro Transit branding where reasonable.
const TRANSPORT_STYLE = {
  lrt:      { color: "#0084c8", weight: 3.5, opacity: 0.9  }, // Mpls LRT blue
  commuter: { color: "#7d2d3e", weight: 4.0, opacity: 0.9  }, // Northstar maroon
  brt:      { color: "#f4a261", weight: 2.5, opacity: 0.85 }, // METRO Rapid orange
  bus:      { color: "#7a93a8", weight: 1.0, opacity: 0.55 }, // muted gray-blue
};
```

Each polyline binds a popup:

```
<b>METRO Green Line</b>
<span>Light Rail · Metro Transit</span>
```

### Legend section

Nuevo bloque en el legend (entre Servicios y la Confiabilidad):

```
TRANSPORTE
■ LRT             4 routes
■ Commuter Rail   1 routes
■ BRT             5 routes
■ Bus            142 routes
```

Master toggle igual a los otros módulos (sync con el tile).

## 10. Testing strategy

| Test type | Coverage | Target count |
|---|---|---|
| Unit (classifier) | 8-10 tag dict samples covering LRT/Commuter/BRT/Bus + edge cases (no `route`, unknown `route`, bus sin METRO network) | ~10 |
| Pipeline integration (mocked Overpass) | Mocked response → emit JS file with 4 DATA_TRANSPORT_* present, correct counts | ~3 |
| Smoke (network, opt-in) | Real Overpass query for Mpls bbox returns ≥30 relations | ~2 |
| CLI | `extract-transporte --city minneapolis` parses args, fails on unknown city, writes output | ~3 |
| Manifest extension | `transporte` entry written to manifest when datos_transporte.js exists | ~2 |
| Visualizer (Playwright) | Tile activates, layer groups render, popup shows route name | ~2 |

Target: **+20 tests**. Total project suite goes from ~360 to ~380.

## 11. Out of scope (deferred)

- Markers de estaciones/stops (v1.1 — agregar `railway=station` + filtro `network=METRO` para ~30 markers de LRT/BRT)
- Otras cities (NY/Amsterdam tienen buena cobertura, activar después agregando bbox queries)
- Animaciones (dash arrays, moving dots)
- GTFS integration (frecuencias, schedules)
- Cable / aerialway / ferry (no relevante para Mpls)

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Overpass timeout para queries grandes | Timeout: 120s suficiente para Mpls (~150 relations); fallback retry con timeout 180s |
| Relations con member ways incompletos (gaps) | Emit MultiLineString (multiple coords arrays) si geometría tiene huecos; log warning |
| Routes que se extienden fuera del bbox de Mpls (Northstar) | Include full route — UX mejor con líneas que se extienden off-map |
| BRT detection falla porque alguna ruta no tiene "METRO" en name | Fallback a `bus` (no breaking, solo categoría diferente) — log warning para review manual |
| Overpass servers down / rate-limited | Detección: HTTP 429 / 504 → fail loud con guidance "retry en 60s" |
| Algunos bus routes tienen `name=null` en OSM | Popup fallback: `Route #<ref>` o `<operator> bus` si falta name+ref |

## 13. Effort estimate

**Sprint 1:** Mpls end-to-end + visualizer activation.
- 4-6 horas de trabajo focused.
- Subagent-driven viable: spec → plan (TDD, 12-15 tasks) → execution.
- Más simple que Official Zoning (sin reproject, sin spatial-join, sin YAML mapping).

## 14. Success criteria

- `extract-transporte --city minneapolis` produces `datos_transporte.js` con 4 DATA_TRANSPORT_* populated.
- Manifest declares `transporte` module entry.
- Visualizer: tile "Transporte" se activa (sin disabled/lock), click toggle shows/hides los 4 layer groups.
- Cada polyline rendea correctamente con su color de categoría.
- Popup muestra nombre real de la línea (verificado para METRO Green Line + Northstar + METRO A Line + algún bus random).
- Legend muestra sección "Transporte" con counts por categoría.
- Tests pass: 20+ new, total ~380. No regressions.

## 15. References

- Spec predecesor (mismo proyecto, día anterior): `docs/specs/2026-05-24-official-zoning-design.md`
- HUD predecesor con el tile placeholder: commit `a30278f` (2026-05-24)
- Existing pattern: `src/vial/zones.py` + `src/vial/classifiers.py`
- Overpass docs: https://overpass-api.de/api/interpreter
- Mpls Metro Transit reference: https://www.metrotransit.org
- OSM transit conventions: https://wiki.openstreetmap.org/wiki/Public_transport
