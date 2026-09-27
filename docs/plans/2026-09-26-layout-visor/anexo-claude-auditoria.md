# Auditoría de UI (Claude)

## Auditoría del layout del visor de ciudad (`visualizer/map.html`)

Tomé medidas reales con Playwright contra el servidor local (`getBoundingClientRect`) y agregué 3 capturas en `shots/`: `audit-12-desktop-vial-off-fondo.png`, `audit-13-pill-hover-clipped.png` y `audit-14-wide-city-legend-covers.png`. No toqué el repo: `git status` sigue limpio.

### 0. El dato que cambia el diagnóstico

Leí los manifests de las 38 ciudades:
- **33** tienen solo `zoning`.
- **3** tienen `zoning` + `external_buildings`: La Plata, Mafra y Valparaíso.
- **1** tiene `zoning` + `vial` + `services`: Chicago.
- **1** tiene los 6 módulos: Minneapolis.

El layout está pensado para Minneapolis, pero lo que ve el jugador en el 95 % de las ciudades es lo de las capturas 07, 08 y audit-14: una pill útil, dos pills con candado, una leyenda con solo zonificación y un panel de Capas que la repite.

### 1. Cuánto del mapa tapa el HUD (medido)

| Viewport | Elemento (px, x,y ancho×alto) | Área tapada |
|---|---|---|
| **1440×900** Minneapolis, estado inicial | zoom 34×66 · chip 174×34 · Star 81×34 · pills 253×56 (1173,14) · **leyenda 322×720** (10,170) · status 347×32 (547,854) · atribución 321×24 · botón Capas 38×38 | **≈21 %** (277k px²). La leyenda sola ocupa la columna x 10–332, o sea el 23 % del ancho |
| 1440×900 con Capas abierto | + panel ≈231×628 (captura 04) | **≈33 %** |
| **1280×720** Minneapolis | leyenda 322×576 (10,134) · pills 253×56 · status 347×32 · Capas abierto 242×504 | **≈25 %**; con Capas abierto **≈38 %** |
| **390×844** móvil | fila 1: chip 164×31 + Star 47×30. Fila 2: pills 253×56 → la franja superior ocupa **0–116 px** (13,7 % del alto). Leyenda plegada 123×42 · Capas 38×38 · atribución abierta de entrada 216×44 | **≈12 %** |
| 390×844 con la leyenda abierta | leyenda 320×704 (10,130) | **≈79 %**: queda una franja de mapa de 60 px a la derecha |

La leyenda de Minneapolis mide 1584 px de contenido y muestra 684 (43 %) en 1440×900. En 1280×720 muestra 540 px (34 %): solo se ve el título "CS2 Zonificación"; Red Vial, Servicios, Transporte, Infraestructura y Confiabilidad quedan debajo del pliegue. El panel de Capas en 1280 tiene 770 px de contenido y muestra 502.

---

### 2. Problemas por gravedad

#### BLOQUEANTE

**B1. Las etiquetas de las pills no aparecen nunca.**
- **Qué pasa:** el tooltip está hecho con `.pill::before` y sale 48 px debajo de la pill (map.html:517-535). Pero `#header-controls` tiene `overflow-x:auto` (map.html:430), y eso fuerza también `overflow-y:auto`. Medí `scrollHeight 77` contra `clientHeight 54`: el tooltip queda recortado adentro de la barra.
- Zoning, Red vial y Servicios tampoco tienen `title`, porque `injectPill` solo lo pone si la pill arranca deshabilitada (map.html:1803).
- En táctil no existe el hover.
- **Resultado:** el control principal de capas son 5 íconos sin nombre (señal de tráfico, maletín, bus, rayo).
- **A quién y en qué tarea:** a todos en la primera visita, al querer "apagar las calles" o "ver solo los servicios". Hay que adivinar clickeando.
- **Evidencia:** captura 05 y `audit-13` (hover sobre Red vial, sin etiqueta).

**B2. La barra de módulos se corre 149 px bajo el cursor al apagar una pill.**
- **Qué pasa:** la barra está anclada a la derecha (`right:14px`). Al apagar un módulo aparece el control "Fondo" al final (map.html:557 y 1959), y la barra pasa de 253 a 402 px de ancho.
- Medido: la pill Red vial pasó de x=1226 a x=1077. En el punto donde se hizo el click queda ahora **Infraestructura**, así que el segundo click para deshacer apaga otra capa.
- En móvil, el mismo control queda fuera de pantalla: la barra tiene `clientWidth` 314 y `scrollWidth` 400, y "Fondo" ocupa x 310–455 en una pantalla de 390. El scroll horizontal está oculto (`scrollbar-width:none`, map.html:431-433), así que no hay pista de que exista.
- **A quién y en qué tarea:** Minneapolis y Chicago en escritorio, al prender y apagar para comparar. Todas las ciudades en móvil, al atenuar un módulo apagado.
- **Evidencia:** `audit-12`.

