"""
infraestructura/classifiers.py -- OSM tags -> (categoria CS2, subtipo)
=====================================================================
Tabla pura (key,value) -> (categoria, subtipo), mas reglas condicionales
(ver Task 3). Categorias: power | water | waste | telecom.

Data real Mpls: power=* (plantas/subestaciones/lineas), man_made=* (agua,
incinerador, telecom), landuse=landfill, amenity=recycling. Sin heuristicas.
"""

# (key, value) -> (categoria, subtipo) -- pares NO condicionales
TAG_TO_CATEGORY = {
    # power
    ("power", "plant"):        ("power", "generacion"),
    ("power", "generator"):    ("power", "generacion"),
    ("power", "substation"):   ("power", "subestacion"),
    ("power", "transformer"):  ("power", "subestacion"),
    ("power", "line"):         ("power", "transmision"),
    ("power", "minor_line"):   ("power", "transmision"),
    # water
    ("man_made", "water_tower"):       ("water", "suministro"),
    ("man_made", "water_works"):       ("water", "suministro"),
    ("man_made", "pumping_station"):   ("water", "suministro"),
    ("man_made", "water_well"):        ("water", "suministro"),
    ("man_made", "reservoir_covered"): ("water", "suministro"),
    ("man_made", "wastewater_plant"):  ("water", "aguas_residuales"),
    # waste
    ("landuse", "landfill"):               ("waste", "disposicion"),
    ("amenity", "waste_transfer_station"): ("waste", "disposicion"),
    ("man_made", "incinerator"):           ("waste", "disposicion"),
    # telecom
    ("man_made", "communications_tower"):  ("telecom", "torre"),
    ("telecom", "data_center"):            ("telecom", "data_center"),
}


def classify_infra(tags: dict) -> tuple[str, str] | None:
    """OSM tags -> (categoria, subtipo) | None (skip)."""
    for key, value in tags.items():
        hit = TAG_TO_CATEGORY.get((key, value))
        if hit is not None:
            return hit
    return None
