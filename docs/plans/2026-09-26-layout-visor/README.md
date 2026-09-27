# Debate de layout del visor de ciudad (Claude vs Codex) — 2026-09-26

El dueño no está convencido con el layout de `visualizer/map.html` y pidió que Claude y
Codex debatan y propongan ideas. Solo ideación: no se tocó el visor.

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

Rama `feat/visor-layout-etapa-0-1` (revisada por Codex; sus dos hallazgos se corrigieron en `a5ac247`):

- Etapa 0 (bugs) — `887ef95`: pills solo de los módulos que la ciudad tiene, estado
  guardado respetado cuando transporte e infraestructura cargan tarde, nombres visibles
  en las pills, "Fondo" al principio de la barra para que no se corran, aviso si un
  módulo no baja.
- Etapa 1 (orientación e idioma) — `f2841a3`: todo en inglés (servicios con los nombres
  de CS2), `‹ Cities`, `Fit city`, escala métrica, leyenda de confianza fiel al mapa,
  etiquetas del fondo sin oscurecer, sin la status bar. Miniaturas: esperan que el
  título deje de decir "Loading" y ocultan la escala.
- Pendiente de la etapa 1: atribución compacta en el celular. No se cerró al arrancar
  porque la guía de atribución de OSM pide que se vea; MapLibre ya la pliega al mover
  el mapa.
- Etapa 2 en adelante: esperan las decisiones del dueño (sección "Lo que queda para el
  dueño" de `05-sintesis.md`).

Etapas 0 y 1: mergeadas en #59 y #60 y publicadas en la v3.4.10.

Etapa 2 (columna única), rama `feat/visor-columna-unica`, especificación en
`06-etapa-2-spec.md` (con las decisiones del dueño al final). La implementó un workflow:
un agente la implementó; Playwright, una revisión de Claude y una de Codex la verificaron;
otro agente corrigió lo confirmado. Después se sumaron las cabeceras fijas (`779243e`).
Verificación: 501 chequeos de Playwright sin fallas (script en el scratchpad de la sesión,
`stage2/verify2.py`). Queda para más adelante: rendimiento sin GPU (un `Only` en
Minneapolis tarda 2,5–3,5 s por software).
