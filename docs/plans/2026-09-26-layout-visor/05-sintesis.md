# Síntesis del debate Claude ↔ Codex: layout del visor de ciudad

Dos rondas: propuestas independientes (`01`, `02`) y críticas cruzadas con verificación
contra el código (`03`, `04`). Terminamos en un layout común, el **Atlas compacto**, con
pocas diferencias que decide el dueño.

## El dato que ordena todo

De 38 ciudades, **33 tienen solo `zoning`**, 3 tienen `zoning + external_buildings`,
Chicago tiene 3 módulos y **solo Minneapolis tiene los 6** (verificado en los manifests
por los dos). El layout actual está pensado para Minneapolis. El nuevo tiene que verse
bien primero con un solo módulo, y los demás controles aparecen solo si la ciudad los
tiene.

## Layout acordado: Atlas compacto

**Una sola columna a la izquierda** que junta leyenda, filtros y selección, en lugar de
las 4 superficies de hoy (pills, "Fondo", leyenda, panel Capas).

Escritorio (1440×900, Minneapolis):

```text
+--------------------------------------------------------------------------------------------------+
| < Cities   Minneapolis, MN                        [Share view] [Satellite] [Fit city] [★ 29] [More] |
+-------------------------------------+------------------------------------------------------------+
| LAYERS                         [«]  |                                                   [+] [-]  |
|                                     |                                                            |
| v Zoning                     [On v] |                                                            |
|   Source: [OSM-derived | 2040 Plan] |                ┏━━━━━━━━━┓                                 |
|   v Residential              [Only] |                ┃▒▒▒▒▒▒▒▒▒┃ ╭──────────────────────────╮    |
|     [x] ■ Low Density Housing  161k |                ┗━━━━━━━━━┛ │ ■ Medium Density Housing │    |
|     [x] ■ Medium Density Hous.  6.7k|                            ╰──────────────────────────╯    |
|     ...                             |                hover: contorno + tooltip, fila marcada     |
|   > Commercial               [Only] |                                                            |
|   > Offices                  [Only] |                          MAP                               |
|   > Industrial               [Only] |                                                            |
|   > Parking                  [Only] |                                                            |
|   ┄ faint + dashed = guessed    (i) |                                                            |
|                                     |                                                            |
| > Roads                     [Dim v] |                                                            |
| > Services                  [Off v] |                                                            |
| > Transit                   [Off v] |                                                            |
| > Utilities                 [Off v] |                                                            |
|-------------------------------------|                                                            |
| SELECTED                    [Clear] |                                                            |
| ■ Medium Density Housing            |                                                            |
| OSM tag-classified                  |                                                            |
| Also here: Lyndale Ave S · Major Rd | 0-----200 m                    © OpenStreetMap · Esri (i)  |
+-------------------------------------+------------------------------------------------------------+
```

En una ciudad de un solo módulo, la columna es directamente la lista de zonas: sin
módulos, sin `On/Dim/Off`, sin candados.

Móvil (390×844): una bandeja inferior con dos alturas, sin depender de gestos:

```text
+--------------------------------------+    +--------------------------------------+
| < Cities  Minneapolis, MN     [More] |    | < Cities  Minneapolis, MN     [More] |
|                               [+][-] |    |                               [+][-] |
|                                      |    |                                      |
|      ┏━━━━━━━━┓                      |    |            MAP (~50 %)               |
|      ┃████████┃ ◂ manzana tocada     |    |                                      |
|      ┗━━━━━━━━┛                      |    | 0----200 m  [Fit] [Satellite]  © (i) |
|                                      |    +--------------------------------------+
|            MAP (~80 %)               |    | [Layers] [Selected]       [Collapse] |
|                                      |    | v Zoning                     [On v] |
| 0----200 m  [Fit] [Satellite]  © (i) |    |   v Residential              [Only] |
+--------------------------------------+    |   [x] ■ Low Density Housing          |
| ■ Medium Density Housing          ✕ |    |   > Industrial               [Only] |
| OSM tag-classified   [Layers ⌃]      |    | > Roads                     [Dim v] |
+--------------------------------------+    +--------------------------------------+
   resumen: la respuesta al tocar           media pantalla: filtros con scroll
```

### Decisiones acordadas

