# Etapa 6c — medir en celdas de 8 m (especificación)

Tercera entrega de la etapa 6 de la [síntesis](05-sintesis.md): traducir distancias reales
a las celdas de zonificación de CS2 (8 × 8 m). Dos piezas: una **escala doble** (metros y
celdas) y una herramienta **Measure**. Solo toca `visualizer/map.html`.

Reparto: Codex implementa `map.html`. Claude escribe esta spec, el test Playwright
`tests/visualizer/test_measure.py`, el ajuste del orden de capas en
`tests/visualizer/test_playable_frame.py`, los README, el CHANGELOG y la verificación.

## 1. Escala doble

- Reemplaza la `maplibregl.ScaleControl` actual (abajo a la derecha, arriba de la
  atribución) por un control propio con el mismo lugar.
- Elemento: `<div class="maplibregl-ctrl maplibregl-ctrl-scale cs2-scale" role="img" aria-label="Scale: 200 m, 25 cells">`
  con dos hijos: `<div class="scale-bar">` (la barra, con su ancho en px) y
  `<span class="scale-label">200 m · 25 cells</span>`. Conserva la clase
  `maplibregl-ctrl-scale`: así siguen valiendo el CSS actual y el ocultado de las
  miniaturas (`src/shared/thumbnails.py` no cambia).
- Cálculo, en `move` y `resize`: la distancia de 110 px horizontales a la altura del centro
  vertical del canvas (`unproject` de los dos extremos y `LngLat.distanceTo`). Se elige el
  número redondo más grande que entra (1, 2, 3 o 5 × 10ⁿ metros) y la barra mide
  `110 × redondo / distancia` px. La barra y el rótulo van separados: el texto no deforma la barra.
- Rótulo: metros `< 1000` → `"200 m"`; si no → `"2 km"`. Celdas = metros / 8, con
  `formatCells()` (§3). Ejemplos: `10 m · 1.3 cells`, `200 m · 25 cells`,
  `500 m · 62.5 cells`, `2 km · 250 cells`.

## 2. Measure

### 2.1 Controles

- Un tercer botón en el grupo de `Fit city` y `Playable area`:
  `<button type="button" class="cs2-measure" aria-label="Measure" aria-pressed="false" title="Measure distance in metres and 8 m cells">`,
  con un ícono de regla (SVG `stroke="currentColor"`).
- Un panel `<div id="measure-panel" class="hud-panel" hidden>` con
  `<span id="measure-total">`, `<button type="button" id="measure-done">Done</button>` y
  `<button type="button" id="measure-clear">Clear</button>`. Botones de 44 px de alto en
  pantallas táctiles, con foco visible.
- Ubicación: como `#frame-panel` (abajo al centro del área visible, esquivando la bandeja,
  la ficha flotante, la escala y la atribución). Si los dos paneles están a la vista,
  `#measure-panel` va **encima** de `#frame-panel`, sin superponerse.

### 2.2 Estados

| Estado | Botón `Measure` | Panel | Clicks en el mapa |
|---|---|---|---|
| Apagado, sin medición | `aria-pressed="false"` | oculto | seleccionan, como siempre |
| **Midiendo** | `aria-pressed="true"` | visible, con `Done` | agregan un punto |
| Terminado, con medición | `aria-pressed="false"` | visible, sin `Done` | seleccionan, como siempre |

- Apretar `Measure` empieza una medición **nueva** (si había una terminada, se borra).
- `Done`, Escape (si el menú de exportación no está abierto) o un doble click terminan:
  la medición **queda** en el mapa hasta `Clear`.
- `Clear` borra todo, oculta el panel y sale del modo medición si estaba activo.
- Apretar `Measure` mientras se mide termina, igual que `Done`.
- No va en la URL ni se guarda.

### 2.3 Mientras se mide

- Cursor `crosshair` sobre el mapa.
- Cada `click` del mapa agrega un punto. MapLibre no emite `click` después de un arrastre o
  un pinch, así que mover el mapa no agrega puntos. Hay que verificarlo en el test.
- El click **no** selecciona ni abre la ficha, y no hay hover (el handler de click y el de
  `mousemove` vuelven antes). Al salir del modo se restauran.
- `map.doubleClickZoom` se desactiva al entrar y se restaura al salir. El doble click
  termina la medición **sin duplicar** el último punto (los dos `click` previos del doble
  click ya agregaron ese punto una sola vez: el segundo no agrega si cae a menos de 3 px
  del anterior).
- El asa del recuadro (6a) se oculta mientras se mide y vuelve al terminar. El recuadro y
  su panel siguen visibles.
- Con puntero fino, un tramo de vista previa (línea punteada del último punto al cursor)
  con su rótulo. En táctil no hay vista previa.
- Máximo 100 puntos. Al llegar, la medición termina sola.

### 2.4 Dibujo

- Fuente GeoJSON **`cs2-measure`** con la línea (`LineString`) y los puntos (`Point`, con `part`).
- Capas, al **final de `LAYER_ORDER`**, después de las del recuadro:

  | id | tipo | estilo |
  |---|---|---|
  | `cs2-measure-line` | line | `#ffd166`, ancho 2.5, opacidad 1 |
  | `cs2-measure-points` | circle | radio 4, `#ffd166`, borde `#0a0e1a` de 1.5 |

  Se crean con `addLayerOrdered` sin `categoryKey`, en `mapReady`, con `visibility: none`
  hasta que hay una medición. No son inspeccionables.
