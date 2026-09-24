# CS2 OSM Toolkit

> Datos GIS reales de OpenStreetMap → Cities: Skylines 2
> Toolkit modular · 100% open source · Sin API keys · Mapa interactivo dark

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/License-MIT-green)
![OSM Data](https://img.shields.io/badge/Data-OpenStreetMap-orange)
![Tests](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/actions/workflows/test.yml/badge.svg)

> 🇬🇧 English version: [README.md](README.md)

---

## Ciudades

**22 ciudades** en 11 países, listas para explorar en el navegador sin instalar nada:

**https://osyanne.github.io/CitiesSkylines2-osm-toolkit/**

| Ciudad | País | Capas |
|--------|------|-------|
| Amsterdam | Países Bajos | Zonificación |
| Antwerp | Bélgica | Zonificación |
| Bacău | Rumania | Zonificación |
| Beverlo | Bélgica | Zonificación |
| Butterworth, Penang | Malasia | Zonificación |
| Charleston, SC | EE. UU. | Zonificación |
| Chicago, IL | EE. UU. | Zonificación, calles, servicios |
| Cincinnati, OH | EE. UU. | Zonificación |
| Fayetteville, NC | EE. UU. | Zonificación |
| Hollister, CA | EE. UU. | Zonificación |
| Hong Kong | Hong Kong | Zonificación |
| Kiel | Alemania | Zonificación |
| Kursk | Rusia | Zonificación |
| Little Rock, AR | EE. UU. | Zonificación |
| Łódź | Polonia | Zonificación |
| Madison, WI | EE. UU. | Zonificación |
| Mafra, SC | Brasil | Zonificación, huellas de edificios de Google |
| Minneapolis, MN | EE. UU. | Zonificación, calles, servicios, transporte, zonificación oficial, infraestructura |
| New York, NY | EE. UU. | Zonificación |
| Pittsburgh, PA | EE. UU. | Zonificación |
| Sacramento, CA | EE. UU. | Zonificación |
| Trondheim | Noruega | Zonificación |

Todas las ciudades tienen zonificación. Minneapolis y Chicago además tienen calles y servicios, y Minneapolis suma transporte, zonificación oficial e infraestructura.

### Agregá tu ciudad

Abrí un [City Request issue](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues/new?template=city-request.yml) con el bbox + nombre. Generamos la zonificación, la publicamos y te avisamos en el mismo issue cuando esté lista.

---

## Inicio rápido — Elige tu camino

### Opción A: Solo ver los mapas

Dos opciones:

**Opción 1 — Hosteado (sin setup, sin instalar nada):** Visitá https://osyanne.github.io/CitiesSkylines2-osm-toolkit/ en tu browser. Hacé clic en cualquiera de las 5 tarjetas de ciudad para abrir el mapa.

**Opción 2 — Clonar localmente (necesitás un mini HTTP server):** Cloná el repo, después serví el folder `visualizer/` por HTTP:

```bash
cd cs2-osm-toolkit/visualizer
python -m http.server 8000
```

Abrí `http://localhost:8000/` en tu browser. Los datos de todas las ciudades están incluidos en el repo, así que no hace falta descargar nada extra.

> **¿Por qué HTTP y no doble clic?** El visualizer usa `fetch()` para leer el registro de ciudades y el manifest de cada ciudad. Los browsers bloquean `fetch()` desde URLs `file://` por defecto (política CORS), entonces abrir `index.html` con doble clic muestra el landing pero los mapas de cada ciudad fallan. Cualquier mini HTTP server funciona — el built-in de Python (arriba), `http-server` de Node, o la extensión Live Server de VS Code.

### Opción B: Usarlo para tu ciudad (15–20 minutos, requiere Python)

Guía paso a paso completa: [docs/QUICKSTART.md](docs/QUICKSTART.md).

La versión corta:
1. Instalá Python 3.11+ con la casilla "Add to PATH" marcada, luego instalá uv
2. Abrí una terminal en la carpeta `src/` y ejecutá `uv sync`
3. Agregá tu ciudad en `cities.json` en la raíz del repo con el bbox, y ejecutá:

        uv run extract-zoning --city your_slug
        uv run extract-vial --city your_slug      (opcional)
        uv run extract-services --city your_slug  (opcional)

4. Ejecutá `uv run generate-landing` para actualizar la landing

5. (Opcional) Generá el thumbnail de la tarjeta de tu ciudad para el landing:

        uv sync --group thumbnails               # one-time install (~300 MB Chromium)
        uv run --group thumbnails playwright install chromium   # one-time
        uv run --group thumbnails generate-thumbnails           # auto-detecta missing

   `generate-thumbnails` lee `cities.json`, navega al map URL deployado de cada ciudad, oculta el chrome UI, y guarda un PNG 1200×800 en `visualizer/assets/thumbnails/<slug>.png`. Flags: `--city <slug>` para uno específico, `--force` para regenerar todos, `--base-url http://localhost:8080` para dev local.

Para extracts puntuales sin modificar `cities.json`, usá el escape hatch: `uv run extract-zoning --bbox "sur,oeste,norte,este" --slug your_slug` (ambos flags se requieren juntos).

**¿Algo no funciona?** Ver [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

### Opción C: Desarrollar o contribuir

Clona el repo, ejecuta `uv sync` dentro de `src/`, corre los tests con `uv run pytest`. Todos los detalles técnicos abajo.

---

## ¿Qué hace este toolkit?

Un toolkit modular que extrae datos reales de infraestructura desde OpenStreetMap (vía Overpass API) y los renderiza en un mapa Leaflet dark-mode interactivo. Sirve como referencia visual para construir Mineapolis 1:1 en Cities: Skylines 2. Tres módulos, ~192k features en total.

### 🗺 Módulo Zonificación
Clasifica todos los polígonos de edificios en los **11 tipos de zona oficiales de Cities: Skylines 2** (Low/Medium/High Density Residential, Row Housing, Mixed Housing, Low Rent Housing, Low/High Density Business, Low/High Density Offices, Industrial Manufacturing). 81.732 polígonos en el bbox de Mineapolis.

Ejecutar: `cd src && uv run extract-zoning --city minneapolis`
Salida: `visualizer/cities/minneapolis/datos_zonificacion.json` (~12 MB, formato compacto)

### 🛣 Módulo Red Vial
Clasifica todas las vías OSM en las **6 categorías de carretera de CS2** (Highway, Major Road, Minor Road, Local Street, Pedestrian Path, Bike Lane). Se renderiza como capa de LineStrings. 108.825 features.

Ejecutar: `cd src && uv run extract-vial --city minneapolis`
Salida: `visualizer/cities/minneapolis/datos_vial.json` (~6 MB, formato compacto)

### 🏥 Módulo Servicios
5 capas alineadas a las solapas de servicios base de Cities: Skylines 2 con buena cobertura OpenStreetMap:

- **H** Atención sanitaria y funeraria — hospitales, clínicas, doctors, funeral directors, crematorios, cementerios
- **E** Educación e investigación — schools, universities, colleges, kindergartens, research institutes
- **B** Bomberos — fire stations
- **A** Policía y administración — police HQ, city hall, courthouses, prison + landmarks culturales (bibliotecas, museos, teatros, arts centres, cinemas) + oficinas de gobierno
- **P** Parques — parks, nature reserves, gardens, playgrounds, sports centres

Ejecutar: `cd src && uv run extract-services --city minneapolis`
Salida: `visualizer/cities/minneapolis/datos_servicios.js` (~1,3 MB)

**Notas:**
- Bibliotecas, museos, teatros, arts centres, cinemas comparten el bucket `admin` con policía y oficinas de gobierno. Se diferencian solo por nombre + subtype en el popup.
- Lugares de culto descartados conscientemente (no en estructura CS2 base).
- Electricidad, agua y saneamiento, gestión de residuos diferidos a Sesión 4 (requieren fuentes EIA + MN GIS Commons + opendata.minneapolismn.gov, no OSM).
- Bbox de Minneapolis típicamente devuelve ~2.300 features. Render async chunked para no bloquear el browser.

### Próximos
- 🚌 Módulo Transporte (Blue/Green Line, BRT, rutas de bus, ciclovías) — Sesión 4

---

## Features del visualizer

- **Module pills (arriba derecha)**: toggle módulos enteros en un click
- **Master toggles en leyenda**: mismo efecto, espejado en la barra lateral
- **Modo de fondo** (cuando hay módulos apagados): Oculto / Atenuado / Completo
- **Layer Control** (arriba derecha): toggle granular por zona / categoría vial
- **Canvas renderer**: pan/zoom fluido con 80k+ polígonos + 108k linestrings
- **Tier-based hiding**: casas individuales se ocultan en zoom <14, bloques siempre visibles
- **Paleta fiel a CS2**: 4 familias (verde/azul/morado/amarillo) alineadas al HUD del juego
- **Tema oscuro**: basemap CartoDB Dark Matter
- **Persistencia**: estado de la vista guardado en localStorage (`cs2-view-state-{slug}-v1`, con scope por ciudad)

## Zonificación oficial (experimental)

Para ciudades con datos de planificación públicos, el visualizador ofrece una
capa de zonificación autoritativa proveniente del portal de datos abiertos de
la ciudad — seleccionable mediante un sub-toggle en la leyenda de Zoning
(OSM-derived ↔ Oficial ↔ Comparación).

| Ciudad | Fuente | Categorías |
|---|---|---|
| Minneapolis | City of Minneapolis Planning | ~25 |
| New York | NYC Department of City Planning (ZoLA) | ~70 |

### Generando datos oficiales

El pipeline está implementado y testeado, pero los `DATA_URL` placeholder en
`src/official_zoning/sources/<city>.py` necesitan ser verificados contra el
portal real antes de que la extracción funcione (los CDNs bloquean
descubrimiento automatizado).

Quick start:

1. Abrir el portal de la ciudad en el browser:
   - Mpls: https://opendata.minneapolismn.gov/datasets/planning-primary-zoning
   - NYC: https://www1.nyc.gov/site/planning/data-maps/open-data/dwn-gis-zoning.page
2. Click en download shapefile; capturar el URL resuelto desde DevTools Network tab.
3. Actualizar `DATA_URL` en `src/official_zoning/sources/<city>.py`. Bump `last_validated` en el YAML.
4. Correr extracción:
   ```bash
   cd src
   uv run extract-official-zoning --city minneapolis
   ```
5. El manifest se actualiza automáticamente. Re-correr `uv run generate-landing` para refrescar landing.

Agregar una ciudad nueva = un source module en `src/official_zoning/sources/<slug>.py` + un YAML mapping en `src/official_zoning/mappings/<slug>.yaml` + entrada `official_source` en `cities.json`. Ver Minneapolis como pattern de referencia.

## Capa de tránsito (Minneapolis)

El visualizer renderea la red Metro Transit de Mpls como overlay de 4 categorías,
sourced desde OSM route relations:

| Categoría | Fuente OSM | Rutas Mpls |
|---|---|---|
| LRT | `route=light_rail` | METRO Blue Line, Green Line |
| Commuter Rail | `route=train` | Northstar |
| BRT | `route=bus` + METRO Rapid pattern | METRO A/C/D/E/F Line |
| Bus | `route=bus` (resto) | ~140 rutas locales Metro Transit |

Generar data de tránsito para una ciudad (Mpls works out of the box; otras ciudades
dependen de su cobertura OSM de tránsito):

```bash
cd src
uv run extract-transporte --city minneapolis
```

El visualizer auto-detecta el módulo via el manifest y activa el tile "Transporte" en el HUD.

**Limitación v1 conocida:** El classifier de BRT detecta METRO Rapid via
`network=METRO` o el name pattern `METRO X Line`. La data OSM real puede usar
tags ligeramente distintos (ej. `network=Metro Transit` también para BRT), causando
que algunas rutas BRT caigan bajo Bus. Refinamiento diferido a v1.1.

---

## Setup técnico

### Requisitos
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (reemplazo más rápido de pip+venv)

### Setup

```bash
git clone https://github.com/Osyanne/CitiesSkylines2-osm-toolkit.git
cd cs2-osm-toolkit/src
uv sync
```

### Prebuilts (ya están en el repo)

Los archivos prebuilt `datos_*` de todas las ciudades están **commiteados en `visualizer/cities/<slug>/`**. No hace falta descargar nada.

Zonificación, red vial y edificios de Google usan un formato JSON compacto y sin pérdida (`datos_*.json`, alrededor de un cuarto del tamaño de los `.js` viejos — ver [METHODOLOGY.md §9](METHODOLOGY.md)). Si tenés ciudades generadas con una versión anterior, convertilas una vez con `cd src && uv run convert-legacy-data` (o `--city <slug>`).

**Para regenerar datos frescos** (ej., tras actualizaciones de OSM):

```bash
cd src
uv run extract-zoning --city minneapolis    # ~3-5 min
uv run extract-vial --city minneapolis      # ~30s
uv run extract-services --city minneapolis  # ~1 min
```

Reemplazá `minneapolis` con cualquier slug del registro `cities.json` (`chicago`, `amsterdam`, `new_york`, `lodz`). Cada extracción actualiza el manifest preservando los otros módulos.

### Levantar el visualizer

```bash
cd visualizer
python -m http.server 8000
# Abrir http://localhost:8000/ (landing) o http://localhost:8000/map.html?city=minneapolis (mapa directo)
```

### Correr tests

```bash
cd src
uv run pytest
```

171 tests pasando en módulos de zoning, vial y services.

---

## Estructura del proyecto

```
cities.json                   # Registro multi-ciudad (bbox, center, zoom, metadata)

src/
├── shared/
│   ├── overpass_client.py    # Cliente Overpass con retry + rotación de endpoints
│   ├── registry.py           # Lee cities.json; resuelve --city <slug> a bbox
│   └── landing.py            # CLI generate-landing (reconstruye visualizer/index.html)
├── zoning/
│   ├── zones.py              # Modelo de zonas CS2 + queries Overpass
│   ├── classifiers.py        # Clasificador OSM tag → zona CS2
│   ├── extract.py            # Pipeline CLI (entry: extract-zoning)
│   └── patch_colors.py       # Utility de paleta
├── vial/
│   ├── zones.py              # Modelo de vías CS2 + query Overpass
│   ├── classifiers.py        # Clasificador OSM highway tag → categoría vial
│   └── extract.py            # Pipeline CLI (entry: extract-vial)
└── services/
    ├── zones.py              # Modelo de servicios CS2 + queries Overpass (5 buckets)
    ├── classifiers.py        # Clasificador OSM tags → bucket H/E/B/A/P
    └── extract.py            # Pipeline CLI (entry: extract-services)

tests/
├── zoning/                   # 84 tests
├── vial/                     # 33 tests
└── services/                 # 54 tests
                              # 171 en total

visualizer/
├── index.html                # Landing, galería de tarjetas de ciudad
├── map.html                  # Visor de mapa — se carga como map.html?city=<slug>
├── cities.json               # Artefacto de deployment (copia del cities.json raíz)
├── cities/
│   ├── minneapolis/          # todos los módulos: zonificación, calles, servicios, transporte, zonificación oficial, infraestructura
│   ├── chicago/              # datos_zonificacion.json + datos_vial.json + datos_servicios.js + manifest.json
│   └── <slug>/               # datos_zonificacion.json + manifest.json (una carpeta por ciudad de cities.json)
└── assets/
    └── thumbnails/           # <slug>.png, una por ciudad

docs/
├── QUICKSTART.md             # Guía ELI5 para usuarios no técnicos
├── TROUBLESHOOTING.md        # Errores comunes y soluciones
├── adapting-to-other-cities.md
├── bbox-mcp-server.md
├── cs2-zone-reference.md
├── github-publishing.md
├── plans/                    # Planes de implementación por sesión
└── specs/                    # Specs de diseño

.github/
└── ISSUE_TEMPLATE/
    └── city-request.yml      # Template de issue para solicitar ciudad
```

---

## Stats del proyecto

| | |
|---|---|
| **Módulos** | Zonificación en las 22 ciudades. Calles y servicios en Minneapolis y Chicago. Transporte, zonificación oficial e infraestructura en Minneapolis. Huellas de edificios de Google en Mafra. |
| **Bounding box** | 22 ciudades, ver `cities.json` |
| **Features totales** | ~1,67M entre todas las ciudades |
| **Tests** | Corren en cada push, ver el badge de arriba |
| **Última extracción** | Depende de la ciudad, ver cada `manifest.json` |

---

## Adaptarlo a otras ciudades

El pipeline es multi-ciudad mediante el registro `cities.json` en la raíz del repo. Para agregar una ciudad:

1. Agregá una entrada en `cities.json` con `display_name`, `country`, `bbox`, `center`, `zoom`, `tagline`, `locale`
2. Ejecutá `uv run extract-zoning --city <your_slug>` (y opcionalmente `extract-vial` / `extract-services`)
3. Ejecutá `uv run generate-landing` para actualizar la landing
4. Abrí un PR al repo upstream si querés que quede incluida para todos

Para extracts puntuales sin modificar `cities.json`: `uv run extract-zoning --bbox "s,o,n,e" --slug your_city`.

Ver [docs/adapting-to-other-cities.md](docs/adapting-to-other-cities.md) para guía específica por ciudad, ejemplos de bbox y calibración de umbrales de densidad.

---

## Créditos

Salvo las primeras, cada ciudad del sitio está porque alguien la pidió.

| Ciudad | La pidió |
|--------|----------|
| Charleston, SC | [@MrWicK95](https://github.com/MrWicK95) |
| Mafra, SC | [@arthuregood](https://github.com/arthuregood) |
| Trondheim | [@SvenErik1968](https://github.com/SvenErik1968) |
| Bacău | [@VasileStelian](https://github.com/VasileStelian) |
| Fayetteville, NC | [@brooklyn85knight-sys](https://github.com/brooklyn85knight-sys) |
| Sacramento, CA | [@jwkueb](https://github.com/jwkueb) |
| Nueva York, NY | [@ooo-89S](https://github.com/ooo-89S) |
| Hollister, CA | [@gileslcaleb-67](https://github.com/gileslcaleb-67) |
| Butterworth, Penang | [@ansehelm](https://github.com/ansehelm) |
| Amberes | [@tomdelamontagne](https://github.com/tomdelamontagne) |
| Łódź | [@Telduu](https://github.com/Telduu) |
| Kiel | [@bamboucha1](https://github.com/bamboucha1) |
| Kursk | [@gandonuebanovic14-spec](https://github.com/gandonuebanovic14-spec) |
| Cincinnati, OH | [@caleb2656](https://github.com/caleb2656) |
| Pittsburgh, PA | [@WARning296](https://github.com/WARning296) |
| Hong Kong | [@Tableisnottable](https://github.com/Tableisnottable) |
| Little Rock, AR | [@rlprice5525](https://github.com/rlprice5525) |
| Beverlo | [@Hobbel1968](https://github.com/Hobbel1968) |
| Chicago, IL | [@Alan-March](https://github.com/Alan-March) |

Quienes apoyan el proyecto en [Patreon](https://www.patreon.com/c/CS2OSMToolkit)
también van acá. A nadie se lo agrega sin preguntarle antes: si apoyás y querés
aparecer, escribime y decime cómo preferís figurar.

---

## Licencia

MIT. Datos OSM via OpenStreetMap contributors bajo ODbL.
