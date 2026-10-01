"""Offline selector parity and real pyosmium extraction, including courtyards."""
import re
import xml.etree.ElementTree as ET

import pytest

from zoning.zones import build_pbf_filters, build_queries


def overpass_selects(query, kind, tags):
    """Evaluate the basic selectors emitted by these two context queries."""
    for selector in re.findall(rf"\b{kind}((?:\[[^\]]+\])+)", query):
        matches = True
        for term in re.findall(r"\[([^\]]+)\]", selector):
            if term.startswith("!"):
                matches &= term[2:-1] not in tags
                continue
            key, op, value = re.fullmatch(r'"([^"]+)"\s*(?:(=|!=|~)\s*"([^"]*)")?', term).groups()
            actual = tags.get(key)
            if op is None:
                matches &= actual is not None
            elif op == "=":
                matches &= actual == value
            elif op == "!=":
                matches &= actual != value
            else:
                matches &= actual is not None and re.search(value, actual) is not None
        if matches:
            return True
    return False


@pytest.mark.parametrize("kind,tags,buildings,commercial", [
    ("way", {"building": "house"}, True, False),
    ("relation", {"building": "yes"}, True, False),
    ("way", {"building": "garage"}, True, False),
    ("way", {"building": "no"}, False, False),
    ("way", {"building:part": "yes"}, False, False),
    ("way", {"building": "yes", "building:part": "yes"}, False, False),
    ("way", {"landuse": "residential"}, False, False),
    ("node", {"shop": "bakery"}, False, True),
    ("node", {"amenity": "restaurant"}, False, True),
    ("node", {"amenity": "marketplace"}, False, True),
    ("node", {"amenity": "school"}, False, False),
    ("node", {"tourism": "hotel"}, False, True),
    ("way", {"shop": "bakery"}, False, False),
])
def test_context_sources_have_same_selectors(kind, tags, buildings, commercial):
    queries = build_queries("44,-94,46,-92")
    filters = build_pbf_filters((44, -94, 46, -92))
    for name, expected in [("morphology_buildings", buildings),
                           ("morphology_commercial_nodes", commercial)]:
        assert overpass_selects(queries[name], kind, tags) == expected
        assert any(c.matches(kind, tags) for c in filters[name].clauses.values()) == expected
        assert not filters[name].spatial_joins


def test_pbf_context_preserves_relation_courtyard(tmp_path):
    from shared.pbf_client import query_batch
    from zoning.morphology import footprint_from_element

    root = ET.Element("osm", version="0.6")
    coords = [(0, 0), (0.003, 0), (0.003, 0.003), (0, 0.003),
              (0.001, 0.001), (0.002, 0.001), (0.002, 0.002), (0.001, 0.002)]
    for i, (x, y) in enumerate(coords, 1):
        ET.SubElement(root, "node", id=str(i), lon=str(-93 + x), lat=str(45 + y), version="1")
    shop = ET.SubElement(root, "node", id="9", lon="-92.9985", lat="45.0015", version="1")
    ET.SubElement(shop, "tag", k="shop", v="bakery")
    for id, refs in [(1, [1, 2, 3, 4, 1]), (2, [5, 6, 7, 8, 5])]:
        way = ET.SubElement(root, "way", id=str(id), version="1")
        for ref in refs:
            ET.SubElement(way, "nd", ref=str(ref))
    rel = ET.SubElement(root, "relation", id="1", version="1")
    for ref, role in [(1, "outer"), (2, "inner")]:
        ET.SubElement(rel, "member", type="way", ref=str(ref), role=role)
    for k, v in [("type", "multipolygon"), ("building", "yes")]:
        ET.SubElement(rel, "tag", k=k, v=v)
    source = tmp_path / "courtyard.osm"
    ET.ElementTree(root).write(source, encoding="utf-8", xml_declaration=True)
    bbox = (44.9, -93.1, 45.1, -92.9)
    specs = {k: v for k, v in build_pbf_filters(bbox).items() if k.startswith("morphology_")}
    result = query_batch(source, bbox, specs)
    buildings = result["morphology_buildings"]["elements"]
    assert [(el["type"], el["id"]) for el in buildings] == [("relation", 1)]
    geom, complete = footprint_from_element(buildings[0])
    assert complete and len(geom.interiors) == 1
    assert geom.area == pytest.approx(0.000008)
    assert [n["id"] for n in result["morphology_commercial_nodes"]["elements"]] == [9]
