# Módulo Infraestructura — Diseño (Sesión 4)

**Fecha:** 2026-05-31
**Estado:** Diseño aprobado — pendiente plan de implementación
**Autor:** brainstorm CS2 OSM Toolkit
**Predecesor:** [Módulo Transporte](2026-05-25-transporte-design.md)

## 1. Contexto

El juego Cities: Skylines II tiene un apartado de **infraestructura / utilities** con sub-secciones: Electricidad, Agua y Alcantarillado, Basura, y Comunicaciones. Los módulos previos del toolkit ya cubren el resto del menú de CS2: Roads (`vial`), Public Transport (`transporte`), y Healthcare/Fire/Police/Education/Parks (`services`). Este módulo cubre las **utilities que faltan** para completar el espejo del menú del juego en el visualizer.

Minneapolis tiene buena cobertura OSM de infraestructura: `power=*` (plantas, subestaciones, líneas de transmisión), `man_made=*` (torres de agua, plantas de tratamiento, estaciones de bombeo), `landuse=landfill`, `amenity=recycling`, y torres de telecom. La extracción es directa vía Overpass, igual que `transporte` y `services`.

## 2. Goals

- Renderar las **4 categorías de utilities** de Mpls como overlay en el visualizer, espejando el apartado del juego.
- Activar un tile **"Infraestructura"** en el top bar del HUD.
- Soportar geometría mixta: **puntos** (instalaciones), **polígonos** (plantas, subestaciones, vertederos, plantas de tratamiento) y **líneas** (red de transmisión eléctrica) — primer módulo con los 3 tipos.
- Cada feature lleva nombre real + categoría + subtipo para el popup (fidelidad al replicar en CS2).
- Seguir el patrón de `transporte`/`services` sin refactor del core. Mpls-first, arquitectura multi-city (`--city`).

## 3. Non-goals (v1)

- **Tuberías de agua / alcantarillado** — van subterráneas y casi no están mapeadas en OSM. Agua/alcantarillado quedan facilities-only.
- **Postes y pilones eléctricos** (`power=tower`, `power=pole`) — miles de puntos de ruido; CS2 tampoco dibuja cada poste.
- **Tachos de calle** (`amenity=waste_basket`, `amenity=recycling` con `recycling_type=container`) — ruido a escala de calle.
- **Cables subterráneos** (`power=cable`) — casi sin mapear.
- **Fuentes non-OSM** (EIA, MN GIS) — descartado por consistencia + para evitar la fragilidad de portales externos (URL-rot, reproyección, dedup). Si una categoría sale rala, el patrón pluggable de `official_zoning` queda como precedente para aumentarla on-demand en una iteración futura.
- **Data de capacidad / atributos autoritativos** (MW de plantas, caudal) — fuera de scope; el overlay es geográfico, no tabular.
- **Markers de detalle** más allá de las instalaciones mapeadas.

## 4. Decisiones clave

| Decisión | Elegido | Razón |
|---|---|---|
| Fuente de datos | **OSM-puro** (Overpass) | Consistente con `transporte`/`services`; ~1 sesión; cero deps nuevas; sin reproyección ni dedup; evita fragilidad de portales externos |
| Cobertura | 4 categorías: Electricidad / Agua y Alcantarillado / Basura / Comunicaciones | Espeja el apartado utilities de CS2 |
| Profundidad | Instalaciones (puntos/áreas) + **red eléctrica** (líneas) | Lo más parecido a CS2 que OSM sostiene; tuberías de agua no están en OSM |
| Module placement | `src/infraestructura/` | Mirrors `vial/`, `services/`, `transporte/` |
| Multi-city | Mpls-first, `--city` capable | Igual que todos los módulos |

## 5. Estructura del módulo

```
src/infraestructura/
├── __init__.py
├── extract.py        # CLI extract-infraestructura --city minneapolis + pipeline + build_infra_feature
├── classifiers.py    # classify_infra(tags) -> (categoria, subtipo) | None  (tabla pura + reglas condicionales)
└── zones.py          # INFRA_LABELS + build_infraestructura_query(bbox)
```