| Tema | Acuerdo | De quién vino |
|---|---|---|
| Superficie de control | Una columna. Se borran las pills, el select "Fondo", las casillas maestras y el panel Capas. | Los dos |
| Visibilidad | `On / Dim / Off` **por módulo**, con significado fijo. Reemplaza el "Fondo" global, que hoy deja los módulos "apagados" dibujados al 100 %. | Codex (Claude cedió su "vista activa + Others") |
| Aislar | Checkbox por categoría + botón `Only` visible (por fila y por grupo). Aparece `Showing 1 of 13 zones · Restore`, y `Restore` vuelve a la configuración anterior. | Codex (Claude cedió "click en la fila = only") |
| "¿Qué zona va acá?" | **Hover en escritorio**: contorno + tooltip + fila marcada, sin clickear. En el celular, tocar y ver la respuesta en la bandeja plegada. | Claude (Codex lo adoptó) |
| Selección | Fija, con contorno, en el pie de la columna. `Also here` lista lo que hay en el punto en vez de mostrar solo lo de arriba. | Los dos |
| Columna | Acoplada (~300 px), plegable. Arranca plegada en ventanas chicas (menos de ~1200×800) y después respeta la preferencia. | Codex (acoplada) + Claude (plegado inicial) |
| Primera visita | Zoning `On`, Roads `Dim`, el resto `Off`. | Los dos |
| Módulos | Solo los del manifest. Si falla la carga, `Couldn't load · Retry`. Nada de candados eternos. | Los dos |
| Orientación | `‹ Cities`, `Fit city`, escala, `Share view` (estado en la URL), todo en inglés, atribución compacta en el celular. | Los dos |
| Estética | Se conservan los paneles oscuros y los colores de CS2. | Los dos |
| Descartado | Pantalla dividida (ya existió y se sacó en `358b1e3`), bandeja inferior grande en escritorio (se come el alto), dock de vistas (repite la columna). | Los dos |

### Lo que queda para el dueño

1. **Conteos en la leyenda.** Claude: dejarlos en gris y chicos (dicen qué mezcla tiene la
   ciudad), y sacarlos en el celular. Codex: moverlos a `City totals`. Los dos coinciden
   en que hay que corregirlos: no cambian al pasar al plan oficial, y la status bar llama
   "polígonos" a las calles.
2. **Herramientas propias de CS2**, cuáles y cuándo: escala en celdas de 8 m, recuadro del
   mapa jugable (23×23 tiles) para decidir qué parte de la ciudad entra, y tipo de vía
   CS2 sugerido por clase OSM. Esta última tabla la tiene que validar el dueño. Van
   después del rediseño y no lo condicionan.
3. **Buscador.** Nominatim acotado al bbox (barato, pero comparte el límite público entre
   todos los usuarios del sitio) o un índice propio generado en la extracción (L, toca
   `src/`).

## Errores que corrigió el debate

Verificados contra el código:

- Son **13 zonas** (incluido parking), no 15: aislar industria hoy cuesta 12 clicks, no 14.
  Los dos lo teníamos mal.
- Minneapolis tiene **281 pines** de servicios y 1.991 polígonos, no 2.272 pines.
- La leyenda abierta en el celular tapa ~68 % de la pantalla, no 79 %.
- Las pills sí sincronizan con las casillas maestras (`syncUI`). Lo que no se sincroniza
  es el panel Capas con las filas de la leyenda.
- **Las teselas solo guardan categoría, id, nombre, método, fuente y confianza**
  (`src/shared/tiles.py`). La ficha no puede mostrar `building=apartments`, área completa
  ni "la calle entera" sin trabajo de datos. Lo que sí puede: zona, nombre, método,
  confianza y fuente.
- Las miniaturas (`src/shared/thumbnails.py`) se rompen al sacar `.master-toggle`,
  `#fondo-control` y `.cs2-layers`, no por traducir el título. Hay que migrarlas en el
  mismo PR que cambia los controles.
- Candados que nunca se abren: en **37 ciudades**, no 36 (Chicago tampoco tiene esos
  módulos).
- Yogyakarta tiene **520.689** features de zonificación: la prueba de rendimiento va con
  esa ciudad, no con Minneapolis.

## Plan por etapas

| Etapa | Costo | Qué entra |
|---|---|---|
| **0. Bugs** | S | Respetar el estado guardado cuando cargan transporte e infraestructura (`map.html:2338`, `2385`). No crear pills de módulos ausentes (`1828-1829`). Arreglar el tooltip recortado y el corrimiento de la barra. |
| **1. Orientación y lenguaje** | M | Todo en inglés (`<html lang="en">`, "Fondo", "Red vial", popups, "polígonos"). `‹ Cities`, `Fit city`, escala. Leyenda de confianza que coincida con el mapa. Sacar el total engañoso. `DARKEN` solo en `base-dark`, para que se lean los nombres de calle. Atribución compacta en el celular. Contrato de miniaturas. |
| **2. Columna única (escritorio y móvil)** | L | Fusionar controles, `On/Dim/Off`, `Only/Restore`, agrupar las categorías vacías, bandeja de dos alturas, controles accesibles (44 px, teclado). **Antes:** medir en Yogyakarta y Minneapolis cuánto cuesta aislar con `setFilter`. |
| **3. Inspección** | M | Hover con `promoteId` + `feature-state`, selección fija, `Also here` sin duplicados de teselas. Solo con los datos que tienen las teselas. |
| **4. Continuidad** | M | Cámara, fuente, filtros y mapa base en la URL, más `Share view`. Precedencia: URL → estado guardado → valores iniciales. |
| **5. OSM vs plan oficial** | M | Contorno del plan sobre el relleno OSM, con las fuentes rotuladas. Una diferencia no es un error. |
| **6. Extras CS2 y buscador** | L | Celdas de 8 m, recuadro de tiles, vía sugerida, buscador. Entregas independientes. |

Validar con cuatro casos: aislar industria en Minneapolis, identificar un edificio entre
capas superpuestas, Nueva York en 1280×720 y la selección visible en 390 px.
