# Etapa 2 — columna única (especificación)

Sale de `05-sintesis.md` ("Atlas compacto"). Conteos: el dueño eligió al azar entre las
tres opciones (2026-09-27) y salió **en la fila, en gris; ocultos en el celular**.

Todo en `visualizer/map.html` salvo las miniaturas (`src/shared/thumbnails.py` y su
test). HTML estático, sin build. Textos de UI en inglés.

## 1. Estructura

### Escritorio (fuera de `SMALL_SCREEN`, es decir más de 640 px de ancho y 500 de alto)

- `<aside id="layers-col">` acoplada a la izquierda, ancho `--col-w: 300px`, alto
  completo, fondo `--bg-panel-solid`, borde derecho `--border-soft`. No es un control de
  MapLibre: es hermana de `#map`.
- `body.col-open` → `#map` se corre `var(--col-w)` a la izquierda (el mapa se achica, no
  queda tapado). Después de abrir o cerrar: `map.resize()`.
- `#title-header` (Cities, ciudad, Star) sigue flotando arriba a la izquierda **del área
  del mapa**: `left: calc(var(--col-w) + 60px)` con la columna abierta, `60px` cerrada.
  Los controles de MapLibre (zoom, Fit city) ya viven dentro de `#map`, se mueven solos.
- Cabecera de la columna: `LAYERS` + botón `«` (`aria-label="Hide layers"`).
- Columna cerrada: aparece un botón flotante `#layers-open` (`☰ Layers`, estilo
  `.hud-panel`) como primer elemento de `#title-header`.
- Estado inicial: el guardado en `localStorage` (`cs2-layers-col-v1`); si no hay,
  **cerrada** cuando `innerWidth < 1200 || innerHeight < 800`, abierta si no.
- Cuerpo con scroll propio; pie fijo con el mapa base: `[Dark | Satellite]`.

### Celular (`SMALL_SCREEN`)

- La misma `#layers-col` pasa a ser una bandeja inferior fija, ancho completo, que tapa el
  mapa (no lo achica; sin `margin-left`).
- Plegada: solo la cabecera (~52 px): `☰ Layers` + un resumen corto de lo que está
  prendido (ej. `Zoning · Roads dimmed`) + chevron. Tocar la cabecera la despliega.
- Desplegada: `max-height: 50dvh`, cuerpo con scroll. Arranca plegada.
- No hay `#layers-open` en el celular.
- Los controles de abajo a la derecha (capas ya no existe; escala y atribución) suben lo
  que mide la cabecera de la bandeja para no quedar tapados.
- Los conteos se ocultan.

## 2. Contenido de la columna

Un bloque por módulo, en este orden y solo si la ciudad lo tiene: Zoning, Roads,
Services, Transit, Utilities (`official_zoning` es una fuente de Zoning;
`external_buildings` es parte de Zoning).

**Cabecera de módulo:** chevron (plegar el bloque) · ícono de `MODULE_META` en su color ·
nombre · total en gris · control `[On | Dim | Off]` (tres `<button>` con
`data-module-state="on|dim|off"` y `aria-pressed`, dentro de un elemento con
`data-module="<key>"`). Zoning arranca desplegado, el resto plegado.

- Ciudad con un solo módulo temático (33 de 38: solo zoning): **no hay cabecera de
  módulo ni `On/Dim/Off`**; el bloque de zonas va directo, sin chevron, con el título
  `CS2 zones`.
- Transit y Utilities, mientras cargan: cabecera con `Loading…` en vez del control. Si
  fallan: `Couldn't load — reload to retry` (reemplaza a `moduleLoadFailed` sobre pills).

**Zoning con plan oficial:** arriba del bloque, `[OSM-derived | Official plan]`
(segmentado, `title` con el nombre completo de la fuente, y el nombre en una línea chica
debajo). Al pasar a oficial, **los conteos pasan a ser los del plan** (contar por zona en
`officialZoningLoaded`); los filtros por categoría valen para las dos fuentes (ya
comparten `layerModule = "zoning"`).

**Grupos** (Residential, Commercial, Office, Industrial, Parking; en Roads: Main roads,
Local roads, Paths): fila de grupo con su nombre y un botón `Only`.

**Filas de categoría:** `<label>` con checkbox visible (mostrar/ocultar la categoría) ·
muestra de color (servicios: `serviceIconUrl`) · nombre · conteo en gris (mono, chico,
**sin** la pastilla de fondo actual) · botón `Only`. En escritorio `Only` aparece con
hover o foco en la fila; en `(hover: none)` está siempre visible. En táctil las filas
miden al menos 44 px.

