"""
cs2_zones.py — Modelo de zonas Cities: Skylines 2 oficial
==========================================================
Realineado en Sesión 1.6 (2026-05-13) al modelo oficial de CS2:

  Residencial (6): low_house, row, med, mixed, low_rent, high
  Comercial (2):   low, high
  Oficinas (2):    low, high
  Industrial (1):  manufacturing
  Parking (2):     surface, ramp  (no es zona CS2, mostrado como referencia)

Queries Overpass diseñadas para máxima cobertura sin timeouts:
  - apartments: edificios apartment con tags (incluye shop/amenity para mixed)
  - landuse_residential: zonas residenciales (fallback para low_house)
  - residential_subtypes: terrace, townhouse, etc → row housing
  - commercial: landuse + retail + shops + amenities comerciales
  - office: building=office + office=* (con uso office)
  - industrial: landuse + buildings industriales
  - parking: amenity=parking
"""

from shared.pbf_filters import Clause, FilterSpec, SpatialJoin, TagMatcher


CS2_LABELS = {
    # Residencial (6) — familia verde
    "res_low_house": "Low Density Housing",
    "res_row":       "Medium Density Row Housing",
    "res_med":       "Medium Density Housing",
    "res_mixed":     "Mixed Housing",
    "res_low_rent":  "Low Rent Housing",
    "res_high":      "High Density Housing",
    # Comercial (2) — familia azul
    "com_low":       "Low Density Business",
    "com_high":      "High Density Business",
    # Oficinas (2) — familia morada
    "office_low":    "Low Density Offices",
    "office_high":   "High Density Offices",
    # Industrial (1) — amarillo
    "industrial":    "Industrial Manufacturing",
    # Parking (2) — gris (no es zona CS2)
    "prk_surface":   "Surface Parking",
    "prk_ramp":      "Parking Structure",
}

