"""Metric geometry fixtures are in metres, converted without output rounding."""
from dataclasses import replace
import math

import pytest
from shapely import affinity
from shapely.geometry import Polygon, box

from zoning.morphology_config import MorphologyConfig


CONFIG = MorphologyConfig(
    touch_tolerance_m=0.5, min_shared_length_m=3, coverage_radius_m=20,
    shared_frac_min=0.2, coverage_med_min=0.55, coverage_row_min=0.10,
    row_area_max_m2=250,
)


def wgs(geom):
    return affinity.translate(affinity.scale(
        geom, xfact=1 / (111320 * math.cos(math.radians(45))),
        yfact=1 / 111320, origin=(0, 0)), xoff=-93, yoff=45)


def metrics(polys, *, values=None, bbox=None):
    from zoning.morphology import compute_metrics
    footprints = {("way", i): wgs(p) for i, p in enumerate(polys)}
    return compute_metrics(footprints, candidate_ids=set(footprints),
                           building_values=values or {}, config=CONFIG, bbox=bbox)


@pytest.mark.parametrize("gap,neighbors", [(0, 1), (0.3, 1), (2, 0)])
def test_shared_wall_tolerance(gap, neighbors):
    m = metrics([box(0, 0, 10, 12), box(10 + gap, 0, 20 + gap, 12)])[("way", 0)]
    assert m.area_m2 == pytest.approx(120, rel=0.001)
    assert m.shared_neighbors == neighbors
    assert (m.shared_frac >= 0.25) == bool(neighbors)


@pytest.mark.parametrize("neighbor", [box(10, 12, 20, 24), box(0, 0, 10, 12), box(5, 0, 15, 12)])
def test_corner_duplicate_and_overlap_are_not_party_walls(neighbor):
    m = metrics([box(0, 0, 10, 12), neighbor])[("way", 0)]
    assert m.shared_neighbors == 0
    assert m.shared_frac == 0


def test_acute_corner_contact_is_not_a_shared_wall():
    # These triangles meet only at their tips; a boundary buffer alone
    # incorrectly turns a long, narrow strip near that tip into a facade.
    first = Polygon([(0, 0), (20, 0), (20, 2), (0, 0)])
    second = Polygon([(0, 0), (20, -2), (20, -0.01), (0, 0)])
    m = metrics([first, second])[("way", 0)]
    assert m.shared_neighbors == 0


def test_exact_shared_fraction_excludes_perpendicular_buffer_tails():
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 12)])[("way", 0)]
    assert m.shared_frac == pytest.approx(12 / 44, rel=0.001)


def test_approximate_coverage_deduplicates_normalized_geometry():
    from shapely import reverse
    first, neighbour = box(0, 0, 10, 12), box(10, 0, 20, 12)
    m = metrics([first, neighbour, reverse(neighbour)])[("way", 0)]
    assert m.shared_neighbors == 1
    assert m.coverage == pytest.approx(240 / (math.pi * 400), rel=0.001)


def test_duplicate_neighbours_count_once():
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 12), box(10, 0, 20, 12)])[("way", 0)]
    assert m.shared_neighbors == 1


def test_overlapping_neighbours_do_not_double_count_the_same_facade():
    # Both neighbours share parts of the right wall; their union covers 12 m.
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 9), box(10, 3, 18, 12)])[("way", 0)]
    assert m.shared_neighbors == 2
    assert m.shared_frac == pytest.approx(12 / 44, rel=0.001)


def test_nested_shared_intervals_count_once():
    m = metrics([box(0, 0, 10, 20), box(10, 0, 20, 20),
                 box(10, 2, 15, 6), box(10, 8, 15, 12)])[("way", 0)]
    assert m.shared_neighbors == 3
    assert m.shared_frac == pytest.approx(20 / 60, rel=0.001)


def test_rotated_footprints_keep_shared_fraction():
    row = [affinity.rotate(box(i * 10, 0, i * 10 + 10, 12), 30, origin=(0, 0))
           for i in range(3)]
    m = metrics(row)[("way", 1)]
    assert m.shared_neighbors == 2
    assert m.shared_frac == pytest.approx(24 / 44, rel=0.001)


def test_small_gap_is_invariant_to_a_collinear_vertex():
    simple = box(0, 0, 10, 20)
    subdivided = Polygon([(0, 0), (5, 0), (10, 0), (10, 20), (0, 20), (0, 0)])
    neighbour = box(10.3, 0, 20.3, 14.7)
    first = metrics([simple, neighbour])[("way", 0)]
    second = metrics([subdivided, neighbour])[("way", 0)]
    assert first.shared_frac == pytest.approx(second.shared_frac, abs=1e-9)
    assert first.shared_neighbors == second.shared_neighbors