- Reutiliza `shared.overpass_client.query_with_retry` y `shared.registry.save_manifest_entry`.
- **Agregar `"infraestructura"` a `VALID_MODULES`** en `src/shared/registry.py` (lección de `transporte` T6).
- Geometría: reutiliza `infer_geometry_kind` (point/polygon, patrón de `services`) **+** `concatenate_ways` (líneas, patrón de `transporte`).
- Entry point `extract-infraestructura` en `pyproject.toml`.
- **Sin `→` ni otros Unicode en argparse description / prints** (lección cp1252 Windows de `transporte` T7) — usar ASCII.

## 6. Mapeo categorías CS2 → tags OSM

Slugs de código en inglés; labels del HUD en español. Cada categoría tiene subtipos para estilo/popup.

| Categoría (slug / label) | Subtipo | Tags OSM | Geometría típica |
|---|---|---|---|
| **`power`** / Electricidad | `generacion` | `power=plant`, `power=generator` | área / punto |
| | `subestacion` | `power=substation`, `power=transformer` | área / punto |
| | `transmision` | `power=line`, `power=minor_line` | **línea** |
| **`water`** / Agua y Alcantarillado | `suministro` | `man_made=water_tower`, `man_made=water_works`, `man_made=pumping_station`, `man_made=water_well`, `man_made=reservoir_covered` | área / punto |
| | `aguas_residuales` | `man_made=wastewater_plant` | área |
| **`waste`** / Basura | `disposicion` | `landuse=landfill`, `amenity=waste_transfer_station`, `man_made=incinerator` | área / punto |
| | `reciclaje` | `amenity=recycling` **solo si `recycling_type=centre`** | punto / área |
| **`telecom`** / Comunicaciones | `torre` | `man_made=communications_tower`; `man_made=mast` o `man_made=tower` **solo si `tower:type=communication`** | punto |
| | `data_center` | `telecom=data_center` | área / punto |

### Exclusiones (deben devolver `None`)

- `power=tower`, `power=pole` (pilones/postes)
- `amenity=recycling` con `recycling_type=container`, y `amenity=waste_basket`
- `power=cable` (subterráneo)
- `man_made=mast`/`tower` **sin** `tower:type=communication` (mástiles no-telecom: observación, iluminación, etc.)

## 7. Clasificación (`classify_infra`)

Tabla pura `(key, value) → (categoria, subtipo)` (estilo `services`), más reglas condicionales para los casos que dependen de un segundo tag:

```python
def classify_infra(tags: dict) -> tuple[str, str] | None:
    """OSM tags -> (categoria, subtipo) | None."""
    # Exclusiones explícitas primero (postes, contenedores, cables)
    if tags.get("power") in ("tower", "pole"):
        return None
    if tags.get("power") == "cable":
        return None
    if tags.get("amenity") == "recycling" and tags.get("recycling_type") == "container":
        return None

    # Reglas condicionales (requieren 2do tag)
    if tags.get("amenity") == "recycling":            # implícito: no es container
        if tags.get("recycling_type") == "centre":
            return ("waste", "reciclaje")
        return None                                   # recycling sin tipo claro = ruido
    if tags.get("man_made") in ("mast", "tower"):
        if tags.get("tower:type") == "communication":
            return ("telecom", "torre")
        return None                                   # mástil no-telecom

    # Tabla directa (key, value) -> (categoria, subtipo)
    for key, value in tags.items():
        hit = TAG_TO_CATEGORY.get((key, value))
        if hit is not None:
            return hit
    return None
```

`TAG_TO_CATEGORY` contiene todos los pares no-condicionales de la tabla de §6. Determinístico por orden de iteración del dict (Python 3.7+), igual que `services`.

## 8. Geometría

`infra_geometry(element)` decide el `kind`:

- `node` → `point` (`[lat, lon]`)
- `way` cerrado (primer nodo == último, ≥4 nodos) → `polygon`
- `way` abierto **y** categoría `power`/subtipo `transmision` → `line`
- `way` abierto en otra categoría → `point` (primer nodo del way; instalación sin polígono cerrado)
- `relation` → multipolygon: outer ring (primer member `role=outer` con geometría); líneas: `concatenate_ways` (helper de `transporte`); sin geometría usable → skip (`None`)

`build_infra_feature(element, categoria, subtipo)` → 
```json
{ "name": "...", "category": "power", "subtype": "transmision",
  "kind": "line|polygon|point", "coords": [...] | [lat,lon],
  "operator": "...", "osm_id": 123 }
```
Name fallback: `name` → `operator` + tipo → `"<Categoría> sin nombre"`.

