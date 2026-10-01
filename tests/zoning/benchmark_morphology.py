"""Manual benchmark (not collected by pytest: filename does not start test_).

From src/ on Windows:
    .venv/Scripts/python.exe ../tests/zoning/benchmark_morphology.py
    .venv/Scripts/python.exe ../tests/zoning/benchmark_morphology.py --dense

190,000 footprints in a suburban grid, half houses and half attached garages.
Generation is excluded from the timed metrics + classification step. Optional
--dense measures a contiguous grid with all 190,000 buildings as candidates.
"""
import argparse
import math
from time import perf_counter

import numpy as np
import shapely

from zoning.morphology import compute_metrics, classify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense", action="store_true")
    parser.add_argument("--count", type=int, default=190_000)
    args = parser.parse_args()
    indices = np.arange(args.count)
    if args.dense:
        x, y = (indices % 500) * 10, (indices // 500) * 12
        widths = np.full(args.count, 10)
    else:
        sites = indices // 2
        x = (sites % 500) * 30 + (indices % 2) * 10
        y = (sites // 500) * 30
        widths = np.where(indices % 2, 4, 10)
    polys = shapely.box(x, y, x + widths, y + 12)
    scale = np.array([111320 * math.cos(math.radians(45)), 111320])
    polys = shapely.transform(polys, lambda xy: xy / scale + [-93, 45])
    footprints = {("way", i): p for i, p in enumerate(polys)}
    candidates = set(footprints) if args.dense else {("way", i) for i in range(0, args.count, 2)}
    values = {} if args.dense else {("way", i): "garage" for i in range(1, args.count, 2)}
    started = perf_counter()
    metrics = compute_metrics(footprints, candidate_ids=candidates, building_values=values)
    changed = sum(classify(m, has_shop=False) is not None for m in metrics.values())
    print(f"footprints={args.count} candidates={len(candidates)} changed={changed} "
          f"seconds={perf_counter() - started:.3f} shapely={shapely.__version__}")
    if not args.dense:
        assert changed == 0, "Attached garages must not upgrade suburban houses"


if __name__ == "__main__":
    main()
