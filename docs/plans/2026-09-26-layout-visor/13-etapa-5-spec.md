# Etapa 5 — OSM contra el plan oficial (especificación)

Etapa 5 de la [síntesis](05-sintesis.md): ver a la vez la zonificación derivada de OSM y la
del plan oficial, con las fuentes rotuladas. **Una diferencia no es un error**: OSM dice lo
que está construido hoy y el plan, lo que la ciudad quiere para 2040.

Hoy solo Minneapolis tiene plan (`official_zoning` en su manifest), pero nada de esta etapa
es propio de Minneapolis: cualquier ciudad que sume un `official_zoning` la tiene sola.

Reparto: Codex implementa `visualizer/map.html`. Claude escribe esta spec, el nombre corto
del plan (§2), el test Playwright `tests/visualizer/test_compare.py`, el README, el
CHANGELOG y la verificación.

## 1. Lo que hay hoy

- `Zoning` tiene un selector de fuente de dos botones, `OSM-derived | Official plan`
  (`sourceToggleHtml()`), y se ve una fuente o la otra. Para comparar hay que alternar y
  acordarse.
- El plan de Minneapolis (`datos_zonificacion_official.js`) son **1.309 polígonos de
  distrito**, en 8 de las 13 zonas, que cubren unos 148 km²: la ciudad entera, no el bbox
  (350 km², que llega a los suburbios). Cada polígono guarda solo la zona CS2 (`coords`); el
  código original del plan (`UN2`, `CM2`, …) no está.
- El emisor guarda solo el anillo exterior (sin agujeros): hay **128 distritos dentro de
  otro** de distinta zona (1,6 km²). En un punto así hay dos distritos; el que vale es el
  más chico (§5).
- La zonificación OSM viene en teselas vectoriales: el navegador no tiene todos los
  edificios a la vez, así que esta etapa no calcula diferencias de toda la ciudad (eso
  quedó fuera, §8).

## 2. Nombre corto del plan

El nombre completo (`source_name`, "Mpls 2040 Plan — Primary Land Use") es largo para el
tooltip. El manifest suma un campo opcional, `short_name`:

```json
"official_zoning": {
  "hash": "…",
  "source_name": "Mpls 2040 Plan — Primary Land Use",
  "short_name": "2040 Plan",
  "source_url": "…"
}
```

- Sale de `official_source.short_name` en `cities.json`; `extract-official-zoning` lo pasa
  al manifest (`save_manifest_official_source`, que lo omite si no viene). Para Minneapolis
  se agrega a mano también en su `manifest.json`, igual a lo que escribiría el extractor.
- El visor usa `officialEntry.short_name || "Official plan"`. En esta spec, **«Plan»**
  quiere decir ese nombre corto ("2040 Plan" en Minneapolis) y **«Plan completo»**,
  `source_name`.

## 3. El control

- El selector pasa a tres botones, en este orden:
  `OSM-derived | Official plan | Compare`, con `data-source="osm" | "official" | "compare"`
  y `aria-pressed`. `Compare` lleva `title="OSM-derived zones with the official plan's
  outlines on top"`.
- `Compare` arranca **deshabilitado**, como `Official plan`, y se habilita en
  `officialZoningLoaded`. Si el plan no carga (`officialFailed`), los dos quedan
  deshabilitados y la fuente vuelve a `osm` (como hoy).
- Debajo del selector, **solo en `Compare`**, una clave que rotula las fuentes (en lugar del
  `src-name` de hoy):
  - una muestra rellena + "Fill: OSM-derived" y una muestra con borde + "Outline: «Plan
    completo»";
  - abajo, en gris: "The plan shows what the city intends, not what is built today, so
    differences are expected."
- La leyenda de confianza (`.conf`, el rayado de lo adivinado) se ve en `Compare`: el
  relleno es OSM.
- En pantallas chicas los tres botones entran en una línea a 390 px. Si no entran con esos
  textos, pasan a `OSM | Plan | Compare` (solo en `SMALL_SCREEN`; el `title` no cambia).

### Estado

- `currentZoningSource` / `requestedZoningSource` suman `"compare"`. Mientras el plan carga
  se ve OSM y se conserva el pedido, igual que con `official`.
