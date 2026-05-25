"""New York zoning source — downloads from NYC Department of City Planning."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import requests
from tqdm import tqdm


slug = "new_york"

# NYC Department of City Planning — Zoning Districts shapefile (zipped)
# Source: https://www1.nyc.gov/site/planning/data-maps/open-data.page
# Updated as of 2026-05-24 from NYC's open data portal.
DATA_URL = "https://s-media.nyc.gov/agencies/dcp/assets/files/zip/data-tools/bytes/nycgiszoningfeatures_202404shp.zip"
CACHE_FILENAME = "nyc_zoning.zip"


def download(cache_dir: Path, force_refresh: bool = False) -> Path:
    """Download the NYC zoning shapefile zip. Caches to cache_dir."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / CACHE_FILENAME

    if target.exists() and not force_refresh:
        return target

    resp = requests.get(DATA_URL, stream=True, timeout=180)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    with open(target, "wb") as f:
        with tqdm(total=total, unit="B", unit_scale=True, desc="NYC zoning") as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
    return target


def read(cache_path: Path) -> gpd.GeoDataFrame:
    """Read the NYC zoning shapefile. The zip contains multiple .shp files;
    the zoning districts one is named `nyzd.shp`.

    geopandas handles `zip://` URIs natively (via pyogrio).
    """
    return gpd.read_file(
        f"zip://{cache_path.resolve()}!nyzd.shp",
        engine="pyogrio",
    )
