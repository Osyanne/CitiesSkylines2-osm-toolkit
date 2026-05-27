"""Test the relation-to-polyline geometry helpers."""
from transporte.extract import extract_way_geoms, concatenate_ways


def test_extract_way_geoms_filters_to_way_members():
    """A relation may have node members (stops) — we want only ways with geometry."""
    relation = {
        "type": "relation",
        "members": [
            {"type": "way", "ref": 1, "geometry": [{"lat": 1.0, "lon": 1.0}, {"lat": 2.0, "lon": 2.0}]},
            {"type": "node", "ref": 99, "lat": 1.5, "lon": 1.5},  # stop, skip
            {"type": "way", "ref": 2, "geometry": [{"lat": 2.0, "lon": 2.0}, {"lat": 3.0, "lon": 3.0}]},
        ],
    }
    result = extract_way_geoms(relation)
    assert len(result) == 2
    assert result[0] == [[1.0, 1.0], [2.0, 2.0]]
    assert result[1] == [[2.0, 2.0], [3.0, 3.0]]


def test_extract_way_geoms_skips_empty_geometry():
    """Member ways without geometry (rare but possible) are skipped."""
    relation = {
        "type": "relation",
        "members": [
            {"type": "way", "ref": 1, "geometry": [{"lat": 1.0, "lon": 1.0}, {"lat": 2.0, "lon": 2.0}]},
            {"type": "way", "ref": 2},  # no geometry
            {"type": "way", "ref": 3, "geometry": []},  # empty
        ],
    }
    assert len(extract_way_geoms(relation)) == 1


def test_extract_way_geoms_empty_relation():
    """A relation with no members returns empty list."""
    assert extract_way_geoms({"type": "relation", "members": []}) == []
    assert extract_way_geoms({"type": "relation"}) == []


def test_concatenate_ways_continuous_single_segment():
    """Two adjacent ways (way1.end == way2.start) merge into one LineString."""
    way1 = [[1.0, 1.0], [2.0, 2.0]]
    way2 = [[2.0, 2.0], [3.0, 3.0]]
    result = concatenate_ways([way1, way2])
    assert len(result) == 1
    assert result[0] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_concatenate_ways_reversed_member():
    """way2 reversed (way2.end == way1.end) — reverse it then concat."""
    way1 = [[1.0, 1.0], [2.0, 2.0]]
    way2 = [[3.0, 3.0], [2.0, 2.0]]  # reversed
    result = concatenate_ways([way1, way2])
    assert len(result) == 1
    assert result[0] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


def test_concatenate_ways_disjoint_emits_separate_segments():
    """Two ways with no shared endpoint stay as separate LineStrings."""
    way1 = [[1.0, 1.0], [2.0, 2.0]]
    way2 = [[5.0, 5.0], [6.0, 6.0]]
    result = concatenate_ways([way1, way2])
    assert len(result) == 2
    assert result[0] == way1
    assert result[1] == way2


def test_concatenate_ways_single():
    assert concatenate_ways([[[1.0, 1.0], [2.0, 2.0]]]) == [[[1.0, 1.0], [2.0, 2.0]]]


def test_concatenate_ways_empty():
    assert concatenate_ways([]) == []