- URL: `src=compare`. Guardado: `source: "compare"` en `cs2-view-state-<slug>-v2`. Misma
  precedencia de la etapa 4 (URL → guardado → primera visita). Un `src` desconocido se
  ignora. La primera visita sigue en `osm`.
- `Share view` comparte `src=compare` sin cambios (lo arma `writeViewHash`).

## 4. Qué se dibuja

Capas nuevas, todas de la fuente `cs2-official`:

| id | tipo | categorías | estilo |
|---|---|---|---|
| `official-compare-hit` | fill | **sin filtro** | `fill-opacity: 0` (solo para consultar, §5) |
| `official-compare-casing` | line | filtradas | `#000`, ancho 4.5, opacidad 0.6 |
| `official-compare-line` | line | filtradas | `zoneNeon` (color de la zona del plan), ancho 2.5, opacidad 0.95 |

- En `LAYER_ORDER`, después de `official-line` y antes de `zoning-hover`:
  `official-compare-hit`, `official-compare-casing`, `official-compare-line`. Arriba del
  relleno OSM, debajo del contorno de hover y selección.
- "Filtradas" = `addLayerOrdered(…, "zoning")`: comparten `hiddenCats.zoning` con OSM, así
  que las casillas, `Only` y `Restore` afectan a las dos fuentes. `Only Industrial` deja los
  edificios industriales de OSM y los distritos industriales del plan.
- Capas visibles por modo (el resto del módulo, `visibility: none`):

  | modo | visibles |
  |---|---|
  | `osm` | `zoning-fill`, `zoning-line`, `zoning-line-lowconf`, `zoning-hover` |
  | `official` | `official-fill`, `official-line`, `official-hover` |
  | `compare` | las de `osm` + `official-compare-hit`, `official-compare-casing`, `official-compare-line`, `official-hover` |

- `On / Dim / Off` del módulo se aplica a todas las visibles del modo (en `compare`, a las
  dos fuentes). `Off` deja de lado también la consulta.
- Cambiar entre `osm` y `compare` no debe volver a filtrar las teselas OSM: solo cambia la
  visibilidad de las capas del plan.
- **Conteos de la leyenda**: siguen al relleno, o sea los de OSM. Una categoría cuenta como
  vacía (y se agrupa como hoy) solo si está vacía en las dos fuentes.

## 5. Consulta: hover, toque y selección

En `compare`, en cada punto se buscan dos cosas:

- **El edificio OSM** (`zoning-fill`), como hoy, con sus filtros.
- **El distrito del plan** (`official-compare-hit`, sin filtro de categorías). Si hay más
  de uno, gana el de **menor área**: al cargar el plan, cada feature guarda su área
  aproximada (en grados², alcanza para comparar) en una propiedad `a`.

Con eso:

| en el punto | lo principal (título, lo que se resalta) | la línea del plan |
|---|---|---|
| edificio + distrito | el edificio, como hoy | `■ Plan: <zona>`, o `Plan: same zone` si coinciden |
| edificio, sin distrito | el edificio, como hoy | `Outside the <Plan>` (p. ej. "Outside the 2040 Plan") |
| distrito visible, sin edificio | el distrito: `■ <zona>` | meta: `<Plan> · no OSM zone here` |
| nada (o el distrito está en una categoría oculta y no hay edificio) | nada, como hoy | — |

- La línea del plan dice la verdad aunque esa categoría esté oculta: si el edificio es
  industrial (visible) y el distrito es residencial (oculto), igual dice `Plan: Mixed
  Housing`. Lo que no se hace es tomar como **principal** un distrito de una categoría
  oculta.
- "Outside" solo cuando de verdad no hay distrito (`official-compare-hit` no devuelve nada).
- `■` es la muestra de color (`areaSwatch`) de la zona del plan, con el color neón.
- La fila de la columna que se marca al pasar el mouse (`is-hover`) es la de lo principal.

### Selección (`Selected`)

- Click en un edificio: la ficha de hoy, más una fila **`<Plan>`** con la muestra y la zona
  del plan (o "Same zone as OSM-derived" / "Outside the <Plan>"), y debajo, en gris, el
  «Plan completo». El edificio queda seleccionado como hoy y **el distrito también**
  (`feature-state` `selected` en `cs2-official`, que dibuja `official-hover`), para que se
  vea de dónde sale la respuesta.
