# Etapa 4 — continuidad: la vista en la URL y `Share view` (especificación)

Sale de `05-sintesis.md` (etapa 4): "Cámara, fuente, filtros y mapa base en la URL, más
`Share view`. Precedencia: URL → estado guardado → valores iniciales." Borrador de Claude
criticado por Codex el 2026-09-27; esta versión incorpora sus correcciones. El dueño dio
el ok el 2026-09-29.

Reparto por rol: **Codex implementa todo en `visualizer/map.html`**. Claude escribe esta
spec, el test Playwright (`tests/visualizer/test_url_state.py`), CHANGELOG y READMEs,
verifica y revisa el diff. Este documento es el contrato entre los dos: ids, parámetros y
comportamiento no cambian sin avisar.

## 1. Formato de la URL

La ciudad sigue en la query. La vista va en el hash, con el estilo de OSM:

```text
map.html?city=minneapolis#map=14.2/44.97780/-93.26500&base=sat&src=official&layers=zoning.on,vial.dim,services.off,transporte.off,infraestructura.off&hide.zoning=res_low_house,com_low&hide.vial=pedestrian,bike
```

| Parámetro | Valores | Se escribe |
|---|---|---|
| `map` | `zoom/lat/lng` (lo arma MapLibre) | siempre |
| `base` | `dark` · `sat` | siempre |
| `src` | `osm` · `official` | solo si la ciudad tiene `official_zoning` |
| `layers` | `<módulo>.<on\|dim\|off>` separados por coma, en el orden de la columna | solo si la ciudad tiene más de un módulo |
| `hide.<módulo>` | claves de categoría separadas por coma, en el orden de la columna | solo si ese módulo tiene categorías ocultas |

- Módulos y categorías usan las claves internas (`zoning`, `vial`, `services`,
  `transporte`, `infraestructura`; `res_low_house`, `pedestrian`, `bus`…). Sin alias.
- El hash se arma a mano, no con `URLSearchParams.toString()` (codifica las comas). Las
  claves son `[a-z_]`: no hace falta codificar nada.
- Orden al escribir: `map`, `base`, `src`, `layers`, `hide.*` en el orden de la columna.
  Los parámetros desconocidos se descartan al reescribir.

## 2. Cámara

- `new maplibregl.Map({ hash: "map", maxPitch: 0, … })`. Verificado en el código de
  MapLibre 5.24 (`src/ui/hash.ts`): el hash con nombre conserva los demás parámetros,
  escribe con `history.replaceState` en cada `moveend` (throttle de 300 ms), y si al crear
  el mapa trae una posición válida le gana a `bounds` y a `fitBoundsOptions`. Sin hash (o
  con uno inválido: zoom fuera de `minZoom`–`maxZoom`, latitud imposible, no numérico) se
  encuadra la ciudad como hoy.
- `maxPitch: 0`: un hash con pitch no puede inclinar el mapa. El bearing del hash ya se
  ignora porque la rotación está desactivada.
- La cámara es centro y zoom: en otra pantalla se ve más o menos alrededor del mismo
  punto. No se recalcula nada al abrir o cerrar la columna (alcanza con el `resize()` que
  ya existe).

## 3. Precedencia y guardado

- **Por campo:** URL → `cs2-view-state-<slug>-v2` → primera visita. La cámara no se
  guarda (sin hash → Fit city). Las categorías ocultas tampoco (sin `hide.*` → todo
  visible).
- El guardado local suma `source` (`"osm" | "official"`) a `modules` y `basemap`. Sigue
  siendo la `v2`: los objetos viejos simplemente no traen `source`.
- **Solo se guarda lo que la persona toca, y solo ese campo.** `saveViewState` pasa a
  mezclar un parche sobre lo guardado (leer, modificar el campo, escribir) en vez de
  volcar todo `moduleStates`. Así, abrir un link con `vial.off` y después prender
  Services guarda `services`, no el `vial` del link.
  - Guardan: `On/Dim/Off` (ese módulo), el mapa base, la fuente, y `Only` cuando prende
    un módulo que estaba en Off o cargando (ese módulo).
  - **No** guardan: importar la URL al cargar, `hashchange`, los valores por defecto, los
    retrocesos automáticos (plan oficial que falla, módulo que falla) ni
    `secondaryModuleReady`.

## 4. Importar el estado (al cargar y en `hashchange`)

- Se parsea el hash y cada campo se resuelve por la precedencia del §3.
- Validación por parámetro, sin cortar la carga ni tirar errores de consola:
  - `layers`: cada entrada por separado; se descartan módulos que la ciudad no tiene,
    estados desconocidos y duplicados (gana la última). Un módulo que no aparece cae al
    guardado y después a la primera visita. En una ciudad de un solo módulo se ignora
    (el módulo queda `on`).
  - `hide.<módulo>`: se valida contra el **catálogo** de categorías del módulo
    (`categoryList`), no contra los conteos: una zona vacía en OSM puede existir en el
    plan oficial. Claves desconocidas y duplicadas se descartan; vacío = nada oculto;
    `hide.` de un módulo que la ciudad no tiene se ignora. Ocultar todas es válido.
  - `src=official` en una ciudad sin plan → `osm`. `base` desconocido → cae al guardado.
