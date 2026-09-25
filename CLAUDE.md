# CS2 OSM Toolkit — notas para Claude

El dueño del repo habla español (rioplatense): respondé en español. Lo que se
publica para jugadores (Reddit, README.md) va en inglés.

## Pendientes

- **Densidad residencial por morfología** (pedido de u/Pamani_ en Reddit, ciudades
  europeas como Amberes salen casi todas `res_low_house`). Plan con números y
  propuesta: [docs/plans/2026-09-24-densidad-residencial-morfologia.md](docs/plans/2026-09-24-densidad-residencial-morfologia.md).
- **Ícono de la pestaña:** la landing y el mapa no declaran `favicon`, así que el
  navegador pide `/favicon.ico` y recibe 404 (cosmético).
- **Del lado del usuario** (recordárselo si no lo hizo): activar *Sponsorships* en
  Settings → General → Features del repo para que aparezca el botón Sponsor; cambiar
  el topic `leaflet` por `maplibre`; subir la portada a Ko-fi; publicar la mejora de
  rendimiento en r/openstreetmap y r/gis (borradores en la sesión del 2026-09-24).

## Versiones

Tags anotados `vX.Y.Z` sobre `main`. Para una versión nueva: subir `version` en
`src/pyproject.toml` y correr `uv lock` (desde `src/`), renombrar `[Unreleased]` en
`CHANGELOG.md` a `[vX.Y.Z] — fecha — título` y fusionar. Desde la nube no se
pueden pushear tags (403: solo se permite el branch de trabajo) y no hay `gh` ni API
de releases: pasarle al usuario un link `releases/new?tag=vX.Y.Z&target=main&title=…&body=…`
ya completado; GitHub crea el tag sobre `main` al tocar "Publish release".

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

Donaciones: el botón **Support ▾** de la landing abre un menú con Ko-fi (primero,
la principal), GitHub Sponsors y Patreon; el footer y los README también listan
las tres. Los links están en
`src/shared/landing.py` y `.github/FUNDING.yml`; después de tocar `landing.py`,
regenerar con `uv run generate-landing`.

## Entorno en la nube

El entorno tiene acceso a la red completo (desde 2026-09-24), así que se puede
abrir la página publicada para probarla. Reddit ("blocked by network security") y
Ko-fi (verificación de Cloudflare) igual bloquean a los navegadores en la nube:
para eso, pedirle al usuario capturas y no intentar saltar esas verificaciones.

Para usar Chromium/Playwright contra sitios externos, primero hay que confiar en la
CA del proxy (el almacén NSS viene vacío):

```bash
apt-get install -y libnss3-tools
certutil -A -d sql:$HOME/.pki/nssdb -n ccr-agent-proxy -t "C,," -i /root/.ccr/agent-proxy-ca.crt
```