**B3. En móvil, la leyenda abierta tapa el mapa y la atribución se le monta encima.**
- **Qué pasa:** la leyenda abierta mide 320×704 y deja 60 px de mapa. No se puede leer un color de la leyenda mirando el mapa al mismo tiempo, que es justamente para lo que sirve la leyenda.
- La atribución, abierta de entrada con `maplibregl-compact-show` (map.html:926), se superpone a la leyenda en x 164–330, y 790–834. En la captura 10 se lee "contri**179**tors" encima de la fila "Parking Structure".
- **A quién y en qué tarea:** a quien entra desde Reddit en el celular y quiere saber "¿este verde qué zona es?".
- **Evidencia:** capturas 09 y 10; map.html:897-927.

#### ALTO

**A1. Hay tres lugares para controlar la visibilidad, no están sincronizados, y aislar una zona cuesta 14 clicks.**
- **Qué pasa:**
  - Las pills (arriba a la derecha) prenden y apagan módulos.
  - La casilla general de cada módulo en la leyenda (a la izquierda) hace lo mismo.
  - El panel Capas (abajo a la derecha) filtra por categoría.
- Las filas de la leyenda (`.li`) no son clickeables (map.html:2091-2095).
- Si se oculta una zona desde Capas, la leyenda no cambia: la fila sigue igual y el conteo no se mueve.
- Capas no tiene Transporte ni Infraestructura: `hiddenCats` solo contempla zoning, vial y services (map.html:1904). La leyenda sí los lista, y no hay forma de ocultar "Bus".
- **Tarea "ver solo la industria":** hay que abrir el panel del otro lado de la pantalla y destildar 14 casillas, y después volver a tildarlas. No hay "solo esta", "todas" ni "ninguna".
- Las dos listas usan controles distintos: casilla custom en la leyenda (map.html:691-715) y checkbox nativo en Capas (map.html:807).
- **Evidencia:** captura 04; map.html:2007-2063 y 2065-2187.

**A2. En 36 de 38 ciudades hay dos pills con candado que nunca se abren.**
- **Qué pasa:** Transporte e Infraestructura se inyectan siempre con candado (map.html:1828-1829) y solo se desbloquean si el módulo carga.
- Roscommon, por ejemplo, no tiene esos módulos. Medido: `pill disabled`, con `aria-pressed="false"`, siguen enfocables y el click no hace nada.
- El candado sugiere "cargando" o "premium".
- La única pill útil repite la casilla "CS2 Zonificación" de la leyenda.
- Si un módulo secundario falla al cargar, solo va un `console.warn` (map.html:1121-1123) y la pill queda con candado para siempre, sin mensaje.
- **Evidencia:** capturas 07, 08 y `audit-14`.

**A3. La sección "Confiabilidad de clasificación" de la leyenda muestra colores que no están en el mapa.**
- **Qué pasa:** la leyenda muestra tres muestras de color: azul `#7c9cd9`, verde `#78c47b` y marrón `#d4a96d` (map.html:2152-2164).
- En el mapa, la confianza se codifica solo con opacidad y borde punteado para `m=="area"`. "Inferred (landuse)" no tiene ninguna marca visual distinta (map.html:1616-1626).
- Además, el azul y el verde chocan con Comercial y Residencial.
- **A quién y en qué tarea:** a quien quiere saber qué zona va en una manzana. Puede leer "polígono azul = clasificado por tag".
- **Evidencia:** capturas 03 y 07.

**A4. No hay salida del visor.**
- **Qué pasa:** el chip de la ciudad es un `div role="status"` y no un link (map.html:975). Después de cargar, el HUD ya no muestra la marca "CS2 OSM Toolkit".
- Tampoco hay link a la lista de ciudades, a "Request your city", a Docs ni a Methodology. La única salida es el botón atrás del navegador.
- **A quién y en qué tarea:** al tráfico de Reddit, que entra directo a `map.html?city=…`. Es un callejón sin salida para descubrir otras ciudades y para el crecimiento del proyecto.
- **Evidencia:** captura 02.

**A5. La leyenda es demasiado alta y tapa datos.**
- **Qué pasa:** está anclada abajo a la izquierda, crece hasta `min(80vh, 100dvh-100px)` (map.html:584-585) y tiene scroll interno. Medidas en la sección 1.
- El encuadre inicial (`bounds`, map.html:1548) no deja margen para la leyenda. En ciudades anchas como Little Rock (proporción 2:1) tapa unos 280 px del oeste de la ciudad.
- **Evidencia:** `audit-14`, capturas 02 y 08.

