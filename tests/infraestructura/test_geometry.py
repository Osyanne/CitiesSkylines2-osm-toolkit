"""infra_geometry: decide kind (point/polygon/line) + extrae coords."""
from infraestructura.extract import infra_geometry

NODE = {"type": "node", "lat": 44.9, "lon": -93.2}
OPEN_WAY = {"type": "way", "geometry": [
    {"lat": 44.9, "lon": -93.2}, {"lat": 44.91, "lon": -93.21}, {"lat": 44.92, "lon": -93.22}]}
CLOSED_WAY = {"type": "way", "geometry": [
    {"lat": 44.9, "lon": -93.2}, {"lat": 44.9, "lon": -93.1},
    {"lat": 44.8, "lon": -93.1}, {"lat": 44.9, "lon": -93.2}]}


def test_node_is_point():
    kind, coords = infra_geometry(NODE, "suministro")
    assert kind == "point"
    assert coords == [44.9, -93.2]

def test_closed_way_is_polygon():
    kind, coords = infra_geometry(CLOSED_WAY, "generacion")
    assert kind == "polygon"
    assert coords[0] == [44.9, -93.2]
    assert len(coords) == 4

def test_open_way_transmision_is_line():
    kind, coords = infra_geometry(OPEN_WAY, "transmision")
    assert kind == "line"
    assert len(coords) == 3

def test_open_way_non_transmision_is_point():
    kind, coords = infra_geometry(OPEN_WAY, "suministro")
    assert kind == "point"
    assert coords == [44.9, -93.2]

def test_way_without_geometry_returns_none():
    assert infra_geometry({"type": "way", "geometry": []}, "generacion") is None

def test_relation_transmision_uses_longest_member_way():
    rel = {"type": "relation", "members": [
        {"type": "way", "role": "", "geometry": [{"lat": 1, "lon": 1}, {"lat": 2, "lon": 2}]},
        {"type": "way", "role": "", "geometry": [
            {"lat": 3, "lon": 3}, {"lat": 4, "lon": 4}, {"lat": 5, "lon": 5}]},
    ]}
    kind, coords = infra_geometry(rel, "transmision")
    assert kind == "line"
    assert len(coords) == 3

def test_relation_polygon_uses_outer_ring():
    rel = {"type": "relation", "members": [
        {"type": "way", "role": "outer", "geometry": [
            {"lat": 1, "lon": 1}, {"lat": 1, "lon": 2}, {"lat": 2, "lon": 2}, {"lat": 1, "lon": 1}]},
    ]}
    kind, coords = infra_geometry(rel, "generacion")
    assert kind == "polygon"
    assert len(coords) == 4
