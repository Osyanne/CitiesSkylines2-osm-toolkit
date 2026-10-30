"""Tests de la revisión de cajas del lote (shared/batch.py), sin red ni PBF."""
import os
import sys

from shapely.geometry import box

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from shared.batch import city_problems

MINNESOTA = {"north-america/us/minnesota": box(-97.5, 43.4, -89.4, 49.4)}
IRELAND = {"europe/ireland-and-northern-ireland": box(-11, 51, -5, 56)}


def _entry(bbox, center=None, region="north-america/us/minnesota"):
    s, w, n, e = bbox
    return {
        "bbox": bbox,
        "center": center or [(s + n) / 2, (w + e) / 2],
        "pbf_region": region,
    }


def test_good_box_has_no_problems():
    assert city_problems(_entry([44.86, -93.38, 45.05, -93.17]), MINNESOTA) == []


def test_box_in_meters_is_out_of_range():
    """Elche llegó en metros Web Mercator (EPSG:3857)."""
    problems = city_problems(_entry([4_600_000, -80_000, 4_610_000, -70_000]), MINNESOTA)
    assert len(problems) == 1 and "metros" in problems[0]


def test_lon_lat_order_out_of_range():
    """St. Louis llegó en lon/lat: -90,3 no es una latitud."""
    problems = city_problems(_entry([-90.3, 38.5, -90.1, 38.7]), MINNESOTA)
    assert len(problems) == 1 and "lon/lat" in problems[0]


def test_lon_lat_order_in_range_is_caught_by_the_region():
    """Galway en lon/lat cae en el océano Índico, lejos del extracto de Irlanda."""
    entry = _entry([-9.1, 53.2, -9.0, 53.3], region="europe/ireland-and-northern-ireland")
    problems = city_problems(entry, IRELAND)
    assert len(problems) == 1 and "0%" in problems[0]


def test_without_region_shapes_only_the_offline_checks_run():
    entry = _entry([-9.1, 53.2, -9.0, 53.3], region="europe/ireland-and-northern-ireland")
    assert city_problems(entry) == []


def test_box_bigger_than_the_trimmed_requests():
    """El pedido original de Kyiv (56 × 45 km) se recortó."""
    entry = _entry([50.140954, 30.199005, 50.642590, 30.836735], region="europe/ukraine")
    problems = city_problems(entry)
    assert len(problems) == 1 and "56 km" in problems[0]


def test_center_outside_the_box():
    problems = city_problems(_entry([44.86, -93.38, 45.05, -93.17], center=[46.0, -93.27]), MINNESOTA)
    assert len(problems) == 1 and "centro" in problems[0]


def test_region_unknown_to_geofabrik():
    entry = _entry([44.86, -93.38, 45.05, -93.17], region="north-america/us/minesota")
    problems = city_problems(entry, MINNESOTA)
    assert len(problems) == 1 and "north-america/us/minesota" in problems[0]


def test_box_that_needs_the_neighbouring_extract():
    """Detroit cruza a Windsor: con Michigan solo, media caja queda sin datos."""
    michigan = {"north-america/us/michigan": box(-90, 42.36, -82, 48)}
    entry = _entry([42.30, -83.13, 42.42, -82.945], region="north-america/us/michigan")
    problems = city_problems(entry, michigan)
    assert len(problems) == 1 and "50%" in problems[0]


def test_missing_pbf_region():
    entry = _entry([44.86, -93.38, 45.05, -93.17])
    del entry["pbf_region"]
    problems = city_problems(entry)
    assert len(problems) == 1 and "pbf_region" in problems[0]
