"""
infraestructura/zones.py -- Categorias CS2 + Overpass query builder
===================================================================
4 categorias: power / water / waste / telecom.
La query es amplia (trae mast/tower y recycling); el classifier (classify_infra)
es el que filtra a telecom-only y recycling=centre.
"""

INFRA_LABELS = {
    "power":   "Electricidad",
    "water":   "Agua y Alcantarillado",
    "waste":   "Basura",
    "telecom": "Comunicaciones",
}


def build_infraestructura_query(bbox: str) -> str:
    """Overpass QL: node+way+relation de infraestructura en el bbox, con geometria.

    Args:
        bbox: "south,west,north,east" decimal degrees.
    """
    return f"""
[out:json][timeout:120];
(
  nwr["power"~"^(plant|substation|transformer|line|minor_line)$"]({bbox});
  nwr["man_made"~"^(water_tower|water_works|pumping_station|water_well|reservoir_covered|wastewater_plant|incinerator|communications_tower|mast|tower)$"]({bbox});
  nwr["landuse"="landfill"]({bbox});
  nwr["amenity"~"^(waste_transfer_station|recycling)$"]({bbox});
  nwr["telecom"="data_center"]({bbox});
);
out body geom;
""".strip()
