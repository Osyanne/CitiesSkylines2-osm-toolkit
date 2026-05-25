"""Test the Minneapolis mapping YAML — validates structure and known codes."""
from pathlib import Path
from official_zoning.mapping import load_mapping


MAPPING_PATH = Path(__file__).parent.parent.parent / "src" / "official_zoning" / "mappings" / "minneapolis.yaml"


def test_mapping_loads():
    m = load_mapping(MAPPING_PATH)
    assert m.city == "minneapolis"
    assert m.source_field in ("ZONE_CODE", "ZONING")
    assert m.crs_in == "EPSG:26915"


def test_mapping_covers_core_residential():
    m = load_mapping(MAPPING_PATH)
    # Mpls Chapter 530 — core residential districts
    for code in ("R1", "R1A", "R2", "R2B", "R3", "R4", "R5", "R6"):
        assert m.translate(code) is not None, f"missing mapping for {code}"


def test_mapping_covers_core_commercial():
    m = load_mapping(MAPPING_PATH)
    for code in ("B1", "B2", "B3", "B4"):
        assert m.translate(code) is not None, f"missing mapping for {code}"


def test_mapping_covers_industrial():
    m = load_mapping(MAPPING_PATH)
    for code in ("I1", "I2", "I3"):
        assert m.translate(code) == "industrial"
