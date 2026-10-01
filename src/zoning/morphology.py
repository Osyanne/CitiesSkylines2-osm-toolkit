"""Conservative residential inference using original OSM footprints.

All footprints share a local equirectangular projection (metres). STRtree
queries and intersections are vectorized in bounded batches, so memory scales
with nearby buildings, rather than the square of the city size.
"""
from dataclasses import dataclass
import math
from typing import Literal

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry

from zoning.morphology_config import MorphologyConfig, DEFAULT

Ref = tuple[str, int]


@dataclass(frozen=True)
class Metrics:
    area_m2: float
    shared_frac: float
    shared_neighbors: int
    coverage: float  # Approximate footprint-area density; NaN without shared walls.
    context_complete: bool


def footprint_from_element(element: dict) -> tuple[BaseGeometry | None, bool]:
    """Reconstruct raw ways/multipolygons, including fragmented rings and holes.

    A partial relation can supply its reconstructible area as context, but is
    marked uncertain and must never be inferred as a candidate.
    """
    def points(geometry):
        return [(p["lon"], p["lat"]) for p in geometry]

    if element.get("type") == "way":
        ring = points(element.get("geometry", []))
        if len(ring) < 4 or ring[0] != ring[-1]:
            return None, False
        poly = Polygon(ring)
        return poly, poly.is_valid and not poly.is_empty
    if element.get("type") != "relation":
        return None, False
    complete = not element.get("_geometry_incomplete", False)
    rings = {"outer": [], "inner": []}
    for member in element.get("members", []):
        role = member.get("role", "")
        if role not in rings:
            if member.get("type") == "way":
                complete = False
            continue
        coords = points(member.get("geometry", []))
        if len(coords) < 2:
            complete = False
            continue
        rings[role].append(LineString(coords))
    areas = {}
    for role, lines in rings.items():
        polygons, cuts, dangles, invalid = shapely.polygonize_full(lines)
        complete &= cuts.is_empty and dangles.is_empty and invalid.is_empty
        # polygonize may turn a nested ring into both a hole in one face and
        # a separate face. Retain shells here; assign explicit holes below.
        areas[role] = [Polygon(p.exterior) for p in shapely.get_parts(polygons)]
    if not areas["outer"]:
        return None, False
    holes = [[] for _ in areas["outer"]]
    for inner in areas["inner"]:
        parents = [i for i, outer in enumerate(areas["outer"]) if outer.covers(inner)]
        if not parents:
            complete = False
        else:
            parent = min(parents, key=lambda i: areas["outer"][i].area)
            holes[parent].append(inner)
    geom = shapely.union_all([
        outer.difference(shapely.union_all(inner))
        for outer, inner in zip(areas["outer"], holes)
    ])
    return geom, bool(complete and geom.is_valid and not geom.is_empty)


