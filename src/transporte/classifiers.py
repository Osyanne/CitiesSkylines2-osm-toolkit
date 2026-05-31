"""
transporte/classifiers.py — OSM route tags → CS2 transit category
==================================================================
Mapeo puro de tags route + name + ref a una de 4 categorías CS2.

Reglas:
  route=light_rail              → lrt
  route=tram                    → lrt   (CS2 visualization)
  route=train | commuter_rail   → commuter
  route=bus + METRO BRT line    → brt   (ver _is_metro_brt)
  route=bus (resto)             → bus
  otros / ausente               → None

BRT: las relaciones reales de Mpls etiquetan TODAS las rutas con
network="Metro Transit" (nunca "METRO"), así que la categoría BRT NO se puede
detectar por network — se detecta por la forma de name/ref. Ver _is_metro_brt.
"""

# METRO highway BRT lines (Red/Orange/Gold) se nombran por color, sin "Line".
_METRO_HIGHWAY_BRT_NAMES = frozenset({"red", "orange", "gold"})


def _is_metro_brt(name: str, ref: str) -> bool:
    """True si una ruta route=bus es una línea METRO BRT de Metro Transit.

    Detectado por la forma real de los tags OSM de Mpls, en dos familias:
      - Arterial aBRT (A/B/C/D/E Line): el name contiene " Line"
        ("Metro Transit A Line (southbound)"). Los buses locales se llaman
        "Metro Transit <numero> (...)" y nunca contienen "Line".
      - Highway BRT (Red/Orange/Gold): se nombran solo por color
        ("Orange", ref 904), sin "Line" en el name.
    """
    if " line" in name.lower():
        return True
    if name.strip().lower() in _METRO_HIGHWAY_BRT_NAMES:
        return True
    return False


def classify_route(tags: dict) -> str | None:
    """Classify an OSM route relation into a CS2 transit category.

    Args:
        tags: OSM tags dict (route, name, ref, etc.).

    Returns:
        "lrt" | "commuter" | "brt" | "bus" | None (skip).
    """
    route = (tags.get("route") or "").lower()
    name = tags.get("name") or ""
    ref = tags.get("ref") or ""

    if route in ("light_rail", "tram"):
        return "lrt"
    if route in ("train", "commuter_rail", "commuter"):
        return "commuter"
    if route == "bus":
        if _is_metro_brt(name, ref):
            return "brt"
        return "bus"
    return None