- Rótulos: un `maplibregl.Marker` por tramo, en el punto medio, con un
  `<div class="measure-label">120 m · 15 cells</div>` con `pointer-events: none`. Si el
  tramo mide menos de 40 px en pantalla, su rótulo se oculta (vuelve al hacer zoom). El
  rótulo de la vista previa es otro `Marker` igual.
- `#measure-total`: `"Total: 1.24 km · 155 cells"`. Con un solo punto: `"Click to add points"`
  (`"Tap to add points"` en táctil).

## 3. Formato

- Distancia: `LngLat.distanceTo` (esfera de 6.371.008,8 m), sumada **antes** de redondear.
- `formatMeters(m)`: `< 1000` → entero + `" m"` (`"120 m"`); si no → dos decimales + `" km"` (`"1.24 km"`).
- `formatCells(m)`: `c = m / 8`. Si `c < 100`, un decimal sin `.0` final (`"12.5"`,
  `"15"`); si no, entero. Separador de miles con coma (`"1,550"`). Siempre `" cells"`
  (también para 1: es una medida, no un conteo).

## 4. Convivencia

- **Exportación PNG (6b):** las capas `cs2-measure-*` se suman a las que la exportación
  omite. Los rótulos son DOM: no llegan al canvas.
- **Escape:** el menú de exportación lo consume primero (ya lo hace en captura). Si no,
  y se está midiendo, Escape termina la medición. El handler actual (limpiar hover y
  selección) sigue igual.
- **Recuadro:** su arrastre no puede empezar mientras se mide (el asa está oculta).
- **Miniaturas:** no cambian. El botón vive en `.maplibregl-ctrl-top-left` y la escala
  conserva `maplibregl-ctrl-scale`; las dos clases ya se ocultan. El panel arranca oculto.

## 5. Fuera de esta etapa

- Una grilla de celdas dibujada en el mapa: en el juego las celdas se alinean a cada calle,
  y una grilla global daría una precisión falsa.
- El tamaño de lo seleccionado en celdas, en la ficha: necesita calcular el área al generar
  las teselas (tarea de datos aparte; ver la opción (b) en la decisión de abajo).
- Medir áreas, guardar o compartir mediciones.

## 6. Verificación (Claude)

`tests/visualizer/test_measure.py`, marcado `network` + `browser` (a mano, fuera del CI):

1. Escala: el rótulo sigue el formato, las celdas son metros / 8, la barra mide ≤ 110 px,
   cambia con el zoom y conserva la clase `maplibregl-ctrl-scale`.
2. Dos clicks en píxeles conocidos: el total coincide (±0,5 %) con la distancia entre los
   dos puntos (`unproject`), en metros y en celdas.
3. Tres puntos: el total es la suma de los tramos y hay dos rótulos.
4. El doble click termina sin duplicar el último punto y no hace zoom.
5. Un arrastre mientras se mide no agrega puntos.
6. Mientras se mide, un click sobre una zona no abre la ficha; después de `Done`, sí.
7. `Done` y Escape dejan la medición; `Clear` la borra y oculta el panel.
8. `Measure` otra vez empieza una medición nueva.
9. El asa del recuadro se oculta mientras se mide y vuelve después.
10. La exportación transparente con todas las zonas ocultas sigue vacía aunque haya una
    medición (las capas de medición no van en el PNG).
11. Celular (390 × 844, táctil): los taps agregan puntos, no hay vista previa y el panel
    entra en la pantalla sin tapar la bandeja.
12. `test_playable_frame.py`: el contrato del orden pasa a ser "las cuatro capas del recuadro
    justo antes de las dos de medición, que son las últimas".

## Decisiones del dueño (2026-10-03)

- En esta entrega: escala doble y Measure. Sin grilla de celdas en el mapa.
- La medición queda en el mapa hasta `Clear`. No va en la URL ni se guarda.
- El tamaño en celdas en la ficha va más adelante, como tarea de datos aparte: calcular el
  área al generar las teselas y guardarla, y mostrarla solo donde exista.
- (Recomendación de Codex, aplicada:) las mediciones no salen en el PNG.

## Decisiones durante la implementación (2026-10-03)

- Terminar (`Done`, Escape, doble click) con **menos de dos puntos** descarta la medición:
  un punto solo no mide nada, y quedaba en el mapa con "Click to add points" sin que los
  clicks agregaran puntos.
- Escape con el **panel de Share** abierto cierra solo ese panel; la medición sigue. Un
  segundo Escape la termina.
- La vista previa guarda el **punto de pantalla** del último `mousemove`, no el geográfico:
  si la cámara se mueve con el teclado, el extremo sigue bajo el cursor.
- La vista previa se dibuja como un SVG en el DOM (`.measure-preview`), no como una capa
  del mapa; las dos capas de §2.4 quedan como están.
- Codex se quedó sin cuota durante la revisión: los tres ajustes de arriba los hizo Claude
  en el carril de Codex.
