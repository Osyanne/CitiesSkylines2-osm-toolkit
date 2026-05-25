"""Source protocol — every per-city source module must implement this interface."""
from pathlib import Path
from typing import Protocol, runtime_checkable

import geopandas as gpd


@runtime_checkable
class Source(Protocol):
    """A city zoning source: downloads from a portal, reads as a GeoDataFrame."""

    slug: str
    """City slug matching the entry in cities.json (e.g. 'minneapolis')."""

    def download(self, cache_dir: Path, force_refresh: bool = False) -> Path:
        """Download the shapefile zip or GeoJSON to cache_dir and return its path.

        Args:
            cache_dir: Directory to write the file. Created if missing.
            force_refresh: If True, re-download even if cache hit.

        Returns:
            Absolute path to the downloaded file (zip or geojson).
        """
        ...

    def read(self, cache_path: Path) -> gpd.GeoDataFrame:
        """Open the downloaded file and return a GeoDataFrame.

        Args:
            cache_path: Output of `download()`.

        Returns:
            GeoDataFrame with at least a geometry column and the source_field
            declared in the city's mapping YAML.
        """
        ...
