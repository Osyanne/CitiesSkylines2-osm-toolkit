# Postura de Claude, ronda 1: layout del visor de ciudad (`map.html`)

Un dato ordena todo lo que sigue. De las 38 ciudades, **33 tienen solo `zoning`**, 3 tienen además `external_buildings` (La Plata, Mafra, Valparaíso), Chicago tiene 3 módulos y **solo Minneapolis tiene los 6**. El layout actual está pensado para Minneapolis, pero en el 95 % de las ciudades el jugador ve una pill útil, dos pills con candado y una leyenda que el panel Capas repite. Mi criterio: diseñar primero para la ciudad de 1 módulo y hacer que el resto aparezca solo cuando existe.

---

## 1. Diagnóstico (por gravedad)

| # | Gravedad | Problema | Evidencia |
|---|---|---|---|
| 1 | **Bloqueante** | **Los botones de módulo no tienen nombre.** El tooltip `.pill::before` queda recortado porque la barra tiene `overflow-x:auto`, que obliga a `overflow-y:auto` (se mide `scrollHeight` 77 contra `clientHeight` 54). Solo las pills deshabilitadas tienen `title`, y en táctil no hay hover. El control principal son 5 íconos que hay que adivinar. | map.html:430, 517-535, 1803 · capturas 05 y `audit-13` |
| 2 | **Bloqueante** | **La barra se corre 149 px debajo del cursor.** Está anclada a la derecha y, al apagar un módulo, le aparece "Fondo" al final. El segundo click cae en otra pill (apagás Red vial y después apagás Infraestructura). En el celular "Fondo" queda fuera de la pantalla y el scroll está oculto. | map.html:557, 1959, 431-433 · `audit-12` |
| 3 | **Bloqueante** | **En el celular, la leyenda abierta tapa el 79 % del mapa** (320×704, quedan 60 px). No se puede mirar un color y buscarlo en la leyenda, que es para lo que existe. Además la atribución, abierta por defecto, se le superpone ("contri**179**tors"). | map.html:926 · capturas 09 y 10 |
| 4 | Alto | **Tres controles de visibilidad que no se sincronizan:** las pills, las casillas maestras de la leyenda y el panel Capas. Las filas de la leyenda no se pueden clickear. Capas no incluye Transit ni Utilities (no hay forma de ocultar "Bus"). "Ver solo la industria" cuesta 14 clicks de ida y 14 de vuelta. Encima hay dos controles distintos que se llaman "Fondo". | map.html:2091-2095, 1904, 2007-2063, 936 y 2010 · captura 04 |
| 5 | Alto | **La tarea más frecuente ("¿qué zona va en esta manzana?") obliga a ir y volver de la leyenda.** Hay seis verdes residenciales parecidos, no hay hover, el polígono clickeado no se resalta y el popup muestra solo el feature de arriba. Las calles sin nombre no tienen popup. | map.html:2259-2269, 1412 · capturas 02 y 06 |
| 6 | Alto | **Candados eternos.** Transit y Utilities se crean siempre bloqueadas: en 36 de 38 ciudades parecen pagas o rotas. Si un módulo falla al cargar, solo va un `console.warn`. Y cuando sí cargan, pisan lo que el usuario había guardado (`moduleStates.x = "on"`). | map.html:1828-1829, 1122, 2338, 2385 · capturas 07, 08 y `audit-14` |
| 7 | Alto | **La leyenda tapa la ciudad.** En 1440×900 ocupa 322×720 (el 23 % del ancho). En 1280×720 muestra solo el 34 % de su contenido. El encuadre inicial no deja margen para ella: en Little Rock tapa unos 280 px del oeste. | map.html:584-585, 1548 · capturas `audit-14` y 08 |
| 8 | Alto | **Callejón sin salida.** El chip de la ciudad es un `div role="status"`, no un link. No hay link a la lista, a otras ciudades, a Methodology ni a Request. El tráfico de Reddit entra directo a `map.html?city=`. | map.html:975 · captura 02 |
| 9 | Alto | **Idioma mezclado.** "Fondo", "Red vial", "CS2 Zonificación", "polígonos · datos OSM", popups con "Sin nombre" y `<html lang="es">`. Las letras de los servicios salen del español: B = Bomberos, A = Administración. | map.html:2, 936, 1289-1293, 1393, 2522 |
| 10 | Alto | **La leyenda de confianza muestra colores que no existen en el mapa** (azul, verde y marrón). En el mapa, la confianza se ve como opacidad y borde punteado. Además, el azul y el verde chocan con Commercial y Residential. | map.html:2152-2164 contra 1611-1627 · captura 03 |
| 11 | Medio | **No se puede volver al mismo punto ni compartirlo.** El mapa no usa `hash`, y no se guardan ni la posición ni los filtros: cada recarga vuelve a la ciudad entera y no hay link a "este barrio". | map.html:1521-1560, 1968 |
| 12 | Medio | **Minneapolis sale saturada y el mapa base casi no se lee.** Hay 2.272 pines con `icon-allow-overlap` desde z11, encima de la zonificación. `DARKEN` también se aplica a la capa de etiquetas, así que no se leen los nombres de calle. La status bar suma 108.859 líneas de calles como "polígonos". | map.html:2457, 1543, 2474 · captura 02 |

---

## 2. Tres propuestas de layout

