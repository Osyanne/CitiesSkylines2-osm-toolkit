"""Tests for the --source CLI flag in zoning.extract."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from zoning.extract import parse_args


def test_default_source_is_pbf():
    args = parse_args(["--city", "minneapolis"])
    assert args.source == "pbf"


def test_source_overpass_accepted():
    args = parse_args(["--city", "minneapolis", "--source", "overpass"])
    assert args.source == "overpass"


def test_source_pbf_accepted():
    args = parse_args(["--city", "minneapolis", "--source", "pbf"])
    assert args.source == "pbf"


def test_invalid_source_rejected():
    with pytest.raises(SystemExit):
        parse_args(["--city", "minneapolis", "--source", "garbage"])


def test_refresh_pbf_flag():
    args = parse_args(["--city", "minneapolis", "--refresh-pbf"])
    assert args.refresh_pbf is True


def test_refresh_pbf_default_false():
    args = parse_args(["--city", "minneapolis"])
    assert args.refresh_pbf is False


def test_city_arg_preserved():
    args = parse_args(["--city", "minneapolis"])
    assert args.city == "minneapolis"


def test_bbox_arg_preserved():
    args = parse_args(["--bbox", "1,2,3,4", "--slug", "test"])
    assert args.bbox == "1,2,3,4"
    assert args.slug == "test"
