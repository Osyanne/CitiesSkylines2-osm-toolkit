"""
compact.py — formato compacto para los módulos pesados (zoning, vial, external_buildings)
=======================================================================================

Los `datos_*.js` repetían en cada feature las mismas claves ("cs2_key", "name": "",
"bridge": false) y guardaban cada coordenada como float de 8-9 caracteres. Este
formato guarda lo mismo sin pérdida en ~1/4 del tamaño:

    {
      "format": "cs2-compact", "version": 1, "module": "zoning",
      "precision": 5,               # coordenadas = enteros × 10^-5 (~1.1 m)
      "meta": {...},                # bbox, generated_at, notas del extract
      "layers": {
        "res_low_house": {          # la clave de capa ES el cs2_key de cada item
          "ids":  [38932348, ...],
          "geom": [[4498737, -9324109, -6, 17, ...], ...],   # primer punto absoluto,
                                                              # el resto como delta
          "props": {"name": {"default": "", "sparse": {"5": "Old Muskego Church"}},
                    "method": {"dict": ["landuse", "area"], "codes": [0, 1, -1, ...]}}
        }
      }
    }

Cada columna de `props` usa una de tres formas (el encoder elige la más corta):
  - {"default": d?, "sparse": {"<índice>": valor}}   pocos valores distintos del default
  - {"default": d?, "dict": [...], "codes": [...]}    muchos valores, pocos distintos (-1 = sin valor)
  - {"values": [...]}                                 todos distintos (ej. conf de Google)
Con "default" la clave existe en todos los items; sin él, solo en los listados.

decode_layers(encode_layers(x)) == x para cualquier dato del pipeline (coords con
≤ 5 decimales, que es lo que produce round_coords).

CLI `convert-legacy-data`: migra los datos_*.js existentes al formato nuevo.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

FORMAT = "cs2-compact"
VERSION = 1
DEFAULT_PRECISION = 5

# Módulos que usan este formato → nombre base del archivo (sin extensión)
COMPACT_MODULES = {
    "zoning": "datos_zonificacion",
    "vial": "datos_vial",
    "external_buildings": "datos_external_buildings",
}

# Una columna con más distintos que esto no se codifica como diccionario
_MAX_DICT_VALUES = 64


class CompactFormatError(ValueError):
    """El archivo no es un cs2-compact válido (o es de una versión futura)."""


def compact_filename(module: str) -> str:
    return f"{COMPACT_MODULES[module]}.json"


def remove_legacy(city_dir: Path, module: str) -> None:
    """Borra el datos_*.js viejo del módulo (si quedó de una versión anterior)."""
    legacy = Path(city_dir) / f"{COMPACT_MODULES[module]}.js"
    if legacy.exists():
        legacy.unlink()


# ── Geometría ────────────────────────────────────────────────────────────────

def _encode_coords(coords: list[list[float]], scale: int) -> list[int]:
    out: list[int] = []
    prev_lat = prev_lon = 0
    for lat, lon in coords:
        a = round(lat * scale)
        b = round(lon * scale)
        out.append(a - prev_lat)
        out.append(b - prev_lon)
        prev_lat, prev_lon = a, b
    return out


def _decode_coords(flat: list[int], scale: int) -> list[list[float]]:
    coords = []
    lat = lon = 0
    for i in range(0, len(flat), 2):
        lat += flat[i]
        lon += flat[i + 1]
        coords.append([lat / scale, lon / scale])
    return coords


# ── Columnas de propiedades ──────────────────────────────────────────────────

def _key(v: Any) -> tuple:
    # (tipo, valor): False y 0 son iguales para Python pero no para este formato
    return (type(v).__name__, v)


def _hashable(v: Any) -> bool:
    try:
        hash(v)
    except TypeError:
        return False
    return True


def _encode_prop(prop: str, items: list[dict]) -> dict:
    n = len(items)
    present = [i for i, it in enumerate(items) if prop in it]
    col: dict[str, Any] = {}

    if len(present) == n:
        values = [it[prop] for it in items]
        if not all(_hashable(v) for v in values):
            return {"values": values}
        counts = Counter(_key(v) for v in values)
        (_, default), freq = counts.most_common(1)[0]
        if freq == n:
            return {"default": default}
        if len(counts) > _MAX_DICT_VALUES and freq * 2 < n:
            return {"values": values}
        col["default"] = default
        dkey = _key(default)
        entries = {i: v for i, v in enumerate(values) if _key(v) != dkey}
    else:
        entries = {i: items[i][prop] for i in present}

    distinct: list[Any] = []
    seen: dict[tuple, int] = {}
    dictable = True
    for v in entries.values():
        if not _hashable(v):
            dictable = False
            break
        k = _key(v)
        if k not in seen:
            seen[k] = len(distinct)
            distinct.append(v)
            if len(distinct) > _MAX_DICT_VALUES:
                dictable = False
                break

    sparse = {"sparse": {str(i): v for i, v in entries.items()}}
    if not dictable:
        return {**col, **sparse}
    codes = [-1] * n
    for i, v in entries.items():
        codes[i] = seen[_key(v)]
    dense = {"dict": distinct, "codes": codes}
    # La que ocupe menos una vez serializada
    size = lambda c: len(json.dumps(c, ensure_ascii=False, separators=(",", ":")))
    return {**col, **(sparse if size(sparse) <= size(dense) else dense)}


def _decode_prop(prop: str, col: dict, items: list[dict]) -> None:
    if "values" in col:
        for it, v in zip(items, col["values"]):
            it[prop] = v
        return
    if "default" in col:
        d = col["default"]
        for it in items:
            it[prop] = d
    if "sparse" in col:
        for i, v in col["sparse"].items():
            items[int(i)][prop] = v
    elif "dict" in col:
        d = col["dict"]
        for it, c in zip(items, col["codes"]):
            if c >= 0:
                it[prop] = d[c]


# ── Capas ────────────────────────────────────────────────────────────────────

_RESERVED = ("id", "coords", "cs2_key")


def encode_layers(layers: dict[str, list[dict]], precision: int = DEFAULT_PRECISION) -> dict:
    """{cs2_key: [item, ...]} → dict con "precision" y "layers" (serializable)."""
    scale = 10 ** precision
    out: dict[str, Any] = {}
    for key, items in layers.items():
        props: dict[str, Any] = {}
        names = []
        for it in items:
            for p in it:
                if p not in _RESERVED and p not in props:
                    props[p] = None
                    names.append(p)
        for it in items:
            if it.get("cs2_key", key) != key:
                raise ValueError(f"item {it.get('id')} con cs2_key={it['cs2_key']!r} en la capa {key!r}")
        out[key] = {
            "ids": [it["id"] for it in items],
            "geom": [_encode_coords(it["coords"], scale) for it in items],
            "props": {p: _encode_prop(p, items) for p in names},
        }
    return {"precision": precision, "layers": out}


def decode_layers(doc: dict) -> dict[str, list[dict]]:
    """Inversa de encode_layers (acepta el documento completo o solo esa parte)."""
    scale = 10 ** doc["precision"]
    result: dict[str, list[dict]] = {}
    for key, layer in doc["layers"].items():
        items = [
            {"id": i, "coords": _decode_coords(g, scale), "cs2_key": key}
            for i, g in zip(layer["ids"], layer["geom"])
        ]
        for prop, col in layer.get("props", {}).items():
            _decode_prop(prop, col, items)
        result[key] = items
    return result


# ── Archivos ─────────────────────────────────────────────────────────────────

def write_compact(
    path: Path,
    module: str,
    layers: dict[str, list[dict]],
    meta: dict | None = None,
    precision: int = DEFAULT_PRECISION,
) -> int:
    """Escribe `layers` en `path`. Devuelve la cantidad de features."""
    doc = {
        "format": FORMAT,
        "version": VERSION,
        "module": module,
        "meta": meta or {},
        **encode_layers(layers, precision),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    return sum(len(v) for v in layers.values())


def read_compact(path: Path) -> tuple[dict[str, list[dict]], dict]:
    """Lee un cs2-compact → (layers, meta)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("format") != FORMAT:
        raise CompactFormatError(f"{path}: no es un archivo {FORMAT}")
    if doc.get("version", 0) > VERSION:
        raise CompactFormatError(
            f"{path}: versión {doc['version']} (este toolkit lee hasta la {VERSION})"
        )
    return decode_layers(doc), doc.get("meta", {})