Las tres difieren en dos decisiones que le toca tomar al dueño:
- **Modelo de visibilidad:** una *vista activa* como las info views de CS2 (A y B), o *capas libres* combinables (C).
- **Dónde vive el HUD:** una sola columna flotante (A), paneles a los dos lados más una toolbar de juego (B), o una barra lateral acoplada (C).

### Base común a las tres (no la repito en cada una)

- **Una sola lista de capas.** Se borran las pills, el select "Fondo", las casillas maestras y el panel Capas (map.html:421-578, 933-944, 2007-2063, 765-809). `hiddenCats` se extiende a Transit y Utilities.
- **Solo aparece lo que la ciudad tiene** según el manifest: sin candados, sin filas en 0 (van agrupadas en `+ 5 zones not found here`). Mientras un módulo carga muestra un spinner; si falla, `!` y "Couldn't load · Retry".
- **Hover en escritorio:** contorno del polígono (feature-state con `promoteId: {zoning:"id"}`), tooltip junto al cursor y la fila de la leyenda marcada. **Click:** una ficha con todo lo que devuelve `hitsAt()`, no solo lo de arriba, más `Query on OSM ↗` (`/query?lat=&lon=`, porque los ids compactos no dicen si son way o relation) y `Copy link`.
- **Navegación:** `‹ Cities`, el nombre de la ciudad abre un selector con filtro (usa el `cities.json` que ya se baja en 1042-1049), y `⌕ Search streets & places` (tecla `/`). La búsqueda va a Nominatim solo al apretar Enter, dentro del bbox; más adelante, a un índice local.
- **Estado en la URL** (`#map=z/lat/lng&view=…&only=…&src=…&base=…`) con localStorage de respaldo, y `↗ Share`.
- **Escala en metros y en celdas de 8 m.** Fila de confianza honesta: `┄ faint + dashed = guessed from building size ⓘ`.
- **Satellite a un click** (tecla `S`), con `Zoning opacity` visible solo mientras está activo. `Hide UI` con la tecla `H`.
- **Se va la status bar**: su dato, corregido ("184,723 zoned areas · 108,859 road segments"), pasa a la info de la ciudad. **Se va el overlay de carga que bloquea**: queda una barra fina y el estado por módulo.
- **`fitBounds` con `padding.left`** igual al ancho del panel.
- **Todo en inglés con los nombres de CS2** ("Healthcare & Deathcare", "Fire & Rescue", "Police & Administration"…), glifos en vez de letras en los servicios y números con `en-US`.

---

### A. Clean Map (la que recomiendo)

**Concepto:** el mapa ocupa toda la pantalla. El hover contesta "qué zona va acá", y todo lo demás vive en una sola columna y un dock de vistas como el del juego.