**A6. El idioma está mezclado en toda la UI pública.**
- **Qué pasa:**
  - Etiquetas en español: `<html lang="es">` (map.html:2); título "Cargando…" (map.html:6); "Fondo / Oculto / Atenuado / Completo" (map.html:936-940); pills "Red vial", "Servicios", "Transporte", "Infraestructura" (map.html:1762-1785), mientras "Zoning" está en inglés.
  - Leyenda: "CS2 Zonificación", "Red Vial"; secciones Residencial, Comercial, Oficinas (map.html:1253-1270); Estructurales, Distribución, No motorizado (map.html:1277-1282); servicios e infraestructura en español (map.html:1289-1314).
  - "Confiabilidad de clasificación" (map.html:2152) encabeza ítems en inglés.
  - Capas: "Fondo / Zonas / Vías / Servicios" y `aria-label="Capas"` (map.html:2010-2033).
  - Popups: "Sin nombre", "(sin nombre)", "puente", "Tags OSM" (map.html:1393, 1416, 1423, 1431).
  - Status bar: "polígonos · datos OSM" (map.html:2522-2524).
  - Pantalla de carga: "Pendiente", "⟳ Teselas…" (map.html:1713, 2399).
  - Página de error: "← Volver a landing" (map.html:1238).
- **Íconos de servicios:** las letras salen del español: **B** = Bomberos, **A** = Administración/Policía (map.html:1289-1293). Para un jugador en inglés, "A" y "B" no dicen nada, y "P" (Parks) se confunde con Police o Parking, que además es una categoría de la leyenda.

#### MEDIO

**M1. Hay dos controles distintos que se llaman "Fondo".**
- El select de la barra decide qué pasa con los módulos apagados (map.html:936). La sección "Fondo" del panel Capas elige el mapa base Dark o Satellite (map.html:2010).
- En modo "Completo", apagar una pill no cambia nada en el mapa (map.html:1929-1930). Como se guarda en localStorage, en la visita siguiente las pills "no funcionan".
- El select solo aparece si hay algo apagado, así que la opción de atenuar casi no se descubre.

**M2. Se guarda poco y no se puede compartir nada.**
- Solo se guardan las pills y el modo Fondo (map.html:1968, 1975).
- No se guardan los filtros por categoría, el mapa base (map.html:2045-2052), la fuente OSM u oficial (map.html:1978-1981) ni la posición y el zoom.
- No hay URL con `#zoom/lat/lng` ni con el estado de capas, así que no se puede mandar "mirá este barrio" en Reddit.

**M3. El popup es pobre para la tarea del jugador.**
- No resalta el polígono clickeado (map.html:2259-2269). En zonas densas no se sabe a qué manzana se refiere.
- Las calles sin nombre no tienen popup (map.html:1412), así que no se puede consultar su clase CS2.
- Solo muestra el feature de arriba; lo que queda debajo no se puede consultar.
- El popup de zonificación no tiene link a OSM, ni área o tamaño útil para CS2.
- El "OSM id" va en `#555` a 10 px: contraste 2,2:1 (map.html:1381-1382).
- El popup oficial no muestra el nombre del distrito del plan original (map.html:1403-1408).

**M4. La status bar aporta poco, tiene un dato mal y empuja el layout.**
- "295.854 polígonos" suma 184.723 de zonificación, **108.859 líneas de calles** y 2.272 servicios (map.html:2474). No son todos polígonos.
- No incluye transporte, infraestructura ni la zonificación oficial.
- Repite el nombre de la ciudad, que ya está en el chip.
- Entre 641 y 1000 px obliga a subir la leyenda 54 px (map.html:889-891).
- En móvil se oculta.

**M5. Accesibilidad.**
- **Foco:** la casilla general de cada módulo es un `<span>` de 14×14 sin `tabindex` ni `role` (medido `tabIndex -1`; map.html:2084 y siguientes). Su estilo `:focus-visible` (map.html:881) nunca se aplica.
- **Tamaño táctil:** esa casilla (14×14), los radios (13×13) y el zoom (32×32) en móvil. La casilla ni siquiera llega al mínimo de 24×24 de WCAG 2.5.8.
- **Orden de tabulación:** pills → canvas → zoom → leyenda → Capas → links de atribución → **Star al final**. No sigue el orden visual.
- **Contraste sobre el panel:**

  | Texto | Color | Tamaño | Contraste |
  |---|---|---|---|
  | Encabezados de sección (`.lsect`) | `#6b7a8f` | 10,5 px | 3,76:1 |
  | Conteos en cero | `#4a5568` | — | **2,18:1** |
  | Secciones del panel Capas | `#666` | 10 px | 2,86:1 (map.html:790) |
  | Atribución | — | — | 2,56:1 |

  Los conteos en cero son justo el dato "esta zona no existe en esta ciudad".
