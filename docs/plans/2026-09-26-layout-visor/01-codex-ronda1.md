**1. Diagnóstico**

1. **Filtrar y entender el mapa exige recorrer tres controles distintos.** Las pills activan módulos; la leyenda explica categorías y repite los interruptores maestros; el panel derecho permite filtrar esas categorías. En la captura de capas abiertas, ambos paneles consumen unos **540 de los 1440 px de ancho**. Para encontrar industria, primero hay que descubrir dónde se puede actuar sobre la lista. `buildLayersControl` genera checkboxes; `buildLegend` vuelve a generar nombres y colores como filas informativas. Evidencia: [visualizer/map.html:2007](<../../../visualizer/map.html:2007>) y [línea 2083](<../../../visualizer/map.html:2083>).

2. **“Apagado” no describe de forma fiable lo que se ve.** Con “Fondo: Completo”, un módulo apagado sigue dibujándose con intensidad completa; con “Atenuado”, sigue visible. Además, “Fondo” también identifica el selector Dark/Satellite del otro panel. Hay dos conceptos distintos con el mismo nombre. Esto dificulta responder algo básico: “¿qué estoy mirando?”. Evidencia: [visualizer/map.html:1924](<../../../visualizer/map.html:1924>). Transporte e infraestructura también fuerzan su estado a encendido al terminar de cargar, incluso habiendo leído preferencias anteriores: [línea 2337](<../../../visualizer/map.html:2337>).

3. **La vista inicial no establece una jerarquía para construir.** En Minneapolis compiten zonificación, calles, servicios, transporte e infraestructura. Los marcadores y líneas atraviesan las manzanas que el jugador necesita interpretar. Los símbolos de servicios permiten explícitamente superposición entre sí. La captura de Nueva York resulta mucho más legible porque tiene menos información simultánea. Evidencia: capturas de escritorio por defecto y Nueva York; [visualizer/map.html:2453](<../../../visualizer/map.html:2453>). Una primera vista debería priorizar zonificación y conservar las calles como contexto.

4. **En móvil, abrir la explicación prácticamente impide consultar el mapa.** En `10-mobile-legend-toggled.png`, la leyenda ocupa aproximadamente el 80 % del ancho y más del 80 % del alto: cerca de dos tercios de la pantalla. La atribución se superpone al panel. El responsive reduce tamaños y recoloca elementos, pero conserva el catálogo largo de escritorio. Además, los interruptores maestros son `span` de 14 × 14 px con listener de click: no son controles operables por teclado. Evidencia: [visualizer/map.html:901](<../../../visualizer/map.html:901>), [línea 691](<../../../visualizer/map.html:691>) y [línea 1987](<../../../visualizer/map.html:1987>).

5. **Inspeccionar una manzana depende del orden de dibujo.** El click recoge elementos cercanos, los ordena por capa y abre el primer popup disponible. Un servicio puede interceptar la consulta de la zonificación situada debajo. El popup aparece sobre el lugar que se está estudiando y no deja un contorno persistente de selección. La captura de Careerforce muestra esa competencia espacial. Evidencia: [visualizer/map.html:2245](<../../../visualizer/map.html:2245>). Para alternar con el juego hace falta una referencia estable.

6. **Los números tienen demasiada presencia y un significado ambiguo.** Los conteos de la leyenda corresponden al conjunto cargado, no a lo visible. Cambiar a la fuente oficial solo cambia capas: no actualiza esos conteos. La barra inferior llama “polígonos” a una suma que incluye vías y servicios, y sigue diciendo “datos OSM” al consultar el plan oficial. Evidencia: [visualizer/map.html:1978](<../../../visualizer/map.html:1978>), [línea 2214](<../../../visualizer/map.html:2214>) y [línea 2520](<../../../visualizer/map.html:2520>). Para construir importa primero la categoría y su procedencia.

7. **Faltan orientación y continuidad de trabajo.** El nombre de ciudad es un `div` de estado; el enlace destacado lleva a GitHub. No hay regreso al catálogo, escala ni acción visible para recuperar el encuadre. La persistencia guarda módulos y “Fondo”, pero no cámara, categorías, fuente ni mapa base. Evidencia: [visualizer/map.html:974](<../../../visualizer/map.html:974>) y [línea 1963](<../../../visualizer/map.html:1963>). Volver al mismo barrio debería ser parte central del producto.

8. **La interfaz requiere aprender convenciones que podría explicar directamente.** Las etiquetas de módulos están ocultas visualmente y aparecen al hover. Transporte e infraestructura se inyectan siempre, por eso Nueva York y Roscommon muestran candados aunque sus manifests solo tengan zonificación. A esto se suma la mezcla de idiomas. Evidencia: [visualizer/map.html:508](<../../../visualizer/map.html:508>) y [línea 1824](<../../../visualizer/map.html:1824>). En lo visual, la landing adjunta usa negro/violeta y el visor azul de juego: conservaría esa identidad del visor, unificando tipografía, bordes y moderación de efectos.