**Escritorio 1440×900.** Minneapolis, vista Zoning, `Others: Dim`, mouse sobre una manzana:
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ╭────────────────────────────────────────────────────────────────╮        ╭────────────────────╮ │
│ │ ‹ Cities │ ▦ Minneapolis, MN ▾ │ ⌕ Search streets & places   / │        │ ★ 29 │ ↗ Share │ ⋯ │ │
│ ╰────────────────────────────────────────────────────────────────╯        ╰────────────────────╯ │
│ ╭─ ▦ ZONING · 184,723 ───────────── « ─╮                                                         │
│ │ [OSM-derived│2040 Plan│Compare]      │                                                         │
│ │ Click a zone = show only it          │                                                         │
│ │ RESIDENTIAL                  169,815 │         ┏━━━━━━━━━┓                                     │
│ │  ■ Low Density Housing       161,015 │         ┃▒▒▒▒▒▒▒▒▒┃ ╭────────────────────────────╮      │
│ │  ■ Medium Density Row Housing  1,730 │         ┗━━━━━━━━━┛ │ ■ Medium Density Housing   │      │
│ │ ▶■ Medium Density Housing      6,725 │                     │   building=apartments      │      │
│ │  ■ Mixed Housing                  40 │                     ╰────────────────────────────╯      │
│ │  ■ Low Rent Housing              185 │                                                         │
│ │  ■ High Density Housing          120 │         hover: outline + tooltip + row ▶                │
│ │ COMMERCIAL                     5,615 │         (no click needed to answer T1)                  │
│ │  ■ Low Density Business        5,498 │                                                         │
│ │  ■ High Density Business         117 │                                                         │
│ │ OFFICE                           415 │                                                         │
│ │  ■ Low Density Offices           358 │           M A P  (full-bleed)                           │
│ │  ■ High Density Offices           57 │         first frame: fitBounds with                     │
│ │ INDUSTRIAL                     2,285 │         padding.left = legend width                     │
│ │  ■ Industrial Manufacturing    2,285 │                                                 ╭─────╮ │
│ │ PARKING                        6,593 │                                                 │ +   │ │
│ │  ■ Surface Parking             6,414 │                                                 │ −   │ │
│ │  ■ Parking Structure             179 │                                                 │ ⌂   │ │
│ │ ┄ faint + dashed = guessed  ⓘ        │                                                 ╰─────╯ │
│ ├──────────────────────────────────────┤                                                         │
│ │ ▸ ═ ROADS                    108,859 │                                    ╭──────────────────╮ │
│ │ ▸ ✚ SERVICES                   2,272 │                                    │ ▒▒ Satellite  S  │ │
│ │ ▸ ▬ TRANSIT                      297 │                                    ╰──────────────────╯ │
│ │ ▸ ϟ UTILITIES                    371 │                                (opacity slider shows    │
│ ╰──────────────────────────────────────╯                                 up while Satellite on)  │
│     ╭────────────────────────────────────────────────────────────────────────────────────────╮   │
│     │ [▦ Zoning 1] │ ═ Roads 2 │ ✚ Services 3 │ ▬ Transit 4 │ ϟ Utilities 5 ┃ Others ◐ Dim ▾ │   │
│     ╰────────────────────────────────────────────────────────────────────────────────────────╯   │
│                                                                                                  │
│ ├────┤ 500 m · 62 cells                                                © OpenStreetMap · Esri  ⓘ │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Escritorio 1280×720 o media pantalla.** Leyenda plegada en un riel de muestras, Industrial aislado y una manzana seleccionada:
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ╭────────────────────────────────────────────────────────────────╮        ╭────────────────────╮ │
│ │ ‹ Cities │ ▦ Minneapolis, MN ▾ │ ⌕ Search streets & places   / │        │ ★ 29 │ ↗ Share │ ⋯ │ │
│ ╰────────────────────────────────────────────────────────────────╯        ╰────────────────────╯ │
│ ╭────╮ ╭─ SELECTED ───────────────────── ✕ ─╮      ╭────────────────────────────────────────╮    │
│ │ ▦» │ │ ■ Industrial Manufacturing         │      │ Showing 1 of 13 zones · Show all  Esc  │    │
│ │ ░  │ │   Industrial · landuse=industrial  │      ╰────────────────────────────────────────╯    │
│ │ ░  │ │   ~5,800 m² ≈ 90 cells (8 m)       │                                                    │
│ │ ░  │ ├────────────────────────────────────┤                                                    │
│ │ ░  │ │ ALSO HERE                          │              ┏━━━━━━━━━━┓                          │
│ │ ░  │ │ ═ Hiawatha Ave · Major Road        │              ┃██████████┃ ◂ clicked: white outline │
│ │ ░  │ │   typical in CS2: Medium Road*     │              ┗━━━━━━━━━━┛                          │
│ │ ░  │ │ ✚ Fire & Rescue · Station 21       │                                                    │
│ │ ░  │ ├────────────────────────────────────┤      industry in colour, other zones grey 18 %     │
│ │ ░  │ │ [Only this ✓] [OSM ↗] [⧉ Link]     │      car roads at 30 %, pins hidden (view Zoning)  │
│ │ ░  │ ╰────────────────────────────────────╯                                                    │
│ │ ■◂ │ ◂ rail = folded legend (default 641–1199 px):                                             │
│ │ ░  │   hovering the map lights the swatch; hover a                                             │
│ │ ░  │   swatch = its name; click = only this                                                    │
│ ╰────╯                                                                                           │
│     ╭────────────────────────────────────────────────────────────────────────────────────────╮   │
│     │ [▦ Zoning 1] │ ═ Roads 2 │ ✚ Services 3 │ ▬ Transit 4 │ ϟ Utilities 5 ┃ Others ◐ Dim ▾ │   │
│     ╰────────────────────────────────────────────────────────────────────────────────────────╯   │
│ ├────┤ 200 m · 25 cells                                                © OpenStreetMap · Esri  ⓘ │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Móvil 390×844.** A la izquierda, peek después de tocar una manzana. A la derecha, la hoja a media altura con la leyenda. En pantalla dice "Utilities" completo.
```
┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
│╭────────────────────────────────────╮│    │╭────────────────────────────────────╮│
││ ‹  Minneapolis, MN ▾      ⌕   ★ 29 ││    ││ ‹  Minneapolis, MN ▾      ⌕   ★ 29 ││
│╰────────────────────────────────────╯│    │╰────────────────────────────────────╯│
│                                      │    │                                      │
│      ┏━━━━━━━━┓                      │    │    M A P  (≈ 50 %: read a colour     │
│      ┃████████┃ ◂ tapped block,      │    │    up here, find it below)           │
│      ┗━━━━━━━━┛   kept above sheet   │    │                                      │
│                                      │    │                                      │
│                                      │    │ ├──┤ 500 m · 62 cells        © OSM ⓘ │
│      M A P  (≈ 80 %)            ╭───╮│    │──────────────────────────────────────│
│                                 │ ⌂ ││    │                ───                   │
│                                 │ ▒ ││    │ [Zoning]│Roads│Services│Transit│Utils│
│                                 ╰───╯│    │ [OSM│2040│Compare]   Others: ◐ Dim ▾ │
│                                      │    │ RESIDENTIAL                  169,815 │
│ ├──┤ 100 m · 12 cells        © OSM ⓘ │    │ ■ Low Density Housing        161,015 │
│──────────────────────────────────────│    │ ■ Medium Density Row Housing   1,730 │
│                ───                   │    │ ■ Medium Density Housing       6,725 │
│ [Zoning]│Roads│Services│Transit│Utils│    │ ■ Mixed Housing                   40 │
│ ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ │    │ ■ Low Rent Housing               185 │
│ ■ Industrial Manufacturing         ✕ │    │ ■ High Density Housing           120 │
│   landuse=industrial · ≈ 90 cells    │    │ COMMERCIAL                     5,615 │
│   + Hiawatha Ave · Major Road        │    │ … rows 44 px · tap = only this ·     │
│   [Only this]  [⧉ Link]       More ⌃ │    │   long-press = add · drag up = full  │
│                                      │    │                                      │
└──────────────────────────────────────┘    └──────────────────────────────────────┘
```
La hoja completa (drag up) tiene la ciudad (fecha OSM, tamaño en km y en tiles de CS2), el mapa base, la opacidad, `CS2 tile grid`, `Playable area`, `How to use this map in CS2`, `Methodology`, `Request your city`, `Support` y `‹ All cities`.