- **Letra chica:** muchas etiquetas van a 10–10,5 px, poco para un segundo monitor mirado de lejos.
- **ARIA:** `role=progressbar` sin `aria-valuenow` (map.html:963), y `role=status aria-live` sobre lo que en realidad es el título (map.html:975).

**M6. En ciudades con varios módulos, el mapa por defecto está saturado.**
- Todo arranca prendido. Los íconos de servicios se dibujan con `icon-allow-overlap` desde zoom 11 (map.html:2452-2460 y 1319) y tapan la zonificación, que es el producto principal.
- Colores que chocan: bici `#81C784` con los verdes residenciales; peatonal cian con Low Density Business; `--cat-vial` e `--cat-infra` casi iguales (map.html:48 y 51).
- Aplica solo a Minneapolis y Chicago.
- **Evidencia:** captura 02.

**M7. Los estados de las pills se distinguen poco.**
- Prendida = anillo azul y subrayado. Apagada = sin anillo, con el mismo tinte de categoría. El anillo es siempre `--accent` y no el color de la categoría (map.html:465).
- En `audit-12`, la pill vial apagada casi no se diferencia de las demás.

**M8. Comparar OSM contra oficial (solo Minneapolis) es incómodo.**
- El radio está al tope de la leyenda, que scrollea.
- Los conteos no cambian al pasar a "Official": siguen siendo los de OSM (map.html:2205-2219).
- No hay swipe, ni vista partida, ni control de opacidad.

#### BAJO

- **L1. Tres identidades visuales:** la pantalla de carga usa negro y violeta como la landing (map.html:99-130); el HUD usa azul marino y azul "CS2" (map.html:13-83); la página de error usa el oscuro de GitHub (map.html:1233-1242). La versión está escrita a mano como "v3.4" (map.html:956), cuando la release actual es v3.4.9.
- **L2. La pantalla de carga no muestra progreso real:**
  - "Features loaded" queda en 0 hasta el final, porque `bump` se llama una sola vez (map.html:2474).
  - Con un solo módulo, la barra salta 0 → 50 → 100.
  - No lista los módulos secundarios.
- **L3. El botón Star está en el lugar más valioso**, pegado al nombre de la ciudad, y compite con él. Es intencional (v3.4.8): conservarlo, pero reubicarlo. El punto que titila en el chip (map.html:385-391) parece un indicador "en vivo" que no significa nada.
- **L4. La leyenda muestra zonas con 0** (en Roscommon son 5 filas). Su ancho cambia según la ciudad: 322 px en Minneapolis por el label de la fuente oficial, 260–270 en otras.
- **L5. Detalles técnicos:** se carga Orbitron y no se usa (map.html:10); `favicon.ico` da 404 (ya está en pendientes).
- **L6. Números inconsistentes:** `toLocaleString()` depende del navegador (en español da "1730" y "161.815"), mientras la estrella usa en-US (map.html:995).
- **L7. Paneles inconsistentes:** Capas se cierra al clickear afuera (map.html:2043) y la leyenda no. En móvil pueden quedar los dos abiertos, superpuestos.
- **L8. Móvil apaisado:** con alto ≤ 500 y ancho > 640, las dos filas de arriba ocupan unos 116 px de 390 (≈30 %). Es un cálculo, no lo medí.

---

### 3. Lo que falta

- Link a la lista de ciudades y la marca en el HUD (ver A4).
- Aislar una zona ("solo esta") y "todas / ninguna" por grupo.
- Escala. Opcionalmente, una grilla o recuadro del tamaño de un tile o mapa de CS2.
- Buscador de calle o lugar.
- Información de la ciudad: fecha del extracto OSM, bbox, qué módulos tiene, y cómo usar el mapa en el juego, con link a la metodología de confianza.
- Resaltado del feature seleccionado y, opcionalmente, un hover.
- URL compartible con posición y capas.
- Control de opacidad de la zonificación para calcar sobre Satellite. El mapa satelital ya existe, pero la zonificación a 0,55 lo tapa.
- Un modo "Hide UI" para capturas o segundo monitor.
- Atajos de teclado.
- Conteos "en vista" además de los totales de la ciudad.

### 4. Lo que funciona y conviene conservar

