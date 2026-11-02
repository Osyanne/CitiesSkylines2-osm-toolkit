# Debate de layout del visor de ciudad (Claude vs Codex) — 2026-09-26

El dueño no está convencido con el layout de `visualizer/map.html` y pidió que Claude y
Codex debatan y propongan ideas. El debate fue solo ideación; lo que salió de él se
implementó después, por etapas (ver [Implementación](#implementación)).

## Estado

| Paso | Archivo | Estado |
|---|---|---|
| Brief común (inventario del layout actual, restricciones, formato) | `00-brief.md` | hecho |
| Capturas del visor actual (escritorio, capas, popup, laptop, móvil, landing) | `capturas/` | hecho |
| Ronda 1 — Codex (diagnóstico + 3 layouts + recomendación) | `01-codex-ronda1.md` | hecho |
| Ronda 1 — Claude (ídem) | `02-claude-ronda1.md` | hecho (auditoría completa en `anexo-claude-auditoria.md`) |
| Ronda 2 — Claude critica a Codex | `03-claude-critica.md` | hecho |
| Ronda 2 — Codex critica a Claude y revisa | `04-codex-ronda2.md` | hecho (prompt en `prompt-codex-ronda2.md`) |
| Síntesis final (acuerdos, desacuerdos, orden de implementación) | `05-sintesis.md` | hecho |

## Cómo retomar

- Si falta `02-claude-ronda1.md`: la postura de Claude la armaba un workflow; se puede
  rehacer con el mismo formato del brief.
- Ronda 2 para Codex, desde la raíz del repo:
  `codex exec -m gpt-6-astra -s read-only -C . -o docs/plans/2026-09-26-layout-visor/04-codex-ronda2.md "<prompt>"`
  pidiéndole que lea `01` y `02`, critique lo de Claude verificando contra el código, diga
  qué concede y qué sostiene, y deje una recomendación revisada.
- `gpt-6-sol` (el modelo del `config.toml` de Codex) ya no está habilitado para la cuenta
  de ChatGPT: usar `-m gpt-6-astra`.

## Implementación

Al 2026-11-02, con la v3.6.1 publicada, salieron todas las etapas de `05-sintesis.md`
menos dos puntos: la vía CS2 sugerida (etapa 6) y la atribución compacta en el celular
(etapa 1). Lo que queda abierto está en [Pendiente](#pendiente).

| Etapa | Especificación | PR | Versión |
|---|---|---|---|
| 0 y 1. Bugs, orientación e idioma | plan por etapas de `05-sintesis.md` | #59 y #60 | v3.4.10 |
| 2. Columna única | `06-etapa-2-spec.md` | #62 | v3.4.11 |
| 3. Inspección | `07-etapa-3-spec.md` | #64 | v3.4.12 |
| 4. La vista en la URL y `Share view` | `08-etapa-4-spec.md` | #68 | v3.4.13 |
| 6a. Recuadro del mapa jugable | `09-etapa-6a-spec.md` | #79 | v3.5.0 |
| 6b. Exportar el recuadro como PNG | `10-etapa-6b-spec.md` | #80 | v3.5.0 |
| 6c. Medir en celdas de 8 m | `11-etapa-6c-spec.md` | #81 | v3.5.0 |
| 6d. Buscador | `12-etapa-6d-spec.md` | #82 | v3.5.0 |
| 5. OSM contra el plan oficial (`Compare`) | `13-etapa-5-spec.md` | #88 | v3.6.0 |

### Cómo se hizo cada etapa

Rama `feat/visor-layout-etapa-0-1` (revisada por Codex; sus dos hallazgos se corrigieron en `a5ac247`):

- Etapa 0 (bugs) — `887ef95`: pills solo de los módulos que la ciudad tiene, estado
  guardado respetado cuando transporte e infraestructura cargan tarde, nombres visibles
  en las pills, "Fondo" al principio de la barra para que no se corran, aviso si un
  módulo no baja.
- Etapa 1 (orientación e idioma) — `f2841a3`: todo en inglés (servicios con los nombres
  de CS2), `‹ Cities`, `Fit city`, escala métrica, leyenda de confianza fiel al mapa,
  etiquetas del fondo sin oscurecer, sin la status bar. Miniaturas: esperan que el
  título deje de decir "Loading" y ocultan la escala.
- De la etapa 1 quedó abierta la atribución compacta en el celular (ver
  [Pendiente](#pendiente)).

Etapas 0 y 1: mergeadas en #59 y #60 y publicadas en la v3.4.10.

Etapa 2 (columna única), rama `feat/visor-columna-unica`, especificación en
`06-etapa-2-spec.md` (con las decisiones del dueño al final). La implementó un workflow:
un agente la implementó; Playwright, una revisión de Claude y una de Codex la verificaron;
otro agente corrigió lo confirmado. Después se sumaron las cabeceras fijas (`779243e`).
Verificación: 501 chequeos de Playwright sin fallas (script en el scratchpad de la sesión,
`stage2/verify2.py`). Mergeada en #62 y publicada en la v3.4.11. El rendimiento sin GPU
quedó en pausa (ver [Pendiente](#pendiente)).

Etapa 3 (inspección), rama `codex/inspeccion-mapa`, especificación en
`07-etapa-3-spec.md`: Codex implementó `map.html`, Claude verificó con Playwright y
escribió la documentación. Mergeada en #64 y publicada en la v3.4.12.

Etapa 4 (la vista en la URL y `Share view`), especificación en `08-etapa-4-spec.md`. Dos
carriles en worktrees: Codex implementó `map.html` (rama `codex/etapa4-url-share`) y
Claude escribió la spec, el test Playwright permanente (`tests/visualizer/`, 18 casos,
fuera del CI) y la documentación (rama `claude/etapa4-url-share`). Mergeada en #68 y
publicada en la v3.4.13.

Etapa 6a (el recuadro del mapa jugable de CS2), especificación en `09-etapa-6a-spec.md`.
Dos carriles en worktrees sobre `feat/playable-frame`: Codex implementó `map.html` (rama
`codex/recuadro-jugable`) y Claude escribió el test Playwright y la documentación (rama
`claude/recuadro-jugable`). La exportación como PNG para Image Overlay quedó para la 6b.
Mergeada en #79 y publicada en la v3.5.0.

Etapa 6b (exportar el recuadro como PNG para el mod Image Overlay), especificación en
`10-etapa-6b-spec.md`. Mismo reparto que la 6a, sobre `feat/frame-export`: Codex
implementó `map.html` (rama `codex/export-png`) y Claude escribió el test y la
documentación (rama `claude/export-png`). Mergeada en #80 y publicada en la v3.5.0.

Etapa 6c (medir en celdas de 8 m: escala doble y `Measure`), especificación en
`11-etapa-6c-spec.md`. Mismo reparto, sobre `feat/measure-cells`: Codex implementó
`map.html` (rama `codex/medir-celdas`) y Claude escribió el test y la documentación (rama
`claude/medir-celdas`). Mergeada en #81 y publicada en la v3.5.0. El tamaño en celdas en
la ficha quedó para una tarea de datos aparte, que salió en la v3.6.0 (abajo).

Etapa 6d (el buscador, con Nominatim y su política de uso), especificación en
`12-etapa-6d-spec.md`. Sobre `feat/search`: Codex implementó `map.html` y
`search-config.json` (rama `codex/buscador`) y Claude escribió el test, que nunca consulta la
API real, y la documentación (rama `claude/buscador`). Mergeada en #82 y publicada en la
v3.5.0.

Etapa 5 (OSM contra el plan oficial: el contorno del plan sobre el relleno OSM, con las dos
zonas en el hover y la ficha), especificación en `13-etapa-5-spec.md`. Sobre
`feat/compare-plan`: Codex implementó `map.html` y Claude escribió el nombre corto del plan
(`short_name`), el test y la documentación. Mergeada en #88 y publicada en la v3.6.0.

### Lo que se sumó después

- **Tamaño en celdas en la ficha** (#89, `c2539319`, v3.6.0), la tarea de datos que dejó
  la 6c: la ficha de una zona seleccionada muestra su área y el equivalente en celdas de
  8 × 8 m de CS2. `src/shared/tiles.py` guarda el área del polígono entero antes de
  cortarlo en teselas. Test: `tests/visualizer/test_cell_size.py`.
- **`Export for CS2`** (#129, v3.6.0): un botón junto a `Share`. El primer click prende el
  recuadro jugable y el siguiente abre la exportación.
- **`Request this area`** (#130, v3.6.0): con el recuadro prendido y su centro fuera de
  las ciudades publicadas, un botón abre un pedido de ciudad en GitHub con la caja
  cargada. Para eso, desde `7b25f969` el buscador encuentra cualquier lugar y pone primero
  los de la ciudad (§3 de `12-etapa-6d-spec.md`), y el recuadro prendido fuera de la
  ciudad va adonde se está mirando (§5 de `09-etapa-6a-spec.md`).

### Pendiente

- **Vía CS2 sugerida** (etapa 6): qué vía del juego usar según la clase de la calle en
  OSM. No tiene spec ni código, y es la única entrega de la etapa 6 que no salió. El dueño
  decide si se hace o se descarta; si se hace, la tabla OSM → CS2 la valida él
  (`05-sintesis.md`, "Lo que queda para el dueño", punto 2, y la tarea T5 de
  `anexo-claude-auditoria.md`).
- **Atribución compacta en el celular** (etapa 1): también la decide el dueño. No se
  cerró al arrancar porque la guía de atribución de OSM pide que se vea; MapLibre ya la
  pliega al mover el mapa.
- **Rendimiento sin GPU de `Only` y `Restore`** (etapa 2): en pausa por decisión del
  dueño (decisiones del 2026-09-27 al final de `06-etapa-2-spec.md`). Un `Only` en
  Minneapolis tarda 2,5–3,5 s por software.
