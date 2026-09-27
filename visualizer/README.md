# CS2 OSM Toolkit — Visualizer (v3.3)

Visualizador interactivo **multi-city** (MapLibre GL + teselas vectoriales) del toolkit OSM para Cities: Skylines 2. Soporta 5 ciudades curadas: Minneapolis (zoning + vial + services) y Manhattan / Tokyo / Amsterdam / Madison (zoning only).

## Quick start

```bash
# Servir el visualizer en localhost:8000
cd visualizer
python -m http.server 8000
```

Dos puntos de entrada:

- **Landing con galería** — http://localhost:8000/index.html — muestra las 5 ciudades disponibles, click en card para abrir el mapa
- **Mapa directo de una ciudad** — http://localhost:8000/map.html?city=minneapolis (también `manhattan`, `tokyo`, `amsterdam`, `madison`)

Si abrís `map.html` sin `?city=`, redirige a la landing automáticamente. Slug inválido también redirige.

## Prebuilts

Zonificación y red vial se dibujan desde teselas vectoriales (`cities/<slug>/tiles/`, generadas con `uv run build-tiles`): el navegador baja solo lo que se ve. Los archivos de datos (`datos_zonificacion.json`, `datos_vial.json`, `datos_servicios.js`) **ya están commiteados** en el repo bajo `visualizer/cities/<slug>/`. **No hay que descargar nada.**

Estructura:

```
visualizer/cities/
├── minneapolis/    # full: zoning + vial + services
├── manhattan/      # zoning only
├── tokyo/          # zoning only
├── amsterdam/      # zoning only
└── madison/        # zoning only
```

Cada directorio incluye un `manifest.json` que declara qué módulos están presentes + sus hashes sha256 para cache busting. El visualizer lo lee primero y solo inyecta scripts para los módulos disponibles — por eso las 4 ciudades nuevas no muestran controles de Vial ni Servicios en la leyenda.

### Regenerar datos localmente (opcional)

Si querés re-extraer datos frescos desde OpenStreetMap:

```bash
cd ../src
uv run extract-zoning   --city minneapolis    # ~3-5 min  → cities/minneapolis/datos_zonificacion.json
uv run extract-vial     --city minneapolis    # ~30s      → cities/minneapolis/datos_vial.json
uv run extract-services --city minneapolis    # ~1 min    → cities/minneapolis/datos_servicios.js
```

Reemplazá `minneapolis` con cualquier slug del registro (`cities.json`). Cada extract actualiza el `manifest.json` correspondiente preservando los módulos ya generados (podés agregar vial a Manhattan sin perder su zoning).

Para ciudades fuera del registro: `uv run extract-zoning --bbox "s,w,n,e" --slug mi_ciudad` (escape hatch sin tocar `cities.json`).

### Regenerar landing

Si agregás o modificás ciudades:

```bash
cd ../src
uv run generate-landing    # regenera visualizer/index.html + copia cities.json
```

## Controles de UI

- **Columna de capas** — acoplada a la izquierda en escritorio (el mapa se achica a su lado; `«` la pliega y `☰ Layers` la vuelve a abrir) y bandeja inferior en el celular (con el celular apaisado, cajón a la izquierda de alto completo). Un bloque por módulo presente en la ciudad; con un solo módulo (zoning) es directamente la lista de zonas
- **On / Dim / Off** por módulo — Dim deja las capas visibles con la opacidad × 0,3. Primera visita: zoning On, vial Dim, el resto Off
- **Checkbox por categoría + `Only`** (por fila y por grupo) — aviso `Showing N of M … · Restore / Show all` arriba del bloque. Las categorías sin nada en la ciudad van a un `N not in this city` plegado
- **Fuente de zonas** (si hay plan oficial) — `OSM-derived | Official plan`; los conteos pasan a ser los del plan
- **Mapa base** — `Dark | Satellite`, en el pie de la columna

## Persistencia

Los módulos (On/Dim/Off) y el mapa base se guardan en `localStorage` con clave **scoped por ciudad**: `cs2-view-state-{slug}-v2` (ej. `cs2-view-state-minneapolis-v2`). Cada ciudad recuerda independientemente su última vista — cambiar de Manhattan a Tokyo no pisa la configuración de la otra. Las categorías ocultas no se guardan. La columna abierta o cerrada es una preferencia global: `cs2-layers-col-v1`.

Para reset de una ciudad: DevTools → Application → Local Storage → borrar la clave correspondiente.

## ¿Tu ciudad no está?

Abrí un [City Request issue](https://github.com/Osyanne/CitiesSkylines2-osm-toolkit/issues/new?template=city-request.yml) con el bbox + nombre. Generamos el prebuilt de zoning y publicamos (~30-60 min turnaround si está activo). Vial + services son ampliación on-demand si la ciudad acumula múltiples requests.