- **Estética de panel CS2:** degradé mate, radio 10, borde fino. Se lee bien sobre el mapa y está tokenizada en `:root` (map.html:13-83), así que rediseñar sale barato.
- **Leyenda agrupada por familia CS2** (Residencial, Comercial, Oficinas, Industrial, Parking), con los nombres oficiales del juego y conteos en mono tabular. Mapea 1:1 con la herramienta de zonas del juego, y la paleta sigue las familias (verde, azul, violeta, amarillo).
- **Encuadre inicial en el bbox** de la ciudad, sin rotación ni inclinación: es una vista cenital de planificación, como en el juego.
- **Carga:** los módulos secundarios cargan después del primer dibujo y hay estado por módulo. La idea es buena aunque falte progreso real.
- **Guardado por ciudad** (localStorage) de módulos y del plegado de la leyenda. La leyenda arranca plegada en pantallas chicas y se usa `dvh`.
- **Honestidad sobre la incertidumbre:** relleno más tenue y borde punteado para la confianza baja, y la línea "⚠ inferred from footprint area" en el popup.
- **Detalles de interacción:** caja de ±4 px para clickear líneas finas, cursor de mano limitado a un cálculo por frame, escape de los nombres OSM en los popups.
- **Opciones de datos:** la comparación OSM contra oficial y el mapa satelital son valor único; hay que hacerlos visibles, no sacarlos.
- **Base de accesibilidad:** `aria-pressed` y `aria-expanded`, estilos de foco, `prefers-reduced-motion`, y la status bar oculta en móvil.

---

# Necesidades del jugador y referentes (Claude)

# Qué necesita el jugador del visor de ciudad (aporte de Claude)

Las frecuencias son una estimación mía, porque el sitio no tiene analytics. La nota de 0 a 5 dice qué tan bien lo resuelve el layout de hoy. Para ponerla miré las capturas y `visualizer/map.html`.

**Resumen:**
- Las dos tareas más frecuentes resuelven mal hoy: "qué zona va en esta manzana" y "llegar a mi barrio y volver ahí".
- La misma lista aparece en tres lugares y ninguno hace todo:
  - prender o apagar un módulo está en las pills y también en los checkboxes maestros de la leyenda;
  - prender o apagar una categoría está solo en el panel de capas;
  - los conteos están solo en la leyenda.
- Falta traducir lo real a las medidas del juego: escala, recorte en tiles, celdas de 8 m y qué vía de CS2 usar. Es lo que haría útil este mapa y no otro mapa OSM cualquiera.

## 1. Tareas del jugador

| # | Tarea | Frecuencia | Hoy | Evidencia |
|---|---|---|---|---|
| T1 | Ver qué zona CS2 va en esta manzana o edificio | Muy alta (~90% de las sesiones, decenas de veces en cada una) | 2 | Hay seis zonas residenciales en verdes y turquesas parecidos (02, 07), así que hay que ir y volver de la leyenda, que ocupa ~300 px. El click da el nombre (`map.html:1375`), pero en un popup que tapa lo que se mira. Además muestra solo la feature de más arriba (`map.html:2222`) y no hay hover ni se resalta la fila de la leyenda. |
| T2 | Llegar a mi barrio, una calle o un lugar conocido | Muy alta (~80%) | 1 | No hay buscador. El fondo está oscurecido (`raster-brightness-max: 0.45`, `map.html:1518`) y las etiquetas casi no se leen. |
| T3 | Volver al mismo punto con la misma vista (segundo monitor, alt-tab, recarga, al otro día) | Muy alta entre quienes están construyendo | 1.5 | Se guardan los módulos y el modo de los apagados, pero no la posición, el zoom ni los filtros. El constructor del mapa no usa `hash` (`map.html:1521-1556`) y no hay ningún `moveend`, así que cada recarga vuelve a la ciudad entera. |
| T4 | Ver una sola zona o familia ("solo industria", "solo oficinas") | Alta (~50%) | 1 | Las filas de la leyenda no se pueden clickear (`map.html:2091-2095`). Hay que abrir otro panel y destildar 14 casillas (04, `map.html:2013-2019`). El filtro no se guarda, porque `writeViewState` solo guarda pills y fondo (`map.html:1968`). |
| T5 | Trazar la red vial (jerarquía, autopistas, puentes) y elegir qué vía de CS2 usar | Alta (~60%) | 3 | La pill de Red Vial con el modo "Atenuado" funciona. Pero el popup de una vía solo aparece si tiene nombre (`map.html:1412`) y no la traduce a una vía del juego (Small/Medium/Large Road, Highway). |
| T6 | Ubicar servicios (hospitales, escuelas, bomberos, policía, parques) | Media-alta (~40%) | 3 | Las categorías ya son las del toolbar de CS2, pero están en español (03). Con la ciudad entera en pantalla, ~2.300 pins (01) tapan la zonificación (02). |
| T7 | Decidir qué recorte entra en el juego y medir en celdas de 8 m | Media (~25%, pero es la primera decisión de cada proyecto) | 0 | El área jugable mide 14.336 m de lado (529 tiles de ~623 m). Sin mods se desbloquean 441 tiles (171 km²). Hoy no hay escala (solo zoom y atribución, `map.html:1559-1560`), ni tamaño del bbox, ni grilla de tiles. |
| T8 | Abrir el mapa desde Reddit en el celular y entender qué es en 5 segundos | Alta en los picos después de cada post | 2 | Las pills no tienen texto (09). La leyenda abierta tapa ~2/3 de la pantalla (10) y la atribución de dos líneas queda encima. No hay "About / How to use". |
| T9 | Volver a la lista de ciudades o cambiar de ciudad | Media (~30%) | 0.5 | El chip de la ciudad no es un link (`map.html:975`, es un `role="status"`). Solo queda el botón "atrás" del navegador. |
| T10 | Cambiar a satélite para ver la forma real (lotes, estacionamientos) | Media (~30%) | 2 | Está escondido en el panel de capas, encima de ~30 checkboxes (04). Además se llama "Fondo", igual que el select de módulos apagados (`map.html:936` y `2010`). |
| T11 | Seguir una línea de transporte (metro, tren, BRT, bus) | Media (~20%) | 2 | El click da el nombre y el operador (`map.html:1436`). No hay lista de líneas, no se resalta el recorrido entero y no se puede aislar un tipo. El panel de capas no tiene Transporte ni Infraestructura (`map.html:2015-2032`). |
| T12 | Comparar la zonificación OSM con la oficial (solo en ciudades con `official_zoning`) | Baja en general (~5%), alta en esas ciudades | 2 | Hay un radio arriba de la leyenda (02): hay que alternar y acordarse de lo que se vio. No hay comparación deslizable ni mapa partido. |

