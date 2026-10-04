# Etapa 6d — el buscador (especificación)

Cuarta entrega de la etapa 6 de la [síntesis](05-sintesis.md): buscar calles y lugares
dentro de la ciudad con **Nominatim**, el buscador de OpenStreetMap. Toca
`visualizer/map.html` y un archivo nuevo, `visualizer/search-config.json`.

Reparto: Codex implementa `map.html` y `search-config.json`. Claude escribe esta spec, el
test Playwright `tests/visualizer/test_search.py`, los README, el CHANGELOG y la verificación.

## 1. La política de Nominatim (obligatoria)

[operations.osmfoundation.org/policies/nominatim](https://operations.osmfoundation.org/policies/nominatim/).
La política dice que el código generado con LLM tiene que cumplirla entera. Lo que nos afecta:

- **Máximo 1 consulta por segundo, sumando a todos los usuarios del sitio.** Cada navegador
  manda como mucho una por segundo. El límite global no se puede garantizar sin un proxy:
  el dueño eligió ir directo (2026-10-03) porque el tráfico es chico; si crece, el
  siguiente paso es un proxy con caché compartida.
- **Autocompletado prohibido**: se consulta solo al confirmar (Enter o el botón), nunca
  mientras se escribe.
- **Identificar la aplicación**: el navegador no deja fijar User-Agent, así que la consulta
  manda el **Referer completo** de la página (§3).
- **Cachear** y no mandar consultas idénticas repetidas (bloquean a los clientes que lo hacen).
- **Atribución** a OpenStreetMap, visible en el buscador.
- **Poder cambiar de servicio en cualquier momento**: la dirección vive en
  `search-config.json` (§2); cambiarla o apagar el buscador no requiere tocar código.

## 2. `visualizer/search-config.json`

```json
{
  "enabled": true,
  "provider": "Nominatim",
  "endpoint": "https://nominatim.openstreetmap.org/search",
  "policy": "https://operations.osmfoundation.org/policies/nominatim/"
}
```

- Se lee una vez al cargar, con `fetch("search-config.json")`. Si falla, no es JSON, o
  `enabled` no es `true`, o `endpoint` no es una URL `https:`, **el botón de buscar no
  aparece** y no hay error en la consola (solo un `console.warn`).
- Las miniaturas no cambian: el botón vive en `#title-header`, que ya se oculta.

## 3. La consulta

`GET <endpoint>?q=<consulta>&format=jsonv2&viewbox=<w>,<n>,<e>,<s>&bounded=1&limit=8&polygon_geojson=1&polygon_threshold=0.00005&accept-language=<idiomas>`

- `viewbox` sale del `bbox` de `CITY_META` (`[s, w, n, e]`). `bounded=1`: sin resultados
  fuera de la ciudad.
- `accept-language`: `navigator.languages.join(",")` (o `navigator.language`).
- `fetch(url, { referrerPolicy: "no-referrer-when-downgrade", credentials: "omit" })`: un GET
  simple, sin headers propios. Con esa política el Referer lleva la URL de la página sin el
  hash (`…/visualizer/map.html?city=<slug>`), que identifica al proyecto.
- La consulta se normaliza (espacios recortados y colapsados). Vacía o de menos de 2
  caracteres: no se consulta.
- **Ritmo:** como mucho una consulta por segundo por página. Si se confirma antes, se
  espera; si mientras tanto se confirma otra, queda solo **la última** pendiente.
- **Repetidas:** confirmar la misma consulta normalizada (misma ciudad e idioma) usa la
  **caché** en memoria (hasta 50 entradas; también guarda los resultados vacíos) y no
  sale a la red.
- **Respuestas viejas:** cada consulta lleva un número; una respuesta que no es de la última
  se descarta. Al empezar otra se aborta la anterior (`AbortController`).
- **Errores:** timeout de 10 s; 429 → "Search is busy. Try again in a moment."; cualquier
  otro error → "Search is unavailable right now." Sin reintentos automáticos.
- Durante una composición IME (`ev.isComposing`), Enter no confirma.

## 4. Interfaz

- Botón `<button type="button" id="search-open" class="hud-panel" aria-label="Search" title="Search streets and places" aria-expanded="false" aria-controls="search-panel">`
  con una lupa (SVG `stroke="currentColor"`), en `#title-header` **después de
  `#title-ctrl` y antes de `#share-view`**, fuera del `role="status"` del título.
- Panel `<div id="search-panel" class="hud-panel" hidden>`, hijo de `#title-header`,
  **debajo de la fila** (no se agranda la fila). Contenido:
  - `<form role="search">` con `<input id="search-input" type="search" role="combobox" aria-autocomplete="none" aria-expanded="false" aria-controls="search-results" enterkeyhint="search" autocomplete="off">`
    (`aria-label` y `placeholder`: "Search in <ciudad>"), fuente de 16 px (que iOS no haga zoom),
    y un botón `#search-close` (✕, `aria-label="Close search"`).
  - `<ul id="search-results" role="listbox" aria-label="Search results" hidden>`: un
    `<li role="option" id="search-opt-<i>" aria-selected>` por resultado, con el nombre
    (`name`, o la primera parte de `display_name`) y debajo el tipo y el contexto (el tipo de
    `type`, legible: `residential` → "Residential", más las dos partes siguientes de
    `display_name`), para distinguir homónimos. Todo con `textContent`.
  - `<p id="search-status" role="status" aria-live="polite">`: "Searching…", "No results in <ciudad>",
    los errores de §3.
  - Al pie, la atribución: "Search by <provider> · © OpenStreetMap contributors", con el link
    a la política (`policy` del JSON).
- Teclado (patrón combobox de WAI-ARIA): el foco queda en el input; flechas arriba/abajo
  mueven la opción activa (`aria-activedescendant`, `aria-selected`); Enter con una opción
  activa la elige, sin opción activa confirma la búsqueda; Escape cierra la lista y, con la
  lista cerrada, el buscador (devuelve el foco a `#search-open`).
- Click en una opción la elige. Click fuera del panel cierra la lista (no el buscador).
- Lugar: en escritorio, el panel mide hasta 360 px y se alinea con la cabecera. En pantallas
  chicas (`SMALL_SCREEN`) ocupa el ancho disponible de la cabecera (en 390 px quedan unos
  316 px a la derecha de los controles), con botones de 44 px y el título recortado con
  elipsis si hace falta. En 844 × 390 con la bandeja abierta hereda el corrimiento de la
  cabecera. La lista tiene scroll y una altura limitada por el espacio visible (también con
  el teclado virtual: `visualViewport`).

## 5. Elegir un resultado

- Se cierra la lista (el campo y el resultado quedan) y se retira el teclado virtual
  (`blur` del input en pantallas táctiles).
- **Encuadre**: con `boundingbox` (`[s, n, w, e]`, números validados) → `fitBounds` con
  `maxZoom: 17` y un padding que respeta el área visible (`visibleMapRect()`); sin
  `boundingbox` → centro a zoom 17.
- **Pin**: un `maplibregl.Marker` con un elemento DOM no interactivo (`pointer-events: none`,
  clase `search-pin`) en `lat`/`lon` del resultado.
- **Resaltado**: si el resultado trae `geojson` de tipo línea o polígono, se dibuja en la
  fuente **`cs2-search`** con dos capas, insertadas en `LAYER_ORDER` **justo antes de las
  del recuadro** (arriba de los datos, debajo del recuadro y de Measure):

  | id | tipo | filtro | estilo |
  |---|---|---|---|
  | `cs2-search-fill` | fill | polígonos | `#4cc9f0`, opacidad 0.15 |
  | `cs2-search-line` | line | todo | `#4cc9f0`, ancho 3, opacidad 0.95 |

  Con `addLayerOrdered` sin `categoryKey`, creadas en `mapReady`, con `visibility: none`
  sin resultado. No son inspeccionables: un click sigue seleccionando la zona de abajo.
- Pin y resaltado se van al cerrar el buscador, al editar la consulta o al buscar otra cosa.
- La cámara cambia, así que `#map=` en la URL la refleja (lo hace MapLibre) y `Share view`
  comparte el lugar. La consulta, los resultados y el pin **no** van en la URL ni se guardan.

## 6. Convivencia

- Abrir el buscador termina Measure (`finishMeasure()`: la medición válida queda) y cierra
  el panel de Share y el menú de exportación.
- Escape: el buscador lo consume **antes** que los demás (exportación, Share, Measure y el
  que limpia la selección) cuando el panel está abierto.
- La exportación PNG omite `cs2-search-*`. El pin es DOM: no llega al canvas.
- El recuadro no se mueve.

## 7. Fuera de esta etapa

- Proxy con caché compartida (si el tráfico crece).
- Autocompletar (prohibido por la política) o un índice propio.
- Guardar búsquedas recientes.

## 8. Verificación (Claude)

`tests/visualizer/test_search.py`, marcado `network` + `browser`. **Nunca consulta la API
real**: `page.route` intercepta el `endpoint` y responde con datos armados.

1. Con la configuración apagada (o sin el archivo), no hay botón.
2. Escribir no manda ninguna consulta; Enter manda una, con `format=jsonv2`, el `viewbox`
   del bbox, `bounded=1`, `limit=8`, `polygon_geojson=1` y `accept-language`, y un Referer
   que incluye `/visualizer/map.html`.
3. La misma consulta otra vez sale de la caché (cero consultas nuevas).
4. Dos consultas distintas seguidas: la segunda sale al menos 1 s después de la primera;
   tres seguidas: solo sale la última pendiente.
5. Una respuesta vieja que llega tarde no pisa la nueva.
6. 429 → el mensaje "busy"; sin resultados → "No results in <ciudad>".
7. La lista: roles ARIA, flechas, Enter, click; elegir encuadra (zoom ≤ 17), pone el pin y
   llena `cs2-search` con la línea del resultado.
8. Escape: cierra la lista, después el buscador (foco a `#search-open`), y se lleva pin y
   resaltado; con Measure activo, abrir el buscador lo termina.
9. El PNG transparente con todas las zonas ocultas sigue vacío con un resultado resaltado.
10. 390 × 844 y 844 × 390: el panel entra en la pantalla y no tapa los demás controles de la cabecera.

## Decisiones del dueño (2026-10-03)

- Nominatim, directo desde el navegador con los resguardos de §1 y §3, sabiendo que el
  límite es global; proxy más adelante si hace falta.
- Al elegir: encuadre, pin y resaltado de la geometría que devuelve Nominatim.
