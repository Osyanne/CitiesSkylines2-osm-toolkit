# Módulo Infraestructura — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un módulo `infraestructura` que extrae de OSM las utilities de Minneapolis (electricidad, agua/alcantarillado, basura, comunicaciones) y las renderea como overlay en el visualizer, espejando el apartado de infraestructura de CS2.

**Architecture:** Módulo OSM-puro `src/infraestructura/` que sigue el patrón de `transporte`/`services`: una query Overpass → `classify_infra(tags)` → geometría (punto/polígono/línea) → `datos_infraestructura.js` + manifest. Visualizer con tile condicional, lazy-load y 4 layer groups, render por `kind`.

**Tech Stack:** Python 3.11+ (stdlib + `requests` vía `shared.overpass_client`), pytest, Leaflet.js (vanilla, en `visualizer/map.html`).

**Spec:** `docs/specs/2026-05-31-infraestructura-design.md`

---

## Notas de ejecución (leer antes de empezar)

- **Cómo correr los tests:** desde la raíz del repo, `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/ -v` (el `conftest.py` de la raíz inyecta `src/` en `sys.path`; `pytest.ini` define los markers). Equivalente documentado del repo: `cd src && uv run pytest ../tests/infraestructura -v`.
- **Commits:** NUNCA agregar `Co-Authored-By: Claude` al body (convención del repo — contributors panel limpio).
- **Windows cp1252:** no usar caracteres Unicode (`→`, `…`, `—`) en `print()`/argparse description; usar ASCII. Sí se permiten en docstrings/comentarios.
- **No worktree:** el repo commitea specs/plans/módulos directo a `main` (igual que transporte). Trabajar en `main`.
- **Slugs de categoría:** `power`, `water`, `waste`, `telecom`. Labels HUD: Electricidad / Agua y Alcantarillado / Basura / Comunicaciones.

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `src/infraestructura/__init__.py` | Marker de package (vacío) |
| `src/infraestructura/classifiers.py` | `classify_infra(tags) -> (categoria, subtipo) | None` — tabla pura + exclusiones + reglas condicionales |
| `src/infraestructura/zones.py` | `INFRA_LABELS` + `build_infraestructura_query(bbox)` |
| `src/infraestructura/extract.py` | Geometry helpers + `build_infra_feature` + CLI `main` (pipeline Overpass→emit) |
| `src/shared/registry.py` | **Modificar:** agregar `"infraestructura"` a `VALID_MODULES` |
| `src/pyproject.toml` | **Modificar:** entry point `extract-infraestructura` + wheel package |
| `tests/infraestructura/` | `test_classifiers.py`, `test_geometry.py`, `test_features.py`, `test_extract_cli.py`, `test_manifest.py`, `__init__.py` |
| `visualizer/map.html` | **Modificar:** wiring bootstrap, layer groups, MODULE_META, pill, legend, `window.infraestructuraLoaded` hook, CSS var |
| `visualizer/cities/minneapolis/datos_infraestructura.js` | **Generado** por el extractor |

**Feature schema** (emitido por `build_infra_feature`, consumido por el renderer) — usar EXACTAMENTE estas keys en todas las tasks:

```json
{ "name": "...", "category": "power|water|waste|telecom", "subtype": "...",
  "kind": "point|polygon|line",
  "coords": [lat, lon]  (si kind=point)  |  [[lat,lon], ...]  (si kind=polygon|line),
  "operator": "...", "osm_id": 123 }
```

---

## Fase 0 — Scaffold

### Task 1: Scaffold del package + registro + entry point

**Files:**
- Create: `src/infraestructura/__init__.py` (vacío)
- Create: `src/infraestructura/classifiers.py` (stub)
- Create: `src/infraestructura/zones.py` (stub)
- Create: `src/infraestructura/extract.py` (stub)
- Create: `tests/infraestructura/__init__.py` (vacío)
- Create: `tests/infraestructura/test_manifest.py`
- Modify: `src/shared/registry.py:74`
- Modify: `src/pyproject.toml:36` y `:46`

- [ ] **Step 1: Write the failing test**

Create `tests/infraestructura/test_manifest.py`:

```python
"""infraestructura debe ser un módulo válido para el manifest."""
from pathlib import Path

from shared.registry import VALID_MODULES, save_manifest_entry


def test_infraestructura_is_valid_module():
    assert "infraestructura" in VALID_MODULES


def test_save_manifest_entry_accepts_infraestructura(tmp_path):
    data = tmp_path / "cities" / "x" / "datos_infraestructura.js"
    data.parent.mkdir(parents=True)
    data.write_text("var DATA_INFRA_POWER = [];\n", encoding="utf-8")
    manifest = save_manifest_entry(
        visualizer_root=tmp_path, slug="x", module="infraestructura",
        file_path=data, features=3,
    )
    assert manifest["modules"]["infraestructura"]["features"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_manifest.py -v`
Expected: FAIL — `assert 'infraestructura' in VALID_MODULES` (no está en el frozenset).

- [ ] **Step 3: Create package files + register the module**

Create empty `src/infraestructura/__init__.py`, `tests/infraestructura/__init__.py`.

Create stubs (se completan en tasks siguientes):
```python
# src/infraestructura/classifiers.py
def classify_infra(tags: dict) -> tuple[str, str] | None:
    raise NotImplementedError
```
```python
# src/infraestructura/zones.py
INFRA_LABELS: dict[str, str] = {}
def build_infraestructura_query(bbox: str) -> str:
    raise NotImplementedError
```
```python
# src/infraestructura/extract.py
def main() -> None:
    raise NotImplementedError
```

Modify `src/shared/registry.py:74`:
```python
VALID_MODULES = frozenset({"zoning", "vial", "services", "external_buildings", "official_zoning", "transporte", "infraestructura"})
```

