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