**Qué cambia (además de la base común):**
- **Un solo eje de visibilidad** (tomado de la propuesta 1 del equipo, como pidieron los dos jueces):
  - Hay siempre una vista activa, elegida en el dock.
  - Un único control, `Others: Color | Dim | Off`, decide qué pasa con el resto. Reutiliza `fondoMode` y `FADE = 0.3`.
  - En `Dim`, la zonificación y las calles para autos quedan al 30 %. Los pines de Services, Transit y Utilities se ocultan, porque un pin atenuado igual ensucia.
  - Peatonales y ciclovías (65k de las 109k líneas) solo aparecen en la vista Roads.
  - `Color` muestra todo, con los pines desde z13 y sin superponerse.
  - No hay combinaciones contradictorias entre dos ejes.
- **La fila de la leyenda es el control:**
  - Click en una fila = `only this` (otro click o `Esc` vuelve a mostrar todo). Ctrl/Shift+click, o mantener apretado en el celular, suma categorías.
  - Click en el título de la familia = aislar la familia.
  - Para ocultar una sola fila (el caso típico es Surface Parking) hay un ojo al final: aparece con el hover en escritorio y es fijo, de 44 px, en táctil.
  - Lo aislado queda en color y el resto en gris al 18 %, como en una info view: la trama no desaparece.
- **Una sola columna:** la ficha `SELECTED` se apila arriba de la leyenda, y la leyenda se pliega a sus encabezados de módulo. En 1280×720 nunca hay dos paneles.
- **Riel de muestras** al plegar (de la propuesta 1):
  - Arranca plegada si el ancho es menor a 1200 o el alto menor a 800.
  - La muestra de la zona bajo el cursor se ilumina.
  - Hover sobre una muestra = su nombre; click = `only`.
- **Dock de ancho fijo, abajo al centro,** con las etiquetas siempre visibles y el atajo 1-5. Nada se corre de lugar. Con 1 módulo no hay dock.
- **Móvil:** una hoja con 3 alturas.
  - Las pestañas de vista van en el encabezado de la hoja: una sola franja, no dos. Como no hay pestaña "All", las 5 entran en 390 px sin scroll.
  - Al tocar una manzana, la respuesta aparece en el peek sin abrir nada.
- **Comparar con el plan oficial:** `Compare` en la cabecera de Zoning dibuja el relleno OSM con el contorno del plan. La ficha muestra las dos zonas y marca `≠` cuando no coinciden (idea de las propuestas 1 y 2).

**Por qué es mejor para un jugador de CS2:**
- **"¿Qué zona va en esta manzana?"** En escritorio, con cero clicks: hover y tooltip. En el celular, un toque, y la respuesta aparece en el peek.
- **"Solo la industria":** 1 click, y `Esc` para volver (hoy son 14 + 14). Queda en la URL.
- **"Trazar las calles":** tecla `2`. Las vías quedan al 100 % y las zonas al 30 %. La ficha de una calle, aunque no tenga nombre, dice `typical in CS2: Medium Road*`.
- **Segundo monitor a media pantalla:** el riel ocupa ≈8 % y `H` deja el mapa limpio.
- **Desde Reddit:** los botones tienen nombre, "Tap any block to see its CS2 zone" está en el peek y `‹ Cities` lleva a otras ciudades.

**Cuánto mapa tapa (estimado):**
- **1440×900 con la leyenda abierta:** ≈21 %, igual que hoy. Pero es un solo panel, sin scroll, que además es el control. Hoy, para filtrar hay que abrir Capas y se llega al 33 %.
- **Con el riel:** ≈8 %.
- **Ciudad de 1 módulo:** ≈14 %.
- **Celular en peek:** ≈19 % con 5 módulos y ≈14 % con 1. Hoy es 12 %, pero con íconos sin nombre.
- **Celular con la hoja a media altura:** 50 % de mapa, contra 7-21 % hoy.

**Costo: L en total, en 4 o 5 PR entregables.** El primero es S y el segundo M (detalle en la sección 4).

**Riesgos:**
1. **Costo de aislar en Minneapolis.** `setFilter` y los cambios de paint que dependen de los datos obligan a reconstruir las teselas de la fuente `cs2`, que comparten zoning y vial. Pasa una vez por click (hoy ya pasa con cada checkbox de Capas y con cada Atenuado), nunca en el hover. Hay que medirlo antes, y probar la idea 9.
2. **"Click = only" rompe la convención de las leyendas**, donde click = ocultar. Lo mitigan la pista de la primera visita, el `cursor:pointer`, el chip `Showing 1 of 13 · Show all` y el ojo por fila.
3. **Gestos de la hoja contra el paneo del mapa en iOS** (`dvh`, `safe-area`): la hoja se arrastra solo desde la manija.
4. **Minneapolis arranca más sobria (Dim).** `Color` está a un click y queda guardado.
5. **`src/shared/thumbnails.py`** clickea `.master-toggle`, oculta `#fondo-control` y `.cs2-layers`, y espera a que el título deje de decir "Cargando". Se rompe en el primer PR si no se migra en ese mismo PR.

