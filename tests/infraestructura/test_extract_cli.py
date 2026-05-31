"""parse_args + main con Overpass mockeado."""
import json
from pathlib import Path
from unittest.mock import patch

from infraestructura.extract import parse_args, main

FAKE_OVERPASS = {"elements": [
    {"type": "node", "id": 1, "lat": 44.9, "lon": -93.2,
     "tags": {"man_made": "water_tower", "name": "Tower A"}},
    {"type": "way", "id": 2, "geometry": [
        {"lat": 44.9, "lon": -93.2}, {"lat": 44.91, "lon": -93.21}],
     "tags": {"power": "line"}},
    {"type": "node", "id": 3, "lat": 44.95, "lon": -93.25,
     "tags": {"amenity": "recycling", "recycling_type": "container"}},  # excluido
]}


def test_parse_args_city():
    ns = parse_args(["--city", "minneapolis"])
    assert ns.city == "minneapolis"


def test_main_emits_4_data_vars(tmp_path):
    cities = tmp_path / "cities.json"
    cities.write_text(json.dumps({"minneapolis": {
        "display_name": "Mpls", "country": "US", "bbox": [44.86, -93.38, 45.05, -93.17],
        "center": [44.97, -93.26], "zoom": 12, "tagline": "x", "locale": "en"}}), encoding="utf-8")
    vis = tmp_path / "visualizer"

    argv = ["--city", "minneapolis", "--cities-file", str(cities), "--visualizer-root", str(vis)]
    with patch("infraestructura.extract.query_with_retry", return_value=FAKE_OVERPASS), \
         patch("sys.argv", ["extract-infraestructura"] + argv):
        main()

    out = (vis / "cities" / "minneapolis" / "datos_infraestructura.js").read_text(encoding="utf-8")
    assert "var DATA_INFRA_POWER = " in out
    assert "var DATA_INFRA_WATER = " in out
    assert "var DATA_INFRA_WASTE = " in out
    assert "var DATA_INFRA_TELECOM = " in out
    assert "Tower A" in out
    assert (vis / "cities" / "minneapolis" / "manifest.json").exists()
