# Brief — rediseño del layout del visor de ciudad (map.html)

## Qué se pide

El dueño del repo (CS2 OSM Toolkit) no está convencido con el layout de **adentro de
las ciudades**: la vista `visualizer/map.html?city=<slug>`. Quiere ideas para un layout
mejor. Es un debate entre Claude y Codex: cada uno propone, después se critican, y al
final se entrega al dueño un conjunto de ideas ordenado, con los acuerdos y los
desacuerdos a la vista. **Nadie modifica el repo en esta etapa: son solo ideas.**

Escribí en español (rioplatense está bien). Los textos que irían en la UI, en inglés
(la UI pública es para jugadores de todo el mundo).

## Contexto del producto

- Sitio estático en GitHub Pages (https://osyanne.github.io/CitiesSkylines2-osm-toolkit/).
  Landing `visualizer/index.html` con la lista de ~38 ciudades → cada una abre
  `visualizer/map.html?city=<slug>`.
- Público: jugadores de Cities: Skylines II que usan el mapa como **referencia para
  replicar una ciudad real** en el juego (qué zona CS2 va en cada manzana, jerarquía
  vial, servicios, transporte, infraestructura). Lo miran en un segundo monitor o
  alternando con el juego, muchas veces con mucho zoom sobre un barrio concreto.
  También lo abren desde Reddit en el celular.
- `map.html` es un único HTML (~2540 líneas: CSS 11–928, markup 930–985, JS 987–2540)
  con MapLibre GL 5.24 desde unpkg. Sin build step. Lee `cities/<slug>/manifest.json`;
  usa teselas vectoriales si existen, si no los `datos_*.json`.
- Módulos por ciudad (según manifest; no todas los tienen): `zoning` (15 zonas CS2 +
  parking), `official_zoning` (solo algunas, ej. Minneapolis: plan oficial 2040),
  `vial` (jerarquía vial), `services` (hospitales, escuelas, policía…), `transporte`
  (líneas), `infraestructura` (energía, agua…). Hasta ~300k polígonos por ciudad.
- Estado de vista guardado en localStorage por ciudad.

## Inventario del layout actual (visto en las capturas)

- **Arriba a la izquierda**: botones de zoom + / − de MapLibre; al lado un "chip" con el
  nombre de la ciudad (ícono de mapa) y un botón "★ Star 29" a GitHub.
- **Arriba a la derecha**: barra de "pills" de módulos (solo íconos: edificio=Zoning,
  cartel=Red vial, maletín=Servicios, bus=Transporte, rayo=Infraestructura). Transporte
  e infraestructura arrancan con candado hasta que cargan. Si se apaga un módulo aparece
  un `<select>` "Fondo: Oculto / Atenuado / Completo" (qué hacer con los módulos
  apagados). Las etiquetas solo aparecen en hover.
- **Izquierda, panel "LEGEND"** (colapsable, con scroll interno): radio "Source:
  OSM-derived / Official (Mpls 2040 Plan)" (si hay oficial), checkbox maestro "CS2
  Zonificación", secciones Residencial / Comercial / Oficinas / Industrial / Parking con
  swatch + nombre de zona CS2 + conteo, luego "Red Vial", "Servicios", etc. con sus
  propios checkboxes maestros y listas.
- **Abajo a la derecha**: botón de "Capas" (ícono de capas) que abre OTRO panel a la
  derecha: Fondo (Dark Esri / Satellite Esri), y checkboxes por categoría: Zonas (las
  mismas 15 de la leyenda), Vías, Servicios… **Duplica** la lista de la leyenda.
- **Abajo al centro**: status bar "295.854 polígonos · Minneapolis, MN · datos OSM".
- **Abajo a la derecha**: atribución.
- **Popup** al clickear una feature: nombre, "Policía y administración · government",
  desplegable "▸ Tags OSM".
- **Pantalla de carga**: overlay con marca, "Loading <ciudad>", grilla de progreso por
  módulo, barra, contador de features.
- **Móvil (390 px)**: chip de ciudad + star arriba, fila de pills debajo, botón "Legend"
  abajo a la izquierda que abre la leyenda, botón capas abajo a la derecha, atribución
  enorme abajo.
- Idioma mezclado: UI con "Fondo", "Zonas", "Vías", "Capas", "CS2 Zonificación",
  "Red Vial", "polígonos", "datos OSM", popups en español; el resto en inglés.
- No hay: botón para volver a la lista de ciudades (el chip de ciudad no navega), buscador
  (de calles/lugares), escala, info de la ciudad (fecha de datos, bbox, tamaño en tiles
  CS2), ayuda de cómo usar el mapa en el juego, ni forma de aislar una zona CS2 rápido
  (hay que destildar las otras 14).

## Capturas (PNG)

Carpeta: `docs/plans/2026-09-26-layout-visor/capturas/`

- `01-desktop-loading.png` — pantalla de carga (1440×900)
- `02-desktop-default.png` — Minneapolis, estado inicial
- `03-desktop-legend-scrolled.png` — leyenda scrolleada hasta abajo
- `04-desktop-layers-open.png` — panel de capas abierto (la duplicación)
- `05-desktop-pill-hover.png` — hover sobre una pill de módulo
- `06-desktop-zoomed-popup.png` — zoom + popup de una feature
- `07-desktop-small-city.png` — ciudad chica (Roscommon)
- `08-laptop-1280x720-newyork.png` — laptop 1280×720, Nueva York (menos módulos)
- `09-mobile-default.png` — móvil 390×844
- `10-mobile-legend-toggled.png` — móvil con la leyenda tocada
- `11-landing-reference.png` — la landing, como referencia del lenguaje visual (estética
  tipo UI del juego CS2: paneles azul oscuro translúcidos, acentos cian)

Se puede servir el visor localmente (`python -m http.server 8766 --directory visualizer`)
si hace falta mirar algo más, pero el código de `visualizer/map.html` y las capturas
deberían alcanzar.

## Restricciones

- Tiene que seguir siendo un HTML estático sin build (se puede partir en archivos
  .js/.css si conviene, pero sin bundler).
- Conviven ciudades con 1 módulo y con 6; el layout tiene que funcionar en las dos.
- Rendimiento: nada que obligue a recorrer los 300k features en el cliente por
  interacción.
- La estética del juego (CS2) es parte de la identidad del sitio; se puede refinar, no
  hace falta tirarla.
- Móvil tiene que funcionar (tráfico de Reddit).

## Formato de cada propuesta

Para cada propuesta de layout:

1. **Nombre** corto y **concepto en una línea**.
2. **Wireframe ASCII** de escritorio (≈100 columnas) y de móvil (≈40 columnas).
3. **Qué cambia** respecto de hoy, concreto (qué se mueve, qué se fusiona, qué se borra,
   qué se agrega).
4. **Por qué es mejor para un jugador de CS2** (tareas concretas: "encontrar qué zona va
   en esta manzana", "ver solo la industria", "comparar OSM vs oficial", etc.).
5. **Costo** de implementación en map.html (S / M / L) y **riesgos**.

Además de las propuestas: un **diagnóstico** de los problemas del layout actual,
ordenados por gravedad, con evidencia (captura o `visualizer/map.html:<línea>`).