---

### B. Info View HUD (la más "juego")

**Concepto:** usar la gramática de CS2 (toolbar grande abajo, panel de info view a la izquierda, ficha de selección a la derecha) para quien planifica manzana por manzana en un segundo monitor.

**Escritorio 1440×900.** Vista Roads, Bike Lane silenciada, una calle seleccionada:
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ╭────────────────────────────────────────────────────────────────────╮             ╭───────────╮ │
│ │ ◈ CS2 OSM Toolkit ‹ 38 cities │ ▦ Minneapolis, MN ▾ │ ⌕ Search   / │             │ ★ Star 29 │ │
│ ╰────────────────────────────────────────────────────────────────────╯             ╰───────────╯ │
│ ╭─ ═ ROADS · 108,859 ──────────────── « ─╮                ╭─ SELECTED ───────────────────── ✕ ─╮ │
│ │ OSM class      typical in CS2*   count │                │ ━ Lyndale Ave S                    │ │
│ │ ━ Highway      Highway           2,450 │                │   Major Road (highway=secondary)   │ │
│ │ ━ Major Road   Large / Medium    3,420 │                │   typical in CS2: Medium Road*     │ │
│ │ ━ Minor Road   Medium / Small   12,394 │                ├────────────────────────────────────┤ │
│ │ ━ Local Street Small Road       25,264 │                │ ALSO HERE                          │ │
│ │ ┄ Pedestrian   Path             61,357 │                │ ■ Medium Density Housing           │ │
│ │ □ Bike Lane    Path  (muted)     3,974 │                │   ≠ 2040 Plan: Low Density Housing │ │
│ │ thicker stroke = bridge                │                │ ✚ Education & Research             │ │
│ │ * suggestion, owner to validate        │                │   Whittier Elementary              │ │
│ │ Show all · Hide all · 1 muted          │                ├────────────────────────────────────┤ │
│ ├────────────────────────────────────────┤                │ [Highlight whole street]           │ │
│ │ Others  [Color│▸Dim│Off]               │                │ [Query on OSM ↗]  [⧉ Copy link]    │ │
│ │   zoning at 30 %, pins hidden          │                │ ▸ OSM tags                         │ │
│ ╰────────────────────────────────────────╯                ╰────────────────────────────────────╯ │
│                                                                                                  │
│                                                                                                  │
│                                                ━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                ▲ whole street highlighted                        │
│                                                                                                  │
│                                                  M A P                                           │
│                                            (≥ 1400 px: SELECTED right;                           │
│                                             < 1400 px: it takes the                              │
│                                             left panel slot instead)                             │
│                                                                                                  │
│       ┌────────┲━━━━━━━━┱──────────┬─────────┬───────────┐ ┌─────┬───────┬─────┬─────┐           │
│       │ ▦    1 ┃ ═    2 ┃ ✚      3 │ ▬     4 │ ϟ       5 │ │ ▒ S │ ▢   F │ ⌂   │ + − │           │
│       │ Zoning ┃ Roads  ┃ Services │ Transit │ Utilities │ │ Sat │ Frame │ Fit │ Zoom│           │
│       └────────┺━━━━━━━━┹──────────┴─────────┴───────────┘ └─────┴───────┴─────┴─────┘           │
│                                                                                                  │
│ ├────┤ 200 m · 25 cells                                                © OpenStreetMap · Esri  ⓘ │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Móvil 390×844.** A la izquierda, peek con chips de color. A la derecha, la ficha de una manzana tocada. La toolbar es el pie de la hoja, no una franja aparte.
```
┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
│╭────────────────────────────────────╮│    │╭────────────────────────────────────╮│
││ ‹  Minneapolis, MN ▾      ⌕   ★ 29 ││    ││ ‹  Minneapolis, MN ▾      ⌕   ★ 29 ││
│╰────────────────────────────────────╯│    │╰────────────────────────────────────╯│
│                                      │    │        ┏━━━━━━━━┓                    │
│                                      │    │        ┃████████┃ ◂ tapped           │
│      M A P  (≈ 76 %)                 │    │        ┗━━━━━━━━┛                    │
│                                      │    │                                      │
│                                      │    │ ├──┤ 100 m · 12 cells        © OSM ⓘ │
│      Frame / Fit / Sat live in       │    │──────────────────────────────────────│
│      the ⋯ of the sheet header       │    │                ───                   │
│                                      │    │ ■ Medium Density Housing           ✕ │
│                                      │    │   Residential · building=apartments  │
│                                      │    │   tagged · ~1,240 m² ≈ 19 cells      │
│                                      │    │   ≠ 2040 Plan: Low Density Housing   │
│                                      │    │ ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ │
│ ├──┤ 500 m · 62 cells        © OSM ⓘ │    │ ALSO HERE                            │
│──────────────────────────────────────│    │ ━ Elm St · Local Street              │
│                ───                   │    │   typical in CS2: Small Road*        │
│ ▦ ZONING · Others: Dim             ⋯ │    │ ✚ Education · Whittier Elementary    │
│ ■LowDens ■Row ■Med ■Mixed ■LowRent ▸ │    │ [Query on OSM ↗]   [⧉ Copy link]     │
│ (swipe chips · tap = mute)           │    │                                      │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│    │━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│┃▦Zoning┃═Roads│✚Servic│▬Trans│ϟUtil  │    │┃▦Zoning┃═Roads│✚Servic│▬Trans│ϟUtil  │
│                                      │    │                                      │
└──────────────────────────────────────┘    └──────────────────────────────────────┘
```