- Click donde hay solo distrito (visible): se selecciona el distrito; la ficha dice la zona,
  "<Plan> · no OSM zone here" y el «Plan completo». `Only this zone` funciona igual que hoy.
  `Explore on OSM` queda.
- En el hover se resalta solo lo principal (no el edificio y el distrito a la vez).
- En el celular, el toque hace lo mismo que el click y la respuesta aparece en la bandeja
  plegada, como hoy.

### Textos

Nada de "error", "wrong", "mismatch", "incorrect" ni "conflict" en la interfaz; tampoco rojo
ni `≠` para marcar diferencias. La diferencia se ve en las dos muestras de color.

## 6. Convivencia

- **Export PNG**: exporta lo que está en pantalla, contornos y borde oscuro incluidos;
  `official-compare-hit` va en la lista de capas omitidas. La atribución suma el «Plan
  completo» (ya lo hace para las capas `official-*`). Un PNG transparente con todas las zonas
  ocultas sigue vacío también en `compare`.
- **Measure, buscador, recuadro jugable**: sin cambios. Con Measure activo, el click no
  selecciona (como hoy).
- **`Official plan`**: igual que hoy.
- **Miniaturas**: sin cambios (usan la fuente inicial).
- **Rendimiento**: 1.309 contornos más; nada que medir aparte. Cambiar de modo no reprocesa
  teselas (§4).

## 7. Verificación (Claude)

`tests/visualizer/test_compare.py`, marcado `network` + `browser`, a mano y fuera del CI
como los anteriores, contra Minneapolis.

1. Tres botones; `Compare` deshabilitado hasta que carga el plan; habilitado después.
2. En `compare`, la tabla de capas visibles de §4; en `osm` y `official`, las suyas.
3. `src=compare` en la URL abre en `compare`; se guarda y sobrevive a la recarga; un link con
   `src=compare` mientras el plan carga queda pedido y se aplica al cargar; `Share view` lo
   incluye.
4. `Only Industrial` filtra las dos fuentes; `official-compare-hit` no se filtra.
5. `Dim` y `Off` afectan a las dos fuentes; con `Off` no hay consulta.
6. Hover sobre un edificio cuya zona difiere de la del plan: dos líneas con las dos zonas.
   Sobre uno que coincide: "same zone". Sobre uno fuera de la ciudad: "Outside the 2040 Plan".
7. Hover sobre un lote sin edificio dentro de un distrito: el distrito como principal, con
   "no OSM zone here".
8. En un punto con dos distritos anidados, gana el más chico.
9. Click en un edificio: fila del plan en la ficha y el distrito con `selected`.
10. Export PNG en `compare`: la atribución nombra el plan; transparente con todo oculto,
    vacío.
11. 390 × 844: el selector entra en una línea y el toque muestra las dos zonas en la bandeja.
12. Ningún texto visible de la interfaz contiene las palabras prohibidas de §5.

Además, `tests/shared/test_official_source_in_manifest.py` suma el caso de `short_name`
(se escribe si viene, se omite si no).

## 8. Fuera de esta etapa

- **Ver solo dónde difieren**: un filtro que deje los edificios OSM cuya zona no coincide
  con el plan. Necesita la zona del plan por edificio en las teselas (`src/`, re-extraer).
- **Categoría original del plan** ("CM2 Corridor Mixed Use → Low Density Commercial") en la
  ficha: necesita volver a bajar el plan, y la `DATA_URL` de
  `src/official_zoning/sources/minneapolis.py` hoy responde 500.
- Agujeros y multipolígonos completos en el emisor (hoy, anillo exterior y la parte más
  grande): el "gana el más chico" de §5 lo cubre para la consulta.
- Pantalla partida o deslizable (descartada en la síntesis).

## Decisiones del dueño (2026-10-13)

- Alcance: contorno del plan sobre el relleno OSM, con hover y ficha que dicen las dos
  zonas. Ni el filtro de diferencias ni la categoría original entran en esta etapa.
- El contorno va con el color de la zona del plan, con un borde oscuro debajo; sin rótulos
  dentro de los distritos.
- El selector suma un tercer botón, `Compare`; `On/Dim/Off` y los filtros por categoría
  afectan a las dos fuentes; los conteos siguen a OSM.
- La consulta funciona también donde no hay edificio (el distrito del plan) y avisa cuando
  un edificio está fuera del plan.
