"""Test the mapping YAML loader + validator."""
import pytest
from official_zoning.mapping import load_mapping, Mapping, UnknownCodeStrategy


def test_load_mapping_returns_mapping_object(sample_mapping_yaml):
    m = load_mapping(sample_mapping_yaml)
    assert isinstance(m, Mapping)
    assert m.city == "test_city"
    assert m.source_field == "ZONE_CODE"
    assert m.crs_in == "EPSG:26915"


def test_mapping_translates_known_codes(sample_mapping_yaml):
    m = load_mapping(sample_mapping_yaml)
    assert m.translate("R1") == "res_low_house"
    assert m.translate("B4") == "com_high"
    assert m.translate("I1") == "industrial"


def test_mapping_unmapped_skip_returns_none(sample_mapping_yaml):
    m = load_mapping(sample_mapping_yaml)
    assert m.translate("UNKNOWN_CODE") is None


def test_mapping_default_strategy(tmp_path):
    """If `unmapped: default: <zone>` then unknown codes get the default."""
    content = """city: test
source_url: https://example.test
source_field: Z
crs_in: EPSG:4326
last_validated: 2026-05-24
mappings:
  X: res_low_house
unmapped:
  default: industrial
"""
    p = tmp_path / "t.yaml"
    p.write_text(content, encoding="utf-8")
    m = load_mapping(p)
    assert m.translate("X") == "res_low_house"
    assert m.translate("ANYTHING_ELSE") == "industrial"


def test_mapping_strategy_enum():
    """UnknownCodeStrategy.SKIP and .DEFAULT exist."""
    assert UnknownCodeStrategy.SKIP
    assert UnknownCodeStrategy.DEFAULT
