# Etapa 6b — exportar el recuadro como PNG para Image Overlay (especificación)

Sigue a la [6a](09-etapa-6a-spec.md): el contenido del recuadro del mapa jugable se baja
como una imagen cuadrada que el mod [Image Overlay](https://github.com/algernon-A/ImageOverlay)
pone sola sobre el área jugable de CS2. Es lo que se le prometió a @lolo-0-5 en el #75.
Solo toca `visualizer/map.html`.

Reparto: Codex implementa `map.html`. Claude escribe esta spec, el test Playwright
`tests/visualizer/test_frame_export.py`, el README (en inglés y en español), el CHANGELOG
y la verificación.

## 1. Lo que espera el mod

- PNG en `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\Overlays`.
- Hasta 16.384 px por lado. Una imagen no cuadrada se estira a cuadrada.
- Se escala sola al área jugable (14.336 m) y se centra. Respeta el canal alfa y tiene
  su propio control de transparencia, rotación y desplazamiento.

Por eso la imagen tiene que ser **cuadrada y cubrir exactamente el recuadro**: ni un
borde de más ni de menos.

## 2. Interfaz

- En `#frame-panel`, junto a `Center here`: `<button type="button" id="frame-export" aria-haspopup="dialog" aria-expanded="false" aria-controls="export-menu">Export PNG</button>`.
- Abre `<div id="export-menu" role="dialog" aria-label="Export overlay image">`, pegado
  arriba del panel y dentro de la ventana (también en el celular). Contenido, en este orden:
  1. **Size**: radios `name="export-size"` con valores `2048`, `4096` (marcado) y `8192`.
     Rótulos "2048 px", "4096 px", "8192 px (large)". El de 8192 **solo existe** si el
     equipo lo soporta (§4.3); si no, no se dibuja.
  2. **Background**: radios `name="export-bg"`: `map` ("As on screen", marcado) y
     `transparent` ("Transparent").
  3. Casilla `#export-grid` "Tile grid", **apagada**.
  4. `<button type="button" id="export-go">Export</button>`.
  5. `<p id="export-status" role="status" aria-live="polite">` para el progreso y los errores.
  6. `<a id="export-link" hidden>`: aparece cuando la imagen está lista (§6).
- Las opciones viven solo en memoria mientras dura la página (no se guardan).
- Escape o un click afuera cierran el menú y devuelven el foco a `#frame-export`.
  `aria-expanded` acompaña. Mientras se exporta, el menú no se cierra solo.
- Controles de 44 px de alto en pantallas táctiles, con foco visible. `placeFramePanel()`
  también acomoda el menú: no se superpone con la bandeja, la ficha flotante ni la atribución.
- Apagar el recuadro cierra el menú. Si había una exportación en curso, la cancela (§7).

## 3. La foto del estado

Al apretar `Export` se toma, de una vez: los bordes del recuadro (`frameBounds()`), su
centro, las opciones y una copia del estilo. Desde ahí, nada de lo que pase en el mapa
principal cambia la imagen.

- **No se exporta mientras algo pedido sigue cargando**: un módulo en On/Dim cuyos datos no
  llegaron, o el plan oficial pedido y todavía no aplicado. El botón queda deshabilitado y
  `#export-status` dice "Waiting for layers to finish loading…". Tampoco durante un arrastre
  del asa.
- Estilo de exportación, a partir de `map.getStyle()`:
  - Los filtros de categorías salen del estado **pedido** (`categoryFilter()`), no del
    aplicado: puede haber filtros pendientes en `staleFilters`. No se fuerza nada en el mapa principal.
  - Se quitan las capas con `visibility: none`, `zoning-hover`, `official-hover` (la
    selección usa `feature-state`, que no viaja), `cs2-frame-mask`, `cs2-frame-casing` y
    `cs2-frame-outline`.
  - `cs2-frame-grid` queda solo si `#export-grid` está marcada, con la fuente `cs2-frame`
    regenerada desde el centro de la foto (no se copia un `setData` pendiente) y visible.
  - Con fondo `transparent` se quitan `background`, `base-dark`, `base-dark-ref` y `base-sat`.
  - Se quitan las fuentes que ya no usa ninguna capa.
  - En las capas raster, `raster-fade-duration: 0`.
- Las imágenes de servicios (`svc-*`) no viajan en el estilo: se vuelven a agregar en el
  mapa de exportación con `serviceIconImage()` y su `pixelRatio`.
- El protocolo `cs2tiles://` ya está registrado de forma global: sirve también al segundo mapa.

## 4. Render

### 4.1 Encuadre exacto

En Mercator el recuadro no es exactamente cuadrado: el alto difiere del ancho hasta un
0,67 % (en el ecuador; 0,34 % a 45°). Entonces:

1. Se proyectan los bordes a Mercator: `dx = (east − west) / 360` y `dy = mercY(south) − mercY(north)`,
   con `mercY(φ) = (1 − ln(tan φ + sec φ) / π) / 2`.
2. El lado mayor mide **N px** y el otro, `round(N × menor / mayor)`: `W × H`.
3. Cámara: `zoom = log2(W / (512 × dx))`, centro en el **punto medio proyectado**
   (`lng = (west + east) / 2`, `lat = invMercY((mercY(south) + mercY(north)) / 2)`),
   `bearing: 0`, `pitch: 0`, sin padding.
4. Al componer (§5) el `W × H` se estira a `N × N`. Así entran los cuatro bordes.

### 4.2 El segundo mapa

- Un contenedor nuevo en `body`: `position: fixed; left: -100000px; top: 0; width: Wpx; height: Hpx; pointer-events: none`
  (no `display: none`, porque MapLibre necesita su tamaño).
- `new maplibregl.Map({ container, style, center, zoom, bearing: 0, pitch: 0, pixelRatio: 1, interactive: false, attributionControl: false, hash: false, fadeDuration: 0, renderWorldCopies: false, trackResize: false, maxCanvasSize: [N, N], canvasContextAttributes: { preserveDrawingBuffer: true, antialias: true } })`.
- Después de crearlo se comprueba que `getCanvas().width === W`, `height === H` y que
  `drawingBufferWidth/Height` coincidan (MapLibre puede achicar el canvas sin avisar). Si
  no: error "This device can't render N px. Try a smaller size."
- Se espera el primer `idle` después de `load`. Timeout: **60 s** para 2048 y 4096, **120 s**
  para 8192. Si se vence: error "Timed out while rendering. Try a smaller size."
- Errores del mapa de exportación (`error`): uno de una fuente de datos incluida aborta con
  "Couldn't load the map data for the image." Uno del fondo de Esri aborta con
  "Basemap tiles failed to load. Try a Transparent background." Las teselas vacías fuera
  de cobertura que devuelve `cs2tiles://` no son errores.
- `webglcontextlost` en el canvas de exportación aborta con "The graphics context was lost. Try a smaller size."
- El zoom depende de N: a más píxeles, más detalle y más etiquetas, y umbrales como
  `SERVICES_POINT_MINZOOM` pueden cambiar lo que aparece. Es lo esperado; se documenta en el README.

### 4.3 ¿Se ofrece 8192?

`exportMaxSize()` crea un contexto WebGL de prueba (una sola vez, perezoso) y devuelve el
mínimo entre `MAX_RENDERBUFFER_SIZE`, `MAX_TEXTURE_SIZE` y `MAX_VIEWPORT_DIMS`. El radio
de 8192 existe solo si ese mínimo es ≥ 8192. Aunque exista, la comprobación de §4.2 sigue
valiendo: un equipo puede anunciar el límite y no tener memoria.

## 5. Composición

- Un canvas 2D de `N × N`: `drawImage(canvasWebGL, 0, 0, W, H, 0, 0, N, N)`.
- **Atribución** abajo a la derecha, siempre, solo de lo que aparece en la imagen:
  `© OpenStreetMap contributors`, más ` · Esri` si el fondo es de Esri, más
  ` · <nombre de la fuente del plan oficial>` si una capa `official-*` quedó en la imagen.
  Fuente sans-serif de `max(12, round(N / 200))` px, texto blanco sobre un rectángulo negro
  al 60 %, con un margen de `round(N / 256)` px. Con fondo transparente también va.
- **Un solo** `toBlob(cb, "image/png")`. Si devuelve `null`: error "Couldn't encode the image."

## 6. Descarga

- Nombre: `<slug>-playable-area-<lat>_<lng>-<N>.png`, con `lat` y `lng` del centro del
  recuadro con 4 decimales (`zurich-playable-area-47.3787_8.5750-4096.png`).
- `URL.createObjectURL(blob)` → `#export-link`: `href`, `download` y el texto
  "Download PNG (x.x MB)", y `hidden = false`. Se le hace **un** `click()` automático. El
  link queda a la vista para volver a bajarla con un gesto explícito (Safari y los
  celulares a veces bloquean la descarga automática).
- La URL anterior se revoca al empezar otra exportación y al apagar el recuadro.
- `#export-status`: "Ready: <nombre>".

## 7. Una a la vez y limpieza

- Mientras se exporta: `#export-go` deshabilitado y `#export-status` con
  "Rendering N × N…". Otra exportación no arranca hasta que termine la primera.
- En **todos** los caminos (éxito, error, timeout, recuadro apagado): `exportMap.remove()`,
  se saca el contenedor y se limpian los listeners y los timers. Nada queda colgado en el
  DOM ni en memoria.
- El mapa principal no se toca: ni cámara, ni hash, ni lo guardado, ni la selección.

## 8. Miniaturas

No cambian: el recuadro arranca apagado y el panel (con el menú) está oculto.

## 9. Fuera de esta etapa

- Rotar el recuadro o la imagen (el mod ya rota).
- Exportar el heightmap o el mapa completo de 57 km.
- Guardar las opciones de exportación.

## 10. Verificación (Claude)

`tests/visualizer/test_frame_export.py`, marcado `network` + `browser` como los demás
(a mano, fuera del CI). El PNG se lee sin dependencias nuevas: el tamaño sale de la
cabecera IHDR y los píxeles se decodifican en el navegador (`createImageBitmap` y un canvas).

1. El menú: abre y cierra con Escape (vuelve el foco), `aria-expanded`, valores por defecto
   (4096, As on screen, sin grilla) y el radio de 8192 presente si y solo si los límites
   WebGL lo permiten.
2. Exportar con 2048 y el mapa de fondo: llega una descarga con el nombre esperado, el PNG
   mide 2048 × 2048, no es de un solo color y la esquina inferior derecha tiene la caja de la
   atribución.
3. Transparente: hay píxeles con alfa 0 y píxeles opacos.
4. Con categorías ocultas (`hide.zoning=…`) hay muchos menos píxeles opacos que sin ocultar.
5. Con la grilla, las columnas `x = k·N/23` son más claras que sin ella.
6. El mapa principal no cambia: cámara, hash y lo guardado.
7. Limpieza: después de exportar queda un solo mapa de MapLibre en la página, y se puede
   exportar dos veces seguidas.
8. Con las teselas de Esri bloqueadas, exportar con el mapa de fondo da el error del fondo
   y exportar transparente funciona.
9. Mientras un módulo pedido carga, `#export-go` está deshabilitado.
10. Celular (390 × 844): el menú entra en la pantalla y no tapa la bandeja.

## Decisiones del dueño (2026-10-03)

- Tamaños 2048, 4096 (por defecto) y 8192 si el equipo lo soporta.
- Fondo elegible: "As on screen" por defecto, o "Transparent".
- Grilla de tiles opcional, apagada.
- Atribución con texto chico en la esquina inferior derecha, solo de las fuentes presentes.