**Qué cambia (además de la base común):**
- **Mismo modelo que A** (vista activa + `Others`), pero **click en una fila = silenciar**: queda gris, como en una info view, y se sigue viendo la manzana. `Only` está siempre visible en el título de cada grupo y, con el hover, en cada fila. Shift+click en un botón de la toolbar oculta el módulo entero.
- **Toolbar al estilo CS2**, con las herramientas agrupadas a su derecha (Sat, Frame, Fit, Zoom). Así quedan 4 regiones en vez de las 6 que criticó el juez.
- **Ficha de planificación a la derecha** (desde 1400 px): por qué se clasificó así, tamaño en celdas, vía de CS2 sugerida, `≠` contra el plan, `Also here`, `Highlight whole street` y `Highlight route`. Por debajo de 1400 px ocupa el lugar del panel izquierdo, así que en 1280 nunca se tapan los dos lados.
- **Vista Roads con la columna `typical in CS2`**, y `Frame`: un cuadrado de 14.336 m con los 23×23 tiles y el botón `Move frame here`, que es más barato que uno arrastrable.
- **Móvil:** la toolbar queda fija en la zona del pulgar, como pie de la hoja. El peek muestra una tira de chips de color que se desliza.

**Por qué es mejor para un jugador de CS2:**
- Es la mejor para **trazar vías y decidir el recorte (T5 y T7):** la tabla OSM → CS2 y el frame de tiles están a la vista.
- Es la que más se parece al juego: el que viene de CS2 la reconoce al instante.
- La ficha de planificación contesta "¿qué pongo acá?" completo, con zona, calle y servicio.

**Cuánto tapa (estimado):**
- **1440 sin selección:** ≈19 %. **Con selección:** ≈29 %.
- **1280:** ≈26 %.
- **Celular en peek:** ≈26 %. Es la más pesada en el celular.

**Costo: L.** El primer PR es M, igual que en A. La ficha de planificación es M y Frame es S-M.

**Riesgos:**
- Hay más superficie fija que en A y la toolbar grande le quita alto al mapa.
- Con "click = silenciar", aislar depende de encontrar `Only`.
- La columna `typical in CS2` es una hipótesis armada sobre `src/vial/classifiers.py`: la tiene que validar el dueño.
- Las miniaturas se rompen igual que en A.

---

### C. Layer Sidebar (GIS acoplado)

**Concepto:** una barra lateral fija, que no flota sobre el mapa, y es a la vez leyenda, control de capas y navegación. Las capas se combinan libremente, con 3 estados por módulo.

