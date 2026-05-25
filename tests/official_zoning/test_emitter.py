"""Test the JS emitter — writes datos_zonificacion_official.js compatible with viewer."""
import geopandas as gpd
import json
from shapely.geometry import Polygon
from official_zoning.emitter import emit


def test_emit_writes_js_file(tmp_path):
    gdf = gpd.GeoDataFrame(
        {
            "cs2_zone": ["res_low_house", "com_high"],
            "geometry": [
                Polygon([(-93.27, 44.97), (-93.26, 44.97), (-93.26, 44.98), (-93.27, 44.98)]),
                Polygon([(-93.25, 44.96), (-93.24, 44.96), (-93.24, 44.97), (-93.25, 44.97)]),
            ],
        },
        crs="EPSG:4326",
    )
    out = tmp_path / "datos_zonificacion_official.js"
    emit(gdf, out, source_name="Test City Planning")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "DATA_OFFICIAL_RES_LOW_HOUSE" in text
    assert "DATA_OFFICIAL_COM_HIGH" in text
    assert "Test City Planning" in text


def test_emit_groups_polygons_by_zone(tmp_path):
    gdf = gpd.GeoDataFrame(
        {
            "cs2_zone": ["res_low_house", "res_low_house", "industrial"],
            "geometry": [
                Polygon([(-93.27, 44.97), (-93.26, 44.97), (-93.26, 44.98), (-93.27, 44.98)]),
                Polygon([(-93.25, 44.96), (-93.24, 44.96), (-93.24, 44.97), (-93.25, 44.97)]),
                Polygon([(-93.23, 44.95), (-93.22, 44.95), (-93.22, 44.96), (-93.23, 44.96)]),
            ],
        },
        crs="EPSG:4326",
    )
    out = tmp_path / "datos_zonificacion_official.js"
    emit(gdf, out, source_name="X")
    text = out.read_text(encoding="utf-8")
    import re
    res_match = re.search(r"var DATA_OFFICIAL_RES_LOW_HOUSE = (\[.*?\]);", text, re.DOTALL)
    assert res_match
    res_list = json.loads(res_match.group(1))
    assert len(res_list) == 2
    ind_match = re.search(r"var DATA_OFFICIAL_INDUSTRIAL = (\[.*?\]);", text, re.DOTALL)
    assert ind_match
    ind_list = json.loads(ind_match.group(1))
    assert len(ind_list) == 1


def test_emit_truncates_coords_to_5_decimals(tmp_path):
    """Same convention as zoning module — 5 decimals (~1m precision)."""
    gdf = gpd.GeoDataFrame(
        {
            "cs2_zone": ["res_low_house"],
            "geometry": [Polygon([(-93.123456789, 44.987654321), (-93.123, 44.988), (-93.124, 44.988), (-93.123456789, 44.987654321)])],
        },
        crs="EPSG:4326",
    )
    out = tmp_path / "datos_zonificacion_official.js"
    emit(gdf, out, source_name="X")
    text = out.read_text(encoding="utf-8")
    assert "-93.12346" in text or "-93.12345" in text  # one of the truncations
    assert "-93.123456789" not in text  # raw precision must be gone
