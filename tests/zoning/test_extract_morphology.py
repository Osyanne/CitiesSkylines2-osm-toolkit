import copy
import csv
from collections import defaultdict

import pytest
from shapely.geometry import box

from tests.zoning.test_morphology import CONFIG, wgs
from zoning import extract


def building(id, value="house", levels=None, geom=None, type="way", **tags):
    geom = wgs(box(0, 0, 10, 12)) if geom is None else geom
    tags = {"building": value, "name": f"Building {id}", **tags}
    if levels is not None:
        tags["building:levels"] = str(levels)
    ring = [{"lon": x, "lat": y} for x, y in geom.exterior.coords]
    return {"type": type, "id": id, "tags": tags,
            **({"geometry": ring} if type == "way" else
               {"members": [{"type": "way", "role": "outer", "geometry": ring}]})}


def run_pass(elements, *, methods=None, keys=None, context=None, nodes=None, report=None,
             bbox=(44, -94, 46, -92)):
    output = defaultdict(list)
    items = {}
    for i, el in enumerate(elements):
        key = keys[i] if keys else "res_low_house"
        item = extract.make_item(el, extract.extract_coords(el), key)
        if methods and methods[i]:
            item["method"] = methods[i]
        output[key].append(item)
        items[(el["type"], el["id"])] = (el, item)
    stats = extract._refine_residential_density(
        {"morphology_buildings": context if context is not None else elements,
         "morphology_commercial_nodes": nodes or []},
        output, items, bbox=bbox, config=CONFIG, report_path=report,
    )
    return output, stats


@pytest.mark.parametrize("value,levels,method,key", [
    ("yes", 5, "landuse", "res_med"), ("yes", 5, "area", "res_med"),
    ("house", 3, None, "res_low_house"), ("house", 4, None, "res_med"),
    ("house", 9, None, "res_high"),
])
def test_height_pass_preserves_identity_and_geometry(value, levels, method, key):
    el = building(1, value, levels)
    expected = extract.make_item(el, extract.extract_coords(el), key)
    output, stats = run_pass([el], methods=[method])
    assert len(output[key]) == 1
    item = output[key][0]
    assert {k: item[k] for k in ("id", "name", "coords", "cs2_key")} == expected
    assert set(item) <= {"id", "name", "coords", "cs2_key", "method"}
    if key != "res_low_house":
        assert item["method"] == "height"
        assert not output["res_low_house"]
    assert stats["candidates"] == 1


def test_height_from_height_tag_and_contained_commercial_nodes():
    el = building(1, "yes", height="15")
    node = {"type": "node", "id": 50, "lon": -93 + 0.00006, "lat": 45 + 0.00005,
            "tags": {"shop": "bakery"}}
    output, _ = run_pass([el], methods=["landuse"], nodes=[node])
    assert output["res_mixed"][0]["method"] == "height"
    node["lon"] = -93.001  # nearby is not contained
    output, _ = run_pass([el], methods=["landuse"], nodes=[node])
    assert output["res_med"] and not output["res_mixed"]


def test_morphology_mixed_uses_shop_inside_footprint_but_not_courtyard():
    # Dense neighbours are context even if not classified/output themselves.
    context = [building(x * 7 + y, geom=wgs(box(x * 10, y * 12, x * 10 + 10, y * 12 + 12)))
               for x in range(7) for y in range(7)]
    candidate = context[24]
    center = wgs(box(30, 36, 40, 48)).centroid
    node = {"type": "node", "id": 99, "lon": center.x, "lat": center.y, "tags": {"amenity": "cafe"}}
    output, _ = run_pass([candidate], context=context, nodes=[node])
    assert output["res_mixed"][0]["method"] == "morphology"
    assert sum(map(len, output.values())) == 1

    relation = building(100, "yes", 5, type="relation", geom=wgs(box(-30, -30, 30, 30)))
    hole = building(101, geom=wgs(box(-15, -15, 15, 15)))["geometry"]
    relation["members"].append({"type": "way", "role": "inner", "geometry": hole})
    node.update(lon=-93, lat=45)
    output, _ = run_pass([relation], methods=["landuse"], nodes=[node])
    assert output["res_med"] and not output["res_mixed"]