### Otros problemas que encontré (para el diagnóstico común)

1. **Pills con candado para siempre.** Las pills de Transporte e Infraestructura se crean siempre (`map.html:1827-1829`) y solo se desbloquean cuando esos datos cargan (`2339`, `2386`). En ciudades que no tienen esos módulos, como Roscommon (07) o New York (08), quedan grises con candado para siempre. Parece contenido pago o algo roto.
2. **La leyenda de "Confiabilidad de clasificación" no coincide con el mapa.** Muestra azul, verde y marrón (`map.html:2152-2164`). El mapa marca la baja confianza con opacidad 0.22 y borde punteado sobre el color de la zona (`map.html:1606-1625`). Esos tres colores no aparecen nunca en el mapa.
3. **Conteos poco útiles.** Son de la ciudad entera (161.815) aunque el jugador esté mirando un barrio. Las zonas con 0 se listan igual: en Roscommon hay seis filas en 0 (07).
4. **Dos estéticas distintas.** La landing (11) y la pantalla de carga (01) son negras con acento violeta. El visor es azul marino con cian (02). El brief dice que la landing es azul y cian, pero la captura muestra otra cosa: conviene que el debate decida cuál es la estética oficial.
5. **Más español en los popups:** "Sin nombre", "(sin nombre)", "puente" y "Policía y administración · government" (`map.html:1393, 1416, 1423`).

## 2. Referentes y qué conviene robar de cada uno

1. **El propio CS2 (info views, toolbar y panel de selección).** Las info views se abren desde un ícono arriba a la izquierda. Son 33, y cada una muestra un panel con leyenda y estadísticas. Al elegir una herramienta de construcción, su info view se abre sola. Desde el parche 1.1, los tooltips del toolbar muestran el atajo de teclado. Qué robar:
   - **Aislar como una info view:** al elegir una familia, esa se ve en color y el resto queda neutro. El modo "Atenuado" de hoy ya hace eso; tiene que ser lo que pasa por defecto al aislar, no una opción escondida en un select.
   - **Los nombres, el orden y los íconos del juego, en inglés:** "Healthcare & Deathcare", "Education & Research", "Fire & Rescue", "Police & Administration", "Parks & Recreation", "Electricity", "Water & Sewage", "Garbage Management". Las zonas ya usan los nombres exactos del juego; falta extenderlo a todo lo demás. La paleta de zonas ya se parece a la del juego: conviene mantenerla.
   - **Un panel fijo para lo seleccionado,** como el Selected Info Panel del juego, en vez de un popup flotante.
   - **Atajos de teclado 1 a 6 para los módulos,** con el atajo en el tooltip.
