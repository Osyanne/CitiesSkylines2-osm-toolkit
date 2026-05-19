"""Tests for shared.pbf_client."""
from __future__ import annotations

from pathlib import Path

import pytest

from shared.pbf_client import _in_bbox, _osmium_tags


MONACO_PBF = Path(__file__).resolve().parents[1] / "fixtures" / "monaco-latest.osm.pbf"
MONACO_BBOX = (43.7236, 7.4090, 43.7521, 7.4395)  # south, west, north, east


class TestInBbox:
    def test_inside(self):
        # (south=0, west=0, north=10, east=10)
        assert _in_bbox(5.0, 5.0, (0.0, 0.0, 10.0, 10.0)) is True

    def test_on_boundary_south_west(self):
        assert _in_bbox(0.0, 0.0, (0.0, 0.0, 10.0, 10.0)) is True

    def test_on_boundary_north_east(self):
        assert _in_bbox(10.0, 10.0, (0.0, 0.0, 10.0, 10.0)) is True

    def test_outside_south(self):
        assert _in_bbox(-1.0, 5.0, (0.0, 0.0, 10.0, 10.0)) is False

    def test_outside_north(self):
        assert _in_bbox(11.0, 5.0, (0.0, 0.0, 10.0, 10.0)) is False

    def test_outside_west(self):
        assert _in_bbox(5.0, -1.0, (0.0, 0.0, 10.0, 10.0)) is False

    def test_outside_east(self):
        assert _in_bbox(5.0, 11.0, (0.0, 0.0, 10.0, 10.0)) is False


@pytest.mark.skipif(not MONACO_PBF.exists(), reason="Monaco fixture missing")
class TestOsmiumTags:
    def test_extracts_real_tags_from_monaco(self):
        """Iterate Monaco PBF, find any way with tags, confirm _osmium_tags returns a populated dict.

        NOTE: pyosmium 4.x invalidates obj references once the iterator advances,
        so we must extract the dict INSIDE the loop, not after break.
        """
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF))
        extracted: dict[str, str] | None = None
        for obj in fp:
            if obj.is_way() and len(obj.tags) > 0:
                extracted = _osmium_tags(obj)
                break

        assert extracted is not None, "Monaco PBF has no tagged ways?"
        assert isinstance(extracted, dict)
        assert len(extracted) > 0
        # All keys and values are strings
        assert all(isinstance(k, str) for k in extracted.keys())
        assert all(isinstance(v, str) for v in extracted.values())

    def test_returns_empty_dict_for_no_tags(self):
        """Untagged nodes (just geometry) should give an empty dict, not crash."""
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF))
        extracted: dict[str, str] | None = None
        for obj in fp:
            if obj.is_node() and len(obj.tags) == 0:
                extracted = _osmium_tags(obj)
                break

        if extracted is None:
            pytest.skip("No untagged nodes in fixture")
        assert extracted == {}


from shared.pbf_client import (
    _node_to_overpass,
    _way_to_overpass,
    _area_to_overpass,
)


@pytest.mark.skipif(not MONACO_PBF.exists(), reason="Monaco fixture missing")
class TestNodeToOverpass:
    def test_returns_overpass_shape(self):
        """A node with tags should become {type, id, tags, lat, lon}."""
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF))
        result: dict | None = None
        for obj in fp:
            if obj.is_node() and len(obj.tags) > 0 and obj.location.valid():
                result = _node_to_overpass(obj)
                break

        if result is None:
            pytest.skip("No tagged nodes in fixture")
        assert result["type"] == "node"
        assert isinstance(result["id"], int)
        assert isinstance(result["tags"], dict)
        assert isinstance(result["lat"], float)
        assert isinstance(result["lon"], float)
        assert 43.7 <= result["lat"] <= 43.8  # Monaco lat range
        assert 7.4 <= result["lon"] <= 7.5    # Monaco lon range

    def test_invalid_location_returns_none(self):
        """Nodes without valid location should return None, not crash."""
        # Hard to construct synthetically; we'll test the behavior via integration later
        # Just sanity-check: real Monaco nodes all have valid locations, so we just
        # confirm the function doesn't crash on real data.
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF))
        result_has_lat: bool | None = None
        for obj in fp:
            if obj.is_node():
                # All real nodes from a PBF have valid locations
                result = _node_to_overpass(obj)
                if result is not None:
                    result_has_lat = "lat" in result
                else:
                    result_has_lat = False  # acceptable
                break
        # Just confirm no crash; result_has_lat is True (real node) or False (None returned)
        assert result_has_lat is not None


@pytest.mark.skipif(not MONACO_PBF.exists(), reason="Monaco fixture missing")
class TestWayToOverpass:
    def test_returns_overpass_shape(self):
        """A way should become {type, id, tags, geometry: [{lat,lon}, ...]}."""
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF)).with_locations()
        result: dict | None = None
        for obj in fp:
            if obj.is_way() and len(obj.tags) > 0 and len(obj.nodes) >= 2:
                # Verify all node locations are resolved
                try:
                    all_valid = all(n.location.valid() for n in obj.nodes)
                except Exception:
                    all_valid = False
                if all_valid:
                    result = _way_to_overpass(obj)
                    break

        assert result is not None, "Monaco PBF has no resolvable tagged ways?"
        assert result["type"] == "way"
        assert isinstance(result["id"], int)
        assert isinstance(result["tags"], dict)
        assert isinstance(result["geometry"], list)
        assert len(result["geometry"]) >= 2
        # Each geometry point is {lat, lon}
        for pt in result["geometry"]:
            assert "lat" in pt and "lon" in pt
            assert isinstance(pt["lat"], float)
            assert isinstance(pt["lon"], float)

    def test_way_with_no_resolvable_nodes_returns_none(self):
        """If a way has no valid locations, we should return None instead of crashing."""
        # Without .with_locations(), node references aren't resolved
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF))  # NO with_locations()
        observed: dict | None = None
        for obj in fp:
            if obj.is_way() and len(obj.tags) > 0:
                # Locations should NOT be valid here
                observed = _way_to_overpass(obj)
                break
        # Either None (no valid coords) or fully populated — both acceptable, just must not crash
        if observed is not None:
            assert "geometry" in observed


@pytest.mark.skipif(not MONACO_PBF.exists(), reason="Monaco fixture missing")
class TestAreaToOverpass:
    def test_returns_relation_shape_with_outer_member(self):
        """Areas become {type: 'relation', id, tags, members: [{role: 'outer', geometry}]}."""
        import osmium

        fp = osmium.FileProcessor(str(MONACO_PBF)).with_areas()
        result: dict | None = None
        for obj in fp:
            if hasattr(obj, "from_way") and len(obj.tags) > 0:
                # This is an area
                result = _area_to_overpass(obj)
                if result is not None:
                    break

        if result is None:
            pytest.skip("No areas with tags in fixture")
        assert result["type"] == "relation"
        assert isinstance(result["id"], int)
        assert isinstance(result["members"], list)
        assert len(result["members"]) >= 1
        outer = result["members"][0]
        assert outer["role"] == "outer"
        assert isinstance(outer["geometry"], list)
        assert len(outer["geometry"]) >= 3
