# CS2 Zone Reference — OSM Tags to Cities: Skylines 2

How the toolkit turns OpenStreetMap tags into the 13 zones on the map: the 11 zones of the Cities: Skylines 2 base game, plus two parking categories shown for reference. Names and colours are the ones in the map's layer column (`ZONES` in `visualizer/map.html`).

Each zone is drawn with a fill (its colour at 55% opacity) and a brighter outline, which is also its swatch in the layer column. A zone guessed only from the size of the footprint gets a fainter fill (22%) and a dashed outline. Low Density Housing and Surface Parking polygons under 3,000 m² only appear once you zoom in close.

Zones are polygons (OSM ways and multipolygons). Tagged points, such as shop nodes, only help classify the buildings around them. "Floors" below means the larger of `building:levels` and `height` ÷ 3 m, rounded.

---

## Residential

| CS2 zone | Fill | Outline | Comes from |
|---|---|---|---|
| Low Density Housing | `#A5D6A7` | `#C8E6C9` | `building=house`, `detached` or `bungalow`; `landuse=residential` areas; `building=yes` inside `landuse=residential`, or under 300 m² with no land use around it |
| Medium Density Row Housing | `#9CCC65` | `#C5E1A5` | `building=terrace`, `townhouse`, `row_house`, `semi`, `semi_detached`, `semidetached_house` or `dormitory` |
| Medium Density Housing | `#66BB6A` | `#81C784` | `building=apartments` or `residential` under 7 floors (unless Mixed or Low Rent); `building=yes` of 300 to 1,500 m² with no land use around it |
| Mixed Housing | `#26A69A` | `#4DB6AC` | `building=apartments`, `residential` or `mixed_use`, or `building:use=mixed` or `residential;commercial`, within 5 m of a shop, restaurant, café, bar, pub, fast food, marketplace or hotel node; apartment buildings tagged with a `shop`, a restaurant, café, bar, pub or fast food `amenity`, or `building:use=mixed` or `residential;commercial` |
| Low Rent Housing | `#558B2F` | `#7CB342` | `building=public_housing` or `council_house`, or `social_housing=yes`; apartment buildings of 4 to 6 floors with a footprint of 1,500 m² or more |
| High Density Housing | `#1B5E20` | `#2E7D32` | `building=residential_tower`; `building=tower` or `skyscraper` with `building:use=residential`; apartment buildings of 7 floors or more |

**Height and shape.** Houses (`building=house`) and untyped buildings zoned as Low Density by their land use or size can then move up a density:

- With a known height: `building=yes` with 3 or more floors, or `building=house` with 4 or more, becomes Medium Density (Mixed Housing if a shop, restaurant or similar is inside), and 7 or more floors make it High Density. Here a measured `height` loses 2.5 m for the roof before it is divided by 3. A building of up to 3 floors and 150 m² that shares walls with its neighbours becomes Row Housing instead of Medium Density. A lower building that shares walls can only become Row Housing.
- Without a height: a building that shares at least a quarter of its outline with other buildings becomes Medium Density when 45% or more of the ground within 60 m is built (Mixed Housing with a shop or similar inside), or Row Housing when 20 to 45% is built and its footprint is 250 m² or less (Medium Density if bigger).

`detached` and `bungalow` never change. Maps extracted before October 2026 don't have this pass yet: they get it when the city is extracted again. Details and calibration: [METHODOLOGY.md §19](../METHODOLOGY.md#sección-19--densidad-residencial-por-altura-y-morfología-2026-10); thresholds in `src/zoning/morphology_config.py`.

---

## Commercial

| CS2 zone | Fill | Outline | Comes from |
|---|---|---|---|
| Low Density Business | `#039BE5` | `#4FC3F7` | `landuse=commercial` or `retail`; `shop=*`; `building=retail`, `supermarket` or `commercial`; `amenity=restaurant`, `fast_food`, `cafe`, `bar`, `pub`, `fuel` or `marketplace`; `tourism=hotel`; `building=yes` inside a commercial or retail land use, or guessed from its size and within 30 m of a civic amenity node (a school, hospital, place of worship and so on) |
| High Density Business | `#01579B` | `#0277BD` | `shop=mall`; `amenity=cinema`, `theatre`, `casino` or `conference_centre`; hotels with 4 or more floors or 2,000 m² or more; `building=commercial` with 4 or more floors; any other tag in the row above with 5 or more floors, except untyped `building=yes` |

---

## Office

| CS2 zone | Fill | Outline | Comes from |
|---|---|---|---|
| Low Density Offices | `#9C27B0` | `#BA68C8` | `building=office`, `office=*` or `landuse=office`, under 4 floors; `building=yes` inside `landuse=office` |
| High Density Offices | `#4A148C` | `#6A1B9A` | `building=office`, `office=*` or `landuse=office` with 4 or more floors; `building=skyscraper` with `building:use=office` |

---

## Industrial

| CS2 zone | Fill | Outline | Comes from |
|---|---|---|---|
| Industrial Manufacturing | `#F9A825` | `#FFCA28` | `landuse=industrial`; `building=industrial`, `warehouse` or `factory`; `building=yes` inside `landuse=industrial`, or of 1,500 m² or more with no land use around it |

---

## Parking

Not CS2 zones: they are on the map for reference.

| Category | Fill | Outline | Comes from |
|---|---|---|---|
| Surface Parking | `#B0BEC5` | `#CFD8DC` | `amenity=parking` |
| Parking Structure | `#37474F` | `#607D8B` | `amenity=parking` with `parking=multi-storey`, `multistorey`, `structure` or `underground` |

---

## Which rule wins

Each OSM element gets one zone. The extractor reads the sources in this order and the first match wins: mixed housing, apartments, house types, residential land use, commercial, offices, industrial, parking and, last, untyped buildings (`building=yes`). So an element tagged with both `shop=*` and `office=*` is commercial. Polygons under 50 m² are dropped. See [METHODOLOGY.md §6](../METHODOLOGY.md#6-osm-element-deduplication-between-categories) and, for untyped buildings, [§17](../METHODOLOGY.md#sección-17--generic-buildings-spatial-join--heurística-v334).

The rules live in `src/zoning/classifiers.py` (`classify_apartment()`, `classify_residential_subtype()`, `classify_commercial()`, `classify_office()`, `classify_parking()` and `classify_generic_building_by_area()`) and the order in `src/zoning/extract.py`. Why these 13 zones: [METHODOLOGY.md §3](../METHODOLOGY.md#3-the-13-zone-model-cs2-oficial-alignment).

---

## Google Open Buildings

In Mafra, Valparaíso and La Plata the map also has building footprints detected by Google Open Buildings, where OSM has few. They follow only the rules for untyped buildings (land use, a nearby civic amenity, size), not the height and shape pass, and their details say "Google Open Buildings". See [METHODOLOGY.md §18](../METHODOLOGY.md#sección-18--external-buildings-augmentation-google-open-buildings-v335).

---

## Notes on Modded Zone Packs

If you play with a zone pack whose zones have other names, rename the labels in `ZONES` in `visualizer/map.html` (what the map shows) and, if you want the extractor's printed summary to match, `CS2_LABELS` in `src/zoning/zones.py`. The rules in `src/zoning/classifiers.py` only use the zone keys (`res_low_house`, `com_high` and so on), not the names.
