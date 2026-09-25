"""Tests del generador de teselas vectoriales (shared/tiles.py).

Las teselas se decodifican con mapbox-vector-tile (dependencia de dev): así se
verifica el encoder propio contra una implementación independiente del spec.
"""
import gzip
import json
import math
import os
import sys

import mapbox_vector_tile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from shared.compact import write_compact
from shared.registry import load_manifest, save_manifest_entry
from shared.tiles import (
    EXTENT,
    MAXZOOM,
    MINZOOM,
    build_city_tiles,
    build_tiles,
)


def _tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    lr = math.radians(lat)
    y = (1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n
    return int(x), int(y)


def _square(lat, lon, half_deg):
    return [[lat - half_deg, lon - half_deg], [lat - half_deg, lon + half_deg],
            [lat + half_deg, lon + half_deg], [lat + half_deg, lon - half_deg],
            [lat - half_deg, lon - half_deg]]


def _read(out_dir, z, x, y):
    path = out_dir / str(z) / str(x) / f"{y}.mvt.gz"
    if not path.exists():
        return {}
    return mapbox_vector_tile.decode(gzip.decompress(path.read_bytes()),
                                     default_options={"y_coord_down": True})


def _features(out_dir, z, lat, lon, layer):
    x, y = _tile_xy(lat, lon, z)
    return _read(out_dir, z, x, y).get(layer, {}).get("features", [])


# Un bloque grande (≈ 800 m de lado), una casa chica (≈ 15 m) y un parking chico
LAT, LON = 44.97, -93.27
ZONING = {
    "res_low_house": [
        {"id": 1, "name": "Bloque", "coords": _square(LAT, LON, 0.004), "cs2_key": "res_low_house", "method": "landuse"},
        {"id": 2, "name": "", "coords": _square(LAT + 0.001, LON + 0.001, 0.00007), "cs2_key": "res_low_house"},
    ],
    "com_low": [
        {"id": 3, "name": "Tienda <b>", "coords": _square(LAT - 0.002, LON, 0.0005), "cs2_key": "com_low", "method": "area"},
    ],
}
EXTERNAL = {
    "res_low_house": [
        {"id": "g0", "name": "", "coords": _square(LAT + 0.002, LON - 0.002, 0.0004), "cs2_key": "res_low_house",
         "method": "area", "src": "google", "conf": 0.8125},
    ],
}
VIAL = {
    "major": [{"id": 10, "name": "Hennepin Avenue", "coords": [[LAT - 0.01, LON], [LAT + 0.01, LON]], "cs2_key": "major", "bridge": True}],
    "pedestrian": [{"id": 11, "name": "", "coords": [[LAT, LON - 0.001], [LAT, LON + 0.001]], "cs2_key": "pedestrian", "bridge": False}],
    "local": [{"id": 12, "name": "", "coords": [[LAT + 0.001, LON - 0.001], [LAT + 0.001, LON + 0.001]], "cs2_key": "local", "bridge": False}],
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("tiles") / "tiles"
    info = build_tiles(out, zoning=ZONING, external=EXTERNAL, vial=VIAL)
    return out, info


def test_tiles_json(built):
    out, info = built
    on_disk = json.loads((out / "tiles.json").read_text(encoding="utf-8"))
    assert on_disk == info
    assert info["format"] == "cs2-tiles"
    assert (info["minzoom"], info["maxzoom"]) == (MINZOOM, MAXZOOM)
    assert info["layers"] == ["zoning", "vial"]
    # Los externos se suman a su zona, como en el visor
    assert info["counts"]["zoning"] == {"res_low_house": 3, "com_low": 1}
    assert info["counts"]["vial"] == {"major": 1, "pedestrian": 1, "local": 1}
    west, south, east, north = info["bounds"]
    assert west < LON < east and south < LAT < north
    # La lista de teselas coincide con los archivos
    listed = {f"{z}/{name}" for z, names in info["tiles"].items() for name in names}
    files = {p.relative_to(out).as_posix()[: -len(".mvt.gz")] for p in out.rglob("*.mvt.gz")}
    assert listed == files


def test_properties_survive_encoding(built):
    out, _ = built
    zoning = {f["properties"]["id"]: f["properties"] for f in _features(out, 14, LAT, LON, "zoning")}
    assert zoning[1] == {"k": "res_low_house", "id": 1, "n": "Bloque", "m": "landuse"}
    assert zoning[2] == {"k": "res_low_house", "id": 2}          # sin nombre: sin "n"
    assert zoning[3]["n"] == "Tienda <b>"                        # el escape es cosa del visor
    ext = [p for p in zoning.values() if p["id"] == "g0"]
    assert ext == [{"k": "res_low_house", "id": "g0", "m": "area", "s": "google", "c": 0.8125}]

    vial = [f["properties"] for f in _features(out, 14, LAT, LON, "vial")]
    assert {"k": "major", "n": "Hennepin Avenue", "b": True} in vial
    assert {"k": "pedestrian"} in vial


def test_polygon_geometry_and_winding(built):
    out, _ = built
    feats = {f["properties"]["id"]: f for f in _features(out, 14, LAT, LON, "zoning")}
    geom = feats[3]["geometry"]
    assert geom["type"] == "Polygon"                  # anillo exterior bien orientado
    ring = geom["coordinates"][0]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    # 0.001° de longitud a z14 = 2^14 · 4096 / 360 · 0.001 ≈ 186 unidades
    assert 180 <= max(xs) - min(xs) <= 192
    assert 255 <= max(ys) - min(ys) <= 270            # mercator estira la latitud (÷ cos 45°)


def test_small_houses_and_minor_roads_wait_for_their_zoom(built):
    out, _ = built
    for z in range(MINZOOM, MAXZOOM + 1):
        ids = {f["properties"]["id"] for f in _features(out, z, LAT, LON, "zoning")}
        kinds = {f["properties"]["k"] for f in _features(out, z, LAT, LON, "vial")}
        assert 1 in ids                                # el bloque grande siempre
        assert (2 in ids) == (z >= 13)                 # casa < 3000 m² → tier chico
        assert ("pedestrian" in kinds) == (z >= 13)
        assert ("local" in kinds) == (z >= 11)
        assert "major" in kinds


def test_subpixel_features_are_dropped_below_maxzoom(tmp_path):
    tiny = {"com_low": [{"id": 9, "name": "", "coords": _square(LAT, LON, 0.00002), "cs2_key": "com_low"}]}
    build_tiles(tmp_path / "t", zoning=tiny)
    assert _features(tmp_path / "t", 9, LAT, LON, "zoning") == []
    assert len(_features(tmp_path / "t", 14, LAT, LON, "zoning")) == 1


def test_long_line_is_clipped_into_every_tile_it_crosses(tmp_path):
    z = 14
    lon0, lon1 = -93.30, -93.24                         # ~5 km: varias teselas de z14
    vial = {"major": [{"id": 1, "name": "", "coords": [[LAT, lon0], [LAT, lon1]], "cs2_key": "major", "bridge": False}]}
    build_tiles(tmp_path / "t", vial=vial)
    x0, y = _tile_xy(LAT, lon0, z)
    x1, _ = _tile_xy(LAT, lon1, z)
    assert x1 - x0 >= 2
    for x in range(x0, x1 + 1):
        feats = _read(tmp_path / "t", z, x, y)["vial"]["features"]
        assert len(feats) == 1
        xs = [p[0] for p in feats[0]["geometry"]["coordinates"]]
        # recortada al área de la tesela + buffer
        assert min(xs) >= -64 - 1 and max(xs) <= EXTENT + 64 + 1


def test_output_is_deterministic(tmp_path):
    a = build_tiles(tmp_path / "a", zoning=ZONING, vial=VIAL)
    b = build_tiles(tmp_path / "b", zoning=ZONING, vial=VIAL)
    assert a["hash"] == b["hash"]
    for p in (tmp_path / "a").rglob("*.mvt.gz"):
        assert p.read_bytes() == (tmp_path / "b" / p.relative_to(tmp_path / "a")).read_bytes()


def test_rebuild_replaces_old_tiles(tmp_path):
    out = tmp_path / "t"
    build_tiles(out, zoning=ZONING, vial=VIAL)
    stale = out / "3" / "0" / "0.mvt.gz"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"x")
    build_tiles(out, zoning=ZONING)
    assert not stale.exists()


def test_empty_input_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        build_tiles(tmp_path / "t")


def _city(tmp_path, slug="testville"):
    city = tmp_path / "cities" / slug
    city.mkdir(parents=True)
    return city


def test_build_city_tiles_updates_manifest(tmp_path):
    city = _city(tmp_path)
    for module, layers, name in (("zoning", ZONING, "datos_zonificacion.json"),
                                 ("vial", VIAL, "datos_vial.json")):
        total = write_compact(city / name, module, layers)
        save_manifest_entry(tmp_path, "testville", module, city / name, total)

    info = build_city_tiles(tmp_path, "testville", quiet=True)

    assert (city / "tiles" / "tiles.json").exists()
    manifest = load_manifest(tmp_path, "testville")
    assert manifest["tiles"] == {"path": "tiles", "hash": info["hash"], "minzoom": MINZOOM,
                                 "maxzoom": MAXZOOM, "layers": ["zoning", "vial"]}
    # Las teselas no son un módulo: la landing no las cuenta como features
    assert "tiles" not in manifest["modules"]


def test_build_city_tiles_reads_legacy_js(tmp_path):
    city = _city(tmp_path)
    legacy = city / "datos_zonificacion.js"
    legacy.write_text("\n".join(f"const DATA_{k.upper()} = {json.dumps(v)};" for k, v in ZONING.items()),
                      encoding="utf-8")
    save_manifest_entry(tmp_path, "testville", "zoning", legacy, 3)
    info = build_city_tiles(tmp_path, "testville", quiet=True)
    assert info["counts"]["zoning"] == {"res_low_house": 2, "com_low": 1}


def test_build_city_tiles_without_heavy_modules(tmp_path):
    _city(tmp_path)
    assert build_city_tiles(tmp_path, "testville", quiet=True) is None


def test_build_city_tiles_with_only_empty_layers_clears_old_tiles(tmp_path):
    city = _city(tmp_path)
    total = write_compact(city / "datos_zonificacion.json", "zoning", ZONING)
    save_manifest_entry(tmp_path, "testville", "zoning", city / "datos_zonificacion.json", total)
    build_city_tiles(tmp_path, "testville", quiet=True)
    assert (city / "tiles").exists()

    # Una nueva extracción que no encontró nada
    write_compact(city / "datos_zonificacion.json", "zoning", {"res_low_house": [], "com_low": []})
    save_manifest_entry(tmp_path, "testville", "zoning", city / "datos_zonificacion.json", 0)
    assert build_city_tiles(tmp_path, "testville", quiet=True) is None
    assert not (city / "tiles").exists()
    assert "tiles" not in load_manifest(tmp_path, "testville")


# Estacionamiento real de Madison (OSM 200198860): se toca a sí mismo, y a z9-z10
# la simplificación lo parte en un MultiPolygon de dos partes.
SELF_TOUCHING_LOT = [
    [43.05512, -89.46816], [43.05517, -89.46806], [43.0552, -89.46801], [43.05474, -89.46739],
    [43.05474, -89.46703], [43.05503, -89.46664], [43.05517, -89.46664], [43.05517, -89.46658],
    [43.05536, -89.46658], [43.05536, -89.46664], [43.05571, -89.46664], [43.05534, -89.46715],
    [43.05572, -89.46768], [43.05576, -89.46764], [43.05581, -89.46771], [43.05589, -89.4676],
    [43.05577, -89.46743], [43.05604, -89.46707], [43.056, -89.46702], [43.05601, -89.46698],
    [43.05601, -89.46691], [43.05601, -89.46685], [43.056, -89.46676], [43.05605, -89.46682],
    [43.05619, -89.46663], [43.05615, -89.46657], [43.05646, -89.46657], [43.05646, -89.46663],
    [43.05655, -89.46664], [43.05683, -89.46704], [43.05686, -89.46699], [43.05689, -89.46703],
    [43.05684, -89.4671], [43.05703, -89.46737], [43.05702, -89.46773], [43.05719, -89.46773],
    [43.05719, -89.46648], [43.05714, -89.46648], [43.05714, -89.46642], [43.05497, -89.46642],
    [43.05465, -89.46642], [43.05465, -89.46651], [43.05458, -89.46651], [43.05458, -89.46676],
    [43.05454, -89.4668], [43.05451, -89.46675], [43.05431, -89.46702], [43.05409, -89.46671],
    [43.05405, -89.46675], [43.05404, -89.46673], [43.05395, -89.46684], [43.05428, -89.46728],
    [43.05436, -89.46717], [43.0544, -89.46722], [43.05452, -89.46706], [43.05448, -89.46701],
    [43.05458, -89.46686], [43.05458, -89.46736], [43.05442, -89.46759], [43.05499, -89.46835],
]


def test_polygon_split_by_simplification_keeps_the_rest_aligned(tmp_path):
    """Regresión: si simplify parte un polígono en MultiPolygon, las features que
    vienen después no pueden quedarse con la geometría de otra."""
    lat, lon = 43.06, -89.40
    after = _square(lat, lon, 0.003)
    zoning = {"prk_surface": [
        {"id": 1, "name": "", "coords": SELF_TOUCHING_LOT, "cs2_key": "prk_surface"},
        {"id": 2, "name": "", "coords": after, "cs2_key": "prk_surface"},
    ]}
    build_tiles(tmp_path / "t", zoning=zoning)

    def world_px(la, lo, z):
        n = 2 ** z * EXTENT
        lr = math.radians(la)
        return (lo + 180) / 360 * n, (1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n

    for z in range(MINZOOM, MAXZOOM + 1):
        x, y = _tile_xy(lat, lon, z)
        feats = {f["properties"]["id"]: f for f in _read(tmp_path / "t", z, x, y)["zoning"]["features"]}
        # Los vértices del cuadrado (id 2) tienen que caer donde está el cuadrado,
        # no donde está otra feature (recortados al borde de la tesela + buffer)
        x0, y1 = world_px(lat - 0.003, lon - 0.003, z)
        x1, y0 = world_px(lat + 0.003, lon + 0.003, z)
        lo_x, hi_x = max(x0 - x * EXTENT, -64), min(x1 - x * EXTENT, EXTENT + 64)
        lo_y, hi_y = max(y0 - y * EXTENT, -64), min(y1 - y * EXTENT, EXTENT + 64)
        for px, py in feats[2]["geometry"]["coordinates"][0]:
            assert lo_x - 2 <= px <= hi_x + 2 and lo_y - 2 <= py <= hi_y + 2, (z, px, py)