_CONST_RE = re.compile(r"^const (DATA_\w+) = ", re.M)


def read_legacy_js(path: Path, module: str) -> tuple[dict[str, list[dict]], dict]:
    """Lee un datos_*.js viejo (`const DATA_* = ...;`) → (layers, meta).

    zoning: DATA_<KEY> · external_buildings: DATA_EXT_<KEY> · vial: DATA_VIAL {key: [...]}.
    Las líneas `// ...` del encabezado se conservan en meta["header"].
    """
    text = Path(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    consts: dict[str, Any] = {}
    for m in _CONST_RE.finditer(text):
        consts[m.group(1)], _ = decoder.raw_decode(text, m.end())
    header = [ln[2:].strip() for ln in text.splitlines()[:12] if ln.startswith("//")]
    meta: dict[str, Any] = {"header": header} if header else {}

    if module == "vial":
        if "DATA_VIAL" not in consts:
            raise CompactFormatError(f"{path}: no define DATA_VIAL")
        meta.update(consts.get("DATA_VIAL_META", {}))
        return dict(consts["DATA_VIAL"]), meta

    prefix = "DATA_EXT_" if module == "external_buildings" else "DATA_"
    layers = {
        name[len(prefix):].lower(): value
        for name, value in consts.items()
        if name.startswith(prefix) and isinstance(value, list)
    }
    if not layers:
        raise CompactFormatError(f"{path}: no define arrays {prefix}*")
    return layers, meta


# ── CLI: migrar datos_*.js → datos_*.json ────────────────────────────────────

def convert_city(visualizer_root: Path, slug: str, keep_legacy: bool = False) -> list[str]:
    """Migra los módulos compactables de una ciudad. Devuelve líneas de reporte."""
    from shared.registry import save_manifest_entry

    city_dir = Path(visualizer_root) / "cities" / slug
    report = []
    for module, base in COMPACT_MODULES.items():
        legacy = city_dir / f"{base}.js"
        if not legacy.exists():
            continue
        layers, meta = read_legacy_js(legacy, module)
        out = city_dir / compact_filename(module)
        total = write_compact(out, module, layers, meta)
        # La migración no puede perder nada: verificar ida y vuelta antes de borrar
        back, _ = read_compact(out)
        if back != layers:
            out.unlink()
            raise CompactFormatError(f"{legacy}: la conversión no es exacta, se deja el .js")
        save_manifest_entry(
            visualizer_root=visualizer_root, slug=slug, module=module,
            file_path=out, features=total,
        )
        before, after = legacy.stat().st_size, out.stat().st_size
        if not keep_legacy:
            legacy.unlink()
        report.append(
            f"{slug}/{module}: {total} features → {out.name} "
            f"({before / 1048576:.1f} MB → {after / 1048576:.1f} MB)"
        )
    return report


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    parser = argparse.ArgumentParser(
        description="Migra datos_zonificacion/vial/external_buildings .js al formato compacto .json",
    )
    parser.add_argument("--city", help="Solo esta ciudad (default: todas las de visualizer/cities/)")
    parser.add_argument("--keep-legacy", action="store_true", help="No borrar los .js originales")
    parser.add_argument(
        "--visualizer-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "visualizer",
    )
    args = parser.parse_args(argv)

    cities_dir = args.visualizer_root / "cities"
    slugs = [args.city] if args.city else sorted(p.name for p in cities_dir.iterdir() if p.is_dir())
    converted = 0
    for slug in slugs:
        for line in convert_city(args.visualizer_root, slug, args.keep_legacy):
            print(line)
            converted += 1
    print(f"\n{converted} archivo(s) migrados")


if __name__ == "__main__":
    main()