2. **Google Maps.** En escritorio, el control de capas está abajo a la izquierda y es una miniatura: el primer click alterna entre mapa y satélite, y "More" muestra el resto de las capas. En el celular abre una hoja con "Map type" y "Map details". Qué robar: el satélite a un click con miniatura, separado de las capas de datos, y la hoja desde abajo en el celular.
3. **OpenStreetMap.org.** Tiene una columna de herramientas a la derecha (capas, leyenda, compartir, consultar). La herramienta "Query features" muestra, al hacer click, lo que hay cerca con sus tags. La posición queda en la URL (`#map=z/lat/lon`). Qué robar:
   - la posición en la URL, que resuelve T3 y T8 a la vez;
   - un panel que al hacer click liste todo lo que hay en ese punto (zona, vía, servicio, línea), no solo la feature de arriba.
4. **Felt.** La leyenda está a la izquierda y es también la lista de capas: desde ahí se prende y se apaga cada una. El panel de detalle, a la derecha, aparece solo cuando se selecciona algo en el mapa o en la leyenda. Cada categoría tiene su propia fila. Qué robar: que la leyenda sea el control, y un panel de detalle a la derecha solo cuando hay algo seleccionado.
5. **ArcGIS Experience Builder.** El widget Map Layers agregó la opción "Show legend" para funcionar como lista de capas y leyenda a la vez. La comunidad había pedido justamente juntar los dos widgets. También tiene "Toggle all" y "Search layers". Qué robar: juntar leyenda y capas, y un "Show all / Hide all" por sección. Además es la prueba de que tener dos paneles con la misma lista es un problema conocido.
6. **kepler.gl.** Tiene un panel lateral con pestañas, controles a la derecha y un mapa partido ("Split Map") en el que cada mitad muestra sus propias capas. Qué robar: el mapa partido o deslizable para comparar OSM con la zonificación oficial (T12). Qué no robar: el panel de pestañas, que está pensado para analistas y es demasiado para un jugador.
7. **NYC ZoLa (el mapa de zonificación de Nueva York).** Se usa buscando primero: por dirección, lote, intersección o lugar, con autocompletado. Los grupos de capas arrancan cerrados. Las capas quedan en la URL (`?layer-groups=[...]`) y hay rutas por bbox. Al hacer click en un lote se abre una ficha con su zonificación. La guía vieja tenía niveles de zoom con nombre: "City View", "Neighborhood View", "Block View", "Building View". Qué robar: el buscador, las capas en la URL y los niveles de zoom con nombre ("Whole city / District / Block").
8. **Minneapolis 2040.** Tiene una leyenda interactiva arriba de cada mapa: al clickear una categoría se explica qué es. Al clickear una parcela se ve qué indica el plan para ese lugar. Qué robar: que cada fila de la leyenda pueda abrir una explicación "What this is in CS2", por ejemplo "Mixed Housing: shops on the ground floor, apartments above". En las ciudades con plan oficial, también la equivalencia de cada categoría oficial con su zona de CS2.
9. **Ejemplos y plugins de MapLibre.** Sirven "Create a hover effect" (resaltar el polígono bajo el cursor), "Get features under the mouse pointer" y los plugins de comparación `@maplibre/maplibre-gl-compare` y `maplibre-gl-swipe`. Todo carga desde un CDN, sin bundler, y cada interacción consulta un solo punto, sin recorrer los 300k features. Ojo: el plugin compare usa dos mapas y duplica memoria y teselas; `maplibre-gl-swipe` trabaja dentro de un mismo mapa y es más barato.

**Sobre el buscador:** Nominatim, el buscador de OSM, prohíbe autocompletar desde el navegador y limita a 1 consulta por segundo. La alternativa sin depender de nadie: que el extractor escriba un índice liviano de nombres de calles y lugares para cada ciudad (esos nombres ya están en `vial` y `services`) y buscar ahí. Nominatim quedaría solo como respaldo cuando se aprieta Enter.

## 3. Cinco principios de diseño, en orden

1. **Cada cosa se controla en un solo lugar.** La leyenda es el panel de capas: cada fila tiene color, nombre y conteo, y se toca para mostrar u ocultar. Tocar el título de una sección aísla esa familia. Se borran el panel de capas duplicado y los checkboxes maestros. De las pills y los controles de la leyenda, queda uno solo. Esto resuelve T4, T10 y T11, y buena parte del diagnóstico.
2. **Hablar el idioma de CS2.** Nombres, orden, íconos y colores del juego, en inglés. Aislar funciona como una info view: lo demás queda neutro. Lo real se traduce a las medidas del juego: escala en metros y celdas de 8 m, recorte de 14,3 km con tiles de ~623 m, y la vía de CS2 sugerida para cada calle. Es lo que diferencia este sitio de cualquier mapa de OSM.
3. **Que el jugador pueda preguntar "¿qué es esto?" sin descifrar colores.** El hover resalta el polígono y su fila en la leyenda. El click abre un panel fijo (a la derecha en escritorio, desde abajo en el celular) con todo lo que hay en ese punto. Cuesta una consulta en un punto (`queryRenderedFeatures` + feature-state), sin recorrer features.
4. **La vista se guarda en la URL.** Posición, zoom, módulos, filtros, fuente (OSM u oficial) y selección van en el hash; localStorage queda solo de respaldo. Sirve para alternar con el juego, para compartir una manzana en Reddit y para retomar al otro día.
5. **El mapa primero, y la interfaz del tamaño de lo que hay.** La interfaz crece o se achica según lo que tiene la ciudad (de 1 a 6 módulos): nada de pills con candado para siempre ni filas en 0. También según la pantalla: en una ventana a media pantalla (~960 px) o en un celular, el mapa conserva al menos el 70% del área. Lo secundario (About, estado, atribución) va junto en un solo lugar discreto. El botón Star sigue visible, pero chico, al lado del link de vuelta a la lista de ciudades, y no en la esquina más valiosa.

