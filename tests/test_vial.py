"""Tests del módulo vial (Sesión 2)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


BBOX = "44.86,-93.38,45.05,-93.17"

# Las 6 categorías viales CS2
EXPECTED_VIAL_KEYS = {"highway", "major", "minor", "local", "pedestrian", "bike"}


def test_vial_labels_has_six_keys():
    from vial_zones import VIAL_LABELS
    assert set(VIAL_LABELS.keys()) == EXPECTED_VIAL_KEYS


def test_vial_labels_are_human_readable():
    from vial_zones import VIAL_LABELS
    assert VIAL_LABELS["highway"] == "Highway"
    assert VIAL_LABELS["major"] == "Major Road"
    assert VIAL_LABELS["minor"] == "Minor Road"
    assert VIAL_LABELS["local"] == "Local Street"
    assert VIAL_LABELS["pedestrian"] == "Pedestrian Path"
    assert VIAL_LABELS["bike"] == "Bike Lane"


def test_build_vial_query_contains_bbox_and_all_highway_tags():
    from vial_zones import build_vial_query
    q = build_vial_query(BBOX)
    # El bbox debe estar embebido
    assert BBOX in q
    # Todas las categorías highway deben aparecer en la regex
    for tag in [
        "motorway", "trunk", "primary", "secondary", "tertiary",
        "residential", "unclassified", "living_street", "service",
        "pedestrian", "footway", "path", "steps", "cycleway",
    ]:
        assert tag in q, f"falta '{tag}' en query"
    # Debe ser una sola query con out body geom
    assert "out body geom" in q
    assert "[out:json]" in q
