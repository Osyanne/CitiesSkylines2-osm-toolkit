Recomiendo **Atlas compacto**: mantener la columna única de mi propuesta, incorporar el hover y la respuesta inmediata en móvil de Claude, y reducir el alcance inicial. Su diagnóstico aporta hallazgos importantes, pero algunos números y costos están inflados o mal fundamentados.

**1. Verificación**

Revisé los 38 manifests, el código y las capturas. Las referencias `L…` corresponden a [visualizer/map.html](<C:/Users/osyanne/Documents/Claude/Projects/Proyecto mineapolis/cs2-minneapolis-zoning/visualizer/map.html>). No repetí las mediciones del DOM ni hice benchmarks.

| Afirmación de Claude | Veredicto y evidencia |
|---|---|
| **33 ciudades tienen solo `zoning`.** | **Cierta.** Otras tres agregan `external_buildings`; Chicago tiene tres módulos y Minneapolis seis. Son **36/38 = 94,7 %** con una sola familia temática visible: zonificación. Ese porcentaje describe ciudades, no tráfico ni frecuencia de uso. |
| **El tooltip queda recortado por `overflow`.** | **Cierta.** `overflow-x:auto` en L430 hace que el otro eje compute `auto`; el tooltip se coloca debajo en L520. La captura `audit-13` coincide con ese mecanismo. [Especificación CSS](https://www.w3.org/TR/css-overflow-3/#overflow-properties). |
| **Los botones “no tienen nombre”.** | **Exagerada.** Les falta nombre **visible**, pero tienen `aria-label` y texto para lectores de pantalla, L1800–1804. Además, `unlockPill()` añade `title`, L1821: no lo tienen exclusivamente los deshabilitados. |
| **La barra se corre 149 px.** | **El corrimiento es real.** Está anclada a la derecha, L424, y agrega `Fondo` al apagar el primer módulo, L1959. Las capturas `audit-12/13` muestran el desplazamiento. **149 px es una medición de esa configuración**, dependiente del contenido y las fuentes; no una constante del diseño. |
| **La leyenda móvil tapa el 79 %.** | **Incorrecta como porcentaje de la leyenda.** Con sus propias medidas: `320×704 / (390×844) = 68,4 %`. El 79 % podría aproximar el conjunto del HUD. La obstrucción y la atribución superpuesta sí son reales, visibles en la captura 10. |
| **Los tres controles no se sincronizan.** | **Falsa como afirmación general.** Pills y casillas maestras llaman a `toggleModule()` y se sincronizan mediante `syncUI()`, L1941–1968. Lo cierto: ocultar categorías no cambia la apariencia de sus filas en la leyenda. |
| **Aislar industria requiere desmarcar otras 14 zonas.** | **Falsa.** `ZONES` contiene **13 categorías, incluido parking**, L1251–1270: son **12 casillas restantes**, más abrir el panel y resolver otros módulos encendidos. Yo también repetí ese error en la ronda 1. |
| **Hay candados permanentes en 36 ciudades.** | **Son 37.** Solo Minneapolis tiene transporte e infraestructura; Chicago tampoco los tiene. Ambos botones se crean incondicionalmente, L1828–1829. |
| **La carga secundaria pisa preferencias y falla silenciosamente.** | **Cierta.** Fuerza `"on"` en L2338 y L2385; los fallos de descarga solo generan `console.warn`, L1122. |
| **Hay 2.272 pines de servicios.** | **Falsa.** Conté **281 puntos y 1.991 polígonos** en `datos_servicios.js`. El total sí es 2.272. La superposición permitida y el mínimo z11 son ciertos, L1319 y L2453–2458. La saturación visual existe, pero no por 2.272 pines. |
| **No hay hover y el popup solo muestra lo de arriba.** | **Esencialmente cierta.** Hay hover para cambiar el cursor, L2273, pero no tooltip ni resaltado. El click devuelve el primer elemento con popup según orden de dibujo, L2259–2266. Las calles sin nombre se descartan expresamente, L1412. |
| **La leyenda de confianza no representa el mapa.** | **Cierta.** Sus muestras azul/verde/marrón, L2152–2164, no corresponden a la codificación cartográfica: esta usa opacidad y borde discontinuo para `m=="area"`, L1616–1625. |
| **Las miniaturas se rompen al traducir “Cargando”.** | **Exagerada.** La dependencia existe, pero el predicado también espera que desaparezca el overlay. **Traducir solo el título no basta para romperlo.** Quitar `.master-toggle` sí rompe su mecanismo para apagar módulos. Véase [thumbnails.py:104](<C:/Users/osyanne/Documents/Claude/Projects/Proyecto mineapolis/cs2-minneapolis-zoning/src/shared/thumbnails.py:104>). |

También confirmé:

- **Falta navegación al catálogo durante el uso normal:** el chip es un `div`, L975.
- **No persiste cámara, filtros, fuente ni mapa base:** se guardan módulos y `Fondo`, L1968 y L1975.
- **Los conteos siguen siendo OSM al cambiar a oficial:** `setZoningSource()` no los actualiza, L1978.
- **“295.854 polígonos” está mal:** suma zonificación, segmentos viales y servicios, L2474.
- **Las etiquetas del fondo también se oscurecen:** `base-dark-ref` recibe `DARKEN`, L1543.
- **Idioma mezclado y controles maestros inaccesibles por teclado:** los maestros son `span`, L2084.

No ratifico como mediciones propias los **77/54 px**, el **34 % de contenido visible** ni los contrastes del anexo. Las capturas respaldan los problemas, pero no reemplazan esas mediciones.

**2. Crítica a las propuestas de Claude**

1. **`Clean Map` conserva demasiados lugares de interacción.** Cabecera, columna, dock inferior, satélite separado y controles de navegación. El dock y los encabezados de módulo repiten navegación. Además, `fitBounds` con padding mejora el encuadre inicial; el panel flotante sigue tapando información cuando paneás.

2. **`Others: Dim` vuelve a esconder reglas.** Atenúa zonificación y calles, oculta pines y elimina determinadas vías. La palabra *Dim* termina significando tres comportamientos. Tampoco permite una combinación sencilla como **zonificación y servicios encendidos, calles atenuadas y transporte apagado**. Los estados por módulo resuelven eso directamente.

3. **`Click = only` sacrifica previsibilidad por una frecuencia supuesta.** No hay datos que demuestren que aislar sea mucho más frecuente que ocultar. Añadir ojo, Ctrl, Shift y pulsación larga complica la interacción. Un botón `Only` visible también permite aislar con un click, sin cambiar el significado del resto de la fila. `Restore` debe recuperar la configuración anterior; `Show all` no equivale a deshacer.

4. **La ficha promete información que hoy no tiene.** Las teselas conservan categoría, nombre, método, fuente y confianza; **no conservan tags como `building=apartments`, área completa ni ID vial**. Véase [tiles.py:108](<C:/Users/osyanne/Documents/Claude/Projects/Proyecto mineapolis/cs2-minneapolis-zoning/src/shared/tiles.py:108>). Calcular área sobre geometrías recortadas puede dar un fragmento del edificio. Filtrar calles por nombre y categoría puede unir calles distintas o dejar partes afuera. Esto requiere trabajo de datos, no solamente maquetación.

5. **“Filtros sin costo” contradice su propio análisis de rendimiento.** Sí están disponibles `m` y `s`; eso evita extraer nuevos atributos. Pero cambiar filtros y ciertas expresiones de pintura provoca reprocesamiento de la fuente en MapLibre 5.24. Una capa por zona tampoco elimina automáticamente la opacidad dependiente de confianza. Mediría antes de multiplicar capas. [Código de MapLibre](https://github.com/maplibre/maplibre-gl-js/blob/v5.24.0/src/style/style.ts#L1186), [actualización de pintura](https://github.com/maplibre/maplibre-gl-js/blob/v5.24.0/src/style/style_layer.ts#L259).

6. **Su PR 0 no es S; su PR 4 contiene varias funcionalidades.** Traducción completa, contrato de miniaturas, URL, escala, iconografía y carga merecen separación. Búsqueda, comparación y grilla tampoco deberían compartir una estimación M. Además, Nominatim con Enter no resuelve por sí solo la dependencia: el límite público se aplica al tráfico agregado de la aplicación. [Política de Nominatim](https://operations.osmfoundation.org/policies/nominatim/).

Sobre las alternativas: **B agrega demasiado HUD para el problema actual. C es la más cercana a una solución sólida**, pero le quitaría el segundo inspector y la exposición permanente de todos los enlaces secundarios.

**3. Qué concedo**

- **Hover con categoría y contorno:** responde mejor que mi ronda 1 a la consulta repetida de edificios. Lo adopto; el hover no reemplaza una selección fijada.
- **Respuesta en la bandeja móvil plegada:** tocar un edificio debe mostrar su categoría sin obligar a abrir la leyenda.
- **Mayor atención a ventanas pequeñas:** adoptaría el plegado inicial en ventanas estrechas, conservando después la preferencia del usuario.
- **Confianza, errores de carga y miniaturas:** Claude detectó dependencias que mi primera propuesta trató superficialmente.
- **Mi costo global M era optimista.** El conjunto completo es **L**, aunque se pueda entregar por partes.

**4. Qué sostengo**

- **Una sola superficie para leyenda, filtros y selección.**
- **`On / Dim / Off` por módulo**, con significados consistentes. Primera visita: zonificación `On`, calles `Dim`, resto `Off`.
- **Checkbox para visibilidad; `Only` explícito; `Restore` reversible.**
- **Selección estable en la misma columna**, sin un segundo panel lateral.
- **Conteos secundarios:** `City totals` dentro de información, identificados por fuente.
- **Procedencia honesta:** diferencia entre OSM y un plan futuro no significa error. `Generated on` tampoco significa fecha del relevamiento OSM.
- **Móvil incluido al sustituir los controles**, aunque los gestos sofisticados lleguen después.

**5. Recomendación revisada: Atlas compacto**

En escritorio, columna acoplada de **aproximadamente 300 px**, plegable mediante un control rotulado `Layers`. El mapa ocupa el espacio restante. Mantendría los paneles oscuros y colores CS2.

La columna contiene módulos disponibles, categorías y una ficha breve de selección al pie. Los nombres largos pueden ocupar dos líneas. El detalle ampliado usa esa misma columna. Con solo zonificación desaparece toda navegación entre módulos.

Escritorio, aproximadamente 100 columnas:

```text
+--------------------------------------------------------------------------------------------------+
| < Cities  Minneapolis, MN                         [Share view] [Satellite] [Fit city] [More]       |
+-------------------------------------+------------------------------------------------------------+
| LAYERS                   [Collapse] |                                                 [+] [-]    |
|                                     |                                                            |
| v Zoning                    [On v]  |                                                            |
|   Source: [OSM-derived v]            |                                                            |
|                                     |                                                            |
|   v Residential             [Only]  |                                                            |
|   [x] Low Density Housing   [Only]  |                         MAP                                |
|   [x] Medium Density Housing        |                                                            |
|   > Commercial              [Only]  |                                                            |
|   > Offices                 [Only]  |             +-------------------+                          |
|   > Industrial              [Only]  |             | selected building |                          |
|   > Parking                 [Only]  |             +-------------------+                          |
|                                     |                                                            |
| > Roads                    [Dim v]  |                                                            |
| > Services                 [Off v]  |                                                            |
| > Transit                  [Off v]  |                                                            |
| > Utilities                [Off v]  |                                                            |
|-------------------------------------|                                                            |
| SELECTED                    [Clear] |                                                            |
| Medium Density Housing              |                                                            |
| OSM tag-classified                  |                                                            |
| [Also here (2)] [Details]            | 0-----200 m               OpenStreetMap / Esri [i]          |
+-------------------------------------+------------------------------------------------------------+
```

En móvil, una bandeja inferior tiene **dos estados iniciales: resumen y media pantalla**. El resumen muestra la selección; la bandeja abierta permite filtrar con scroll interno. Botones de expansión y cierre siempre disponibles, sin exigir arrastrar.

Móvil, aproximadamente 40 columnas; bandeja abierta:

```text
+--------------------------------------+
| < Cities Minneapolis, MN      [More] |
|                                      |
|                                [+]   |
|                                [-]   |
|                                      |
|                 MAP                  |
|                                      |
|         +------------------+         |
|         | selected building|         |
|         +------------------+         |
|                                      |
| 0----200 m       [Fit] [Satellite]   |
| OpenStreetMap / Esri [i]             |
+--------------------------------------+
| [Layers] [Selected 1]     [Collapse] |
|                                      |
| v Zoning                    [On v]  |
| Source: [OSM-derived v]              |
|                                      |
| v Residential               [Only]  |
| [x] Low Density Housing     [Only]  |
| > Industrial                [Only]  |
| > Roads                    [Dim v]  |
| > Services                 [Off v]  |
| ...                                  |
+--------------------------------------+
```

`Only` actúa sobre las categorías de su módulo y conserva el contexto de los demás. Al activarlo aparece `Showing 1 of 13 zones · Restore`. Los módulos ausentes no aparecen; los fallidos ofrecen `Retry`. `More` reúne información, ayuda, metodología y apoyo al proyecto.

| Etapa | Costo | Entrega |
|---|---|---|
| **0. Corregir fallos actuales** | **S** | Respetar preferencias durante cargas tardías; quitar candados de módulos ausentes; corregir tooltip y desplazamiento de barra. |
| **1. Orientación y lenguaje** | **M** | Inglés completo, `Cities`, `Fit city`, escala métrica, confianza coherente, retiro del total engañoso y contrato explícito de miniaturas/carga. |
| **2. Panel único, escritorio y móvil** | **L** | Fusionar controles; estados por módulo; `Only / Restore`; categorías vacías agrupadas; bandeja de dos alturas y controles accesibles. Medir filtros antes de cambiar la estructura de capas. |
| **3. Inspección** | **M** | Hover, selección persistente y ficha con entidades visibles coincidentes, sin duplicados de teselas. Usar información realmente disponible; no prometer área ni calle completa. |
| **4. Continuidad** | **M** | Cámara, fuente, filtros y mapa base compartibles. Precedencia explícita: URL → preferencias guardadas → valores iniciales. |
| **5. Comparación** | **M** | OSM y contorno del plan, con fuentes rotuladas. Mostrar diferencias sin calificarlas automáticamente como errores. |
| **6. Nuevos datos y herramientas** | **L** | Búsqueda indexada, áreas completas y herramientas de escala CS2 como entregas independientes. No condicionan el rediseño. |

Validaría especialmente `Only / Restore` en Minneapolis, Nueva York a 1280×720, Little Rock por su anchura y la selección visible a 390 px. Para rendimiento incluiría **Yogyakarta: tiene 520.689 elementos de zonificación**, por encima del supuesto de 300.000 del brief.

No modifiqué archivos.