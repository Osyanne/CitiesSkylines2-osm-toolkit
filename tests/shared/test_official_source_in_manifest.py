"""Tests para oficial_zoning module en manifest.json con official_source metadata."""
import sys, os, json
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from shared.registry import (
    load_manifest, save_manifest_official_source, manifest_path, hash_file,
)


def test_save_manifest_official_source_creates_entry(tmp_path):
    """Crear entry official_zoning con source_name y source_url."""
    data_file = tmp_path / "datos_zonificacion_official.js"
    data_file.write_text("const zones = [];")

    manifest = save_manifest_official_source(
        tmp_path,
        "minneapolis",
        data_file,
        "City of Minneapolis Planning",
        "https://opendata.minneapolismn.gov/datasets/zoning"
    )

    assert "official_zoning" in manifest["modules"]
    assert manifest["modules"]["official_zoning"]["hash"] == hash_file(data_file)
    assert manifest["modules"]["official_zoning"]["source_name"] == "City of Minneapolis Planning"
    assert manifest["modules"]["official_zoning"]["source_url"] == "https://opendata.minneapolismn.gov/datasets/zoning"
    assert "generated_at" in manifest


def test_save_manifest_official_source_persists_to_disk(tmp_path):
    """Guardar official_zoning debe escribir manifest.json en disco."""
    data_file = tmp_path / "datos.js"
    data_file.write_text("x")

    save_manifest_official_source(
        tmp_path,
        "minneapolis",
        data_file,
        "Test Source",
        "http://example.com"
    )

    p = manifest_path(tmp_path, "minneapolis")
    assert p.exists()
    on_disk = load_manifest(tmp_path, "minneapolis")
    assert on_disk is not None
    assert on_disk["modules"]["official_zoning"]["source_name"] == "Test Source"


def test_save_manifest_official_source_preserves_other_modules(tmp_path):
    """Guardar official_zoning no debe borrar otros módulos."""
    # Crear manifest con módulo zoning existente
    p = manifest_path(tmp_path, "minneapolis")
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({
        "modules": {"zoning": {"hash": "abc123", "features": 1000}},
        "generated_at": "2026-05-01T00:00:00+00:00",
    }))

    # Agregar official_zoning
    data_file = tmp_path / "datos.js"
    data_file.write_text("y")
    manifest = save_manifest_official_source(
        tmp_path,
        "minneapolis",
        data_file,
        "NYC DCP",
        "http://nyc.gov"
    )

    # Ambos modules deben existir
    assert "zoning" in manifest["modules"]
    assert "official_zoning" in manifest["modules"]
    assert manifest["modules"]["zoning"]["features"] == 1000
    assert manifest["modules"]["official_zoning"]["source_name"] == "NYC DCP"


def test_save_manifest_official_source_hash_deterministic(tmp_path):
    """El hash debe ser determinístico."""
    data_file = tmp_path / "datos.js"
    data_file.write_text("const zones = [1, 2, 3];")

    m1 = save_manifest_official_source(
        tmp_path,
        "new_york",
        data_file,
        "Source",
        "http://url.com"
    )
    h1 = m1["modules"]["official_zoning"]["hash"]

    # Cargar de disco
    m2 = load_manifest(tmp_path, "new_york")
    h2 = m2["modules"]["official_zoning"]["hash"]

    assert h1 == h2
    assert len(h1) == 8  # trunco a 8 chars


def test_save_manifest_official_source_overwrites_previous(tmp_path):
    """Llamar save_manifest_official_source dos veces debe overwrite."""
    data_file_v1 = tmp_path / "v1.js"
    data_file_v1.write_text("old")

    m1 = save_manifest_official_source(
        tmp_path,
        "minneapolis",
        data_file_v1,
        "Old Source",
        "http://old.com"
    )

    data_file_v2 = tmp_path / "v2.js"
    data_file_v2.write_text("new")

    m2 = save_manifest_official_source(
        tmp_path,
        "minneapolis",
        data_file_v2,
        "New Source",
        "http://new.com"
    )

    assert m2["modules"]["official_zoning"]["source_name"] == "New Source"
    assert m2["modules"]["official_zoning"]["source_url"] == "http://new.com"
    assert m2["modules"]["official_zoning"]["hash"] == hash_file(data_file_v2)