Fuentes:
- [Info views – CS2 Wiki](https://cs2.paradoxwikis.com/Info_views)
- [Patch 1.1.X – CS2 Wiki](https://cs2.paradoxwikis.com/Patch_1.1.X)
- [Zoning – CS2 Wiki](https://cs2.paradoxwikis.com/Zoning)
- [CS2 map size (VideoGamer)](https://www.videogamer.com/guides/cities-skylines-2-map-size-buildable-area-tiles/)
- [CS2 tiles (PCGamesN)](https://www.pcgamesn.com/cities-skylines-2/tiles)
- [Google Maps layers – Desktop help](https://support.google.com/maps/answer/3092439?hl=en&co=GENIE.Platform%3DDesktop)
- [Google Maps layers – Android help](https://support.google.com/maps/answer/3092439?hl=en&co=GENIE.Platform%3DAndroid)
- [OSM Query features tool (wiki)](https://wiki.openstreetmap.org/wiki/Query_features_tool)
- [OSM blog: New query feature](https://blog.openstreetmap.org/2014/12/01/new-query-feature/)
- [OSM wiki: Browsing](https://wiki.openstreetmap.org/wiki/Browsing)
- [Felt: Tour the interface](https://help.felt.com/getting-started/tour-the-interface)
- [Felt: List](https://help.felt.com/layers/list)
- [Felt: Legends](https://developers.felt.com/felt-style-language/legends)
- [ArcGIS Experience Builder: Map Layers widget](https://doc.arcgis.com/en/experience-builder/latest/configure-widgets/map-layers-widget.htm)
- [Esri idea: Combine Legend Widget and Layers Widget](https://community.esri.com/t5/arcgis-experience-builder-ideas/experience-builder-combine-legend-widget-and/idi-p/1228988)
- [kepler.gl user guides](https://docs.kepler.gl/docs/user-guides)
- [kepler.gl split maps](https://github.com/heshan0131/kepler.gl/blob/master/docs/f-map-styles/6-split-maps.md)
- [ZoLa repo (NYC Planning Labs)](https://github.com/NYCPlanning/labs-zola)
- [ZoLa User Guide (PDF)](https://www.nyc.gov/assets/planning/download/pdf/data-maps/maps-geography/zola/zola-userguide.pdf)
- [ZoLa data URL with layer-groups](https://zola.planning.nyc.gov/data?layer-groups=%5B%22street-centerlines%22%2C%22tax-lots%22%5D)
- [Minneapolis 2040: Land Use & Built Form](https://minneapolis2040.com/topics/land-use-built-form/)
- [MapLibre: Create a hover effect](https://maplibre.org/maplibre-gl-js/docs/examples/create-a-hover-effect/)
- [MapLibre: Get features under the mouse pointer](https://maplibre.org/maplibre-gl-js/docs/examples/get-features-under-the-mouse-pointer/)
- [maplibre-gl-compare](https://github.com/maplibre/maplibre-gl-compare)
- [maplibre-gl-swipe](https://github.com/opengeos/maplibre-gl-swipe)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)

Archivos consultados (no modifiqué nada del repo):
- `C:\Users\osyanne\Documents\Claude\Projects\Proyecto mineapolis\cs2-minneapolis-zoning\visualizer\map.html`
- `C:\Users\osyanne\AppData\Local\Temp\claude\C--Users-osyanne-Documents-Claude-Projects-Proyecto-mineapolis-cs2-minneapolis-zoning\b019c131-7c47-479d-a70c-f508eaab7d12\scratchpad\debate\brief.md`
- `C:\Users\osyanne\AppData\Local\Temp\claude\C--Users-osyanne-Documents-Claude-Projects-Proyecto-mineapolis-cs2-minneapolis-zoning\b019c131-7c47-479d-a70c-f508eaab7d12\scratchpad\shots\`