## 9. Output

`visualizer/cities/<slug>/datos_infraestructura.js`:

```js
// Auto-generated by infraestructura.extract — <ts>
var DATA_INFRA_POWER   = [ {name, category, subtype, kind, coords, operator, osm_id}, ... ];
var DATA_INFRA_WATER   = [ ... ];
var DATA_INFRA_WASTE   = [ ... ];
var DATA_INFRA_TELECOM = [ ... ];
```

`save_manifest_entry(module="infraestructura", features=total)` actualiza `manifest.json`.

## 10. Integración con el visualizer

- **Tile "Infraestructura"** en el top bar: activación condicional cuando el manifest tiene el módulo + `DATA_INFRA_POWER` cargado (patrón de `transporte`). Lazy-load vía `SECONDARY` set; `window.infraestructuraLoaded` hook que parchea `MODULES.infraestructura` (sin duplicate listeners).
- **4 layer groups** (power/water/waste/telecom) toggleables.
- **Render por `kind`:** `point` → circle marker; `polygon` → área rellena; `line` → polyline (transmisión).
- **Colores** (CS2-ish): Electricidad `#f1c40f` (amarillo), Agua `#3498db` (azul), Basura `#8d6e63` (marrón), Comunicaciones `#9b59b6` (violeta). Subtipos varían peso/opacidad.
- **Legend** sección "Infraestructura" con 4 sub-items + counts dinámicos.
- **Popup:** `<b>name</b>` + `Categoría · Subtipo` + operator.

## 11. Testing

Estructura TDD de los módulos previos. **Fixtures con tags OSM reales**, no idealizados (meta-lección del bug BRT 2026-05-31: los fixtures inventados ocultaron un bug shipped).

| Test file | Cobertura | Target |
|---|---|---|
| `test_classifiers.py` | tabla `(key,value)→(cat,subtipo)` de las 4 categorías + reglas condicionales (recycling centre vs container, mast con/sin tower:type) + **exclusiones** (power=tower/pole/cable, waste_basket) + edge cases | ~18 |
| `test_geometry.py` | `kind` (node→point, way cerrado→polygon, way power abierto→line) + concatenación de líneas + multipolygon outer ring | ~7 |
| `test_features.py` | `build_infra_feature` (name fallback, coords, subtype carried) | ~5 |
| `test_extract_cli.py` | `parse_args` + `main` con Overpass mockeado (4 DATA_INFRA_* presentes, counts) | ~4 |
| manifest + integration (network, opt-in) | entry `infraestructura` en manifest; real Mpls query ≥20 elementos (umbral conservador) | ~3 |

Target: ~35-40 tests nuevos. Suite total ~440. Sin regresiones.

## 12. Edge cases / riesgos

| Caso | Manejo |
|---|---|
| Instalación waste-to-energy (HERC incinerator) taggeada como `power=plant`+`plant:source=waste` | Clasifica por la primera regla matched; documentar. Aceptable si cae en `power` (es generación real). |
| `power=line` como relación (no way) | `concatenate_ways` de los member ways. |
| Planta/subestación como multipolygon relation | Outer ring; si no hay geometría usable, skip (`None`). |
| Cobertura telecom rala en OSM | Aceptable — capa más fina; documentar count real. |
| Recycling sin `recycling_type` | Devuelve `None` (evita ruido de tachos). |
| Overpass 429/504 | `query_with_retry` ya maneja (backoff + rotación). |
| Mástil no-telecom (`man_made=mast` sin `tower:type=communication`) | Excluido (devuelve None). |

## 13. Criterios de aceptación

- Tile "Infraestructura" se activa (sin disabled/lock); toggle muestra/oculta los 4 layer groups.
- Puntos, polígonos y líneas renderizan con su color de categoría; transmisión eléctrica visible como polylines.
- Popup muestra nombre + categoría · subtipo (verificado para una planta, una subestación, una torre de agua, un vertedero, una torre telecom y un tramo de línea).
- Legend muestra sección "Infraestructura" con counts por categoría.
- Mpls regenerado: `datos_infraestructura.js` con las 4 vars, counts > 0 en power/water/waste (telecom puede ser bajo).
- Tests pass: ~35-40 nuevos, total ~440. Sin regresiones.