Modify `src/pyproject.toml` — add to `[project.scripts]` (after line 36):
```toml
extract-infraestructura = "infraestructura.extract:main"
```
And add `"infraestructura"` to `[tool.hatch.build.targets.wheel]` packages (line 46):
```toml
packages = ["shared", "zoning", "vial", "services", "official_zoning", "transporte", "infraestructura"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_manifest.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infraestructura/ tests/infraestructura/ src/shared/registry.py src/pyproject.toml
git commit -m "feat(infraestructura): scaffold package + register module"
```

---

## Fase 1 — Clasificador

### Task 2: `classify_infra` — tabla base (sin condicionales)

**Files:**
- Modify: `src/infraestructura/classifiers.py`
- Test: `tests/infraestructura/test_classifiers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/infraestructura/test_classifiers.py`:

```python
"""classify_infra: tags OSM reales -> (categoria, subtipo) | None."""
from infraestructura.classifiers import classify_infra


def test_power_plant_is_generacion():
    assert classify_infra({"power": "plant", "name": "Riverside"}) == ("power", "generacion")

def test_power_generator_is_generacion():
    assert classify_infra({"power": "generator", "generator:source": "solar"}) == ("power", "generacion")

def test_substation_is_subestacion():
    assert classify_infra({"power": "substation", "name": "Main St"}) == ("power", "subestacion")

def test_power_line_is_transmision():
    assert classify_infra({"power": "line"}) == ("power", "transmision")

def test_minor_line_is_transmision():
    assert classify_infra({"power": "minor_line"}) == ("power", "transmision")

def test_water_tower_is_suministro():
    assert classify_infra({"man_made": "water_tower"}) == ("water", "suministro")

def test_water_works_is_suministro():
    assert classify_infra({"man_made": "water_works", "name": "Fridley"}) == ("water", "suministro")

def test_wastewater_plant_is_aguas_residuales():
    assert classify_infra({"man_made": "wastewater_plant"}) == ("water", "aguas_residuales")

def test_landfill_is_disposicion():
    assert classify_infra({"landuse": "landfill"}) == ("waste", "disposicion")

def test_incinerator_is_disposicion():
    assert classify_infra({"man_made": "incinerator", "name": "HERC"}) == ("waste", "disposicion")

def test_communications_tower_is_telecom_torre():
    assert classify_infra({"man_made": "communications_tower"}) == ("telecom", "torre")

def test_data_center_is_telecom():
    assert classify_infra({"telecom": "data_center"}) == ("telecom", "data_center")

def test_unknown_returns_none():
    assert classify_infra({"amenity": "cafe"}) is None

def test_empty_returns_none():
    assert classify_infra({}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_classifiers.py -v`
Expected: FAIL — `classify_infra` raises `NotImplementedError`.

- [ ] **Step 3: Write minimal implementation**

Replace `src/infraestructura/classifiers.py`:

```python
"""
infraestructura/classifiers.py — OSM tags -> (categoria CS2, subtipo)
=====================================================================
Tabla pura (key,value) -> (categoria, subtipo), mas reglas condicionales
(ver Task 3). Categorias: power | water | waste | telecom.

Data real Mpls: power=* (plantas/subestaciones/lineas), man_made=* (agua,
incinerador, telecom), landuse=landfill, amenity=recycling. Sin heuristicas.
"""

# (key, value) -> (categoria, subtipo) — pares NO condicionales
TAG_TO_CATEGORY = {
    # power
    ("power", "plant"):        ("power", "generacion"),
    ("power", "generator"):    ("power", "generacion"),
    ("power", "substation"):   ("power", "subestacion"),
    ("power", "transformer"):  ("power", "subestacion"),
    ("power", "line"):         ("power", "transmision"),
    ("power", "minor_line"):   ("power", "transmision"),
    # water
    ("man_made", "water_tower"):       ("water", "suministro"),
    ("man_made", "water_works"):       ("water", "suministro"),
    ("man_made", "pumping_station"):   ("water", "suministro"),
    ("man_made", "water_well"):        ("water", "suministro"),
    ("man_made", "reservoir_covered"): ("water", "suministro"),
    ("man_made", "wastewater_plant"):  ("water", "aguas_residuales"),
    # waste
    ("landuse", "landfill"):               ("waste", "disposicion"),
    ("amenity", "waste_transfer_station"): ("waste", "disposicion"),
    ("man_made", "incinerator"):           ("waste", "disposicion"),
    # telecom
    ("man_made", "communications_tower"):  ("telecom", "torre"),
    ("telecom", "data_center"):            ("telecom", "data_center"),
}


def classify_infra(tags: dict) -> tuple[str, str] | None:
    """OSM tags -> (categoria, subtipo) | None (skip)."""
    for key, value in tags.items():
        hit = TAG_TO_CATEGORY.get((key, value))
        if hit is not None:
            return hit
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_classifiers.py -v`
Expected: PASS (14 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infraestructura/classifiers.py tests/infraestructura/test_classifiers.py
git commit -m "feat(infraestructura): classify_infra base table (4 categorias)"
```

### Task 3: `classify_infra` — reglas condicionales + exclusiones

**Files:**
- Modify: `src/infraestructura/classifiers.py`
- Test: `tests/infraestructura/test_classifiers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/infraestructura/test_classifiers.py`:

```python
# ── Reglas condicionales + exclusiones (tags reales OSM) ──

def test_recycling_centre_is_reciclaje():
    assert classify_infra({"amenity": "recycling", "recycling_type": "centre"}) == ("waste", "reciclaje")

def test_recycling_container_excluded():
    assert classify_infra({"amenity": "recycling", "recycling_type": "container"}) is None

def test_recycling_without_type_excluded():
    # tachos sin tipo claro = ruido
    assert classify_infra({"amenity": "recycling"}) is None

def test_mast_communication_is_telecom():
    assert classify_infra({"man_made": "mast", "tower:type": "communication"}) == ("telecom", "torre")

def test_tower_communication_is_telecom():
    assert classify_infra({"man_made": "tower", "tower:type": "communication"}) == ("telecom", "torre")

def test_mast_without_tower_type_excluded():
    # mastil no-telecom (observacion, iluminacion, etc.)
    assert classify_infra({"man_made": "mast"}) is None

def test_power_tower_excluded():
    # pilones — miles de puntos, ruido
    assert classify_infra({"power": "tower"}) is None

def test_power_pole_excluded():
    assert classify_infra({"power": "pole"}) is None

def test_power_cable_excluded():
    # subterraneo
    assert classify_infra({"power": "cable"}) is None

def test_waste_basket_excluded():
    assert classify_infra({"amenity": "waste_basket"}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_classifiers.py -v`
Expected: FAIL — p.ej. `test_power_tower_excluded` devuelve `("power","transmision")`? No: `power=tower` no está en la tabla, así que hoy devuelve `None` por accidente. Pero `test_mast_without_tower_type_excluded` y `test_recycling_without_type_excluded` fallan porque `man_made=mast`/`amenity=recycling` no están en la tabla → devuelven None ya... revisar: los que SÍ fallan son `test_recycling_centre_is_reciclaje` (no está en tabla → None, esperado reciclaje) y `test_mast_communication_is_telecom` (man_made=mast no en tabla → None, esperado telecom). Confirmar al menos esos 2 fallan.

- [ ] **Step 3: Write the implementation**

Replace the `classify_infra` function in `src/infraestructura/classifiers.py` (deja `TAG_TO_CATEGORY` igual):

```python
def classify_infra(tags: dict) -> tuple[str, str] | None:
    """OSM tags -> (categoria, subtipo) | None (skip).

    Orden: exclusiones explicitas -> reglas condicionales (requieren 2do tag)
    -> tabla directa.
    """
    # Exclusiones explicitas (pilones/postes/cables subterraneos)
    if tags.get("power") in ("tower", "pole", "cable"):
        return None

    # Reglas condicionales (dependen de un 2do tag)
    if tags.get("amenity") == "recycling":
        if tags.get("recycling_type") == "centre":
            return ("waste", "reciclaje")
        return None  # containers / sin tipo = ruido de calle
    if tags.get("man_made") in ("mast", "tower"):
        if tags.get("tower:type") == "communication":
            return ("telecom", "torre")
        return None  # mastil no-telecom

    # Tabla directa
    for key, value in tags.items():
        hit = TAG_TO_CATEGORY.get((key, value))
        if hit is not None:
            return hit
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_classifiers.py -v`
Expected: PASS (24 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infraestructura/classifiers.py tests/infraestructura/test_classifiers.py
git commit -m "feat(infraestructura): BRT-style conditional rules + exclusiones (pilones, tachos, mastiles no-telecom)"
```

---

## Fase 2 — Query builder

### Task 4: `zones.py` — labels + Overpass query

**Files:**
- Modify: `src/infraestructura/zones.py`
- Test: `tests/infraestructura/test_zones.py`

- [ ] **Step 1: Write the failing test**

Create `tests/infraestructura/test_zones.py`:

```python
"""INFRA_LABELS + build_infraestructura_query."""
from infraestructura.zones import INFRA_LABELS, build_infraestructura_query


def test_labels_cover_4_categories():
    assert set(INFRA_LABELS.keys()) == {"power", "water", "waste", "telecom"}
    assert INFRA_LABELS["power"] == "Electricidad"

def test_query_includes_bbox():
    q = build_infraestructura_query("44.86,-93.38,45.05,-93.17")
    assert "44.86,-93.38,45.05,-93.17" in q

def test_query_targets_all_categories():
    q = build_infraestructura_query("1,2,3,4")
    assert "power" in q
    assert "man_made" in q
    assert "landfill" in q
    assert "recycling" in q
    assert "data_center" in q

def test_query_uses_nwr_and_geom():
    q = build_infraestructura_query("1,2,3,4")
    assert "nwr" in q          # node+way+relation
    assert "out body geom;" in q
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_zones.py -v`
Expected: FAIL — `INFRA_LABELS` vacío + `build_infraestructura_query` raises NotImplementedError.

- [ ] **Step 3: Write the implementation**

Replace `src/infraestructura/zones.py`:

```python
"""
infraestructura/zones.py — Categorias CS2 + Overpass query builder
===================================================================
4 categorias: power / water / waste / telecom.
La query es amplia (trae mast/tower y recycling); el classifier (classify_infra)
es el que filtra a telecom-only y recycling=centre.
"""

INFRA_LABELS = {
    "power":   "Electricidad",
    "water":   "Agua y Alcantarillado",
    "waste":   "Basura",
    "telecom": "Comunicaciones",
}


def build_infraestructura_query(bbox: str) -> str:
    """Overpass QL: node+way+relation de infraestructura en el bbox, con geometria.

    Args:
        bbox: "south,west,north,east" decimal degrees.
    """
    return f"""
[out:json][timeout:120];
(
  nwr["power"~"^(plant|generator|substation|transformer|line|minor_line)$"]({bbox});
  nwr["man_made"~"^(water_tower|water_works|pumping_station|water_well|reservoir_covered|wastewater_plant|incinerator|communications_tower|mast|tower)$"]({bbox});
  nwr["landuse"="landfill"]({bbox});
  nwr["amenity"~"^(waste_transfer_station|recycling)$"]({bbox});
  nwr["telecom"="data_center"]({bbox});
);
out body geom;
""".strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_zones.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infraestructura/zones.py tests/infraestructura/test_zones.py
git commit -m "feat(infraestructura): INFRA_LABELS + build_infraestructura_query (Overpass nwr)"
```

---

## Fase 3 — Geometría + features

### Task 5: Geometry helpers (`kind` + coords)

**Files:**
- Modify: `src/infraestructura/extract.py`
- Test: `tests/infraestructura/test_geometry.py`

- [ ] **Step 1: Write the failing test**

Create `tests/infraestructura/test_geometry.py`:

```python
"""infra_geometry: decide kind (point/polygon/line) + extrae coords."""
from infraestructura.extract import infra_geometry

NODE = {"type": "node", "lat": 44.9, "lon": -93.2}
OPEN_WAY = {"type": "way", "geometry": [
    {"lat": 44.9, "lon": -93.2}, {"lat": 44.91, "lon": -93.21}, {"lat": 44.92, "lon": -93.22}]}
CLOSED_WAY = {"type": "way", "geometry": [
    {"lat": 44.9, "lon": -93.2}, {"lat": 44.9, "lon": -93.1},
    {"lat": 44.8, "lon": -93.1}, {"lat": 44.9, "lon": -93.2}]}


def test_node_is_point():
    kind, coords = infra_geometry(NODE, "suministro")
    assert kind == "point"
    assert coords == [44.9, -93.2]

def test_closed_way_is_polygon():
    kind, coords = infra_geometry(CLOSED_WAY, "generacion")
    assert kind == "polygon"
    assert coords[0] == [44.9, -93.2]
    assert len(coords) == 4

def test_open_way_transmision_is_line():
    kind, coords = infra_geometry(OPEN_WAY, "transmision")
    assert kind == "line"
    assert len(coords) == 3

def test_open_way_non_transmision_is_point():
    # instalacion mapeada como way abierto -> primer nodo
    kind, coords = infra_geometry(OPEN_WAY, "suministro")
    assert kind == "point"
    assert coords == [44.9, -93.2]

def test_way_without_geometry_returns_none():
    assert infra_geometry({"type": "way", "geometry": []}, "generacion") is None

def test_relation_transmision_uses_longest_member_way():
    rel = {"type": "relation", "members": [
        {"type": "way", "role": "", "geometry": [{"lat": 1, "lon": 1}, {"lat": 2, "lon": 2}]},
        {"type": "way", "role": "", "geometry": [
            {"lat": 3, "lon": 3}, {"lat": 4, "lon": 4}, {"lat": 5, "lon": 5}]},
    ]}
    kind, coords = infra_geometry(rel, "transmision")
    assert kind == "line"
    assert len(coords) == 3  # el member mas largo

def test_relation_polygon_uses_outer_ring():
    rel = {"type": "relation", "members": [
        {"type": "way", "role": "outer", "geometry": [
            {"lat": 1, "lon": 1}, {"lat": 1, "lon": 2}, {"lat": 2, "lon": 2}, {"lat": 1, "lon": 1}]},
    ]}
    kind, coords = infra_geometry(rel, "generacion")
    assert kind == "polygon"
    assert len(coords) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_geometry.py -v`
Expected: FAIL — `cannot import name 'infra_geometry'`.

- [ ] **Step 3: Write the implementation**

Replace `src/infraestructura/extract.py` with (module docstring + geometry helpers; el `main` se agrega en Task 7, el archivo aún no tiene `main` tras esta task):

```python
"""
infraestructura/extract.py — Infra extractor para CS2 OSM Toolkit
=================================================================
Pipeline:
  1. Query Overpass (build_infraestructura_query) por utilities en el bbox
  2. classify_infra(tags) -> (categoria, subtipo)
  3. infra_geometry(element, subtipo) -> (kind, coords)  [point/polygon/line]
  4. build_infra_feature(...) -> dict
  5. Emit visualizer/cities/<slug>/datos_infraestructura.js

CLI: cd src && uv run extract-infraestructura --city minneapolis
"""
from __future__ import annotations


def _latlon_list(geometry: list) -> list[list[float]]:
    return [[p["lat"], p["lon"]] for p in (geometry or [])]


def _is_closed(coords: list[list[float]]) -> bool:
    return len(coords) >= 4 and coords[0] == coords[-1]


def _longest_member_way(element: dict) -> list[list[float]]:
    """Devuelve las coords del member way mas largo de una relation (o [])."""
    best: list[list[float]] = []
    for m in element.get("members", []):
        if m.get("type") != "way":
            continue
        coords = _latlon_list(m.get("geometry"))
        if len(coords) > len(best):
            best = coords
    return best


def _outer_ring(element: dict) -> list[list[float]]:
    """Outer ring de una relation multipolygon (primer member role=outer con geom),
    fallback al member way mas largo."""
    for m in element.get("members", []):
        if m.get("type") == "way" and m.get("role") == "outer":
            coords = _latlon_list(m.get("geometry"))
            if coords:
                return coords
    return _longest_member_way(element)


def infra_geometry(element: dict, subtype: str) -> tuple[str, list] | None:
    """(kind, coords) o None si no hay geometria usable.

    - node            -> ("point", [lat,lon])
    - way cerrado     -> ("polygon", [[lat,lon],...])
    - way abierto + transmision -> ("line", [[lat,lon],...])
    - way abierto otro -> ("point", [lat,lon] del primer nodo)
    - relation + transmision -> ("line", member way mas largo)
    - relation otro   -> ("polygon", outer ring)
    """
    etype = element.get("type")
    if etype == "node":
        return ("point", [element["lat"], element["lon"]])

    if etype == "way":
        coords = _latlon_list(element.get("geometry"))
        if not coords:
            return None
        if _is_closed(coords):
            return ("polygon", coords)
        if subtype == "transmision":
            return ("line", coords)
        return ("point", coords[0])

    if etype == "relation":
        if subtype == "transmision":
            coords = _longest_member_way(element)
            return ("line", coords) if len(coords) >= 2 else None
        ring = _outer_ring(element)
        return ("polygon", ring) if len(ring) >= 3 else None

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_geometry.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infraestructura/extract.py tests/infraestructura/test_geometry.py
git commit -m "feat(infraestructura): infra_geometry (point/polygon/line + relation handling)"
```

### Task 6: `build_infra_feature`

**Files:**
- Modify: `src/infraestructura/extract.py`
- Test: `tests/infraestructura/test_features.py`

- [ ] **Step 1: Write the failing test**

Create `tests/infraestructura/test_features.py`:

```python
"""build_infra_feature: element + clasificacion -> dict feature."""
from infraestructura.extract import build_infra_feature

NODE_TOWER = {"type": "node", "id": 7, "lat": 44.9, "lon": -93.2,
              "tags": {"man_made": "water_tower", "name": "Witch's Hat", "operator": "Mpls Water"}}


def test_feature_has_full_schema():
    f = build_infra_feature(NODE_TOWER, "water", "suministro")
    assert f["name"] == "Witch's Hat"
    assert f["category"] == "water"
    assert f["subtype"] == "suministro"
    assert f["kind"] == "point"
    assert f["coords"] == [44.9, -93.2]
    assert f["operator"] == "Mpls Water"
    assert f["osm_id"] == 7

def test_name_fallback_to_operator_when_unnamed():
    el = {"type": "node", "id": 1, "lat": 1, "lon": 2,
          "tags": {"power": "substation", "operator": "Xcel Energy"}}
    f = build_infra_feature(el, "power", "subestacion")
    assert "Xcel Energy" in f["name"]

def test_name_fallback_to_category_when_no_name_no_operator():
    el = {"type": "node", "id": 1, "lat": 1, "lon": 2, "tags": {"power": "substation"}}
    f = build_infra_feature(el, "power", "subestacion")
    assert f["name"] == "Electricidad sin nombre"

def test_returns_none_when_no_geometry():
    el = {"type": "way", "id": 1, "geometry": [], "tags": {"power": "plant"}}
    assert build_infra_feature(el, "power", "generacion") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_features.py -v`
Expected: FAIL — `cannot import name 'build_infra_feature'`.

- [ ] **Step 3: Write the implementation**

Append al final de `src/infraestructura/extract.py` (después de `infra_geometry`):

```python
from infraestructura.zones import INFRA_LABELS


def build_infra_feature(element: dict, category: str, subtype: str) -> dict | None:
    """Convierte un element Overpass + su clasificacion en un feature dict.

    Devuelve None si no hay geometria usable.
    """
    geo = infra_geometry(element, subtype)
    if geo is None:
        return None
    kind, coords = geo

    tags = element.get("tags") or {}
    name = tags.get("name") or ""
    operator = tags.get("operator") or ""
    if not name:
        name = operator or f"{INFRA_LABELS.get(category, category)} sin nombre"

    return {
        "name": name,
        "category": category,
        "subtype": subtype,
        "kind": kind,
        "coords": coords,
        "operator": operator,
        "osm_id": element.get("id"),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_features.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infraestructura/extract.py tests/infraestructura/test_features.py
git commit -m "feat(infraestructura): build_infra_feature (schema + name fallback)"
```

---

## Fase 4 — CLI + pipeline

### Task 7: CLI `main` (Overpass -> emit datos_infraestructura.js)

**Files:**
- Modify: `src/infraestructura/extract.py`
- Test: `tests/infraestructura/test_extract_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/infraestructura/test_extract_cli.py`:

```python
"""parse_args + main con Overpass mockeado."""
import json
from pathlib import Path
from unittest.mock import patch

from infraestructura.extract import parse_args, main

FAKE_OVERPASS = {"elements": [
    {"type": "node", "id": 1, "lat": 44.9, "lon": -93.2,
     "tags": {"man_made": "water_tower", "name": "Tower A"}},
    {"type": "way", "id": 2, "geometry": [
        {"lat": 44.9, "lon": -93.2}, {"lat": 44.91, "lon": -93.21}],
     "tags": {"power": "line"}},
    {"type": "node", "id": 3, "lat": 44.95, "lon": -93.25,
     "tags": {"amenity": "recycling", "recycling_type": "container"}},  # excluido
]}


def test_parse_args_city():
    ns = parse_args(["--city", "minneapolis"])
    assert ns.city == "minneapolis"


def test_main_emits_4_data_vars(tmp_path, capsys):
    cities = tmp_path / "cities.json"
    cities.write_text(json.dumps({"minneapolis": {
        "display_name": "Mpls", "country": "US", "bbox": [44.86, -93.38, 45.05, -93.17],
        "center": [44.97, -93.26], "zoom": 12, "tagline": "x", "locale": "en"}}), encoding="utf-8")
    vis = tmp_path / "visualizer"

    argv = ["--city", "minneapolis", "--cities-file", str(cities), "--visualizer-root", str(vis)]
    with patch("infraestructura.extract.query_with_retry", return_value=FAKE_OVERPASS), \
         patch("sys.argv", ["extract-infraestructura"] + argv):
        main()

    out = (vis / "cities" / "minneapolis" / "datos_infraestructura.js").read_text(encoding="utf-8")
    assert "var DATA_INFRA_POWER = " in out
    assert "var DATA_INFRA_WATER = " in out
    assert "var DATA_INFRA_WASTE = " in out
    assert "var DATA_INFRA_TELECOM = " in out
    # water tower + power line clasificados; recycling container excluido
    assert "Tower A" in out
    assert (vis / "cities" / "minneapolis" / "manifest.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_extract_cli.py -v`
Expected: FAIL — `cannot import name 'parse_args'` / `main` raises NotImplementedError.

- [ ] **Step 3: Write the implementation**

Append al final de `src/infraestructura/extract.py` la sección CLI + `main` (mirror de transporte/extract.py):

```python
# ──────────────────────────────────────────────────────────────────────────
# CLI + main pipeline
# ──────────────────────────────────────────────────────────────────────────

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from shared.overpass_client import query_with_retry
from shared.registry import (
    load_cities, get_city, CityNotFoundError, RegistryError, save_manifest_entry,
)
from infraestructura.classifiers import classify_infra
from infraestructura.zones import INFRA_LABELS, build_infraestructura_query

CATEGORIES = ("power", "water", "waste", "telecom")


def resolve_city_args(city, bbox, slug, cities_file: Path) -> tuple[str, str]:
    if city is not None:
        cities = load_cities(cities_file)
        entry = get_city(cities, city)
        s, w, n, e = entry["bbox"]
        return (f"{s},{w},{n},{e}", city)
    if bbox is not None:
        if slug is None:
            raise ValueError("If you pass --bbox you must also pass --slug")
        return (bbox, slug)
    raise ValueError("You must pass --city or --bbox+--slug")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract OSM infrastructure -> JS prebuilt")
    p.add_argument("--city", help="City slug from cities.json (e.g. minneapolis)")
    p.add_argument("--bbox", help="Escape hatch: bbox 's,w,n,e' (requires --slug)")
    p.add_argument("--slug", help="Output slug when using --bbox without --city")
    p.add_argument("--cities-file", default=None)
    p.add_argument("--visualizer-root", default=None)
    return p.parse_args(argv)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    cities_file = Path(args.cities_file) if args.cities_file else repo_root / "cities.json"
    vis_root = Path(args.visualizer_root) if args.visualizer_root else repo_root / "visualizer"

    try:
        bbox, slug = resolve_city_args(args.city, args.bbox, args.slug, cities_file)
    except (CityNotFoundError, RegistryError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    out_dir = vis_root / "cities" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "datos_infraestructura.js"

    print("CS2 OSM Toolkit - Infraestructura Extractor")
    print(f"City         : {slug}")
    print(f"Bounding Box : {bbox}")

    query = build_infraestructura_query(bbox)
    print("[1/2] Downloading infrastructure from Overpass...")
    result = query_with_retry(query, "infraestructura")
    elements = result.get("elements", [])
    print(f"      raw elements: {len(elements)}")

    print("[2/2] Classifying + building features...")
    buckets: dict[str, list] = defaultdict(list)
    skipped_class = skipped_geom = 0
    for el in elements:
        if el.get("type") not in ("node", "way", "relation"):
            continue
        hit = classify_infra(el.get("tags") or {})
        if hit is None:
            skipped_class += 1
            continue
        category, subtype = hit
        feat = build_infra_feature(el, category, subtype)
        if feat is None:
            skipped_geom += 1
            continue
        buckets[category].append(feat)

    total = sum(len(v) for v in buckets.values())
    print(f"  {'category':<10}  count")
    for key in CATEGORIES:
        print(f"  {key:<10}  {len(buckets.get(key, [])):>5}")
    print(f"  TOTAL: {total}   skipped(class)={skipped_class} skipped(geom)={skipped_geom}")

    with out_path.open("w", encoding="utf-8") as f:
        f.write("// Auto-generated by infraestructura.extract\n")
        f.write(f"// {slug} - Infraestructura - bbox: {bbox}\n")
        f.write(f"// Total: {total}\n\n")
        for key in CATEGORIES:
            f.write(f"var DATA_INFRA_{key.upper()} = ")
            json.dump(buckets.get(key, []), f, ensure_ascii=False, separators=(",", ":"))
            f.write(";\n")

    print(f"Done. {out_path} - {out_path.stat().st_size/1024:.1f} KB - {total} features")
    save_manifest_entry(visualizer_root=vis_root, slug=slug,
                        module="infraestructura", file_path=out_path, features=total)


if __name__ == "__main__":
    main()
```

> NOTA: el `from infraestructura.zones import INFRA_LABELS` del Task 6 ya existe arriba; este bloque re-importa `INFRA_LABELS` junto con `build_infraestructura_query` — Python deduplica, está OK. Mantener un solo import si el linter se queja.

- [ ] **Step 4: Run test to verify it passes**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/test_extract_cli.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the FULL module suite (no regressions)**

Run: `src/.venv/Scripts/python.exe -m pytest tests/infraestructura/ -v`
Expected: PASS (~39 passed).

- [ ] **Step 6: Commit**

```bash
git add src/infraestructura/extract.py tests/infraestructura/test_extract_cli.py
git commit -m "feat(infraestructura): CLI main pipeline (Overpass -> classify -> emit + manifest)"
```

---

## Fase 5 — Integración visualizer (`visualizer/map.html`)

> Estas tasks editan el HTML monolítico del visualizer (sin unit tests JS, igual que transporte/services). Verificación: cargar el mapa y revisar consola + counts. Cada task indica el ancla exacta.

### Task 8: Wiring de bootstrap + CSS color var

**Files:**
- Modify: `visualizer/map.html` (líneas ~50, ~947, ~956, ~981-983)

- [ ] **Step 1: CSS color var**

En el bloque `:root` de CSS (cerca de la línea 50, junto a `--cat-transport`), agregar:
```css
      --cat-infra:        #f1c40f;   /* amarillo infraestructura */
```

- [ ] **Step 2: moduleToFile**

En `moduleToFile` (línea ~947), agregar la entry:
```js
      transporte:         "datos_transporte.js",
      infraestructura:    "datos_infraestructura.js",
```

- [ ] **Step 3: SECONDARY set**

Línea ~956, agregar al set:
```js
    const SECONDARY = new Set(["official_zoning", "transporte", "infraestructura"]);
```

- [ ] **Step 4: lazy-load dispatch**

En el loop de secondary modules (línea ~981, después del bloque `transporte`), agregar:
```js
        if (m === "infraestructura" && typeof window.infraestructuraLoaded === "function") {
          window.infraestructuraLoaded();
        }
```

- [ ] **Step 5: Verify (no rompe el load)**

Run: `cd visualizer && python -m http.server 8765` y abrir `http://localhost:8765/map.html?city=minneapolis`.
Expected: el mapa carga igual que antes (aún no hay datos_infraestructura.js → la consola muestra el warn de fetch 404 del módulo, que es benigno porque infraestructura no está en el manifest todavía). Sin errores JS rojos.

- [ ] **Step 6: Commit**

```bash
git add visualizer/map.html
git commit -m "feat(visualizer): wire infraestructura bootstrap (moduleToFile, SECONDARY, lazy dispatch, CSS var)"
```

### Task 9: Layer groups + estilo + MODULE_META + pill + MODULES init

**Files:**
- Modify: `visualizer/map.html` (líneas ~1191, ~1568, ~1601-1617, ~1652)

- [ ] **Step 1: Layer groups + estilo + labels**

Después del bloque `transporteGroups` / `TRANSPORT_LABELS` (línea ~1205), agregar:
```js
  // Parallel layer groups for infraestructura — lazy-populated by window.infraestructuraLoaded()
  const infraGroups = {
    power:   L.layerGroup().addTo(map),
    water:   L.layerGroup().addTo(map),
    waste:   L.layerGroup().addTo(map),
    telecom: L.layerGroup().addTo(map),
  };

  const INFRA_STYLE = {
    power:   { color: "#f1c40f", weight: 2.0, opacity: 0.85, fillOpacity: 0.25 }, // amarillo
    water:   { color: "#3498db", weight: 2.0, opacity: 0.85, fillOpacity: 0.25 }, // azul
    waste:   { color: "#8d6e63", weight: 2.0, opacity: 0.85, fillOpacity: 0.25 }, // marron
    telecom: { color: "#9b59b6", weight: 2.0, opacity: 0.85, fillOpacity: 0.25 }, // violeta
  };

  const INFRA_LABELS = {
    power:   "Electricidad",
    water:   "Agua y Alcantarillado",
    waste:   "Basura",
    telecom: "Comunicaciones",
  };
```

- [ ] **Step 2: MODULE_META entry**

En `MODULE_META` (después de la entry `transporte`, línea ~1575), agregar:
```js
    infraestructura: {
      label: "Infraestructura",
      cat: "var(--cat-infra)",
      svg: `<svg class="pill-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">` +
           `<path d="M13 2 L4 14 h6 l-1 8 9-12 h-6 z"/></svg>`,
    },
```

- [ ] **Step 3: sync helper**

Después de `syncTransporteAvailability` (línea ~1611), agregar:
```js
  function syncInfraestructuraAvailability() {
    const pill = document.querySelector('.pill[data-module="infraestructura"]');
    if (!pill) return;
    if (typeof DATA_INFRA_POWER !== "undefined") {
      pill.classList.remove("disabled");
      const lock = pill.querySelector(".pill-lock");
      if (lock) lock.remove();
      pill.title = MODULE_META.infraestructura.label;
    }
  }
```

- [ ] **Step 4: injectPill**

Después de `injectPill("transporte", hasTransporte);` (línea ~1617), agregar:
```js
  const hasInfra = !!(CITY_MANIFEST.modules?.infraestructura) && typeof DATA_INFRA_POWER !== "undefined";
  injectPill("infraestructura", hasInfra);
```

- [ ] **Step 5: MODULES init**

Después de `MODULES.transporte = { ... };` (línea ~1652), agregar:
```js
  MODULES.infraestructura = { label: "Infraestructura", enabled: false, layerGroupsRef: () => [] };
```

- [ ] **Step 6: Verify**

Recargar `http://localhost:8765/map.html?city=minneapolis`. Expected: aparece el pill "Infraestructura" (disabled/lock, porque aún no hay datos). Sin errores JS.

- [ ] **Step 7: Commit**

```bash
git add visualizer/map.html
git commit -m "feat(visualizer): infraestructura layer groups, style, MODULE_META, pill, MODULES init"
```

### Task 10: Legend + counts + `window.infraestructuraLoaded` (render por kind)

**Files:**
- Modify: `visualizer/map.html` (líneas ~1926, ~1977, ~2059)

- [ ] **Step 1: Legend section**

Después del bloque de legend de `transporte` (línea ~1926, después de su `}`), agregar:
```js
    const hasInfra = !!(CITY_MANIFEST.modules?.infraestructura);
    if (hasInfra) {
      html += `<h4 style="margin-top:14px"><span class="master-toggle on" data-module="infraestructura" title="Toggle Infraestructura"></span>Infraestructura</h4>`;
      for (const key of Object.keys(INFRA_STYLE)) {
        const style = INFRA_STYLE[key];
        html += `<div class="li">
          <div class="ldot" style="background:${style.color}"></div>
          <span class="lname">${escHtml(INFRA_LABELS[key])}</span>
          <span class="lcount zero" id="icount-${key}">0</span>
        </div>`;
      }
    }
```

- [ ] **Step 2: updateLegendCounts**

En `updateLegendCounts`, después del loop de `transporteGroups` (línea ~1977), agregar:
```js
    for (const cat of Object.keys(infraGroups || {})) {
      const el = document.getElementById("icount-" + cat);
      if (!el) continue;
      const count = infraGroups[cat].getLayers().length;
      el.textContent = count.toLocaleString();
      el.classList.toggle("zero", count === 0);
    }
```

- [ ] **Step 3: `window.infraestructuraLoaded` hook**

Después del cierre de `window.transporteLoaded = function () { ... };` (línea ~2059), agregar:
```js
  window.infraestructuraLoaded = function () {
    let total = 0;
    for (const cat of Object.keys(infraGroups)) {
      const data = window[`DATA_INFRA_${cat.toUpperCase()}`];
      if (!Array.isArray(data)) continue;
      const style = INFRA_STYLE[cat];
      for (const f of data) {
        if (!f.coords) continue;
        const popup = `<b>${escHtml(f.name || "Sin nombre")}</b><br>` +
          `<span style="color:#888;font-size:11px">${escHtml(INFRA_LABELS[cat])} · ${escHtml(f.subtype || "")}` +
          (f.operator ? ` · ${escHtml(f.operator)}` : "") + `</span>`;
        let layer;
        if (f.kind === "point") {
          layer = L.circleMarker(f.coords, { radius: 4, ...style, fillOpacity: 0.9 });
        } else if (f.kind === "polygon") {
          layer = L.polygon(f.coords, style);
        } else { // line
          if (f.coords.length < 2) continue;
          layer = L.polyline(f.coords, style);
        }
        layer.bindPopup(popup);
        infraGroups[cat].addLayer(layer);
        total++;
      }
    }
    window._cs2InfraCount = total;
    console.log(`[infraestructura] Loaded ${total} features across ${Object.keys(infraGroups).length} layer groups.`);

    for (const cat of Object.keys(infraGroups)) {
      const el = document.getElementById(`icount-${cat}`);
      if (!el) continue;
      const count = infraGroups[cat].getLayers().length;
      el.textContent = count.toLocaleString();
      el.classList.toggle("zero", count === 0);
    }

    MODULES.infraestructura = {
      label: "Infraestructura",
      enabled: true,
      layerGroupsRef: () => Object.values(infraGroups),
    };
    moduleStates.infraestructura = "on";
    if (typeof syncInfraestructuraAvailability === "function") syncInfraestructuraAvailability();
    if (typeof syncUI === "function") syncUI();
  };
```

- [ ] **Step 4: Verify (tras generar datos en Task 11)**

Este task se verifica end-to-end junto con Task 11 (necesita `datos_infraestructura.js`). Por ahora confirmar que no hay errores de sintaxis JS: recargar el mapa, la consola no debe tirar errores.

- [ ] **Step 5: Commit**

```bash
git add visualizer/map.html
git commit -m "feat(visualizer): infraestructura legend + counts + infraestructuraLoaded render-by-kind hook"
```

---

## Fase 6 — Datos Mpls + docs

### Task 11: Generar datos de Minneapolis + verificar end-to-end

**Files:**
- Generate: `visualizer/cities/minneapolis/datos_infraestructura.js`
- Modify: `visualizer/cities/minneapolis/manifest.json` (vía el extractor)

- [ ] **Step 1: Correr el extractor (live Overpass)**

Run: `cd src && ./.venv/Scripts/python.exe -m infraestructura.extract --city minneapolis`
Expected: tabla de counts con `power`, `water`, `waste` > 0 (telecom puede ser bajo). TOTAL > 20. Sin errores. Genera `datos_infraestructura.js` + actualiza `manifest.json`.

- [ ] **Step 2: Verificar la data generada**

Run: `src/.venv/Scripts/python.exe -c "import re,json; t=open(r'visualizer/cities/minneapolis/datos_infraestructura.js',encoding='utf-8').read(); [print(m.group(1), len(json.loads(m.group(2)))) for m in re.finditer(r'var DATA_INFRA_(\w+) = (\[.*?\]);', t, re.DOTALL)]"`
Expected: imprime las 4 categorías con sus counts. Confirmar que power tiene líneas (kind=line) y puntos/polígonos.

- [ ] **Step 3: Verificar en el visualizer**

Levantar `cd visualizer && python -m http.server 8765`, abrir `http://localhost:8765/map.html?city=minneapolis`. Expected:
- Pill "Infraestructura" activo (sin lock).
- Toggle muestra/oculta las capas; líneas eléctricas amarillas visibles, instalaciones como puntos/áreas.
- Legend "Infraestructura" con counts > 0.
- Popups muestran nombre + categoría · subtipo.

- [ ] **Step 4: Commit**

```bash
git add visualizer/cities/minneapolis/datos_infraestructura.js visualizer/cities/minneapolis/manifest.json
git commit -m "feat(infraestructura): generate Minneapolis infrastructure data"
```

### Task 12: Docs (README + METHODOLOGY del módulo)

**Files:**
- Create: `src/infraestructura/README.md`
- Create: `docs/methodology/infraestructura.md` (seguir la ubicación que usó transporte; si transporte puso la methodology en otro path, igualar)

- [ ] **Step 1: Verificar dónde puso transporte sus docs**

Run: `git show --stat ac3dcea~1..ac3dcea -- '*transporte*README*' '*METHODOLOGY*'` o `ls src/transporte/` para ver si hay README.md y dónde está la methodology.
Expected: identificar el path/convención exacta (el commit `d5aef0d` fue "docs(transporte): README + Methodology").

- [ ] **Step 2: Escribir README del módulo**

Contenido mínimo de `src/infraestructura/README.md`:
```markdown
# Módulo Infraestructura

Extrae utilities de OSM (electricidad, agua/alcantarillado, basura, comunicaciones) para CS2.

## Uso
```
cd src && uv run extract-infraestructura --city minneapolis
```

## Categorías (OSM → CS2)
- **power** (Electricidad): `power=plant/generator/substation/transformer/line/minor_line`
- **water** (Agua y Alcantarillado): `man_made=water_tower/water_works/pumping_station/water_well/reservoir_covered/wastewater_plant`
- **waste** (Basura): `landuse=landfill`, `amenity=waste_transfer_station`, `amenity=recycling` (solo `recycling_type=centre`), `man_made=incinerator`
- **telecom** (Comunicaciones): `man_made=communications_tower`; `man_made=mast/tower` con `tower:type=communication`; `telecom=data_center`

## Exclusiones
`power=tower/pole/cable`, `amenity=waste_basket`, recycling containers, mástiles no-telecom.

Ver spec: `docs/specs/2026-05-31-infraestructura-design.md`.
```

- [ ] **Step 3: Commit**

```bash
git add src/infraestructura/README.md docs/methodology/infraestructura.md
git commit -m "docs(infraestructura): README + methodology"
```

---

## Verificación final

- [ ] **Suite completa sin regresiones**

Run: `src/.venv/Scripts/python.exe -m pytest tests/ -q -m "not network and not integration"`
Expected: ~440 passed (los ~39 nuevos de infraestructura + el baseline ~403). Las fallas conocidas de `official_zoning` (URL-rot en tests de red) quedan excluidas por `-m "not network and not integration"`; si igual aparecen, confirmar que pre-existen en HEAD.

- [ ] **Update MOC + memoria** (fuera del repo, en el vault `brain`): marcar Módulo Infraestructura como shipped en `🏙 CS2-Mineapolis (MOC).md`, crear nota de sesión, actualizar `cs2_*` memory + MEMORY.md.