def test_approximate_coverage_sums_unique_footprint_areas():
    # Partial overlaps are an accepted approximation; exact duplicates are not.
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 12), box(5, 0, 15, 12)])[("way", 0)]
    assert m.coverage == pytest.approx(360 / (math.pi * 400), rel=0.001)


def test_coverage_is_not_computed_without_shared_neighbours():
    from zoning.morphology import classify
    m = metrics([box(0, 0, 10, 12)])[("way", 0)]
    assert math.isnan(m.coverage)
    assert classify(m, has_shop=False, config=CONFIG) is None


def test_approximate_coverage_uses_representative_point_distance():
    # Nearby footprint edge is inside R, but its representative point is outside.
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 12), box(22, 0, 42, 12)])[("way", 0)]
    assert m.coverage == pytest.approx(240 / (math.pi * 400), rel=0.001)


def test_invalid_candidate_and_missing_candidate_abstain():
    from zoning.morphology import compute_metrics
    bad = wgs(Polygon([(0, 0), (10, 12), (10, 0), (0, 12), (0, 0)]))
    result = compute_metrics({("way", 1): bad}, candidate_ids={("way", 1), ("way", 2)},
                             building_values={}, config=CONFIG)
    assert not result[("way", 1)].context_complete
    assert not result[("way", 2)].context_complete


def test_row_dense_block_and_isolated_house():
    from zoning.morphology import classify
    row = metrics([box(i * 10, 0, i * 10 + 10, 12) for i in range(7)])[("way", 3)]
    assert classify(row, has_shop=False, config=CONFIG) == "row"
    dense = metrics([box(x * 10, y * 12, x * 10 + 10, y * 12 + 12)
                     for x in range(7) for y in range(7)])[("way", 24)]
    assert classify(dense, has_shop=False, config=CONFIG) == "med"
    assert classify(dense, has_shop=True, config=CONFIG) == "mixed"
    isolated = metrics([box(0, 0, 10, 12)])[("way", 0)]
    assert classify(isolated, has_shop=True, config=CONFIG) is None


def test_garages_add_coverage_without_making_suburban_houses_attached():
    from zoning.morphology import classify
    polys = [box(0, 0, 10, 12), box(10, 0, 14, 8), box(30, 0, 40, 12)]
    m = metrics(polys, values={("way", 1): "garage"})[("way", 0)]
    assert m.shared_frac == 0
    assert math.isnan(m.coverage)
    assert classify(m, has_shop=False, config=CONFIG) is None


def test_accessories_add_coverage_for_attached_candidates():
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 12), box(-4, 0, 0, 8)],
                values={("way", 2): "garage"})[("way", 0)]
    assert m.shared_neighbors == 1
    assert m.coverage == pytest.approx(272 / (math.pi * 400), rel=0.001)


def test_courtyard_is_excluded_from_coverage():
    outer = box(-10, -10, 10, 10)
    courtyard = Polygon(outer.exterior.coords, [box(-5, -5, 5, 5).exterior.coords])
    m = metrics([courtyard, box(10, -6, 20, 6)])[("way", 0)]
    assert m.area_m2 == pytest.approx(300, rel=0.001)
    assert m.coverage == pytest.approx(420 / (math.pi * 400), rel=0.001)


def test_edge_abstains_and_complete_context_does_not():
    from zoning.morphology import classify
    bounds = wgs(box(-5, -100, 100, 100)).bounds
    bbox = (bounds[1], bounds[0], bounds[3], bounds[2])
    m = metrics([box(0, 0, 10, 12), box(10, 0, 20, 12)], bbox=bbox)[("way", 0)]
    assert not m.context_complete
    assert classify(m, has_shop=False, config=CONFIG) is None


def test_classification_thresholds_and_large_attached_building():
    from zoning.morphology import Metrics, classify
    m = Metrics(300, 0.25, 2, 0.2, True)
    assert classify(m, has_shop=False, config=CONFIG) == "med"
    assert classify(m, has_shop=True, config=CONFIG) == "mixed"
    assert classify(replace(m, coverage=0.05), has_shop=False, config=CONFIG) is None
    assert classify(replace(m, context_complete=False), has_shop=False, config=CONFIG) is None
