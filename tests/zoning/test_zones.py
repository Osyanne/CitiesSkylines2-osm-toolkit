"""Tests for zoning.zones.build_pbf_filters."""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from zoning.zones import build_pbf_filters, build_queries
from shared.pbf_filters import FilterSpec, TagMatcher


BBOX = (44.86, -93.38, 45.05, -93.17)


def test_returns_filterspecs_with_same_keys_as_overpass():
    pbf = build_pbf_filters(BBOX)
    overpass = build_queries("44.86,-93.38,45.05,-93.17")
    assert set(pbf.keys()) == set(overpass.keys())


def test_apartments_filter_matches_apartments_building():
    pbf = build_pbf_filters(BBOX)
    spec = pbf["apartments"]
    assert isinstance(spec, FilterSpec)
    apt_clause = spec.clauses["apartments"]
    assert any(m.matches({"building": "apartments"}) for m in apt_clause.tag_filters)


def test_civic_amenities_includes_schools_and_hospitals():
    pbf = build_pbf_filters(BBOX)
    spec = pbf["civic_amenities"]
    clause = next(iter(spec.clauses.values()))
    assert any(m.matches({"amenity": "school"}) for m in clause.tag_filters)
    assert any(m.matches({"amenity": "hospital"}) for m in clause.tag_filters)


def test_mixed_apartments_has_spatial_join():
    pbf = build_pbf_filters(BBOX)
    spec = pbf["mixed_apartments"]
    assert len(spec.spatial_joins) >= 1
    sj = spec.spatial_joins[0]
    assert sj.buffer_m == 5.0


def test_parking_matches_amenity_parking():
    pbf = build_pbf_filters(BBOX)
    spec = pbf["parking"]
    clause = next(iter(spec.clauses.values()))
    assert any(m.matches({"amenity": "parking"}) for m in clause.tag_filters)


def test_industrial_matches_warehouse_building():
    pbf = build_pbf_filters(BBOX)
    spec = pbf["industrial"]
    clause = next(iter(spec.clauses.values()))
    assert any(m.matches({"building": "warehouse"}) for m in clause.tag_filters)


def test_generic_buildings_matches_building_yes():
    pbf = build_pbf_filters(BBOX)
    spec = pbf["generic_buildings"]
    clause = next(iter(spec.clauses.values()))
    assert any(m.matches({"building": "yes"}) for m in clause.tag_filters)