def build_queries(bbox: str) -> dict:
    """
    Construir queries Overpass QL para las 7 categorías source.

    Cada query devuelve elementos con geometría completa (`out body geom`)
    para que el clasificador pueda inspeccionar tags y geometría en una sola
    pasada.

    Diseño:
      - apartments: incluye TODOS los apartment buildings (con o sin levels)
        y joins con shop/amenity para detectar Mixed Housing en una pasada
      - landuse_residential: para detectar low_house cuando no hay buildings
      - residential_subtypes: building tags específicos de row housing
      - commercial: amplio para capturar shops, amenities y landuse comercial
      - office: específico (no se mezcla con commercial)
      - industrial: landuse + buildings industriales
      - parking: superficie + estructuras
    """
    return {
        # MIXED_APARTMENTS — spatial join: apartments QUE CONTIENEN POIs comerciales.
        # En OSM real las tiendas/restaurantes están como NODOS dentro del polígono
        # del edificio (no como tags en la misma vía). Esta query usa around.comm:5
        # para encontrar apartments cuya geometría toca un nodo comercial. Se procesa
        # ANTES que la query 'apartments' para que el dedup global lo capture como
        # res_mixed antes de que classify_apartment lo clasifique como res_med/high.
        "mixed_apartments": f"""
[out:json][timeout:180];
(
  node["shop"]({bbox});
  node["amenity"="restaurant"]({bbox});
  node["amenity"="cafe"]({bbox});
  node["amenity"="bar"]({bbox});
  node["amenity"="pub"]({bbox});
  node["amenity"="fast_food"]({bbox});
  node["amenity"="marketplace"]({bbox});
  node["tourism"="hotel"]({bbox});
)->.comm;
(
  way["building"="apartments"](around.comm:5);
  way["building"="residential"](around.comm:5);
  way["building"="mixed_use"]({bbox});
  way["building:use"="mixed"]({bbox});
  way["building:use"="residential;commercial"]({bbox});
);
out body geom;
""".strip(),

        # APARTMENTS — todos los edificios apartment SIN spatial join.
        # Las apartments que ya salieron por mixed_apartments serán deduplicadas
        # por OSM id en extract_zoning.py.
        "apartments": f"""
[out:json][timeout:180];
(
  way["building"="apartments"]({bbox});
  way["building"="residential"]({bbox});
  way["building"="tower"]["building:use"~"residential"]({bbox});
  way["building"="residential_tower"]({bbox});
  way["building"="skyscraper"]["building:use"~"residential"]({bbox});
  way["building"="public_housing"]({bbox});
  way["building"="council_house"]({bbox});
  way["social_housing"="yes"]({bbox});
);
out body geom;
""".strip(),

        # LANDUSE_RESIDENTIAL — fallback para Low Density Housing
        "landuse_residential": f"""
[out:json][timeout:180];
(
  way["landuse"="residential"]({bbox});
  relation["landuse"="residential"]({bbox});
);
out body geom;
""".strip(),

        # RESIDENTIAL_SUBTYPES — building tags específicos de row housing
        "residential_subtypes": f"""
[out:json][timeout:180];
(
  way["building"="terrace"]({bbox});
  way["building"="townhouse"]({bbox});
  way["building"="row_house"]({bbox});
  way["building"="semi"]({bbox});
  way["building"="semi_detached"]({bbox});
  way["building"="semidetached_house"]({bbox});
  way["building"="dormitory"]({bbox});
  way["building"="house"]({bbox});
  way["building"="detached"]({bbox});
  way["building"="bungalow"]({bbox});
);
out body geom;
""".strip(),

        # COMMERCIAL — amplio (landuse + retail + shops + amenities + hoteles)
        "commercial": f"""
[out:json][timeout:180];
(
  way["landuse"="commercial"]({bbox});
  relation["landuse"="commercial"]({bbox});
  way["landuse"="retail"]({bbox});
  relation["landuse"="retail"]({bbox});
  way["shop"]({bbox});
  way["building"="retail"]({bbox});
  way["building"="supermarket"]({bbox});
  way["building"="commercial"]({bbox});
  way["amenity"="restaurant"]({bbox});
  way["amenity"="fast_food"]({bbox});
  way["amenity"="cafe"]({bbox});
  way["amenity"="bar"]({bbox});
  way["amenity"="pub"]({bbox});
  way["amenity"="fuel"]({bbox});
  way["amenity"="marketplace"]({bbox});
  way["amenity"="cinema"]({bbox});
  way["amenity"="theatre"]({bbox});
  way["amenity"="casino"]({bbox});
  way["amenity"="conference_centre"]({bbox});
  way["tourism"="hotel"]({bbox});
);
out body geom;
""".strip(),

        # OFFICE — específico
        "office": f"""
[out:json][timeout:180];
(
  way["building"="office"]({bbox});
  relation["building"="office"]({bbox});
  way["office"]({bbox});
  way["landuse"="office"]({bbox});
  way["building"="skyscraper"]["building:use"~"office"]({bbox});
);
out body geom;
""".strip(),

        # INDUSTRIAL — landuse + buildings
        "industrial": f"""
[out:json][timeout:180];
(
  way["landuse"="industrial"]({bbox});
  relation["landuse"="industrial"]({bbox});
  way["building"="industrial"]({bbox});
  way["building"="warehouse"]({bbox});
  way["building"="factory"]({bbox});
);
out body geom;
""".strip(),

        # PARKING — superficie + estructuras
        "parking": f"""
[out:json][timeout:180];
(
  way["amenity"="parking"]({bbox});
  relation["amenity"="parking"]({bbox});
);
out body geom;
""".strip(),

        # GENERIC_BUILDINGS — footprints sin tipificar (building=yes).
        # En OSM real (sobre todo zonas con cobertura esparsa: LATAM, África,
        # parte de Asia) la mayoría de los edificios se mapean como building=yes
        # sin tag de tipo. Esta query los recoge para clasificarlos por spatial
        # join contra landuse polygons (residential/commercial/retail/industrial/
        # office) o por heurística de área si no hay landuse que los contenga.
        # Se procesa al final del pipeline; dedup global por OSM id evita
        # colisión con buildings ya capturados por queries específicas.
        "generic_buildings": f"""
[out:json][timeout:180];
(
  way["building"="yes"]({bbox});
  relation["building"="yes"]({bbox});
);
out body geom;
""".strip(),

        # CIVIC_AMENITIES — nodes amenity=school/hospital/church/etc.
        # Usado para amenity cross-reference (v3.3.7): si un building clasificado
        # por heurística de área está cerca (≤30m) de un node con uno de estos
        # tags, se reclasifica a com_low (no industrial). Reduce falsos positivos
        # "industrial" en pueblos pequeños donde escuelas e iglesias tienen
        # footprints ≥1500 m².
        "civic_amenities": f"""
[out:json][timeout:180];
(
  node["amenity"~"^(school|university|college|kindergarten|hospital|clinic|doctors|dentist|pharmacy|place_of_worship|townhall|courthouse|public_building|police|fire_station|post_office|library|community_centre|social_facility|theatre|arts_centre|cinema|funeral_hall|crematorium)$"]({bbox});
);
out body;
""".strip(),
    }


# ── PBF filter specs (v3.4.0+) ───────────────────────────────────────────────
# Estos son siblings estructurados de las queries Overpass de arriba. Los
# extractores leen uno u otro según la flag --source.

CIVIC_AMENITY_VALUES = [
    "school", "university", "college", "kindergarten",
    "hospital", "clinic", "doctors", "dentist", "pharmacy",
    "place_of_worship", "townhall", "courthouse", "public_building",
    "police", "fire_station", "post_office", "library",
    "community_centre", "social_facility", "theatre", "arts_centre",
    "cinema", "funeral_hall", "crematorium",
]

COMMERCIAL_AMENITY_VALUES = [
    "restaurant", "fast_food", "cafe", "bar", "pub",
    "fuel", "marketplace", "cinema", "theatre", "casino", "conference_centre",
]

MIXED_NODE_AMENITY_VALUES = ["restaurant", "cafe", "bar", "pub", "fast_food", "marketplace"]


