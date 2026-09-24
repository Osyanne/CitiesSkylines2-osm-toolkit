"""Test the CLI entry point — argument parsing + orchestration."""
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from official_zoning.extract import main


def test_main_requires_city_arg(capsys):
    """Without --city, CLI exits with usage error."""
    with patch.object(sys, "argv", ["extract-official-zoning"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code != 0


def test_main_rejects_unknown_city(capsys):
    """City not in SOURCES registry exits with error."""
    with patch.object(sys, "argv", ["extract-official-zoning", "--city", "atlantis"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code != 0


REAL_MPLS_MANIFEST = Path(__file__).resolve().parents[2] / "visualizer" / "cities" / "minneapolis" / "manifest.json"


def _fake_mpls_gdf():
    import geopandas as gpd
    from shapely.geometry import Polygon

    # Mock GDF uses the real Mpls 2040 Plan schema: Land_Use_C in EPSG:3857.
    # UN1 maps to res_low_house in minneapolis.yaml.
    return gpd.GeoDataFrame(
        {
            "Land_Use_C": ["UN1"],
            "geometry": [Polygon([(-10380000, 5610000), (-10379900, 5610000), (-10379900, 5610100), (-10380000, 5610100)])],
        },
        crs="EPSG:3857",
    )


def _run_mpls(tmp_path, extra_args):
    fake_cache = tmp_path / "mpls.zip"
    fake_cache.write_bytes(b"fake")
    with patch("official_zoning.sources.minneapolis.download", return_value=fake_cache) as m_dl, \
         patch("official_zoning.sources.minneapolis.read", return_value=_fake_mpls_gdf()) as m_rd:
        with patch.object(sys, "argv", ["extract-official-zoning", "--city", "minneapolis", *extra_args]):
            main()
    return fake_cache, m_dl, m_rd


def test_main_calls_source_pipeline_with_minneapolis(tmp_path, monkeypatch):
    """With --city minneapolis, the Mpls source's download + read are called."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    real_manifest_before = REAL_MPLS_MANIFEST.read_bytes() if REAL_MPLS_MANIFEST.exists() else None

    fake_cache, m_dl, m_rd = _run_mpls(tmp_path, ["--out-dir", str(out_dir)])

    m_dl.assert_called_once()
    m_rd.assert_called_once_with(fake_cache)
    expected_out = out_dir / "datos_zonificacion_official.js"
    assert expected_out.exists()
    # --out-dir fuera del visualizer: el manifest real del repo no se toca
    if real_manifest_before is not None:
        assert REAL_MPLS_MANIFEST.read_bytes() == real_manifest_before


def test_main_registers_manifest_under_visualizer_root(tmp_path):
    """Sin --out-dir, el archivo va a <visualizer-root>/cities/<slug>/ y ahí se
    registra en el manifest."""
    vis_root = tmp_path / "visualizer"

    _run_mpls(tmp_path, ["--visualizer-root", str(vis_root)])

    city_dir = vis_root / "cities" / "minneapolis"
    assert (city_dir / "datos_zonificacion_official.js").exists()
    import json
    manifest = json.loads((city_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "official_zoning" in manifest["modules"]
