# Densidad residencial por morfología (pendiente)

**Estado:** idea aprobada, sin empezar. Quedó para otra sesión (2026-09-24).

**Origen:** comentario de u/Pamani_ en la publicación del toolkit en r/CitiesSkylines2:
en Amberes todo el casco antiguo sale como `res_low_house`, cuando en realidad son
edificios de uso mixto de 4–5 pisos pegados unos a otros.

## El problema

En `src/zoning/extract.py`, `_process_generic_buildings` clasifica los edificios sin
tipo (`building=yes`) buscando el polígono de `landuse` que contiene su centroide.
`LANDUSE_TO_CS2_KEY` (`src/zoning/classifiers.py`) manda `landuse=residential` siempre
a `res_low_house`, sin mirar altura, paredes compartidas ni cuánto suelo libre hay.
Esos items llevan `method: "landuse"`.

Además, muchos edificios etiquetados `building=house` / `residential` sin
`building:levels` también caen en baja densidad (items sin `method`, clasificados
por tag).

Medido sobre los `datos_zonificacion.json` publicados (2026-09-24):

| Ciudad | Terrenos | `res_low_house` | …por `landuse` | …por tag | row+med+mixed+high |
|---|---:|---:|---:|---:|---:|
| antwerp | 126.100 | 117.005 (93%) | 74.334 | 41.931 | 3.842 |
| beverlo | 46.947 | 44.101 (94%) | 8.356 | 34.711 | 905 |
| bacau_ro | 12.847 | 11.064 (86%) | 10.425 | 253 | 922 |
| kursk | 39.261 | 32.830 (84%) | 27.306 | 4.143 | 1.904 |
| lodz | 77.175 | 48.627 (63%) | 28.430 | 17.263 | 10.468 |
| kiel | 64.247 | 38.156 (59%) | 16.673 | 20.113 | 19.796 |
| trondheim | 40.272 | 19.098 (47%) | — | — | 16.778 |
| amsterdam | 82.763 | 26.674 (32%) | 6.519 | 19.175 | 47.015 |
| minneapolis (control) | 184.723 | 161.015 (87%) | 44.459 | 63.664 | 8.615 |

Minneapolis sirve de control: ahí el 87% de baja densidad sí es realista (casas
unifamiliares), así que la regla nueva no debería cambiarla mucho.

## Propuesta

### Etapa 1 — inferencia morfológica solo con OSM (hacer primero)

Para edificios residenciales sin niveles conocidos (por `landuse` y por tag sin
`building:levels`/`height`):

1. **Paredes compartidas:** con un STRtree de los footprints, contar vecinos que
   tocan o están a < ~0,5 m (usar un buffer pequeño por errores de digitalización).
   Medir qué fracción del perímetro es compartida.
2. **Cobertura del entorno:** fracción del suelo ocupada por edificios en un radio
   (p. ej. 50–75 m) o dentro de la manzana (polígonos delimitados por calles).
3. **Reglas tentativas** (calibrar con Amberes, Łódź y Minneapolis):
   - perímetro compartido alto + cobertura alta → `res_med` (o `res_mixed` si hay
     comercio en planta baja: `shop=*` / `amenity=*` dentro del footprint)
   - paredes compartidas en fila, footprint chico, cobertura media → `res_row`
   - aislado → se queda `res_low_house`
4. Marcar los items reclasificados con un `method` nuevo (p. ej. `"morphology"`)
   para que el visor pueda mostrar la confianza y se pueda revertir.

### Etapa 2 — alturas de Copernicus GHSL (opcional, después)

GHS-BUILT-H (altura media) y GHS-BUILT-V (volumen), rasters globales a 100 m.
Sirve para confirmar densidad por cuadra, no por edificio. Revisar la licencia y la
atribución antes de integrarlo, y cómo bajar solo el bbox de la ciudad (los tiles
son grandes).

## Cómo validar

- Tests unitarios con footprints sintéticos: fila de casas pegadas, manzana cerrada,
  casa aislada.
- Regenerar Amberes y comparar el reparto por zona antes/después (la tabla de arriba).
- Revisar visualmente el casco antiguo de Amberes y un barrio de casas de Minneapolis.
- Regenerar las teselas (`build-tiles --city <slug>`); los extractores ya lo hacen
  al final.
- Cuando esté publicado, avisar a u/Pamani_ en el hilo de Reddit.