- Al importar se reconstruye todo junto: `hiddenCats` de cada módulo, se borran las
  fotos de `Only` (`snapshots`), se aplican módulos, fuente y mapa base, se
  sincronizan la columna, los conteos y el aviso de filtro, y al final
  `syncInspection()`. Un link filtrado muestra `Show all` (no hay foto); un `Only`
  posterior toma como foto el filtro importado, y `Restore` vuelve a él.
- Después de importar se reescribe el hash canónico con `replaceState` (no dispara
  `hashchange`), sin guardar nada.
- `hashchange` (pegar otro link de la misma ciudad en la pestaña, o borrar el hash):
  MapLibre mueve la cámara si el `map=` es válido y si no la deja donde está; nosotros
  reimportamos el resto con la misma regla. Borrar el hash entero deja la cámara, vuelve
  a lo guardado y muestra todas las categorías.

## 5. Escribir el estado

- Cada cambio de estado (de la persona o automático) reescribe el hash completo con
  `replaceState`, conservando el `map=` que haya (MapLibre hace lo mismo con los
  nuestros al moverse). No se agregan entradas al historial.
- La URL muestra el **estado pedido**, no solo el aplicado:
  - Módulos que cargan tarde (transporte, infraestructura): `moduleStates` ya guarda lo
    pedido mientras cargan; se escribe eso. Un `hide.transporte` importado se aplica
    cuando el módulo llega (hoy sus capas no están en `layerModule` hasta que se
    agregan: hay que dejar el filtro pendiente para cuando aparezcan).
  - Plan oficial: separar `requestedZoningSource` de `currentZoningSource`. Con
    `src=official` (o guardado) se ve OSM hasta que el plan carga y entonces se cambia,
    salvo que la persona haya elegido OSM mientras tanto: gana la última acción. La URL
    escribe lo pedido.
  - Si el plan oficial falla: lo pedido pasa a `osm`, la URL escribe `src=osm` y se
    conserva `hide.zoning`. No se toca lo guardado.
  - Si un módulo falla: la URL escribe `<módulo>.off` (así quien reciba el link no hereda
    su estado guardado) y se borra su `hide.`. No se toca lo guardado.
- No van a la URL: columna abierta o cerrada, bloques plegados, la selección, la
  bandeja del celular ni la foto de `Restore`.

## 6. `Share view`

- Botón `<button id="share-view">` en `#title-header`, entre `#title-ctrl` y `#star-link`,
  con el mismo estilo `.hud-panel`. Ícono de compartir + texto `Share`;
  `aria-label="Share this view"`, `title="Share this view"`. En `SMALL_SCREEN` solo el
  ícono, con al menos 44 px de toque.
- El link se arma desde el estado actual con la API pública (`map.getCenter()`,
  `map.getZoom()`, con el mismo redondeo que MapLibre), no leyendo `location.href`, que
  puede estar hasta 300 ms atrasado. Al compartir también se reescribe el hash.
- Táctil (`(hover: none) and (pointer: coarse)`) con `navigator.share`: hoja nativa con
  `{ title: "<display_name> — CS2 zoning map", url }`. Si la persona la cancela
  (`AbortError`) no pasa nada más. Otro error → se sigue como en escritorio.
- Si no: `navigator.clipboard.writeText(url)` y aviso `Link copied` en
  `<div id="share-status" role="status" aria-live="polite">` durante ~2 s.
- Si el portapapeles no está o falla: panel `<div id="share-panel" role="dialog"
  aria-label="Share link">` junto al botón, con un `<input readonly>` que trae el link
  ya seleccionado y un botón de cierre (`aria-label="Close"`). Se cierra con ✕, `Esc` o
  un click afuera, y el foco vuelve a `#share-view`. **Ese `Esc` se consume**: no borra
  la selección ni el hover (el `keydown` de la selección no debe verlo).
- Sin interacción, `#share-status` y `#share-panel` están `hidden`.

## 7. Miniaturas

`_hide_chrome_js` ya oculta todo `#title-header`, y `thumbnails.py` abre
`map.html?city=<slug>` sin hash. No debería hacer falta tocarlo: se verifica.

## 8. Rendimiento

Escribir el hash es barato; importar un link filtrado es un solo `setFilter` por capa
(el mismo camino que un `Only`). Nada de reimportar en cada `moveend`.

## 9. Verificación (Claude)

`tests/visualizer/test_url_state.py`, marcado `network` y `browser` (MapLibre viene de
unpkg), fuera del CI por decisión del dueño. Se corre a mano:

```bash
cd src && uv run --group thumbnails pytest ../tests/visualizer -m browser
```

Levanta `http.server` sobre `visualizer/` (solo lectura) y cubre, en Minneapolis (6
módulos + plan oficial) y Nueva York (1 módulo): ida y vuelta por la URL al recargar;
precedencia URL → guardado sin escribir `localStorage` al importar; valores inválidos;
`hashchange`; `Only`/`Restore` sobre un filtro importado; transporte y plan oficial
demorados y caídos (con `page.route`); `Share view` con portapapeles, sin portapapeles y
con la hoja nativa (simulada); `maxPitch`. Además, a mano: 1440×900, 1280×720, 390×844 y
844×390 con la bandeja abierta, miniaturas de Minneapolis y Nueva York, y sin errores de
consola.
