"""infraestructura debe ser un módulo válido para el manifest."""
from pathlib import Path

from shared.registry import VALID_MODULES, save_manifest_entry


def test_infraestructura_is_valid_module():
    assert "infraestructura" in VALID_MODULES


def test_save_manifest_entry_accepts_infraestructura(tmp_path):
    data = tmp_path / "cities" / "x" / "datos_infraestructura.js"
    data.parent.mkdir(parents=True)
    data.write_text("var DATA_INFRA_POWER = [];\n", encoding="utf-8")
    manifest = save_manifest_entry(
        visualizer_root=tmp_path, slug="x", module="infraestructura",
        file_path=data, features=3,
    )
    assert manifest["modules"]["infraestructura"]["features"] == 3
