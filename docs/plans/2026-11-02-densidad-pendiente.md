# Densidad residencial: qué le falta a cada ciudad (2026-11-02)

Estado de la densidad residencial (`METHODOLOGY.md` §19 y el
[plan](2026-09-24-densidad-residencial-morfologia.md)) en las 77 ciudades publicadas,
medido el 2026-11-02 sobre `main` en `794b31e0` (v3.6.1), en sus
`visualizer/cities/<slug>/datos_zonificacion.json`:

- **Etapa 1** (altura + morfología, v3.4.14): la ciudad la tiene si alguna zona lleva
  `method` `height` o `morphology`.
- **Calibración del techo** (v3.6.1, `1feb7132`): resta 2,5 m de techo a las alturas
  medidas antes de contar pisos de 3 m, y deja como Row Housing los edificios de hasta tres
  pisos y 150 m² pegados a sus vecinos. No deja marca propia en los datos: la tienen las
  ciudades extraídas con ese código.
- La fecha es la de extracción, en UTC: `meta.generated_at`, o la que figura en el
  `header` de las ciudades convertidas del formato viejo (las 17 de la primera tabla
  extraídas hasta el 2026-09-20).

Para ponerlas al día hay que volver a extraerlas, desde `src/`:
`uv run --group thumbnails process-cities <slug> …` (extrae la zonificación, regenera la
landing y saca las miniaturas; en la nube, las miniaturas van aparte, ver `CLAUDE.md`).
Al rehacer una ciudad, sacala de su tabla.

## Sin la etapa 1 (34)

Extraídas antes de la v3.4.14. Les llega al volver a extraerlas.

| Extraída | Ciudades |
|---|---|
| 2026-05-20 | madison, charleston, bacau_ro, mafra_sc_brazil, fayetteville_nc, sacramento |
| 2026-05-22 | trondheim, amsterdam |
| 2026-05-23 | hollister, butterworth, lodz |
| 2026-05-24 | kursk |
| 2026-09-19 | little_rock, hong_kong, pittsburgh, cincinnati |
| 2026-09-20 | chicago |
| 2026-09-25 | yogyakarta, drammen, koege, valparaiso_chile, atlanta, denton_tx |
| 2026-09-26 | la_plata, roscommon, scranton, luebeck, carmel_in, kansas_city, pune, recife, buenos_aires |
| 2026-09-28 | seattle, sioux-falls |

Mafra, Valparaíso y La Plata también tienen edificios de Google Open Buildings
(`datos_external_buildings.json`). Al volver a extraerlas, la etapa 1 les llega a los
edificios de OSM, pero no a los de Google: `extract-google-buildings` los clasifica solo
por `landuse`, por un amenity cívico a menos de 30 m o por área
(`src/zoning/extract_google_buildings.py:363-391`).

## Con la etapa 1, sin la calibración (39)

Extraídas entre la v3.4.14 y la calibración. Les llega al volver a extraerlas, y cuánto
cambia depende de la ciudad: con los mismos extractos, Amberes cambiaba 326 zonas, Kiel 10,
y Beverlo y Minneapolis ninguna (mensaje de `1feb7132`).

| Extraída | Ciudades |
|---|---|
| 2026-10-01 | kiel, minneapolis, beverlo, antwerp |
| 2026-10-02 | lyon |
| 2026-10-03 | zurich |
| 2026-10-05 | leipzig |
| 2026-10-10 | edinburgh |
| 2026-10-21 | kyiv, vancouver, detroit_mi, chisinau, munich, clermont_ferrand, marseille, galway, milan, ljubljana, houston |
| 2026-10-22 | hamburg, bremen, ghent, st_louis, denizli, wroclaw, singapore, malaga, elche, cardiff, cagayan_de_oro |
| 2026-10-27 | bialystok, reims, groningen, rotterdam, sydney, gothenburg, toronto |
| 2026-10-29 | tulsa, timisoara |

## Con la calibración (4)

| Extraída | Ciudades |
|---|---|
| 2026-10-31 | philadelphia, new_york (los datos entraron en el mismo commit que la calibración, `1feb7132`) |
| 2026-11-02 | amersfoort, reston |

## Cómo se midió

Desde la raíz del repo:

```python
import json, re
from collections import Counter
from pathlib import Path


def methods(col, n):  # columna "method" del formato compacto (src/shared/compact.py)
    if col is None:
        return Counter()
    if "dict" in col:
        return Counter(col["dict"][c] for c in col["codes"] if c >= 0)
    if "values" in col:
        return Counter(col["values"])
    sparse = col.get("sparse", {})
    return Counter(sparse.values()) + Counter({col.get("default"): n - len(sparse)})


for f in sorted(Path("visualizer/cities").glob("*/datos_zonificacion.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    c = Counter()
    for layer in d["layers"].values():
        c += methods(layer["props"].get("method"), len(layer["ids"]))
    meta = d["meta"]
    date = meta.get("generated_at") or re.search(r"\d{4}-\d\d-\d\d", " ".join(meta["header"])).group()
    print(f.parent.name, date[:10], c["height"], c["morphology"])
```

Una ciudad con `0 0` en las dos últimas columnas no tiene la etapa 1. Para la calibración,
comparar la fecha con la de `1feb7132` (2026-10-31 02:01 UTC), salvo Filadelfia y Nueva
York, que se extrajeron con ese código unos minutos antes del commit.