def _rectangle_shared(bounds_a, bounds_b, left, size, config):
    """Exact interval unions for touching axis-aligned rectangular footprints.

    Avoid GEOS overlays for this common shape. Intervals are grouped by the
    candidate's four sides, so overlapping neighbours never double a facade.
    All other geometries keep the general GEOS path below.
    """
    dx = np.minimum(bounds_a[:, 2], bounds_b[:, 2]) - np.maximum(bounds_a[:, 0], bounds_b[:, 0])
    dy = np.minimum(bounds_a[:, 3], bounds_b[:, 3]) - np.maximum(bounds_a[:, 1], bounds_b[:, 1])
    vertical = (dx == 0) & (dy >= config.min_shared_length_m)
    horizontal = (dy == 0) & (dx >= config.min_shared_length_m)
    keep = vertical | horizontal
    left, a, b, vertical = left[keep], bounds_a[keep], bounds_b[keep], vertical[keep]
    counts = np.bincount(left, minlength=size)
    lengths = np.zeros(size)
    if not len(left):
        return lengths, counts
    side = np.where(vertical, (b[:, 0] >= a[:, 2]).astype(int),
                    2 + (b[:, 1] >= a[:, 3]).astype(int))
    group = left * 4 + side
    starts = np.where(vertical, np.maximum(a[:, 1], b[:, 1]), np.maximum(a[:, 0], b[:, 0]))
    ends = np.where(vertical, np.minimum(a[:, 3], b[:, 3]), np.minimum(a[:, 2], b[:, 2]))
    order = np.lexsort((starts, group))
    group, starts, ends = group[order], starts[order], ends[order]
    _, inverse, sizes = np.unique(group, return_inverse=True, return_counts=True)
    # Bound temporary memory even for unusually many overlapping neighbours.
    if len(sizes) * sizes.max() > 1_000_000:
        for indices in np.split(np.arange(len(group)), np.cumsum(sizes)[:-1]):
            previous = np.r_[-np.inf, np.maximum.accumulate(ends[indices])[:-1]]
            lengths[group[indices[0]] // 4] += np.maximum(0, ends[indices] - np.maximum(starts[indices], previous)).sum()
    else:
        slots = np.arange(len(group)) - np.repeat(np.cumsum(sizes) - sizes, sizes)
        end_grid = np.full((len(sizes), sizes.max()), -np.inf)
        end_grid[inverse, slots] = ends
        running = np.maximum.accumulate(end_grid, axis=1)
        previous = np.full(len(group), -np.inf)
        mask = slots > 0
        previous[mask] = running[inverse[mask], slots[mask] - 1]
        lengths = np.bincount(group // 4, weights=np.maximum(0, ends - np.maximum(starts, previous)), minlength=size)
    return lengths, counts


def compute_metrics(
    footprints: dict[Ref, BaseGeometry], *, candidate_ids: set[Ref],
    building_values: dict[Ref, str], config: MorphologyConfig = DEFAULT,
    bbox: tuple[float, float, float, float] | None = None,
    uncertain_ids: set[Ref] | None = None,
) -> dict[Ref, Metrics]:
    """Measure WGS84 polygons; bbox is (south, west, north, east).

    Invalid/missing candidate geometry abstains. Invalid context geometry is
    omitted; its vicinity also abstains. Overlapping buildings and duplicate
    geometries never contribute party walls. Coverage is an approximation:
    sum unique footprint areas whose representative points are within R of
    the candidate centroid, divided by pi*R**2 and capped at one. Partial
    overlaps can overestimate density; holes are excluded from footprint area.
    Candidates without shared neighbours have NaN coverage (not evaluated).
    """
    result = {ref: Metrics(0, 0, 0, math.nan, False) for ref in candidate_ids}
    if not footprints or not candidate_ids:
        return result
    refs = list(footprints)
    original = np.asarray(list(footprints.values()), dtype=object)
    valid = shapely.is_valid(original) & ~shapely.is_empty(original)
    valid &= np.isin(shapely.get_type_id(original), [3, 6])
    if not valid.any():
        return result
    bounds = shapely.total_bounds(original[valid])
    lon0, lat0 = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
    scale = np.array([111320 * math.cos(math.radians(lat0)), 111320])

    def project(xy):
        return (xy - [lon0, lat0]) * scale

    geoms = shapely.transform(original[valid], project)
    valid_refs = [ref for ref, ok in zip(refs, valid) if ok]
    indices = {ref: i for i, ref in enumerate(valid_refs)}
    candidates = np.asarray([indices[r] for r in valid_refs if r in candidate_ids], dtype=int)
    boundaries = shapely.boundary(geoms)
    areas = shapely.area(geoms)
    lengths = shapely.length(boundaries)
    envelopes = shapely.bounds(geoms)
    envelope_areas = (envelopes[:, 2] - envelopes[:, 0]) * (envelopes[:, 3] - envelopes[:, 1])
    rectangles = ((shapely.get_num_coordinates(geoms) == 5)
                  & np.isclose(areas, envelope_areas, rtol=1e-12, atol=0))
    accessories = np.asarray([building_values.get(r, "").lower() in config.accessory_buildings
                              for r in valid_refs])
    # One normalized identity per footprint, shared by both indices. This also
    # deduplicates ways/relations with different ring starts or orientations.
    _, unique_ids, identities = np.unique(
        shapely.to_wkb(shapely.normalize(geoms)), return_index=True, return_inverse=True,
    )
    unique_accessories = np.ones(len(unique_ids), dtype=bool)
    np.logical_and.at(unique_accessories, identities, accessories)
    neighbour_ids = unique_ids[~unique_accessories]
    tree = shapely.STRtree(geoms[neighbour_ids])
    coverage_tree = None  # Lazily built: detached suburbs never need coverage.
    uncertain = set(uncertain_ids or ())
    # A broken footprint may hide a nearby neighbour: retain its envelope as
    # an uncertainty zone, rather than silently declaring complete context.
    doubtful = [g.envelope for g, ok in zip(original, valid)
                if not ok and g is not None and not g.is_empty]
    doubtful.extend(original[i].envelope for i, r in enumerate(refs)
                    if r in uncertain and original[i] is not None and not original[i].is_empty)
    doubtful_tree = (shapely.STRtree(shapely.transform(np.asarray(doubtful, dtype=object), project))
                     if doubtful else None)
    frame = None
    if bbox is not None:
        s, w, n, e = bbox
        frame = shapely.transform(box(w, s, e, n), project)

    for start in range(0, len(candidates), 2048):
        ids = candidates[start:start + 2048]
        batch = geoms[ids]
        complete = np.ones(len(ids), dtype=bool)
        if frame is not None:
            complete &= shapely.covers(frame, batch)
            complete &= shapely.distance(batch, frame.boundary) >= config.coverage_radius_m
        if doubtful_tree is not None:
            near, _ = doubtful_tree.query(batch, predicate="dwithin", distance=config.coverage_radius_m)
            complete[near] = False

        left, right = tree.query(batch, predicate="dwithin", distance=config.touch_tolerance_m)
        right = neighbour_ids[right]
        keep = identities[ids[left]] != identities[right]
        left, right = left[keep], right[keep]
        fast = rectangles[ids].copy()
        a, b = envelopes[ids[left]], envelopes[right]
        touching_bounds = ((a[:, 0] <= b[:, 2]) & (b[:, 0] <= a[:, 2])
                           & (a[:, 1] <= b[:, 3]) & (b[:, 1] <= a[:, 3]))
        # Gaps must use the same tolerance bands as nonrectangular geometry;
        # otherwise adding a collinear vertex could change classification.
        np.logical_and.at(fast, left, rectangles[right] & touching_bounds)
        is_fast = fast[left]
        fast_lengths, fast_counts = _rectangle_shared(
            envelopes[ids[left[is_fast]]], envelopes[right[is_fast]],
            left[is_fast], len(ids), config,
        )
        left, right = left[~is_fast], right[~is_fast]
        # A positive-area intersection means overlap, not a shared facade.
        keep = shapely.relate_pattern(batch[left], geoms[right], "F********")
        left, right = left[keep], right[keep]
        shared = shapely.intersection(boundaries[ids[left]], boundaries[right])
        separated = shapely.is_empty(shared)
        # Exact point contacts must stay points, even for an acute corner whose
        # tolerance band follows a long stretch of the other facade.
        if separated.any() and config.touch_tolerance_m > 0:
            bands = shapely.buffer(boundaries[right[separated]], config.touch_tolerance_m, quad_segs=2)
            shared[separated] = shapely.intersection(boundaries[ids[left[separated]]], bands)
        keep = shapely.length(shared) >= config.min_shared_length_m
        left, right, shared = left[keep], right[keep], shared[keep]
        counts = np.bincount(left, minlength=len(ids))
        shared_lengths = np.bincount(left, weights=shapely.length(shared), minlength=len(ids)).astype(float)
        multiple = np.flatnonzero(counts > 1)
        if len(multiple):
            # Vectorized per-candidate unions, only for multiple neighbours.
            # Keep an allocation cap for unusual polygons with thousands of neighbours.
            width = int(counts.max())
            if len(multiple) * width <= 1_000_000:
                slots = np.arange(len(left)) - np.repeat(np.cumsum(counts) - counts, counts)
                rows = np.full(len(ids), -1, dtype=int)
                rows[multiple] = np.arange(len(multiple))
                mask = counts[left] > 1
                groups = np.full((len(multiple), width), None, dtype=object)
                groups[rows[left[mask]], slots[mask]] = shared[mask]
                shared_lengths[multiple] = shapely.length(shapely.union_all(groups, axis=1))
            else:
                for local in multiple:
                    shared_lengths[local] = shapely.length(shapely.union_all(shared[left == local]))

        shared_lengths += fast_lengths
        counts += fast_counts

        coverage = np.full(len(ids), math.nan)
        attached = np.flatnonzero(counts > 0)
        if len(attached):
            if coverage_tree is None:
                coverage_tree = shapely.STRtree(shapely.point_on_surface(geoms[unique_ids]))
            ci, ni = coverage_tree.query(shapely.centroid(batch[attached]), predicate="dwithin",
                                         distance=config.coverage_radius_m)
            coverage[attached] = np.minimum(1, np.bincount(
                ci, weights=areas[unique_ids[ni]], minlength=len(attached),
            ) / (math.pi * config.coverage_radius_m ** 2))
        for local, idx in enumerate(ids):
            ref = valid_refs[idx]
            result[ref] = Metrics(
                float(areas[idx]), float(min(1, shared_lengths[local] / lengths[idx])),
                int(counts[local]), float(np.clip(coverage[local], 0, 1)),
                bool(complete[local] and ref not in uncertain),
            )
    return result


def classify(metrics: Metrics, *, has_shop: bool, config: MorphologyConfig = DEFAULT
             ) -> Literal["row", "med", "mixed"] | None:
    if (not metrics.context_complete or not metrics.shared_neighbors
            or metrics.shared_frac < config.shared_frac_min or not math.isfinite(metrics.coverage)):
        return None
    if metrics.coverage >= config.coverage_med_min:
        return "mixed" if has_shop else "med"
    if metrics.coverage >= config.coverage_row_min:
        if metrics.area_m2 <= config.row_area_max_m2:
            return "row"
        return "mixed" if has_shop else "med"
    return None
