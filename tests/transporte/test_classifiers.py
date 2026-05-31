"""Test the route classifier: OSM tags → CS2 category."""
from transporte.classifiers import classify_route


def test_light_rail_classifies_as_lrt():
    """METRO Blue/Green Line use route=light_rail."""
    assert classify_route({"route": "light_rail", "name": "METRO Green Line"}) == "lrt"


def test_tram_classifies_as_lrt():
    """European trams map to LRT in CS2 visualization."""
    assert classify_route({"route": "tram", "name": "Tram 4"}) == "lrt"


def test_train_classifies_as_commuter():
    """Northstar uses route=train."""
    assert classify_route({"route": "train", "name": "Northstar"}) == "commuter"


def test_commuter_rail_alias_classifies_as_commuter():
    """Some OSM data uses commuter_rail as the route value."""
    assert classify_route({"route": "commuter_rail", "name": "X"}) == "commuter"


def test_metro_rapid_classifies_as_brt():
    """METRO Rapid Bus (A/C/D/E/F Line) is BRT, detected via network=METRO."""
    assert classify_route({"route": "bus", "network": "METRO", "name": "METRO A Line"}) == "brt"


def test_metro_rapid_classifies_as_brt_name_only():
    """Fallback: name contains METRO and ' Line' but network may be absent."""
    assert classify_route({"route": "bus", "name": "METRO C Line"}) == "brt"


def test_local_bus_classifies_as_bus():
    """Regular Metro Transit local bus route."""
    assert classify_route({"route": "bus", "name": "Route 5", "network": "Metro Transit"}) == "bus"


def test_bus_without_name_classifies_as_bus():
    """Bus with no name fields still classifies - doesn't match BRT pattern."""
    assert classify_route({"route": "bus"}) == "bus"


def test_unknown_route_returns_none():
    """Routes we don't care about (ferry, hiking, etc.) return None."""
    assert classify_route({"route": "ferry"}) is None


def test_missing_route_returns_none():
    """No route tag at all → None."""
    assert classify_route({"name": "something"}) is None


def test_empty_tags_returns_none():
    assert classify_route({}) is None


def test_route_value_is_case_insensitive():
    """Defensive against weird OSM data - but real OSM uses lowercase."""
    assert classify_route({"route": "Light_Rail"}) == "lrt"


# ──────────────────────────────────────────────────────────────────────────
# Real-OSM-shape tests
# ──────────────────────────────────────────────────────────────────────────
# The idealized tests above (network="METRO", name="METRO A Line") all passed,
# yet the shipped run produced BRT=0 - every rapid line fell into bus. Reason:
# real Mpls relations tag network="Metro Transit" (never "METRO") and name
# "Metro Transit A Line (southbound)" / "Orange". These tests pin the ACTUAL
# tag shapes returned by Overpass so the bug can't silently return.


def test_real_arterial_a_line_classifies_as_brt():
    """Real OSM shape: arterial aBRT 'A Line', network='Metro Transit', ref='A'."""
    tags = {
        "route": "bus",
        "network": "Metro Transit",
        "name": "Metro Transit A Line (southbound)",
        "ref": "A",
    }
    assert classify_route(tags) == "brt"


def test_real_arterial_e_line_classifies_as_brt():
    """Newest aBRT line - same real shape, different letter/direction."""
    tags = {
        "route": "bus",
        "network": "Metro Transit",
        "name": "Metro Transit E Line (northbound)",
        "ref": "E",
    }
    assert classify_route(tags) == "brt"


def test_real_highway_orange_line_classifies_as_brt():
    """METRO Orange Line: highway BRT named by colour, ref='904', no 'Line' token."""
    tags = {
        "route": "bus",
        "network": "Metro Transit",
        "name": "Orange",
        "ref": "904",
        "colour": "#f68b1e",
    }
    assert classify_route(tags) == "brt"


def test_real_local_bus_with_letter_suffix_stays_bus():
    """Regression: local 'Metro Transit 3A' carries ref='3' - must NOT become BRT."""
    tags = {
        "route": "bus",
        "network": "Metro Transit",
        "name": "Metro Transit 3A (eastbound)",
        "ref": "3",
    }
    assert classify_route(tags) == "bus"


def test_real_local_bus_alphanumeric_ref_stays_bus():
    """Regression: 'Metro Transit 10C' has ref='10C' (len > 1) - stays bus."""
    tags = {
        "route": "bus",
        "network": "Metro Transit",
        "name": "Metro Transit 10C (northbound)",
        "ref": "10C",
    }
    assert classify_route(tags) == "bus"


def test_real_plymouth_metrolink_stays_bus():
    """Regression: 'Metrolink' contains 'link', not ' line' - stays bus (other agency)."""
    tags = {
        "route": "bus",
        "network": "Plymouth Metrolink",
        "name": "Plymouth Metrolink 747 (eastbound)",
        "ref": "747",
    }
    assert classify_route(tags) == "bus"