def test_height_high_is_not_lowered_to_mixed_by_shop():
    output, _ = run_pass([building(1, levels=9, shop="bakery")])
    assert output["res_high"] and not output["res_mixed"]


def test_commercial_node_batch_matches_only_containing_building():
    els = [building(i, levels=4, geom=wgs(box(i * 100, 0, i * 100 + 10, 12))) for i in range(3)]
    pt = wgs(box(100, 0, 110, 12)).centroid
    nodes = [{"type": "node", "id": 90, "lon": pt.x, "lat": pt.y, "tags": {"shop": "bakery"}}]
    output, _ = run_pass(els, nodes=nodes)
    assert [item["id"] for item in output["res_mixed"]] == [1]
    assert {item["id"] for item in output["res_med"]} == {0, 2}


def test_commercial_nodes_without_eligible_candidates_do_not_crash():
    nodes = [{"type": "node", "id": 90, "lon": -93, "lat": 45, "tags": {"shop": "bakery"}}]
    output, stats = run_pass([building(1, "detached", 9)], nodes=nodes)
    assert stats["candidates"] == 0
    assert output["res_low_house"][0]["id"] == 1


def test_protected_items_never_change():
    els = [building(1, "detached", 9), building(2, "bungalow", 9),
           building(3, "apartments", 9), building(4, "terrace", 9),
           building(5, "yes", 9), building(6, "house", 9, landuse="residential")]
    output, stats = run_pass(els, methods=[None, None, None, None, "amenity", None],
                             keys=["res_low_house"] * 2 + ["res_med", "res_row"] + ["res_low_house"] * 2)
    assert sum(map(len, output.values())) == 6
    assert len(output["res_low_house"]) == 4
    assert stats["candidates"] == 0


def test_morphology_and_csv_include_unchanged_candidates(tmp_path):
    els = [building(i, geom=wgs(box(i * 10, 0, i * 10 + 10, 12))) for i in range(7)]
    els.append(building(20, geom=wgs(box(200, 0, 210, 12))))
    report = tmp_path / "report.csv"
    output, stats = run_pass(els, report=report)
    assert len(output["res_row"]) == 7
    assert output["res_low_house"][0]["id"] == 20
    rows = list(csv.DictReader(report.open(encoding="utf-8", newline="")))
    assert len(rows) == 8
    assert rows[0]["reason"] == "attached_row"
    assert rows[-1]["reason"] == "detached"
    assert rows[-1]["coverage"] == ""
    assert rows[0]["new_method"] == "morphology"
    assert stats["morphology"] == {"res_row": 7}


def test_known_low_height_can_be_row_with_report(tmp_path):
    els = [building(i, levels=2, geom=wgs(box(i * 10, 0, i * 10 + 10, 12))) for i in range(7)]
    report = tmp_path / "low.csv"
    output, stats = run_pass(els, report=report)
    assert len(output["res_row"]) == 7
    assert all(item["method"] == "morphology" for item in output["res_row"])
    rows = list(csv.DictReader(report.open(encoding="utf-8")))
    assert {row["reason"] for row in rows} == {"attached_low"}
    assert stats["height_candidates"] == 7
    assert stats["morphology_candidates"] == 7


def test_known_low_height_isolated_house_stays_low():
    output, _ = run_pass([building(1, levels=2)])
    assert len(output["res_low_house"]) == 1
    assert "method" not in output["res_low_house"][0]


@pytest.mark.parametrize("shop", [False, True])
def test_known_low_generic_in_dense_block_is_capped_at_row(shop):
    context = [building(x * 7 + y, "yes", 2,
                        geom=wgs(box(x * 10, y * 12, x * 10 + 10, y * 12 + 12)))
               for x in range(7) for y in range(7)]
    el = context[24]
    if shop:
        el["tags"]["shop"] = "bakery"
    output, _ = run_pass([el], methods=["landuse"], context=context)
    assert output["res_row"][0]["method"] == "morphology"
    assert not output["res_med"] and not output["res_mixed"]