**Escritorio 1440×900.** Barra lateral a la izquierda e inspector acoplado a la derecha:
```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       ┃                          ┃                               │
│ ◧ CS2 OSM Toolkit   ‹ All cities      ┃                   ╭───╮  ┃ AT THIS SPOT                ✕ │
│ [▦ Minneapolis, MN ▾ · 16.5×21.1 km]  ┃                   │ + │  ┃ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ [⌕ Search streets & places     / ]    ┃                   │ − │  ┃ ZONE                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ┃                   │ ⌂ │  ┃ ■ Medium Density Housing      │
│ ▾ ▦ Zoning  184,723           [◉]◐ ○  ┃                   ╰───╯  ┃   Residential · ✓ tagged      │
│   [OSM-derived│2040 Plan│Compare]     ┃                          ┃   building=apartments         │
│   RESIDENTIAL                   Only  ┃                          ┃   [Only this zone]            │
│   ■ Low Density Housing      161,015  ┃  ┏━━━━━━━┓               ┃ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│   ■ Medium Density Row Hous.   1,730  ┃  ┃███████┃◂ selected     ┃ ROAD                          │
│   ■ Medium Density Housing     6,725  ┃  ┗━━━━━━━┛               ┃ ━ Lyndale Ave S · Major Road  │
│   … 3 more · COMMERCIAL · OFFICE ·    ┃                          ┃   typical in CS2: Medium Rd*  │
│     INDUSTRIAL · PARKING (open ▸)     ┃                          ┃   [Highlight whole street]    │
│   ┄ dashed = guessed from size ⓘ      ┃                          ┃ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│   [ ] Hide guessed buildings          ┃                          ┃ 2040 PLAN (Compare on)        │
│ ▸ ═ Roads   108,859            ◉[◐]○  ┃    M A P                 ┃ ■ Low Density Housing   ≠     │
│ ▸ ✚ Services  2,272           ◉ ◐[○]  ┃ (nothing floats          ┃ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ ▸ ▬ Transit     297           ◉ ◐[○]  ┃  over it: the map        ┃ [Query on OSM ↗]              │
│ ▸ ϟ Utilities   371           ◉ ◐[○]  ┃  is resized, and         ┃ [⧉ Copy link to this spot]    │
│   ◉ colour · ◐ dim · ○ off            ┃  fitBounds fits          ┃ ▸ OSM tags                    │
│   row click = hide · Only = solo      ┃  the free area)          ┃                               │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ┃                          ┃                               │
│ Base  [▸Dark│Satellite]               ┃                          ┃ docked, opens on click;       │
│ Zoning opacity  ━━━━●──  55 %         ┃                          ┃ < 1440 px: becomes a          │
│ CS2   [ ] Map frame  [ ] Tile grid    ┃                          ┃ 'Selected' tab in the         │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ┃                          ┃ sidebar (one dock only)       │
│ How to use in CS2 · Methodology       ┃                          ┃                               │
│ Request a city · Report a problem     ┃                          ┃                               │
│ ★ Star 29   ♥ Support ▾      [«]      ┃                          ┃                               │
│                                       ┃                          ┃                               │
│                                       ┃                          ┃                               │
│                                       ┃                          ┃                               │
│                                       ┃├───┤ 200 m · 25 cells    ┃                               │
│                                       ┃© OSM · Esri  ⓘ           ┃                               │
│                                       ┃                          ┃                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Móvil 390×844.** A la izquierda, peek con los módulos y su estado. A la derecha, la leyenda a media altura.
```
┌──────────────────────────────────────┐    ┌──────────────────────────────────────┐
│╭────────────────────────────────────╮│    │╭────────────────────────────────────╮│
││ ‹  ⌕ Search Minneapolis…      ★ 29 ││    ││ ‹  ⌕ Search Minneapolis…      ★ 29 ││
│╰────────────────────────────────────╯│    │╰────────────────────────────────────╯│
│                                      │    │                                      │
│                                      │    │    M A P  (≈ 50 %)                   │
│      M A P  (≈ 80 %)                 │    │                                      │
│                                      │    │                                      │
│                                      │    │ ├──┤ 500 m · 62 cells        © OSM ⓘ │
│                                      │    │──────────────────────────────────────│
│                                 ╭───╮│    │                ───                   │
│                                 │ ⌂ ││    │ ▦◉  ═◐  ✚○  ▬○  ϟ○     [Legend│City] │
│                                 │ ▒ ││    │ ▾ ▦ Zoning                    [◉]◐ ○ │
│                                 ╰───╯│    │   [OSM│2040 Plan│Compare]            │
│                                      │    │   RESIDENTIAL                   Only │
│                                      │    │   ■ Low Density Housing      161,015 │
│ ├──┤ 500 m · 62 cells        © OSM ⓘ │    │   ■ Medium Density Row Hous.   1,730 │
│──────────────────────────────────────│    │   ■ Medium Density Housing     6,725 │
│                ───                   │    │   ■ Mixed Housing                 40 │
│  ▦      ═      ✚      ▬      ϟ       │    │   COMMERCIAL                    Only │
│ Zoning Roads  Servic Transit Util    │    │   … rows 44 px · tap = hide          │
│   ◉      ◐      ○      ○      ○      │    │ ▸ ═ Roads                      ◉[◐]○ │
│ tap = colour → dim → off             │    │ ▸ ✚ Services                  ◉ ◐[○] │
│ drag up = legend · ▦ Minneapolis ▾   │    │   ▸ Transit · ▸ Utilities            │
│                                      │    │                                      │
└──────────────────────────────────────┘    └──────────────────────────────────────┘
```

**Qué cambia (además de la base común):**
- **Sin vistas.** Cada módulo tiene `[◉ Colour │ ◐ Dim │ ○ Off]`. Recupera el "Atenuado" por módulo que perdía la propuesta 2 original, que según los jueces es lo que hoy mejor funciona para trazar vías.
- **Click en una fila = ocultar** (la convención de Felt y Google); `Only` por fila y por grupo.
- **La barra está acoplada** (`map.resize()`). El encuadre inicial encaja en el área libre y nada flota encima del mapa salvo el zoom. Plegada queda un riel de 48 px con los íconos y el estado de cada módulo.
- **La barra concentra la navegación y lo secundario:** marca, selector de ciudades con filtro y buscador arriba; How to use, Methodology, Request, Report, ★ Star y Support abajo.
- **Inspector acoplado a la derecha** desde 1440 px; por debajo, pasa a ser una pestaña `Selected` de la barra.
- **Correcciones a la propuesta 2 que marcaron los jueces:**
  - El hover sobre una fila **no** repinta el mapa (reconstruiría teselas en cada hover). Solo funciona al revés: hover en el mapa → fila marcada.
  - La ficha muestra el plan 2040 solo con `Compare` activo, cuando el contorno está visible. No hay una capa oficial dibujada siempre al 0 %.
- **Filtros sin costo**, porque los datos ya están en las teselas: `Hide guessed buildings` (`m=="area"`) y, en La Plata, Mafra y Valparaíso, `Google ML buildings` (`s=="google"`).
- **Valores por defecto a decidir:** Zoning en ◉, Roads en ◐, y los demás en ○.

**Por qué es mejor para un jugador de CS2:**
- Es la única donde se ven **Zoning y Services a todo color a la vez** sin cambiar un modo global.
- Es la más fácil de entender: lo que está prendido se ve y lo que está apagado no.
- Nada tapa el mapa, y el selector de ciudades a mano invita a explorar otras.

**Cuánto tapa:**
- No tapa, achica. La barra se lleva 320 px de ancho: el 22 % en 1440 y el 25 % en 1280.
- En 1440, con el inspector abierto, el mapa queda en el 57 % del ancho.
- Plegada, ≈3 %.
- Celular en peek: ≈21 %.

**Costo: L.** El primer PR es M. El CSS acoplado es más simple que el flotante, pero hay más combinaciones de estado para probar (5 módulos × 3 estados × filtros por fila).

**Riesgos:**
- Se aleja de la estética HUD del juego y se acerca a una herramienta GIS.
- En 1280 el mapa pierde un cuarto del ancho de forma permanente, salvo que se pliegue la barra.
- Sin foco, Minneapolis puede volver a saturarse si alguien prende todo.
- Las miniaturas se rompen igual que en A.

---

## 3. Ideas sueltas (sirven con cualquier layout)

1. Sacar el `"on"` forzado de `transporteLoaded` e `infraestructuraLoaded` (map.html:2338 y 2385), que pisa lo que el usuario guardó.
2. `hash: "map"` en el constructor (map.html:1521-1560). El resto del estado va en el mismo hash, con `replaceState` en `moveend`.
3. Aplicar `DARKEN` solo a `base-dark` y no a `base-dark-ref` (map.html:1543): vuelven a leerse los nombres de calle antes de que exista el buscador.
4. Pines de servicios con `icon-allow-overlap: false` (map.html:2457) y `minzoom` 13 cuando no son el foco.
5. `fitBounds` con `padding.left` igual al ancho del panel (map.html:1548), para que la ciudad no arranque tapada.
6. Un contrato estable para las miniaturas: `#ui=0&view=zoning&ctx=off` más `document.body.dataset.ready`, en el **mismo PR que traduce el título**, porque `thumbnails.py` espera que desaparezca "Cargando".
7. Atribución compacta y cerrada por defecto en el celular (map.html:926), con `© OpenStreetMap` siempre visible en una línea.
8. Probar una capa `fill` por zona, con color constante. Aislar o silenciar pasa a ser un cambio de paint constante, que MapLibre aplica sin reconstruir las teselas; hoy `setFilter` y el `["*", factor, …]` de Atenuado sí las reconstruyen. Medirlo en Minneapolis contra `setFilter` y contra `global-state`.
9. Glifos para los servicios (cruz, birrete, llama, escudo, árbol) en lugar de H/E/B/A/P, `<html lang="en">` y números con `toLocaleString("en-US")`.
10. La ficha de una calle también para calles sin nombre ("Unnamed road · Local Street"), con `Highlight whole street` filtrando por `n` y `k`: un solo `setFilter` por click.

