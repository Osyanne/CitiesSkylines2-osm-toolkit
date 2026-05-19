"""Tests for shared.output_helpers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from shared.output_helpers import round_coords


def test_rounds_to_default_5_decimals():
    coords = [[44.969234567, -93.271234567], [44.970987654, -93.272987654]]
    result = round_coords(coords)
    assert result == [[44.96923, -93.27123], [44.97099, -93.27299]]


def test_custom_decimals():
    coords = [[44.969234567, -93.271234567]]
    assert round_coords(coords, decimals=3) == [[44.969, -93.271]]


def test_empty_list():
    assert round_coords([]) == []


def test_single_point():
    assert round_coords([[1.123456789, 2.987654321]]) == [[1.12346, 2.98765]]


def test_does_not_mutate_input():
    coords = [[44.969234567, -93.271234567]]
    result = round_coords(coords)
    # Result is a new list, not the same object
    assert result is not coords
    # Original is unchanged
    assert coords == [[44.969234567, -93.271234567]]
