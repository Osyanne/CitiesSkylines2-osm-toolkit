# Adapting This Pipeline to Other Cities

This pipeline is city-agnostic. Any city with reasonable OpenStreetMap coverage can be processed. If you haven't set up Python and uv yet, start with [QUICKSTART.md](QUICKSTART.md) — it walks through the full install from zero.

---

## Step 1: Find Your City's Bounding Box

You need four coordinates in `south,west,north,east` order — a rectangle that covers your city.

**Option A — bboxfinder.com (easiest for beginners):**

Go to [bboxfinder.com](http://bboxfinder.com/). In the box at the bottom, under **Coordinate Format**, choose **Lat / Lng**. Then zoom to your city and draw a rectangle. The **Box** line shows its coordinates in the right order. Copy them.

Choose the format before you draw. The default, Lng / Lat, puts longitude first, and the Box line doesn't change if you switch it afterwards.

**Option B — Nominatim:**

Search your city on [nominatim.openstreetmap.org](https://nominatim.openstreetmap.org/). The result page shows a bounding box, or use the API directly:

    https://nominatim.openstreetmap.org/search?q=Chicago,IL,USA&format=json&limit=1

The response includes `"boundingbox": ["south", "north", "west", "east"]`. Note that Nominatim returns south, **north**, west, east — you need to reorder to south, **west**, north, east for these extractors.

**Option C — bbox-mcp-server (if you use AI tools):**

If you have the bbox-mcp-server set up, ask your AI assistant: "What is the bounding box for Chicago, IL?" See [bbox-mcp-server.md](bbox-mcp-server.md) for setup.

**Example bboxes,** as they are in `cities.json`, with the Geofabrik region each city reads:

| City | Bounding Box | `pbf_region` |
|------|--------------|--------------|
| Minneapolis, MN | `[44.86, -93.38, 45.05, -93.17]` | `north-america/us/minnesota` |
| Madison, WI | `[43.03, -89.5, 43.13, -89.3]` | `north-america/us/wisconsin` |
| Buenos Aires, Argentina | `[-34.690533, -58.527946, -34.543045, -58.341866]` | `south-america/argentina` |
| Amsterdam | `[52.32, 4.83, 52.42, 4.97]` | `europe/netherlands` |
| Hong Kong | `[22.24, 114.1, 22.36, 114.24]` | `asia/china/hong-kong` |
| Sydney, Australia | `[-33.98, 150.98, -33.76, 151.3]` | `australia-oceania/australia` |
| Amersfoort, Netherlands | `[52.0968, 5.2683, 52.2257, 5.4778]` | `["europe/netherlands/utrecht", "europe/netherlands/gelderland"]` |

Keep bboxes reasonably sized. A city's urban core (not the entire metro region) is usually the right scope: about 10–20 km per side, close to the 14.3 km of a CS2 playable area. Very large bboxes take longer to extract and make bigger files, and `process-cities` refuses a box with a side over 50 km.

---

## Step 2: Add the City to cities.json

The extractors only work on cities listed in `cities.json`, at the root of the repo. Add an entry for yours:

    "your_slug": {
      "display_name": "Your City, Country",
      "country": "Country",
      "country_code": "XX",
      "bbox": [south, west, north, east],
      "center": [center_lat, center_lon],
      "zoom": 12,
      "tagline": "One line about the city",
      "locale": "es",
      "pbf_region": "region/path/on/geofabrik"
    }

- `display_name`, `country`, `bbox`, `center`, `zoom`, `tagline` and `locale` are required (`src/shared/registry.py`). `country_code` is optional: it puts a flag on the city card.
- `pbf_region` is the [Geofabrik](https://download.geofabrik.de/) extract to read: the path of its download link without `-latest.osm.pbf`. If the box crosses into a second region, list both, like Amersfoort in the table above. Without `pbf_region`, `extract-zoning` stops with `has no 'pbf_region'`.
- The slug becomes the folder `visualizer/cities/your_slug/` and the address `map.html?city=your_slug`.

[Step 7 of the Quick Start](QUICKSTART.md#step-7-add-your-city-to-citiesjson) goes through each field.

---

## Step 3: Run the Extractors

Open a terminal inside the `src/` folder. If you haven't done `uv sync` yet, do that first.

**Zoning (building polygons classified into CS2 zone types):**

    uv run extract-zoning --city your_slug

The first run downloads the region's extract from Geofabrik to `~/.cache/cs2-osm-toolkit/pbf/`, and later runs reuse it for 7 days. This is the slowest extractor: it reads every building and land use area in the box and classifies each one into one of the 11 CS2 zone types, plus surface parking and parking structures.

Output: `visualizer/cities/your_slug/datos_zonificacion.json`, plus the `tiles/` folder the map draws from.

**Road network (roads classified into CS2 road categories):**

    uv run extract-vial --city your_slug

Classifies all OSM `highway=*` ways into the 6 CS2 road categories.

Output: `visualizer/cities/your_slug/datos_vial.json`, and the tiles are rebuilt with the roads.

**Services (hospitals, schools, fire stations, parks, police/admin):**

    uv run extract-services --city your_slug

Returns points and polygons for 5 service buckets aligned to CS2's service tabs.

Output: `visualizer/cities/your_slug/datos_servicios.js`

Roads and services read the same extract as zoning, but only when `pbf_region` is a single region. With a list, they stop with an error.

You can run all three for the same slug, or just the ones you need. Each extract updates the city's `manifest.json` preserving other modules already generated.

**Transit and infrastructure** (`uv run extract-transporte --city your_slug` and `uv run extract-infraestructura --city your_slug`) query the Overpass API instead of reading the extract. They were built for Minneapolis: what they find elsewhere depends on how well the city's transit lines and utilities are mapped in OSM.

**Several cities at once:** add all the entries and run `uv run --group thumbnails process-cities first_slug second_slug`. It checks every box against its Geofabrik regions before downloading any extract, extracts the zoning three cities at a time, runs `generate-landing` and takes the city card pictures. See [Several Cities at Once](QUICKSTART.md#several-cities-at-once) in the Quick Start.

`--source overpass` makes zoning, roads and services query the Overpass API instead of reading the extract. It doesn't need `pbf_region`, but it depends on the public Overpass servers.

---

## Step 4: Open the Visualizer

Run `uv run generate-landing` to add your new city to the city list. It rewrites `visualizer/index.html` and `visualizer/cities.json`, the copy of the registry that the map reads.

Then serve the `visualizer/` folder over HTTP. A double-click on the files doesn't work: browsers block the map's data requests from `file://`.

    cd ../visualizer
    python -m http.server 8000

Open `http://localhost:8000/` and your city appears as a card in the city list. Click it to open `map.html?city=your_slug`. The map opens framed on the box from `cities.json`.

If the map appears blank or shows an error, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Step 5: Calibrate Density Thresholds (if needed)

The density thresholds were tuned on a handful of cities. They may not be a perfect fit for yours.

Open your city's visualizer and compare against Google Maps or local knowledge. Look at areas you know well before changing anything. The zone of a building is decided in two places.

**1. Tags: `src/zoning/classifiers.py`.** Each building first gets a zone from its OSM tags. Floors are the larger of `building:levels` and `height` at 3 m per floor (`_effective_levels()`).

- `classify_apartment()`: `building=apartments` is High Density Housing at 7 floors or more, Low Rent Housing at 4 to 6 floors on a footprint of 1,500 m² or more (or with `social_housing=yes`), Mixed Housing with a shop or restaurant in it, and Medium Density Housing otherwise.
- `classify_residential_subtype()`: which `building=*` values are row houses (`terrace`, `townhouse`, `semi`, `dormitory`…) and which are houses (`house`, `detached`, `bungalow`).
- `classify_commercial()` and `classify_office()`: business is high density at 5 floors or more (4 for `building=commercial`), and so are malls, cinemas, theatres and big hotels. Offices are high density at 4 floors or more.
- `LANDUSE_TO_CS2_KEY` and `classify_generic_building_by_area()`: a plain `building=yes` takes the zone of the `landuse=*` area it stands in. Outside any known land use, it becomes Low Density Business within 30 m of a school, a clinic, a church or another amenity in `CIVIC_AMENITIES`. Otherwise it goes by area: a house under 300 m², Medium Density Housing under 1,500 m², industrial above that.

**2. Residential density: `src/zoning/morphology_config.py`.** Buildings that the first pass left as Low Density Housing (`building=house`, and plain `building=yes` placed by land use or area) get a second look, with the values in `MorphologyConfig`:

- **By height**, when OSM has `building:levels` or `height`. Floors are the larger of `building:levels` and `(height − height_roof_m) / 3`, because a measured height includes the roof (`height_roof_m` is 2.5 m). A `building=yes` becomes Medium Density Housing from `generic_levels_med_min` floors (3), a `building=house` from `house_levels_med_min` (4), and either one High Density Housing from `levels_high_min` (7). An attached building of up to `height_row_levels_max` floors (3) and `height_row_area_max_m2` (150 m²) becomes a row house instead.
- **By shape**, when it has neither, or its floors fall short of those thresholds. A building that shares at least `shared_frac_min` (25%) of its outline with its neighbors becomes Medium Density Housing if buildings cover at least `coverage_med_min` (45%) of the ground within `coverage_radius_m` (60 m). If they cover at least `coverage_row_min` (20%), it becomes a row house when its footprint is up to `row_area_max_m2` (250 m²), and Medium Density Housing when it's bigger. A building whose height is known but low, like a two-story house, can only become a row house this way.

In both passes, a shop inside makes it Mixed Housing instead of Medium Density Housing. The shape pass leaves detached buildings as they are, and skips buildings within 60 m of the edge of the box, where it can't see all their neighbors.

The defaults were calibrated on Antwerp, Beverlo, Kiel and Minneapolis, and the height ones against the Philadelphia and New York cadastres: see §19 of [METHODOLOGY.md](../METHODOLOGY.md). They're shared by every city, so a change applies to every city you extract afterwards.

To see what the second pass did, ask for its report:

    uv run extract-zoning --city your_slug --morphology-report density.csv

It writes one row per candidate building: its zone before and after, the reason, and what it measured (floors, footprint, shared outline, coverage).

**Most buildings come out as low density?** See whether they have `building:levels` or `height` in OSM before changing any threshold. Without them, only the shape pass can move a building, and only when it shares walls with its neighbors. See the coverage section below.

---

## OSM Coverage Gaps Will Affect Your Output

This is worth being upfront about. OSM is a volunteer-built map, and coverage varies significantly by region.

The toolkit works best for cities where contributors have mapped:
- Building footprints with `building:levels` or `height` tags (for density classification)
- `landuse=residential/commercial/industrial` polygons (for broad zone classification)
- Amenity and facility tags (`amenity=hospital`, `leisure=park`, etc.) for services

Cities with strong OSM communities — most of North America, Western Europe, Japan, Australia — usually produce good results. Cities with sparser coverage may produce fewer polygons and coarser classification.

Missing floors are a common gap, even where buildings are well mapped. A building without `building:levels` or `height` stays low density unless it shares walls with its neighbors (the shape pass in Step 5).

**Check your city's coverage** at [osmstats.neis-one.org](https://osmstats.neis-one.org/). If the edit and contributor counts are low, expect sparse output.

**Few buildings at all?** `uv run extract-google-buildings --city your_slug` adds footprints from Google Open Buildings, buildings detected by machine learning in satellite imagery, as a layer on top of OSM's. It skips the ones OSM already has, and places the rest only by land use, a nearby civic amenity or their area, without the density pass of Step 5. Google's dataset focuses on Latin America, Africa and Southeast Asia. On the site, Mafra, Valparaíso and La Plata use it. Like roads and services, it needs a single `pbf_region`.

The best fix is contributing to OSM for your area — it improves the map for everyone, not just this tool. The OSM wiki has tutorials for beginners.

---

## A Note on Zoning vs. Land Use

This toolkit classifies buildings using OSM land use tags and building attributes, not actual municipal zoning data. These are related but not the same thing. What OSM tags as "residential" matches what CS2 calls residential zone, but the exact density breakdown is an approximation based on floor counts, building types and building shapes — not a direct read from your city's zoning code. For a reference layer while building in CS2, this is accurate enough. For anything requiring legal zoning data, consult your municipality's GIS portal.

The one exception on the site is Minneapolis, which can also show the land use of its 2040 Plan: switch the Zoning layer to **Official plan**, or to **Compare** to see both.

---

## Common Errors

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for fixes for mistakes in `cities.json`, a missing `pbf_region`, a box in the wrong order, empty output, Overpass timeouts, uv errors and visualizer issues.