**2. Tres propuestas de layout**

Los wireframes muestran estados de trabajo, con paneles abiertos o una selección hecha. En las tres mantendría los colores de zonificación y los paneles oscuros de CS2. Los controles salen del manifest; el plan oficial aparece como fuente dentro de `Zoning`. Los módulos ausentes no ocupan botones, y los pendientes muestran `Loading…` o `Retry`.

**A. Atlas de trabajo — Un mapa con una única columna que reúne leyenda, filtros y selección.**

Escritorio, aproximadamente 100 columnas:

```text
+--------------------------------------------------------------------------------------------------+
| < Cities / Minneapolis, MN                                     [Share view] [Map] [More]           |
+--------------------------------+-----------------------------------------------------------------+
| LAYERS                   [<]   |                                                       [+] [-]   |
|                                |                                                                 |
| Zoning                [On v]   |                                                                 |
| Source: [OSM-derived v]         |                                                                 |
|                                |                                                                 |
| Residential              [v]   |                         MAP                                     |
| [x] Low Density Housing [Only] |                                                                 |
| [x] Medium Density Housing     |                    +-----------+                                |
| ...                            |                    | selected  |                                |
| Industrial               [>]   |                    | building  |                                |
|                                |                    +-----------+                                |
| Roads                [Dim v]   |                                                                 |
| Services             [Off v]   |                                                                 |
| Transit              [Off v]   |                                                                 |
| Utilities            [Off v]   |                                                                 |
|--------------------------------|                                                                 |
| SELECTED                   [x] |                                                                 |
| Low Density Housing            |                                                                 |
| OSM tag-classified             |                                                                 |
| [Only this category] [Details] | 0---------200 m               [Fit city]         OSM / Esri [i] |
+--------------------------------+-----------------------------------------------------------------+
```

Móvil, aproximadamente 40 columnas:

```text
+--------------------------------------+
| < Cities  Minneapolis, MN      [More] |
+--------------------------------------+
|                                [+]   |
|                                [-]   |
|                                      |
|                 MAP                  |
|                                      |
|          +-----------+               |
|          | selected  |               |
|          +-----------+               |
|                                      |
| 0------200 m     [Fit] OSM / Esri [i] |
+--------------------------------------+
| [Layers] [Selected 1]         [Close] |
| Zoning                       [On v]  |
| Source: [OSM-derived v]              |
| Residential                     [v]  |
| [x] Low Density Housing       [Only] |
| [x] Medium Density Housing           |
| Roads                       [Dim v]  |
+--------------------------------------+
```

**Qué cambia**

- Una columna de unos **288–304 px**, plegable, reemplaza la leyenda, el panel derecho y las pills. El mapa se encuadra en el espacio disponible.
- Cada fila combina muestra de color, nombre y checkbox. `Only` aísla una categoría; `Restore` recupera la selección anterior. Los grupos se pliegan.
- Cada módulo tiene un estado explícito: `On / Dim / Off`. `Basemap` queda separado dentro de `Map`.
- La selección ocupa una sección estable de la columna; el objeto queda resaltado sobre el mapa. Si coinciden varias entidades, se puede elegir cuál inspeccionar.
- En móvil, una única bandeja inferior arranca plegada. Abierta ocupa como máximo media pantalla; `Layers` y `Selected` comparten esa bandeja.
- Los conteos pasan a una opción secundaria, `City totals`, identificados por fuente.

**Por qué es mejor para jugar**

La misma fila que explica un verde permite aislarlo. Se puede dejar industria visible, calles atenuadas y consultar cada edificio sin saltar entre esquinas. Al volver del juego, la categoría seleccionada sigue en el mismo sitio. Comparar OSM con el plan oficial conserva cámara y filtros.

Con una ciudad de un solo módulo, la columna contiene directamente sus categorías; con seis, los grupos evitan un catálogo interminable.

**Costo: M.** Reutiliza bastante del estado y de los filtros existentes, pero exige fusionar controles y reorganizar la selección.

**Riesgos:** la columna resta ancho en laptop; debe plegarse sin perder estado. La selección persistente necesita identificar correctamente los elementos y sus fragmentos de teselas. La sección de detalle debe tener altura limitada para no desplazar todos los filtros.

---

**B. Mesa de construcción — Una bandeja inferior cambia el mapa según la tarea que estás haciendo en CS2.**

Escritorio:

```text
+--------------------------------------------------------------------------------------------------+
| < Cities / Minneapolis, MN                                           [Share view] [Map] [More]     |
+--------------------------------------------------------------------------------------------------+
|                                                                                       [+] [-]   |
|                                                                                                  |
|                                                                                                  |
|                                              MAP                                                 |
|                                                                                                  |
|                                        +-----------+                                             |
|                                        | selected  |                                             |
|                                        +-----------+                                             |
|                                                                                                  |
| 0---------200 m                                                [Fit city]         OSM / Esri [i]  |
+--------------------------------------------------------------------------------------------------+
| [Zoning *]       [Roads]       [Services]       [Transit]       [Utilities]             [Collapse] |
| Source: [OSM-derived v]                  Context: [Roads - Dimmed v]                               |
+-------------------------------------------------------------------+------------------------------+
| [Residential *] [Commercial] [Offices] [Industrial] [Parking]       | SELECTED                 [x] |
|                                                                   | Low Density Housing          |
| [Low Density] [Row Housing] [Medium Density] [More...]              | OSM tag-classified           |
| [Show all]    [Restore]                                            | [Details]                    |
+-------------------------------------------------------------------+------------------------------+
```

Móvil:

```text
+--------------------------------------+
| < Cities  Minneapolis, MN      [More] |
+--------------------------------------+
|                                [+]   |
|                                [-]   |
|                                      |
|                 MAP                  |
|                                      |
|          +-----------+               |
|          | selected  |               |
|          +-----------+               |
|                                      |
| 0------200 m          OSM / Esri [i]  |
+--------------------------------------+
| Task: [Zoning v]          [Collapse]  |
| [Palette] [Selected 1]               |
| Source: [OSM-derived v]              |
| Group: [Residential v]               |
| [Low Density]    [Row Housing]       |
| [Medium Density] [More...]           |
| [Show all]       [Context]           |
+--------------------------------------+
```

**Qué cambia**

- Desaparecen ambos paneles laterales. Una bandeja inferior de unos **144–176 px** aloja la tarea, su paleta y el detalle seleccionado; plegada deja solo la fila de tareas.
- `Zoning`, `Roads`, `Services`, `Transit` y `Utilities` son vistas de trabajo. Elegir una establece el foco visual y la prioridad de inspección.
- `Context` permite conservar otras capas atenuadas. Por ejemplo, construir transporte con calles visibles y zonificación tenue.
- Las categorías se presentan como una paleta agrupada, cercana al vocabulario del juego. Los nombres completos aparecen dentro de cada opción, aunque aquí estén abreviados.
- En móvil se elige la tarea con un selector rotulado y la paleta usa dos columnas. No se arrastra una barra horizontal para descubrir funciones.
- Con solo zonificación disponible se omite la navegación entre tareas y queda la paleta.

**Por qué es mejor para jugar**

Acompaña una secuencia reconocible: trazar calles, zonificar, ubicar servicios y reproducir transporte. Al elegir `Roads`, las calles ganan protagonismo y prioridad de click. El jugador configura una tarea una vez y puede consultar muchos objetos sin volver a tocar capas.

**Costo: M.** El movimiento del HUD es sencillo; definir y recordar vistas de trabajo coherentes requiere más cuidado.

**Riesgos:** reduce altura útil, especialmente en 1280 × 720. Las combinaciones avanzadas quedan menos expuestas. Cambiar de tarea podría resultar frustrante si borra ajustes manuales: cada tarea debe recordar su configuración y mostrar cuándo fue personalizada.

---

**C. Doble referencia — Dos vistas sincronizadas muestran el mismo lugar con referencias diferentes.**

Escritorio:

```text
+--------------------------------------------------------------------------------------------------+
| < Cities / Minneapolis, MN                                      [Filters] [Share view] [More]      |
+-------------------------------------------------+------------------------------------------------+
| A: [OSM-derived v]                               | B: [Satellite v]                               |
+-------------------------------------------------+------------------------------------------------+
|                                                 |                                                |
|                                                 |                                                |
|                  ZONING MAP                     |                SATELLITE MAP                   |
|                                                 |                                                |
|                                                 |                                                |
|                       +                         |                       +                        |
|                 selected point                  |                 same location                  |
|                                                 |                                                |
|                                                 |                                                |
|                                                 |                                                |
|                                                 |                                                |
| 0-------200 m                                   | 0-------200 m                                  |
+-------------------------------------------------+------------------------------------------------+
| [Linked view: On] [Fit city]                   Legend: [Low Density Housing] [More...]            |
+--------------------------------------------------------------------------------------------------+
| SELECTED: Low Density Housing | OSM tag-classified | [Other features here] [Details]          [x] |
|                                                                                  OSM / Esri [i] |
+--------------------------------------------------------------------------------------------------+
```

Móvil:

```text
+--------------------------------------+
| < Cities  Minneapolis, MN      [More] |
+--------------------------------------+
| [A: OSM-derived *] [B: Satellite]     |
+--------------------------------------+
|                                [+]   |
|                                [-]   |
|                                      |
|              ACTIVE MAP              |
|                                      |
|                  +                   |
|           selected point             |
|                                      |
|                                      |
| 0------200 m          OSM / Esri [i]  |
+--------------------------------------+
| [Filters] [Sources]       [Fit city]  |
| SELECTED                         [x] |
| Low Density Housing                  |
| OSM tag-classified                   |
| [Other features here] [Details]      |
+--------------------------------------+
```

**Qué cambia**

- El espacio principal se divide entre dos mapas con centro y zoom sincronizados.
- La combinación inicial es `OSM-derived` y `Satellite`. Cuando existe, `Official plan` se puede elegir para cualquiera de las dos vistas.
- Los filtros viven en un único panel temporal. La fuente de cada lado permanece siempre rotulada.
- Una selección marca la misma ubicación en ambas vistas y abre una ficha compartida. Las entidades encontradas se presentan por fuente, sin asumir que un edificio OSM corresponde a un único polígono oficial.
- En móvil se muestra **un mapa por vez**: `A/B` cambia la referencia conservando exactamente el encuadre.
- Funciona con una ciudad que solo tenga zonificación porque la segunda referencia puede ser el mapa satelital.

**Por qué es mejor para jugar**

Permite contrastar una categoría sugerida con la forma física del lugar: tamaño de edificios, estacionamientos y distribución de manzanas. También facilita estudiar diferencias entre OSM y un plan oficial sin depender de recordar la vista anterior. Es especialmente útil al reproducir un barrio con detalle.

**Costo: L.** Requiere administrar dos mapas, sincronizar cámara, coordinar selecciones y resolver estados independientes de fuentes.

**Riesgos:** dos mapas pueden aumentar considerablemente el consumo de memoria y renderizado; cada mitad ofrece menos espacio para leer. En móvil se pierde la simultaneidad. La comparación exige explicar que las fuentes representan cosas distintas y pueden cubrir áreas diferentes.

En las tres propuestas, los filtros y la atenuación pueden apoyarse en `applyCategoryFilter` y `setLayerState`; la inspección consulta únicamente elementos renderizados cerca del click. Los conteos provienen de estadísticas existentes. Ninguna interacción necesita recorrer las 300.000 entidades desde el código del HUD.

**3. Ideas sueltas**

- `Fit city` y una escala en metros/pies siempre accesibles para recuperar orientación y estimar distancias.
- `Copy view link` con cámara, fuente y filtros para compartir exactamente el barrio consultado.
- `Resume last view` que restaure también zoom, centro, categorías y mapa base por ciudad.
- `Search this city` mediante un índice estático de nombres y coordenadas preparado durante la extracción.
- `Map info` con cobertura, módulos y fecha `Generated on`; esa fecha no debe presentarse como antigüedad de los datos OSM.
- Un límite discreto de cobertura que ayude a reconocer dónde termina el extracto.
- `Hide controls` para el segundo monitor, con una acción visible para recuperarlos y soporte de `Esc`.
- `All layers hidden — Restore` cuando la configuración deje el mapa sin información temática.

**4. Mi recomendación**

**Haría A, Atlas de trabajo.** Resuelve directamente la fragmentación, conserva la lectura simultánea de mapa y categorías y admite tanto consulta rápida como combinaciones avanzadas. Su adaptación móvil ofrece una única superficie de interacción predecible.

Lo implementaría en este orden:

1. **Corregir significado y reducir ruido — S.** Primera visita con zonificación visible, vías atenuadas y los otros módulos apagados; respetar preferencias posteriores, incluso al terminar cargas. Omitir botones de módulos ausentes. Retirar conteos incorrectos al cambiar de fuente y sacar el total global del centro del mapa.
2. **Agregar orientación inmediata — S.** `Back to cities`, `Fit city`, escala y textos en inglés. Mover `Star` a `More`.
3. **Construir el panel único, incluyendo móvil — M.** Fusionar leyenda y filtros; incorporar `Only / Restore` y estados `On / Dim / Off`; eliminar los controles duplicados y el ajuste global “Fondo”. Resolver bandeja móvil, áreas táctiles de al menos 44 px y controles semánticos en esta misma pieza.
4. **Estabilizar la consulta — M.** Contorno de selección, ficha persistente y elección entre entidades superpuestas. Categoría sugerida primero; procedencia y método de clasificación después.
5. **Guardar el lugar de trabajo y pulir — S/M.** Persistir cámara y filtros, compartir vistas y ajustar contraste, espaciado y efectos. Dejar la búsqueda indexada para una mejora posterior.

Validaría el resultado con cuatro situaciones concretas: aislar industria en Minneapolis, identificar un edificio entre capas superpuestas, consultar Nueva York en 1280 × 720 y usar la leyenda en 390 px manteniendo visible el lugar seleccionado.