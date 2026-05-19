"""
output_helpers.py
=================
Shared helpers for writing extract output (JS data files).

Quick wins applied across all extract*.py modules:
- round_coords: truncate lat/lon to 5 decimals (~1.1m precision)
"""
from __future__ import annotations


def round_coords(coords: list[list[float]], decimals: int = 5) -> list[list[float]]:
    """
    Round lat/lon coordinates to `decimals` decimal places.

    Default 5 decimals = ~1.1m precision at equator. More than sufficient for
    CS2 city-building reference data. Reduces output file size 30-40% vs Python's
    default float repr.
    """
    return [[round(c[0], decimals), round(c[1], decimals)] for c in coords]
