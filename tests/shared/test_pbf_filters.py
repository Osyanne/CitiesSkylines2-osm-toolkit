"""Tests for shared.pbf_filters."""
from __future__ import annotations

import pytest

from shared.pbf_filters import (
    Clause,
    FilterSpec,
    SpatialJoin,
    TagMatcher,
    FilterSpecError,
)


class TestTagMatcher:
    def test_exact_match(self):
        m = TagMatcher({"building": "apartments"})
        assert m.matches({"building": "apartments"}) is True
        assert m.matches({"building": "house"}) is False
        assert m.matches({}) is False

    def test_presence_match(self):
        m = TagMatcher({"shop": True})
        assert m.matches({"shop": "supermarket"}) is True
        assert m.matches({"shop": ""}) is True  # presence only
        assert m.matches({"building": "yes"}) is False

    def test_one_of_match(self):
        m = TagMatcher({"amenity": ["school", "hospital"]})
        assert m.matches({"amenity": "school"}) is True
        assert m.matches({"amenity": "hospital"}) is True
        assert m.matches({"amenity": "restaurant"}) is False

    def test_multi_tag_all_required(self):
        m = TagMatcher({"building": "apartments", "levels": True})
        assert m.matches({"building": "apartments", "levels": "5"}) is True
        assert m.matches({"building": "apartments"}) is False  # missing 'levels'

    def test_empty_matcher_raises(self):
        with pytest.raises(FilterSpecError):
            TagMatcher({})


class TestClause:
    def test_minimal_clause(self):
        c = Clause(
            geom_types=["way"],
            tag_filters=[TagMatcher({"building": "apartments"})],
        )
        assert "way" in c.geom_types
        assert len(c.tag_filters) == 1

    def test_empty_geom_types_raises(self):
        with pytest.raises(FilterSpecError):
            Clause(geom_types=[], tag_filters=[TagMatcher({"x": "y"})])

    def test_invalid_geom_type_raises(self):
        with pytest.raises(FilterSpecError):
            Clause(geom_types=["polygon"], tag_filters=[TagMatcher({"x": "y"})])  # type: ignore

    def test_empty_filters_raises(self):
        with pytest.raises(FilterSpecError):
            Clause(geom_types=["way"], tag_filters=[])


class TestSpatialJoin:
    def test_basic(self):
        sj = SpatialJoin(anchor_clause="comm", target_clause="apt", buffer_m=5.0)
        assert sj.buffer_m == 5.0

    def test_negative_buffer_raises(self):
        with pytest.raises(FilterSpecError):
            SpatialJoin(anchor_clause="a", target_clause="b", buffer_m=-1.0)


class TestFilterSpec:
    def test_minimal_spec(self):
        spec = FilterSpec(
            clauses={
                "apartments": Clause(
                    geom_types=["way"],
                    tag_filters=[TagMatcher({"building": "apartments"})],
                ),
            },
        )
        assert "apartments" in spec.clauses

    def test_empty_clauses_raises(self):
        with pytest.raises(FilterSpecError):
            FilterSpec(clauses={})

    def test_spatial_join_unknown_clause_raises(self):
        with pytest.raises(FilterSpecError):
            FilterSpec(
                clauses={
                    "a": Clause(geom_types=["way"], tag_filters=[TagMatcher({"x": "y"})]),
                },
                spatial_joins=[SpatialJoin(anchor_clause="a", target_clause="ghost", buffer_m=5)],
            )
