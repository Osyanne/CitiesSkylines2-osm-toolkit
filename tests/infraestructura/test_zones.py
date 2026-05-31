"""INFRA_LABELS + build_infraestructura_query."""
from infraestructura.zones import INFRA_LABELS, build_infraestructura_query


def test_labels_cover_4_categories():
    assert set(INFRA_LABELS.keys()) == {"power", "water", "waste", "telecom"}
    assert INFRA_LABELS["power"] == "Electricidad"

def test_query_includes_bbox():
    q = build_infraestructura_query("44.86,-93.38,45.05,-93.17")
    assert "44.86,-93.38,45.05,-93.17" in q

def test_query_targets_all_categories():
    q = build_infraestructura_query("1,2,3,4")
    assert "power" in q
    assert "man_made" in q
    assert "landfill" in q
    assert "recycling" in q
    assert "data_center" in q

def test_query_uses_nwr_and_geom():
    q = build_infraestructura_query("1,2,3,4")
    assert "nwr" in q
    assert "out body geom;" in q
