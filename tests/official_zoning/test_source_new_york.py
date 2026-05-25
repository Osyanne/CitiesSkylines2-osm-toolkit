"""Test the New York source module — downloader + parser."""
from pathlib import Path
import pytest
from official_zoning.source_interface import Source
from official_zoning.sources import new_york


def test_new_york_source_implements_protocol():
    """The module exposes download() + read() + slug per the Source protocol."""
    assert new_york.slug == "new_york"
    assert callable(new_york.download)
    assert callable(new_york.read)


def test_new_york_registered_in_sources():
    """The module is registered in the SOURCES dict."""
    from official_zoning.sources import SOURCES
    assert "new_york" in SOURCES
    assert SOURCES["new_york"] is new_york


def test_new_york_data_url():
    """The module must declare DATA_URL pointing to NYC open data portal."""
    assert hasattr(new_york, "DATA_URL")
    assert new_york.DATA_URL.startswith("https://")
    assert "nyc.gov" in new_york.DATA_URL or "planning.nyc" in new_york.DATA_URL or "opendata" in new_york.DATA_URL.lower()


@pytest.mark.network
def test_new_york_download_real_portal(tmp_path):
    """Network test — actually fetch the shapefile. Opt-in via -m network."""
    path = new_york.download(tmp_path, force_refresh=True)
    assert path.exists()
    assert path.stat().st_size > 100_000  # at least 100 KB


@pytest.mark.network
def test_new_york_read_returns_geodataframe(tmp_path):
    """Network test — download + read returns valid GDF with zoning district column."""
    import geopandas as gpd
    path = new_york.download(tmp_path)
    gdf = new_york.read(path)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert "ZONEDIST" in gdf.columns or "Zoning_District" in gdf.columns or "ZONE" in gdf.columns
    assert len(gdf) > 1000