- Transit y Utilities también tienen filas con checkbox: `hiddenCats` se extiende a
  `transporte` e `infraestructura` (sus features ya traen `k`).
- **Categorías vacías** (conteo 0 una vez conocidos los conteos): se mueven a un
  `<details>` al final del bloque, `N not in this city`. Los conteos de zoning con
  teselas se conocen al empezar; sin teselas y en los módulos secundarios, al cargar: una
  función re-ubica las filas cada vez que se actualizan los conteos.
- **Aviso de filtro:** si hay categorías ocultas en un módulo, arriba del bloque:
  `Showing 1 of 13 zones · Restore` (con foto previa de un `Only`) o
  `Showing 12 of 13 zones · Show all` (sin foto). Unidades: zones / road types /
  services / lines / networks.
- La leyenda de confianza (dos filas) queda al final del bloque de Zoning.

## 3. Estado

- `moduleStates[key]` ∈ `"on" | "dim" | "off"`. Se borran `fondoMode`, el select y su
  CSS. `applyModuleState`: on → visible, factor 1; dim → visible, factor `FADE`; off →
  oculto. Para los módulos que cargan tarde se mantiene el `??=` con el valor inicial de
  la tabla.
- **Primera visita** (sin estado guardado): zoning `on`, vial `dim`, services,
  transporte e infraestructura `off`.
- Guardado por ciudad en `cs2-view-state-${slug}-v2`: `{modules: {...}, basemap:
  "dark"|"sat"}`. La `v1` no se lee. Las categorías ocultas **no** se guardan (eso es de
  la etapa 4, con la URL).
- `Only(module, cats)`: si no hay foto, `snapshot[module] = new Set(hiddenCats[module])`;
  `hiddenCats[module]` = todas las del módulo menos `cats`; aplicar filtros; si el módulo
  estaba en `off`, pasa a `on`. `Restore`: vuelve a la foto y la borra. `Show all`:
  vacía `hiddenCats[module]` y la foto. Tocar checkboxes a mano no borra la foto.
- El filtro sigue siendo `setFilter` (lo que ya usan los checkboxes). Medir en
  Yogyakarta (520.689 features) cuánto tarda un `Only` hasta `idle`.

## 4. Se borra

Pills y `#header-controls` (y su CSS), `#fondo-control` y su lógica, `.master-toggle`,
`buildLayersControl` / `.cs2-layers` (el mapa base pasa al pie de la columna),
`buildLegend` / `.legend` y su CSS, `LEGEND_COLLAPSED_KEY`. Se conservan `MODULE_META`
(íconos, nombres, colores), popups, cursor de hover, pantalla de carga, `‹ Cities`,
`Fit city` y la escala.

## 5. Accesibilidad

Controles reales (`<button>`, `<input>`), foco visible, `aria-expanded` en lo que se
pliega, `aria-pressed` en `On/Dim/Off` y en el mapa base, filas de 44 px en táctil.

## 6. Miniaturas

- `_hide_chrome_js`: ocultar `#layers-col` y `#layers-open`, sacar `col-open` del `body`
  y llamar a `window.CS2_MAP.resize()` para que el mapa ocupe todo. Quitar los selectores
  que ya no existen (`#header-controls`, `.legend`, `.cs2-layers`).
- `_zoning_only_js`: clickear `[data-module-state="off"]` de todos los módulos menos
  zoning (en ciudades de un módulo no hay nada que clickear).
- Actualizar `tests/shared/test_thumbnails.py` (hoy verifica `"master-toggle"`).

## 7. CHANGELOG

En `[Unreleased]`, sección Changed: la columna única reemplaza leyenda, panel de capas,
botones de arriba y "Switched off"; `On/Dim/Off`; `Only`/`Restore`; conteos en gris;
primera visita más sobria; bandeja en el celular.

## 8. Verificación

Playwright contra `python -m http.server 8766 --directory visualizer`, en Nueva York (1
módulo), Chicago (3), Minneapolis (6 + oficial) y Yogyakarta (rendimiento), a 1440×900,
1280×720, 1024×768, 390×844 y 844×390:

- sin errores de consola ni texto en español;
- columna abierta o cerrada según tamaño, y al plegar el canvas ocupa el ancho libre;
- `On/Dim/Off` cambia visibilidad y opacidad de las capas;
- `Only` filtra y `Restore` vuelve; el aviso cuenta bien;
- el cambio a plan oficial cambia los conteos;
- al recargar se conservan módulos y mapa base, no las categorías ocultas;
- filas vacías agrupadas;
- miniaturas de Minneapolis y Nueva York limpias;
- `uv run pytest ../tests/ -m "not network"` pasa y `git status` solo muestra lo previsto.