def build_pbf_filters(bbox: tuple[float, float, float, float]) -> dict[str, FilterSpec]:
    """
    Sibling estructurado de build_queries(bbox_string).

    Devuelve un dict con las mismas keys (mixed_apartments, apartments,
    landuse_residential, residential_subtypes, commercial, office, industrial,
    parking, generic_buildings, civic_amenities) pero los valores son FilterSpec
    en lugar de Overpass QL strings.

    bbox: tuple (south, west, north, east). El argumento es el mismo bbox que
    se usaría para Overpass; aquí no se interpola en strings, se usa en el
    pbf_client al cargar el OSM().
    """
    return {
        "mixed_apartments": FilterSpec(
            clauses={
                "comm_nodes": Clause(
                    geom_types=["node"],
                    tag_filters=[
                        TagMatcher({"shop": True}),
                        TagMatcher({"amenity": MIXED_NODE_AMENITY_VALUES}),
                        TagMatcher({"tourism": "hotel"}),
                    ],
                ),
                "mixed_buildings": Clause(
                    geom_types=["way"],
                    tag_filters=[
                        TagMatcher({"building": "apartments"}),
                        TagMatcher({"building": "residential"}),
                        TagMatcher({"building": "mixed_use"}),
                        TagMatcher({"building:use": "mixed"}),
                        TagMatcher({"building:use": "residential;commercial"}),
                    ],
                ),
            },
            spatial_joins=[
                SpatialJoin(
                    anchor_clause="comm_nodes",
                    target_clause="mixed_buildings",
                    buffer_m=5.0,
                ),
            ],
        ),

        "apartments": FilterSpec(
            clauses={
                "apartments": Clause(
                    geom_types=["way"],
                    tag_filters=[
                        TagMatcher({"building": "apartments"}),
                        TagMatcher({"building": "residential"}),
                        TagMatcher({"building": "residential_tower"}),
                        TagMatcher({"building": "public_housing"}),
                        TagMatcher({"building": "council_house"}),
                        TagMatcher({"social_housing": "yes"}),
                        TagMatcher({"building": "tower", "building:use": ["residential", "residential;commercial"]}),
                        TagMatcher({"building": "skyscraper", "building:use": ["residential", "residential;commercial"]}),
                    ],
                ),
            },
        ),

        "landuse_residential": FilterSpec(
            clauses={
                "lr": Clause(
                    geom_types=["way", "relation"],
                    tag_filters=[TagMatcher({"landuse": "residential"})],
                ),
            },
        ),

        "residential_subtypes": FilterSpec(
            clauses={
                "rs": Clause(
                    geom_types=["way"],
                    tag_filters=[
                        TagMatcher({"building": "terrace"}),
                        TagMatcher({"building": "townhouse"}),
                        TagMatcher({"building": "row_house"}),
                        TagMatcher({"building": "semi"}),
                        TagMatcher({"building": "semi_detached"}),
                        TagMatcher({"building": "semidetached_house"}),
                        TagMatcher({"building": "dormitory"}),
                        TagMatcher({"building": "house"}),
                        TagMatcher({"building": "detached"}),
                        TagMatcher({"building": "bungalow"}),
                    ],
                ),
            },
        ),

        "commercial": FilterSpec(
            clauses={
                "c": Clause(
                    geom_types=["way", "relation"],
                    tag_filters=(
                        [
                            TagMatcher({"landuse": "commercial"}),
                            TagMatcher({"landuse": "retail"}),
                            TagMatcher({"shop": True}),
                            TagMatcher({"building": "retail"}),
                            TagMatcher({"building": "supermarket"}),
                            TagMatcher({"building": "commercial"}),
                            TagMatcher({"tourism": "hotel"}),
                        ]
                        + [TagMatcher({"amenity": v}) for v in COMMERCIAL_AMENITY_VALUES]
                    ),
                ),
            },
        ),

        "office": FilterSpec(
            clauses={
                "o": Clause(
                    geom_types=["way", "relation"],
                    tag_filters=[
                        TagMatcher({"building": "office"}),
                        TagMatcher({"office": True}),
                        TagMatcher({"landuse": "office"}),
                        TagMatcher({"building": "skyscraper", "building:use": ["office", "office;commercial"]}),
                    ],
                ),
            },
        ),

        "industrial": FilterSpec(
            clauses={
                "i": Clause(
                    geom_types=["way", "relation"],
                    tag_filters=[
                        TagMatcher({"landuse": "industrial"}),
                        TagMatcher({"building": "industrial"}),
                        TagMatcher({"building": "warehouse"}),
                        TagMatcher({"building": "factory"}),
                    ],
                ),
            },
        ),

        "parking": FilterSpec(
            clauses={
                "p": Clause(
                    geom_types=["way", "relation"],
                    tag_filters=[TagMatcher({"amenity": "parking"})],
                ),
            },
        ),

        "generic_buildings": FilterSpec(
            clauses={
                "gb": Clause(
                    geom_types=["way", "relation"],
                    tag_filters=[TagMatcher({"building": "yes"})],
                ),
            },
        ),

        "civic_amenities": FilterSpec(
            clauses={
                "ca": Clause(
                    geom_types=["node"],
                    tag_filters=[TagMatcher({"amenity": CIVIC_AMENITY_VALUES})],
                ),
            },
        ),
    }
