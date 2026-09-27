# Ronda 2 — Claude critica la ronda 1 de Codex

## Lo que verifiqué de Codex (todo cierto)

- Transporte e infraestructura se fuerzan a `"on"` al terminar de cargar y pisan el
  estado guardado: `map.html:2337` (`moduleStates.transporte = "on"`), igual en
  infraestructura.
- Las pills de Transit y Utilities se inyectan siempre, bloqueadas
  (`map.html:1828-1829`): candados que nunca se abren en 36 de 38 ciudades.
- "Fondo: Completo" deja los módulos apagados dibujados al 100 %: en `applyModuleState`,
  `visible = state === "on" || fondoMode !== "hidden"` y el factor solo baja con
  `faded`. "Apagado" no significa apagado.
- El click ordena por `LAYER_ORDER` y abre solo el primer popup (`hitsAt`,
  `map.html:2245-2269`): un pin de servicio tapa la zona de abajo.

Codex encontró los dos bugs de estado (el `"on"` forzado y la semántica de Fondo) con más
precisión que yo; los adopto tal cual.

## Críticas

1. **Diseña para Minneapolis, que es 1 de 38.** Verificado en los manifests: 33 ciudades
   tienen solo `zoning`, 3 tienen `zoning + external_buildings`, Chicago tiene 3 módulos
   y solo Minneapolis los 6. La B (bandeja con 5 tareas) y la C (dos mapas) resuelven la
   ciudad excepcional. En una ciudad de un módulo, la B se reduce a una paleta que se come
   144–176 px de alto (20–24 % de un 1280×720): peor que hoy.
2. **La C ya se probó y se sacó.** El repo tuvo un modo "Comparison" con pantalla
   dividida y divisor arrastrable (`ec58baa`) y se borró 105 líneas después (`358b1e3`,
   2026-05-25). Dos instancias de MapLibre con 300k features duplican memoria y GPU, y el
   costo es L. Lo que tiene de valioso (ver el edificio real) sale a costo S con un
   **Satellite a un click con opacidad de la zonificación** (tecla `S`).
3. **Le falta la interacción de cero clicks.** La pregunta más frecuente es "¿qué zona va
   en esta manzana?". En el Atlas hay que clickear y leer la sección Selected, lejos del
   lugar. Con **hover en escritorio** (contorno + tooltip junto al cursor + la fila de la
   leyenda marcada) la respuesta sale sin clickear. Con `promoteId` y `feature-state` no
   cuesta nada por frame.
4. **No es una herramienta de CS2 todavía.** Ninguna de las tres propone nada propio del
   juego: escala en celdas de 8 m, el recuadro del mapa jugable (23×23 tiles, ~14,3 km)
   para decidir qué parte de la ciudad entra, o la vía de CS2 sugerida para cada tipo de
   calle OSM. Es lo que diferencia este visor de un mapa de zonificación genérico.
5. **Columna acoplada fija en laptop.** 288–304 px acoplados son el 23 % del ancho de un
   1280 todo el tiempo. Acepto la columna única, pero plegable a un **riel de muestras**
   (≈48 px, la muestra de la zona bajo el cursor se ilumina) y arrancando plegada por
   debajo de 1200×800. Y `fitBounds` con `padding.left` para que la ciudad no arranque
   tapada.
6. **Conteos.** Mandarlos a "City totals" es de más: el conteo por zona le dice al
   jugador qué mezcla tiene la ciudad (161k casas bajas contra 120 torres). Lo dejaría en
   gris y chico, y lo sacaría en el celular. Sí corregir lo que Codex marcó: no cambian al
   pasar al plan oficial y la status bar llama "polígonos" a las calles.
7. **Buscador.** Un índice estático generado en la extracción es L y toca `src/`.
   Nominatim acotado al bbox, solo al apretar Enter, es S y respeta su política de uso.
   El índice propio queda para después.
8. **Riesgo que no aparece:** `src/shared/thumbnails.py` depende de `#fondo-control`,
   `.cs2-layers`, `.master-toggle` y de que el título deje de decir "Cargando". El primer
   PR de layout rompe las miniaturas si no las migra en el mismo PR.

## Qué concedo

- **El modelo `On / Dim / Off` por módulo es mejor que mi "vista activa + Others".** Es
  la generalización directa de lo que ya existe (`moduleStates` + `FADE`), se entiende
  sin explicación y no pelea con ciudades de 1 módulo. Mis "vistas" quedan, a lo sumo,
  como atajos (teclas 1-5 que ponen un módulo en On y el resto en Dim).
- **Primera visita sobria:** Zoning en On, calles en Dim y el resto en Off. Coincidimos.
- **Selección estable con contorno y elección entre features superpuestos.** Coincidimos;
  lo mío (ficha con todo lo que hay en el punto) es lo mismo.
- **Su orden de PRs**: arrancar por significado y ruido (S), después orientación (S),
  después el panel único (M). Es el mismo que el mío.

## Qué sostengo

- **Click en la fila = "only this"**, con un ojo para ocultar una sola fila. "Ver solo la
  industria" es mucho más frecuente que "ocultar el parking". Codex pone `[Only]` como
  botón aparte, que es más convencional. Es la única diferencia real de interacción que
  queda: la decide el dueño.
- **Hover como respuesta principal en escritorio** y el peek con la respuesta al tocar
  en el celular.
- **Afordancias propias de CS2** (celdas, recuadro de tiles, vía sugerida) en la etapa 4.