def test_height_abstains_on_uncertain_relation_and_bbox_edge():
    el = building(1, "yes", 9, type="relation")
    el["members"].append({"type": "way", "role": "inner", "ref": 99})
    output, _ = run_pass([el], methods=["landuse"])
    assert len(output["res_low_house"]) == 1
    output, _ = run_pass([building(2, levels=9)], bbox=(45, -93, 46, -92))
    assert len(output["res_low_house"]) == 1


def test_raw_relation_holes_and_incomplete_rings():
    from zoning.morphology import footprint_from_element
    el = building(1, type="relation", geom=wgs(box(-30, -30, 30, 30)))
    hole = building(2, geom=wgs(box(-15, -15, 15, 15)))["geometry"]
    el["members"].append({"role": "inner", "type": "way", "geometry": hole})
    geom, complete = footprint_from_element(el)
    assert complete
    assert len(geom.interiors) == 1
    assert not geom.contains(wgs(box(-1, -1, 1, 1)).centroid)
    el["members"][1]["geometry"] = hole[:3]
    geom, complete = footprint_from_element(el)
    assert not complete


def test_fragmented_outer_ring_reconstructs():
    from zoning.morphology import footprint_from_element
    el = building(1, type="relation")
    ring = el["members"][0]["geometry"]
    el["members"] = [{"type": "way", "role": "outer", "geometry": ring[:3]},
                     {"type": "way", "role": "outer", "geometry": ring[2:]}]
    geom, complete = footprint_from_element(el)
    assert complete
    assert geom.area == pytest.approx(wgs(box(0, 0, 10, 12)).area)


def test_unknown_relation_role_is_uncertain():
    from zoning.morphology import footprint_from_element
    el = building(1, type="relation", geom=wgs(box(-30, -30, 30, 30)))
    hole = building(2, geom=wgs(box(-15, -15, 15, 15)))["geometry"]
    el["members"].append({"role": "", "type": "way", "geometry": hole})
    _, complete = footprint_from_element(el)
    assert not complete


def test_relation_preserves_building_island_inside_courtyard():
    from zoning.morphology import footprint_from_element
    el = building(1, type="relation", geom=wgs(box(0, 0, 30, 30)))
    for role, geom in [("inner", box(5, 5, 25, 25)), ("outer", box(10, 10, 20, 20))]:
        ring = building(2, geom=wgs(geom))["geometry"]
        el["members"].append({"role": role, "type": "way", "geometry": ring})
    geom, complete = footprint_from_element(el)
    assert complete
    assert geom.area / wgs(box(0, 0, 10, 10)).area == pytest.approx(6)
    assert geom.contains(wgs(box(12, 12, 13, 13)).centroid)


def test_extractor_end_to_end_typed_dedup_and_report(tmp_path, monkeypatch, capsys):
    from shared.compact import read_compact
    house = building(7, levels=4)
    generic = building(7, "yes", 9, type="relation")
    raw = {"residential_subtypes": [house, house], "generic_buildings": [generic],
           "morphology_buildings": [house, generic, building(99, "garage")],
           "morphology_commercial_nodes": []}
    report = tmp_path / "calibration.csv"
    args = extract.parse_args(["--bbox", "44,-94,46,-92", "--slug", "test",
                               "--source", "overpass", "--visualizer-root", str(tmp_path),
                               "--morphology-report", str(report)])
    monkeypatch.setattr(extract, "parse_args", lambda: args)
    monkeypatch.setattr(extract, "query_with_retry", lambda q, key: {"elements": copy.deepcopy(raw.get(key, []))})
    # Actual compact writer, manifest writer and tile builder operate in tmp_path.
    extract.main()
    layers, _ = read_compact(tmp_path / "cities/test/datos_zonificacion.json")
    assert len(layers["res_med"]) == 1
    assert len(layers["res_high"]) == 1
    assert sum(len(v) for v in layers.values()) == 2
    assert len(list(csv.DictReader(report.open(encoding="utf-8")))) == 2
    assert "height" in capsys.readouterr().out