---

## 4. Recomendación de Claude

**Haría A, Clean Map.** De la B tomaría el contenido de la ficha de planificación (tamaño en celdas, vía sugerida, `≠` contra el plan), pero dentro de la columna única de A. De la C, el selector de ciudades y los filtros `Hide guessed` y `Google ML`.

Por qué A:
- Es la que mejor resuelve las dos tareas que más se repiten: "qué zona va acá" (hover o un toque) y "solo la industria" (1 click).
- Es la que menos mapa tapa donde de verdad se usa: media pantalla, segundo monitor y celular.
- Su primer tramo se puede publicar sin tocar la hoja móvil.

**Orden de implementación** (primero lo de más impacto y menos costo):

| PR | Costo | Qué incluye | Qué resuelve |
|---|---|---|---|
| 0. Arreglos que sirven con cualquier layout | **S** | Ideas 1-7 y 9. Fila de confianza honesta (map.html:2152-2164). Filas en 0 agrupadas. El chip pasa a ser el link `‹ Cities`. Todo el texto en inglés. Se borra la status bar. Escala con celdas. Contrato de miniaturas. | Diagnóstico 3 (parte), 6 (parte), 8, 9, 10, 11 (posición) y 12 |
| 1. Un solo control | **M** | Dock armado desde el manifest, con ancho fijo. Vista + `Others` en lugar de las pills, el Fondo y las casillas maestras. Filas-botón (`only` y ojo). Se borra Capas. `hiddenCats` para Transit y Utilities. Botón Satellite con opacidad. **Antes:** medio día de prueba de la idea 8 para medir cuánto cuesta aislar. | 1, 2, 4, 6 y 7 |
| 2. "¿Qué es esto?" | **M** | Hover con `promoteId`, ficha `SELECTED` en la columna con todo lo que hay en el punto, resaltado, `Copy link` y el estado completo en el hash. | 5 y 11 |
| 3. Móvil | **M-L** | Hoja de 3 alturas con las pestañas en el encabezado y la respuesta en el peek. Probar en un iPhone real. | 3 |
| 4. CS2 | **M** | Riel de muestras, `Compare` con contorno y `≠`, frame de 23×23 tiles, buscador (Nominatim con Enter y después un índice local desde `src/`), `typical in CS2` cuando el dueño valide la tabla, atajos y `Hide UI`. | Lo que falta hoy (T7, T2 y T12) |

**Tres decisiones que tiene que tomar el dueño antes del PR 1:**
1. **Vista activa (A/B) o capas libres (C).** Yo voto por la vista activa: es lo que hace el juego y evita que Minneapolis se sature.
2. **Click en una fila = "only" (A) o "ocultar" (B/C).** Yo voto por "only", porque "solo la industria" es mucho más frecuente que "ocultar el parking".
3. **Cómo arranca Minneapolis:** en `Dim` (sobria) o en `Color` (como hoy). Yo voto por `Dim`.

No toqué el repo. Los wireframes se arman con un script que quedó en el scratchpad:
- Script: `C:\Users\osyanne\AppData\Local\Temp\claude\C--Users-osyanne-Documents-Claude-Projects-Proyecto-mineapolis-cs2-minneapolis-zoning\b019c131-7c47-479d-a70c-f508eaab7d12\scratchpad\debate\claude-final\wf.py`
- Salida: `...\debate\claude-final\wf.txt`