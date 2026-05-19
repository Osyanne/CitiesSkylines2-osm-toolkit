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
