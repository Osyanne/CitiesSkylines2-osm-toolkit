# CS2 OSM Toolkit — notas para Claude

El dueño del repo habla español (rioplatense): respondé en español. Lo que se
publica para jugadores (Reddit, README.md) va en inglés.

## Pendientes

- **Densidad residencial por morfología** (pedido de u/Pamani_ en Reddit, ciudades
  europeas como Amberes salen casi todas `res_low_house`). Plan con números y
  propuesta: [docs/plans/2026-09-24-densidad-residencial-morfologia.md](docs/plans/2026-09-24-densidad-residencial-morfologia.md).

## Cómo está armado

- Extractores en `src/` (`extract-zoning`, `extract-vial`, …; ver `[project.scripts]`
  en `src/pyproject.toml`). Escriben `visualizer/cities/<slug>/datos_*.json` en el
  formato compacto (`src/shared/compact.py`) y al final regeneran las teselas
  vectoriales (`src/shared/tiles.py` → `visualizer/cities/<slug>/tiles/`).
- Si se tocan datos a mano: `uv run build-tiles --city <slug>` (desde `src/`).
- Visor: `visualizer/map.html` con MapLibre GL. Lee `manifest.json` de cada ciudad;
  usa las teselas si existen y, si no, los `datos_*.json`.
- Detalles técnicos y números de rendimiento: `METHODOLOGY.md` §8–§9.

## Tests

```bash
cd src && uv sync && uv run pytest ../tests/ -m "not network"
```

Después de correrlos, `git status` tiene que quedar limpio (ningún test debe tocar
los manifests reales de `visualizer/cities/`).

## Publicación

GitHub Pages publica desde `main` (https://osyanne.github.io/CitiesSkylines2-osm-toolkit/).
Un merge a `main` dispara "pages build and deployment" y el workflow `Tests`.

Donaciones: Ko-fi es la principal (botón **Support →** de la landing); el footer y
los README también listan GitHub Sponsors y Patreon. Los links están en
`src/shared/landing.py` y `.github/FUNDING.yml`; después de tocar `landing.py`,
regenerar con `uv run generate-landing`.

## Entorno en la nube

Las sesiones remotas no llegan a reddit.com, ko-fi.com, github.io ni google.com (403 del proxy);
para Reddit, pedirle al usuario capturas o el texto de los comentarios.
