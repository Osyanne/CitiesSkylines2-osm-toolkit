# Etapa 6a — el recuadro del mapa jugable de CS2 (especificación)

Primera entrega de la etapa 6 de la [síntesis](05-sintesis.md) ("Extras CS2"): un recuadro
del tamaño del área jugable de Cities: Skylines 2 que el jugador mueve sobre la ciudad
para decidir qué parte entra en el juego (tarea T7 del
[anexo](anexo-claude-auditoria.md)). Solo toca `visualizer/map.html`.

Reparto: Codex implementa `map.html`. Claude escribe esta spec, el test Playwright
`tests/visualizer/test_playable_frame.py`, los ajustes a `tests/visualizer/test_url_state.py`
que pida el parámetro nuevo, el CHANGELOG y la verificación.

## 1. Datos de CS2

| Dato | Valor |
|---|---|
| Lado del área jugable | **14.336 m** |
| Tiles | **23 × 23 = 529** |
| Lado de un tile | 14.336 / 23 = **623,304… m** (no redondear) |

El mod [Image Overlay](https://github.com/algernon-A/ImageOverlay) escala su imagen
justo a ese cuadrado, centrado: la exportación de la etapa 6b va a salir de este recuadro.

## 2. Geometría

- El recuadro es un cuadrado de 14.336 m **en el terreno**, alineado al norte, alrededor
  de un centro `(lat0, lng0)`. Medio lado: 7.168 m.
- Conversión con metros por grado del elipsoide WGS84 en la latitud del centro φ:
  - `mLat = 111132.954 − 559.822·cos 2φ + 1.175·cos 4φ`
  - `mLng = 111412.84·cos φ − 93.5·cos 3φ + 0.118·cos 5φ`
  - bordes: `lat0 ± 7168 / mLat`, `lng0 ± 7168 / mLng`.

  Es una aproximación local: el error en el borde llega a ~0,2 % (unos 14 m a 60° de
  latitud). Alcanza para esta etapa; se documenta con un comentario en el código.
- Grilla: **22 líneas verticales y 22 horizontales interiores** (44 en total), cada una
  de borde a borde, separadas un tile. Más el **contorno** (una LineString cerrada de 5
  puntos). Nada de 529 polígonos.
- **Máscara**: un polígono que cubre el mundo (`±180`, `±85.051129`) con el recuadro
  como agujero, para oscurecer lo que queda afuera.
- Centro válido: se fuerza (clamp) a que el recuadro entero quede dentro de
  `lat ±85.051129` y `lng ±180`. No hay casos de antimeridiano entre las ciudades: el
  clamp alcanza.

## 3. Fuente y capas

- Una sola fuente GeoJSON, **`cs2-frame`**, con una `FeatureCollection` cuyas features
  llevan la propiedad `part`: `"mask"`, `"grid"` u `"outline"`.
- Cuatro capas, que se agregan **al final de `LAYER_ORDER`**, en este orden (abajo → arriba):

  | id | tipo | filtro | estilo |
  |---|---|---|---|
  | `cs2-frame-mask` | fill | `part == mask` | `#000000`, opacidad 0.35 |
  | `cs2-frame-grid` | line | `part == grid` | `#ffffff`, ancho 1, opacidad 0.35 |
  | `cs2-frame-casing` | line | `part == outline` | `#000000`, ancho 4, opacidad 0.5 |
  | `cs2-frame-outline` | line | `part == outline` | `#ffffff`, ancho 2, opacidad 0.95 |

- Se agregan con `addLayerOrdered` **sin** `categoryKey`: no pertenecen a ningún módulo,
  no las tocan On/Dim/Off, Only/Restore ni los filtros de categorías. Así quedan arriba
  también de las capas que cargan tarde (transporte, infraestructura, plan oficial).
- Se crean al estar listo el estilo (`mapReady`, `style.load`), sin esperar a Esri. Con
  el recuadro apagado tienen `visibility: none`.
- **No son inspeccionables**: no entran en `LINE_LAYERS` ni `AREA_LAYERS`, así que el
  hover y el click siguen viendo solo los datos de abajo.
- Al mover el recuadro se actualiza la fuente con `setData`, como mucho una vez por frame
  (`requestAnimationFrame`).

## 4. Controles

### Botón `Playable area`

- Un segundo botón en el grupo de `Fit city` (arriba a la izquierda):
  `<button type="button" class="cs2-frame" aria-label="Playable area" aria-pressed="false" title="CS2 playable area (14.3 km, 23 × 23 tiles)">`.
- Ícono: un cuadrado con una grilla de 3 × 3 (SVG con `stroke="currentColor"`, como el de `Fit city`).
- Prende y apaga el recuadro. Prendido: `aria-pressed="true"` y color de acento.

### Panel `#frame-panel`

- Un `div#frame-panel.hud-panel` con `hidden` mientras el recuadro está apagado.
- Contenido: `<span class="frame-label">Playable area · 14.3 km · 23 × 23 tiles</span>`
  y `<button type="button" id="frame-center">Center here</button>`.
- Lugar: abajo al centro del área visible del mapa. No tapa la escala ni la atribución
  (abajo a la derecha). En el celular vertical va arriba de la cabecera de la bandeja;
  en el apaisado (bandeja como cajón a la izquierda) va en la parte visible. Botón de
  44 px de alto en pantallas táctiles y con foco visible.

### `Center here`

Lleva el centro del recuadro al **centro visible** (§6). Es una acción de la persona: guarda y
reescribe la URL (§7).

### Asa para arrastrar

- Un `maplibregl.Marker` con `draggable: true` en el centro del recuadro. Su elemento es
  `<button type="button" class="frame-handle" aria-label="Move playable area" title="Drag to move the playable area">`,
  un círculo de 28 px con un ícono de mover en cuatro direcciones, `cursor: grab`
  (`grabbing` mientras se arrastra).
- **Solo con puntero fino**: se muestra cuando `hoverMedia`
  (`(hover: hover) and (pointer: fine)`) coincide y se saca cuando deja de coincidir. En
  el celular el recuadro se mueve con `Center here`.
- Arrastre:
  - `dragstart`: `dragging = true` y `clearHover()`.
  - `drag`: se recalcula el recuadro desde `marker.getLngLat()` (rAF).
  - `dragend`: `dragging = false`, se guarda y se reescribe la URL.
  - El arrastre no mueve el mapa ni selecciona nada: el click que pueda llegar al soltar
    no debe abrir la ficha.
- Teclado: con el asa enfocada, las flechas mueven el recuadro un tile (623,3 m) en esa
  dirección. Cada tecla es una acción de la persona: guarda y reescribe la URL.

## 5. Dónde aparece

Al prender el recuadro:

1. Si hay una posición recordada (en memoria o guardada), va ahí.
2. Si no: si el **centro visible** cae dentro del bbox de la ciudad, va ahí; si no, va al
   centro de la ciudad (`center` de su entrada en `cities.json`; si falta, el centro del bbox).
3. Si después de ubicarlo su centro queda fuera del área visible,
   `map.fitBounds(bordes del recuadro, { padding: fitPadding() })`. Si no, la cámara no se mueve.

Apagarlo no olvida la posición: al volver a prenderlo aparece donde estaba.

## 6. Centro visible

Es el centro del rectángulo del canvas del mapa menos lo que tape `#layers-col`
cuando se superpone al mapa:

- En el celular vertical la bandeja tapa una franja de abajo (plegada o abierta): se
  descuenta esa altura.
- En el apaisado el cajón tapa una franja de la izquierda: se descuenta ese ancho.
- En escritorio la columna está acoplada y el mapa ya se achica: es `map.getCenter()`.

Se calcula con los `getBoundingClientRect()` del canvas y de `#layers-col`, y
`map.unproject()` del punto medio. Va en una función `visibleCenter()`.

## 7. Estado: URL y guardado

Sigue la [etapa 4](08-etapa-4-spec.md).

| Dónde | Forma |
|---|---|
| Memoria | `{ on: boolean, lat: number \| null, lng: number \| null }` |
| URL | `frame=off` o `frame=<lat>,<lng>`, con `toFixed(5)` |
| Guardado | `saveViewState({ frame: { on, lat, lng } })` en `cs2-view-state-<slug>-v2` |

- **La URL lleva siempre `frame`**, como `base`, para que un link con el recuadro apagado
  no lo muestre prendido en un navegador que lo tenía guardado. Va **último**, después de
  los `hide.*`: `map`, `base`, `src`, `layers`, `hide.*`, `frame`.
- Al importar (carga y `hashchange`), campo por campo como en la etapa 4:
  1. `frame` válido en la URL (`off`, o dos números finitos separados por coma con
     `|lat| ≤ 85.051129` y `|lng| ≤ 180`) → manda.
  2. Si falta o es inválido → lo guardado: `on` y coordenadas finitas → prendido ahí;
     si no, apagado.
  3. Si no hay nada → apagado (primera visita).

  Con `frame=off` en la URL, la posición recordada sale de lo guardado, si hay.
  Importar **nunca guarda**. Después de importar se reescribe la URL normalizada (un
  `frame` inválido se reemplaza por el valor aplicado).
- Se guarda solo por acciones de la persona: el botón, `Center here`, el fin del
  arrastre y las flechas del asa. Durante el arrastre no se escribe nada.
- `Share view` comparte el recuadro, porque usa `writeViewHash()`.

## 8. Miniaturas

No cambian. `src/shared/thumbnails.py` abre un contexto nuevo, sin hash ni nada guardado:
el recuadro arranca apagado y el panel con `hidden`. El botón vive en
`.maplibregl-ctrl-top-left`, que la miniatura ya oculta.

## 9. Fuera de esta etapa

- Exportar el recuadro como PNG para Image Overlay (etapa **6b**: atribución, CORS de
  Esri, 4096 × 4096 px).
- Rotación del recuadro.
- El límite de 441 tiles del juego sin mods (cuáles se compran lo decide el jugador:
  no es un cuadrado fijo).
- El contorno del mapa completo de 57.344 m.

## 10. Verificación (Claude)

`tests/visualizer/test_playable_frame.py`, marcado `network` + `browser` como
`test_url_state.py` (a mano, fuera del CI):

1. Primera visita: recuadro apagado, `aria-pressed="false"`, panel oculto, capas con
   `visibility: none` y `frame=off` al final del hash.
2. Prender: aparece en el centro visible (dentro del bbox), la URL lleva
   `frame=<lat>,<lng>` y se guarda `frame.on = true`.
3. Geometría: el contorno mide 14.336 m de lado (±0,5 %, con haversine) y hay 44 líneas
   interiores equiespaciadas.
4. `Center here` después de mover el mapa lleva el recuadro al centro visible.
5. Arrastrar el asa mueve el recuadro, no mueve el mapa, no abre la ficha y guarda al soltar.
6. Las flechas sobre el asa lo mueven un tile.
7. Precedencia: `frame=off` le gana a lo guardado prendido y no guarda; coordenadas en la
   URL le ganan a lo guardado; un valor inválido cae a lo guardado y se normaliza.
8. `hashchange` reimporta el recuadro sin guardar.
9. En Minneapolis, después de que cargan transporte e infraestructura, las cuatro capas
   del recuadro siguen siendo las últimas del estilo.
10. Un click sobre el contorno selecciona la zona de abajo.
11. Celular (375 × 812, táctil): sin asa, y `Center here` usa el centro arriba de la bandeja.
12. `test_url_state.py`: las expectativas del hash suman `frame=off`.

## Decisiones del dueño (2026-10-03)

- La exportación PNG va en una etapa 6b aparte.
- El recuadro se mueve con un asa central (escritorio) y `Center here` (en todos lados).
- Sin rotación.
