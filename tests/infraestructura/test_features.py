"""build_infra_feature: element + clasificacion -> dict feature."""
from infraestructura.extract import build_infra_feature

NODE_TOWER = {"type": "node", "id": 7, "lat": 44.9, "lon": -93.2,
              "tags": {"man_made": "water_tower", "name": "Witch's Hat", "operator": "Mpls Water"}}


def test_feature_has_full_schema():
    f = build_infra_feature(NODE_TOWER, "water", "suministro")
    assert f["name"] == "Witch's Hat"
    assert f["category"] == "water"
    assert f["subtype"] == "suministro"
    assert f["kind"] == "point"
    assert f["coords"] == [44.9, -93.2]
    assert f["operator"] == "Mpls Water"
    assert f["osm_id"] == 7


def test_name_fallback_to_operator_when_unnamed():
    el = {"type": "node", "id": 1, "lat": 1, "lon": 2,
          "tags": {"power": "substation", "operator": "Xcel Energy"}}
    f = build_infra_feature(el, "power", "subestacion")
    assert "Xcel Energy" in f["name"]


def test_name_fallback_to_category_when_no_name_no_operator():
    el = {"type": "node", "id": 1, "lat": 1, "lon": 2, "tags": {"power": "substation"}}
    f = build_infra_feature(el, "power", "subestacion")
    assert f["name"] == "Electricidad sin nombre"


def test_returns_none_when_no_geometry():
    el = {"type": "way", "id": 1, "geometry": [], "tags": {"power": "plant"}}
    assert build_infra_feature(el, "power", "generacion") is None
