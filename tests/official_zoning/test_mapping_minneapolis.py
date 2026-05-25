"""Test the Minneapolis mapping YAML — validates structure and known 2040 Plan codes."""
from pathlib import Path
from official_zoning.mapping import load_mapping


MAPPING_PATH = Path(__file__).parent.parent.parent / "src" / "official_zoning" / "mappings" / "minneapolis.yaml"


def test_mapping_loads():
    m = load_mapping(MAPPING_PATH)
    assert m.city == "minneapolis"
    assert m.source_field == "Land_Use_C"
    assert m.crs_in == "EPSG:3857"


def test_mapping_covers_urban_neighborhood():
    """UN1-UN3 are the residential density tiers in Mpls 2040 Plan."""
    m = load_mapping(MAPPING_PATH)
    for code in ("UN1", "UN2", "UN3"):
        assert m.translate(code) is not None, f"missing mapping for {code}"


def test_mapping_covers_mixed_use():
    """CM1-CM4 are the corridor/community/destination mixed-use tiers."""
    m = load_mapping(MAPPING_PATH)
    for code in ("CM1", "CM2", "CM3", "CM4"):
        assert m.translate(code) is not None, f"missing mapping for {code}"


def test_mapping_covers_downtown_and_production():
    m = load_mapping(MAPPING_PATH)
    for code in ("DT1", "DT2"):
        assert m.translate(code) == "com_high"
    for code in ("PR1", "PR2"):
        assert m.translate(code) == "industrial"


def test_mapping_covers_residence_transitions():
    """RM1-RM3 are residence + adjacent-uses transitions."""
    m = load_mapping(MAPPING_PATH)
    for code in ("RM1", "RM2", "RM3"):
        assert m.translate(code) == "res_mixed"


def test_mapping_transportation_to_parking():
    m = load_mapping(MAPPING_PATH)
    assert m.translate("TR1") == "prk_surface"
