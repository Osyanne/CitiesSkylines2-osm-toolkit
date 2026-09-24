"""
tiles.py — teselas vectoriales (MVT) por ciudad para el visualizador MapLibre
============================================================================

Con cientos de miles de polígonos por ciudad, bajar y dibujar TODO en el
navegador congela la pestaña. Las teselas cortan los datos por zoom y zona: el
visor baja solo los pedazos que se ven, ya simplificados para ese zoom.

Salida en `visualizer/cities/<slug>/tiles/`:

    tiles/<z>/<x>/<y>.mvt.gz   Mapbox Vector Tile 2.1, gzip. Capas "zoning"
                               (OSM + edificios externos) y "vial".
    tiles/tiles.json           minzoom, maxzoom, bounds, conteos por categoría,
                               lista de teselas existentes y hash del conjunto.

Por qué archivos sueltos y no un .pmtiles: PMTiles necesita pedidos HTTP por
rango, y `python -m http.server` (start-visualizer.bat) no los soporta. Los
.gz se sirven como binario opaco en cualquier servidor estático y el visor los
descomprime con DecompressionStream.

Propiedades de cada feature (claves cortas, se repiten en cada tesela):
    zoning: k = cs2_key, id, n = nombre (si hay), m = method, s = src, c = conf
    vial:   k = categoría, n = nombre (si hay), b = true si es puente

Reglas de nivel de detalle (zooms de MapLibre; MapLibre z = Leaflet z - 1):
    - Casas y estacionamientos < 3000 m² desde z13 (el "tier" del visor Leaflet).
    - Calles locales desde z11, ciclovías desde z12, sendas peatonales desde z13.
    - Debajo de maxzoom: simplificación de 0.5 px y se descarta lo que mide < 1 px.

Python puro (shapely + numpy, ya dependencias del toolkit): corre igual en Windows.
El encoder MVT está acá mismo para no sumar protobuf/pyclipper como dependencias.

CLI: `uv run build-tiles [--city <slug>]`. Los extractores de zoning, vial y
Google buildings lo llaman solos al terminar.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import shutil
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import shapely

FORMAT = "cs2-tiles"
VERSION = 1

EXTENT = 4096           # unidades por lado de tesela (estándar MVT)
BUFFER = 64             # margen alrededor de cada tesela, en unidades
MINZOOM = 9
MAXZOOM = 14            # más allá MapLibre sobre-amplía las de z14 (~0.4 m por unidad)
SIMPLIFY_UNITS = 4.0    # 0.5 px en una tesela de 512 px (8 unidades por px)
MIN_SIZE_UNITS = 8.0    # < 1 px de lado → no se incluye debajo de maxzoom

TIER_MIN_AREA_M2 = {"res_low_house": 3000.0, "prk_surface": 3000.0}
TIER_MINZOOM = 13
VIAL_MINZOOM = {"local": 11, "bike": 12, "pedestrian": 13}

TILES_DIRNAME = "tiles"
TILE_SUFFIX = ".mvt.gz"

_MAX_LAT = 85.05112878


# ── Features ─────────────────────────────────────────────────────────────────

@dataclass
class _Features:
    """Features de una capa MVT, en coordenadas mercator normalizadas [0, 1]."""
    layer: str
    polygon: bool
    props: list[dict] = field(default_factory=list)
    coords: list[np.ndarray] = field(default_factory=list)   # (n, 2) lon/lat
    minzoom: list[int] = field(default_factory=list)

    def add(self, props: dict, latlon: list[list[float]], minzoom: int) -> None:
        pts = np.asarray(latlon, dtype=np.float64)
        if pts.ndim != 2 or len(pts) < 2:
            return
        if self.polygon:
            if np.array_equal(pts[0], pts[-1]):
                pts = pts[:-1]          # shapely vuelve a cerrar el anillo
            if len(pts) < 3:
                return
        self.props.append(props)
        self.coords.append(pts)
        self.minzoom.append(minzoom)


def _poly_area_m2(latlon: np.ndarray) -> float:
    """Área aproximada (proyección equirectangular) — misma cuenta que el visor Leaflet."""
    lat0 = latlon[:, 0].mean()
    k = 111320.0
    x = latlon[:, 1] * k * math.cos(math.radians(lat0))
    y = latlon[:, 0] * k
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))) / 2.0


def zoning_features(zoning: dict[str, list[dict]], external: dict[str, list[dict]] | None = None) -> _Features:
    """Capa "zoning": por cada zona, primero OSM y después los edificios externos
    (mismo orden de dibujo que el visor Leaflet)."""
    feats = _Features("zoning", polygon=True)
    external = external or {}
    keys = list(zoning) + [k for k in external if k not in zoning]
    for key in keys:
        threshold = TIER_MIN_AREA_M2.get(key)
        for item in list(zoning.get(key, [])) + list(external.get(key, [])):
            props: dict[str, Any] = {"k": key, "id": item["id"]}
            if item.get("name"):
                props["n"] = item["name"]
            for src, dst in (("method", "m"), ("src", "s"), ("conf", "c")):
                if item.get(src) is not None:
                    props[dst] = item[src]
            coords = item["coords"]
            minzoom = MINZOOM
            if threshold is not None and len(coords) >= 3:
                if _poly_area_m2(np.asarray(coords, dtype=np.float64)) < threshold:
                    minzoom = TIER_MINZOOM
            feats.add(props, coords, minzoom)
    return feats


def vial_features(vial: dict[str, list[dict]]) -> _Features:
    feats = _Features("vial", polygon=False)
    for key, items in vial.items():
        minzoom = VIAL_MINZOOM.get(key, MINZOOM)
        for item in items:
            props: dict[str, Any] = {"k": key}
            if item.get("name"):
                props["n"] = item["name"]
            if item.get("bridge"):
                props["b"] = True
            feats.add(props, item["coords"], minzoom)
    return feats


# ── Proyección ───────────────────────────────────────────────────────────────

def _to_mercator(latlon: np.ndarray) -> np.ndarray:
    """[[lat, lon], ...] → [[x, y], ...] en [0, 1] (y hacia abajo, como las teselas)."""
    lat = np.radians(np.clip(latlon[:, 0], -_MAX_LAT, _MAX_LAT))
    x = (latlon[:, 1] + 180.0) / 360.0
    y = (1.0 - np.log(np.tan(lat) + 1.0 / np.cos(lat)) / math.pi) / 2.0
    return np.column_stack([x, y])


def _tile_to_lonlat(x: float, y: float) -> tuple[float, float]:
    lon = x * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))
    return lon, lat


# ── Encoder MVT (protobuf a mano) ────────────────────────────────────────────

def _varint(n: int, out: bytearray) -> None:
    while n > 0x7F:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)


def _field_bytes(num: int, payload: bytes | bytearray, out: bytearray) -> None:
    _varint((num << 3) | 2, out)
    _varint(len(payload), out)
    out += payload


def _field_varint(num: int, value: int, out: bytearray) -> None:
    _varint(num << 3, out)
    _varint(value, out)


def _packed(values: Iterable[int]) -> bytearray:
    buf = bytearray()
    for v in values:
        _varint(v, buf)
    return buf


def _encode_value(v: Any) -> bytes:
    out = bytearray()
    if isinstance(v, bool):
        _field_varint(7, int(v), out)
    elif isinstance(v, int):
        if v >= 0:
            _field_varint(5, v, out)                       # uint_value
        else:
            _field_varint(6, (v << 1) ^ (v >> 63), out)    # sint_value (zigzag)
    elif isinstance(v, float):
        _varint((3 << 3) | 1, out)                         # double_value
        out += struct.pack("<d", v)
    else:
        _field_bytes(1, str(v).encode("utf-8"), out)       # string_value
    return bytes(out)


_GEOM_LINESTRING, _GEOM_POLYGON = 2, 3
_CMD_MOVE_TO_1 = (1 << 3) | 1     # MoveTo con 1 punto
_CMD_CLOSE_PATH = (1 << 3) | 7    # ClosePath


# Los anillos típicos tienen 5-10 puntos: con arrays tan chicos cada llamada a
# numpy cuesta más que la cuenta. Todo lo que es por feature va en Python simple.

def _quantize(coords: list, x0: float, y0: float) -> list[tuple[int, int]]:
    """Coordenadas de píxel mundo → enteros de tesela, sin puntos repetidos."""
    out: list[tuple[int, int]] = []
    last = None
    for x, y in coords:
        p = (round(x - x0), round(y - y0))
        if p != last:
            out.append(p)
            last = p
    return out


def _ring(coords: list, x0: float, y0: float, exterior: bool) -> list | None:
    pts = _quantize(coords, x0, y0)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()                             # ClosePath cierra el anillo
    if len(pts) < 3:
        return None
    area = 0
    px, py = pts[-1]
    for x, y in pts:
        area += px * y - x * py
        px, py = x, y
    if area == 0:
        return None
    # MVT: exterior con área positiva en coordenadas de tesela (y hacia abajo)
    if (area > 0) != exterior:
        pts.reverse()
    return pts


def _line(coords: list, x0: float, y0: float) -> list | None:
    pts = _quantize(coords, x0, y0)
    return pts if len(pts) >= 2 else None


def _commands(parts: list[list[tuple[int, int]]], polygon: bool) -> list[int]:
    """Anillos o líneas ya cuantizados → comandos de geometría MVT."""
    cmds: list[int] = []
    cx = cy = 0
    for pts in parts:
        x, y = pts[0]
        dx, dy = x - cx, y - cy
        cmds += (_CMD_MOVE_TO_1, (dx << 1) ^ (dx >> 31), (dy << 1) ^ (dy >> 31),
                 ((len(pts) - 1) << 3) | 2)
        px, py = x, y
        for x, y in pts[1:]:
            dx, dy = x - px, y - py
            cmds.append((dx << 1) ^ (dx >> 31))
            cmds.append((dy << 1) ^ (dy >> 31))
            px, py = x, y
        if polygon:
            cmds.append(_CMD_CLOSE_PATH)
        cx, cy = px, py
    return cmds


def _clip(geom, x0: float, y0: float):
    rect = (x0 - BUFFER, y0 - BUFFER, x0 + EXTENT + BUFFER, y0 + EXTENT + BUFFER)
    try:
        return shapely.clip_by_rect(geom, *rect)
    except shapely.errors.GEOSException:
        # Geometría inválida de origen (anillo que se cruza, etc.): repararla y reintentar
        try:
            return shapely.clip_by_rect(shapely.make_valid(geom), *rect)
        except shapely.errors.GEOSException:
            return None


def _flatten(geom):
    """Multi* y colecciones (también anidadas) → geometrías simples."""
    if hasattr(geom, "geoms"):
        for g in geom.geoms:
            yield from _flatten(g)
    else:
        yield geom


def _clipped_parts(geom, x0: float, y0: float, polygon: bool) -> list:
    """Partes de una geometría recortada por shapely (Polygon/Multi*/colección)."""
    parts = []
    if geom is None:
        return parts
    for g in _flatten(geom):
        if g.is_empty:
            continue
        if polygon and g.geom_type == "Polygon":
            ext = _ring(g.exterior.coords, x0, y0, exterior=True)
            if ext is None:
                continue
            parts.append(ext)
            for hole in g.interiors:
                r = _ring(hole.coords, x0, y0, exterior=False)
                if r is not None:
                    parts.append(r)
        elif not polygon and g.geom_type == "LineString":
            ln = _line(g.coords, x0, y0)
            if ln is not None:
                parts.append(ln)
    return parts


class _LayerBuilder:
    def __init__(self, name: str, polygon: bool):
        self.name = name
        self.geom_type = _GEOM_POLYGON if polygon else _GEOM_LINESTRING
        self.keys: dict[str, int] = {}
        self.values: dict[tuple, int] = {}
        self.encoded_values: list[bytes] = []
        self.features = bytearray()
        self.count = 0

    def add(self, props: dict, cmds: list[int]) -> None:
        tags: list[int] = []
        for k, v in props.items():
            ki = self.keys.setdefault(k, len(self.keys))
            vkey = (type(v).__name__, v)
            vi = self.values.get(vkey)
            if vi is None:
                vi = self.values[vkey] = len(self.encoded_values)
                self.encoded_values.append(_encode_value(v))
            tags += (ki, vi)
        feat = bytearray()
        _field_bytes(2, _packed(tags), feat)
        _field_varint(3, self.geom_type, feat)
        _field_bytes(4, _packed(cmds), feat)
        _field_bytes(2, feat, self.features)
        self.count += 1

    def encode(self) -> bytearray:
        out = bytearray()
        _field_varint(15, 2, out)                              # version
        _field_bytes(1, self.name.encode("utf-8"), out)        # name
        out += self.features                                   # features (campo 2)
        for k in self.keys:
            _field_bytes(3, k.encode("utf-8"), out)            # keys
        for v in self.encoded_values:
            _field_bytes(4, v, out)                            # values
        _field_varint(5, EXTENT, out)                          # extent
        return out


def encode_tile(layers: list[_LayerBuilder]) -> bytes:
    out = bytearray()
    for layer in layers:
        if layer.count:
            _field_bytes(3, layer.encode(), out)
    return bytes(out)


# ── Corte por zoom ───────────────────────────────────────────────────────────

def _cut_zoom(feats: _Features, world: list[np.ndarray], z: int,
              tiles: dict[tuple[int, int], dict[str, _LayerBuilder]]) -> None:
    """Agrega a `tiles` las features de `feats` que corresponden al zoom z."""
    n = len(world)
    if n == 0:
        return
    scale = float(2 ** z * EXTENT)
    minzoom = np.asarray(feats.minzoom)

    lengths = np.fromiter((len(w) for w in world), dtype=np.int64, count=n)
    flat = np.concatenate(world) * scale
    offsets = np.concatenate([[0], np.cumsum(lengths)])
    mins = np.minimum.reduceat(flat, offsets[:-1], axis=0)
    maxs = np.maximum.reduceat(flat, offsets[:-1], axis=0)
    size = np.max(maxs - mins, axis=1)

    eligible = minzoom <= z
    if z < MAXZOOM:
        eligible &= size >= MIN_SIZE_UNITS
    idx = np.nonzero(eligible)[0]
    if len(idx) == 0:
        return

    # Geometrías de shapely en unidades de "píxel mundo" de este zoom
    sel = flat[np.repeat(eligible, lengths)]
    sel_offsets = np.concatenate([[0], np.cumsum(lengths[idx])])
    if feats.polygon:
        geoms = shapely.from_ragged_array(
            shapely.GeometryType.POLYGON, sel, (sel_offsets, np.arange(len(idx) + 1)))
    else:
        geoms = shapely.from_ragged_array(shapely.GeometryType.LINESTRING, sel, (sel_offsets,))
    if z < MAXZOOM:
        geoms = shapely.simplify(geoms, SIMPLIFY_UNITS, preserve_topology=False)
    bounds = shapely.bounds(geoms)
    # La simplificación puede dejar geometrías vacías (bounds NaN) o anillos de
    # 3 coordenadas, que GEOS no acepta al recortar: afuera
    ok = ~np.isnan(bounds).any(axis=1)
    if feats.polygon:
        ok &= shapely.get_num_coordinates(geoms) >= 4
    if not ok.all():
        idx, geoms, bounds = idx[ok], geoms[ok], bounds[ok]

    t0 = np.floor((bounds[:, :2] - BUFFER) / EXTENT).astype(np.int64)
    t1 = np.floor((bounds[:, 2:] + BUFFER) / EXTENT).astype(np.int64)
    limit = 2 ** z - 1
    t0 = np.clip(t0, 0, limit).tolist()
    t1 = np.clip(t1, 0, limit).tolist()
    bnds = bounds.tolist()

    # Coordenadas de todas las geometrías en una sola llamada. Ojo: simplify
    # puede partir un polígono en un MultiPolygon (una "pesa" pierde el cuello),
    # y con uno solo el arreglo entero pasa a ser de tipo Multi*: los offsets se
    # recorren según el tipo que devuelve, no según el de entrada.
    gtype, coords, offs = shapely.to_ragged_array(geoms)
    coords = coords.tolist()
    n_geoms = len(geoms)
    if feats.polygon:
        coord_of_ring = offs[0].tolist()
        ring_of_poly = offs[1].tolist()
        poly_of_geom = (offs[2].tolist() if gtype == shapely.GeometryType.MULTIPOLYGON
                        else list(range(n_geoms + 1)))
    else:
        coord_of_line = offs[0].tolist()
        line_of_geom = (offs[1].tolist() if gtype == shapely.GeometryType.MULTILINESTRING
                        else list(range(n_geoms + 1)))

    def local_parts(j: int, x0: float, y0: float) -> list:
        """Partes de la geometría j (ya entera dentro de la tesela), cuantizadas."""
        parts = []
        if feats.polygon:
            for pi in range(poly_of_geom[j], poly_of_geom[j + 1]):
                for k, ri in enumerate(range(ring_of_poly[pi], ring_of_poly[pi + 1])):
                    ring = _ring(coords[coord_of_ring[ri]:coord_of_ring[ri + 1]], x0, y0, exterior=k == 0)
                    if ring is None:
                        if k == 0:
                            break         # sin exterior no hay polígono
                        continue
                    parts.append(ring)
        else:
            for li in range(line_of_geom[j], line_of_geom[j + 1]):
                line = _line(coords[coord_of_line[li]:coord_of_line[li + 1]], x0, y0)
                if line is not None:
                    parts.append(line)
        return parts

    layer_name = feats.layer
    polygon = feats.polygon
    for j, i in enumerate(idx.tolist()):
        props = feats.props[i]
        minx, miny, maxx, maxy = bnds[j]
        for tx in range(t0[j][0], t1[j][0] + 1):
            x0 = tx * EXTENT
            for ty in range(t0[j][1], t1[j][1] + 1):
                y0 = ty * EXTENT
                if (minx >= x0 - BUFFER and miny >= y0 - BUFFER
                        and maxx <= x0 + EXTENT + BUFFER and maxy <= y0 + EXTENT + BUFFER):
                    parts = local_parts(j, x0, y0)
                else:
                    parts = _clipped_parts(_clip(geoms[j], x0, y0), x0, y0, polygon)
                if not parts:
                    continue
                layers = tiles.setdefault((tx, ty), {})
                lb = layers.get(layer_name)
                if lb is None:
                    lb = layers[layer_name] = _LayerBuilder(layer_name, polygon)
                lb.add(props, _commands(parts, polygon))


# ── Tileset de una ciudad ────────────────────────────────────────────────────

def build_tiles(
    out_dir: Path,
    zoning: dict[str, list[dict]] | None = None,
    external: dict[str, list[dict]] | None = None,
    vial: dict[str, list[dict]] | None = None,
    minzoom: int = MINZOOM,
    maxzoom: int = MAXZOOM,
) -> dict:
    """Escribe las teselas en `out_dir` (lo vacía antes) y devuelve el tiles.json."""
    groups: list[_Features] = []
    counts: dict[str, dict[str, int]] = {}
    if zoning or external:
        groups.append(zoning_features(zoning or {}, external))
        merged: dict[str, int] = {}
        for src in (zoning or {}, external or {}):
            for k, items in src.items():
                merged[k] = merged.get(k, 0) + len(items)
        counts["zoning"] = merged
    if vial:
        groups.append(vial_features(vial))
        counts["vial"] = {k: len(v) for k, v in vial.items()}

    world = [[_to_mercator(c) for c in g.coords] for g in groups]
    everything = [w for ws in world for w in ws]
    if not everything:
        raise ValueError("no hay features para teselar")
    allpts = np.concatenate(everything)
    (x_min, y_min), (x_max, y_max) = allpts.min(axis=0), allpts.max(axis=0)
    west, north = _tile_to_lonlat(x_min, y_min)
    east, south = _tile_to_lonlat(x_max, y_max)

    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    digest = hashlib.sha256()
    listing: dict[str, list[str]] = {}
    total_bytes = 0
    for z in range(minzoom, maxzoom + 1):
        tiles: dict[tuple[int, int], dict[str, _LayerBuilder]] = {}
        for g, w in zip(groups, world):
            _cut_zoom(g, w, z, tiles)
        names = []
        for (tx, ty) in sorted(tiles):
            layers = tiles[(tx, ty)]
            data = encode_tile([layers[g.layer] for g in groups if g.layer in layers])
            if not data:
                continue
            # mtime=0: mismos datos → mismos bytes → git no ve cambios falsos
            blob = gzip.compress(data, compresslevel=9, mtime=0)
            path = out_dir / str(z) / str(tx) / f"{ty}{TILE_SUFFIX}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            digest.update(f"{z}/{tx}/{ty}:".encode())
            digest.update(blob)
            total_bytes += len(blob)
            names.append(f"{tx}/{ty}")
        if names:
            listing[str(z)] = names

    info = {
        "format": FORMAT,
        "version": VERSION,
        "minzoom": minzoom,
        "maxzoom": maxzoom,
        "bounds": [round(float(v), 6) for v in (west, south, east, north)],
        "layers": [g.layer for g in groups],
        "counts": counts,
        "hash": digest.hexdigest()[:8],
        "bytes": total_bytes,
        "tiles": listing,
    }
    (out_dir / "tiles.json").write_text(
        json.dumps(info, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return info


def _load_module(city_dir: Path, manifest: dict, module: str) -> dict[str, list[dict]] | None:
    from shared.compact import COMPACT_MODULES, read_compact, read_legacy_js

    entry = manifest.get("modules", {}).get(module)
    if not entry:
        return None
    base = COMPACT_MODULES[module]
    name = entry.get("file") or f"{base}.js"
    path = city_dir / name
    if not path.exists():
        return None
    if path.suffix == ".json":
        return read_compact(path)[0]
    return read_legacy_js(path, module)[0]


def build_city_tiles(visualizer_root: Path, slug: str, quiet: bool = False) -> dict | None:
    """Arma las teselas de una ciudad con los módulos que tenga y actualiza su manifest.

    Devuelve el tiles.json, o None si la ciudad no tiene zoning/vial/externos.
    """
    from shared.registry import clear_manifest_tiles, load_manifest, save_manifest_tiles

    city_dir = Path(visualizer_root) / "cities" / slug
    manifest = load_manifest(visualizer_root, slug) or {"modules": {}}
    zoning = _load_module(city_dir, manifest, "zoning")
    external = _load_module(city_dir, manifest, "external_buildings")
    vial = _load_module(city_dir, manifest, "vial")
    total = sum(len(items) for src in (zoning, external, vial) if src for items in src.values())
    if total == 0:
        # Nada que teselar (ej. un bbox sin datos): que no queden teselas viejas
        if (city_dir / TILES_DIRNAME).exists():
            shutil.rmtree(city_dir / TILES_DIRNAME)
        if "tiles" in manifest:
            clear_manifest_tiles(visualizer_root, slug)
        return None

    t = time.time()
    info = build_tiles(city_dir / TILES_DIRNAME, zoning=zoning, external=external, vial=vial)
    save_manifest_tiles(
        visualizer_root, slug,
        {
            "path": TILES_DIRNAME,
            "hash": info["hash"],
            "minzoom": info["minzoom"],
            "maxzoom": info["maxzoom"],
            "layers": info["layers"],
        },
    )
    if not quiet:
        n = sum(len(v) for v in info["tiles"].values())
        print(f"Tiles        : {city_dir / TILES_DIRNAME} — {n} teselas, "
              f"{info['bytes'] / 1048576:.1f} MB, {time.time() - t:.0f} s")
    return info


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    parser = argparse.ArgumentParser(description="Genera las teselas vectoriales del visualizador")
    parser.add_argument("--city", help="Solo esta ciudad (default: todas las de visualizer/cities/)")
    parser.add_argument(
        "--visualizer-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "visualizer",
    )
    args = parser.parse_args(argv)

    cities_dir = args.visualizer_root / "cities"
    slugs = [args.city] if args.city else sorted(p.name for p in cities_dir.iterdir() if p.is_dir())
    for slug in slugs:
        print(f"[{slug}]")
        if build_city_tiles(args.visualizer_root, slug) is None:
            print("  sin zoning/vial: nada que teselar")


if __name__ == "__main__":
    main()
