# Etapa 3 — inspección (especificación)

Sale de `05-sintesis.md` (etapa 3). Borrador de Claude criticado por Codex el
2026-09-27; esta versión incorpora sus correcciones. Reparto por rol: **Codex implementa
todo en `visualizer/map.html`**; Claude verifica con Playwright, revisa el diff y escribe
CHANGELOG y documentación.

## 1. Identidad de las features

- Se guarda `{source, sourceLayer, id}`, nunca la geometría (viene recortada por tesela)
  ni `layer.id`.
- `cs2` (vectorial): `promoteId: { zoning: "id" }`. `cs2-zoning` (GeoJSON, ciudades sin
  teselas): `promoteId: "id"`. `cs2-official`: `generateId: true` (sus props `{k, i}` no
  identifican: `i` reinicia por categoría; el dato es estático, sin `setData`).
- Los `id` de zoning son enteros OSM **o** strings (`g123` Google, `ms123` Microsoft).
  MapLibre acepta strings con `promoteId`. Comprobar que ningún entero pasa de
  `Number.MAX_SAFE_INTEGER`.
- Calles: sin id (ni nativo MVT). Solo se describen; no se resaltan.

## 2. Hover (escritorio: `(hover: hover) and (pointer: fine)`)

- `feature-state` `hover` en la zona bajo el cursor: `zoning-fill` u `official-fill`
  según la fuente activa, solo si el módulo está visible (On/Dim) y la categoría no está
  oculta.
- Capas de línea nuevas `zoning-hover` y `official-hover` en `LAYER_ORDER` después de las
  líneas de zoning, con paint según `feature-state` (hover: neón ~1.5 px; selected: blanco
  ~2.5 px). Siguen el estado del módulo (ocultas en Off), la fuente activa y los filtros
  de categoría. **Excluidas de `hitsAt()`.**
- Se actualiza solo cuando cambia la identidad (throttle con el `requestAnimationFrame`
  del `mousemove` que ya existe). Se limpia al salir del canvas y al empezar un arrastre.
- Tooltip `#hover-tip` junto al cursor (se da vuelta cerca de los bordes): muestra de
  color + zona CS2; debajo, nombre si hay; `Guessed from size` si `m == "area"`;
  `Google Open Buildings` / `Microsoft Building Footprints` según `s` o el prefijo del
  id (`g…`, `ms…`); `Official plan` si
  la fuente es el plan. Nunca en táctil ni durante un arrastre.
- La fila de esa zona en la columna se marca con `.is-hover` (sin scrollear la lista).
- Hover solo para zonas. El cursor de mano sigue para todo lo clickeable.

## 3. Click = selección fija (reemplaza los popups de MapLibre)

- **Prioridad:** la zona de la fuente activa en ese punto, si su módulo está visible;
  si no hay, el primer hit de `hitsAt()`.
- La zona elegida queda con `feature-state` `selected`.
- Sección `#selection` (`aria-live="polite"`) en la columna, entre el cuerpo y el pie del
  mapa base:
  - Cabecera `SELECTED` + botón `.sel-clear` (`aria-label="Clear selection"`).
  - `.sel-primary` con `data-layer` (id de la capa de MapLibre) y `data-cat` (`k`):
    - zona: muestra + nombre de la zona CS2, nombre del lugar (`Unnamed` si no hay),
      procedencia (`From OSM tags` / `From OSM land use` / `Guessed from size` /
      `Google Open Buildings · confidence 0.8` / `Official plan: <fuente>`);
      botón `.sel-only` `Only this zone` (reusa el mismo `Only`/`Restore` de la
      columna) y link `a.sel-osm` `Explore on OSM ↗`
      (`https://www.openstreetmap.org/query?lat=…&lon=…`: va a coordenadas, no al
      edificio);
    - calle: nombre (`Unnamed road`), clase, `bridge`;
    - servicio: nombre, categoría, subtipo, `<details>` con los tags OSM;
    - transporte: nombre de la línea, modo, operador;
    - servicios públicos: nombre, categoría, subtipo, operador.
  - `.sel-also` (`Also here`): el resto de los hits, sin duplicados de teselas: zoning
    por id; servicios, transporte y servicios públicos por fuente + `k` + `i`; calles
    por `(k, n, b)` (agrupa descripciones; puede juntar dos calles homónimas y se
    acepta). Calles sin nombre incluidas (`Unnamed road · Local Street`). Hasta 6
    entradas y `+N more`, con alto máximo y scroll.
- Se limpia con `.sel-clear`, `Esc` o un click en un lugar vacío. También cuando la
  feature deja de verse (módulo en Off, categoría oculta, cambio de fuente).
- **Columna de escritorio cerrada:** `#selection` flota abajo a la izquierda del mapa
  (misma tarjeta, ~300 px), para que la selección siempre se vea.
- **Celular:** con la bandeja plegada, la cabecera muestra la selección (muestra + zona)
  en lugar del resumen; al limpiar vuelve el resumen. Desplegada, `#selection` va arriba
  del cuerpo. Con la bandeja plegada `#selection` se oculta expresamente.
- Se borran `popupFor`, el `Popup` de MapLibre y el CSS `.cs2-popup` (los accesores de
  datos se reusan para la ficha).

## 4. Rendimiento

Nada de `setFilter` en hover ni click: solo `feature-state`. `hitsAt()` solo en el click y
en el `mousemove` con throttle.

## 5. Miniaturas

Sin interacción no aparecen `#hover-tip` ni `#selection`: no debería hacer falta tocar
`thumbnails.py`. Se verifica.

## 6. Verificación (Claude)

Playwright: Nueva York y Mafra (GeoJSON / Google), Minneapolis (teselas + plan oficial +
todos los módulos), Yogyakarta (rendimiento del hover), a 1440×900, 1280×720, 1024×768
con la columna cerrada, 390×844 y 844×390. Hover cambia `feature-state` y el tooltip sin
llamar a `setFilter`; click arma la ficha con los datos correctos; `Also here` sin
duplicados al cruzar teselas; `Only this zone` y `Restore`; limpieza con ✕, `Esc`, click
vacío, Off y cambio de fuente; ficha visible con la columna cerrada; bandeja móvil;
selección después de un zoom; sin errores de consola; miniaturas limpias.
