"""
morphology_config.py — Umbrales de la densidad residencial inferida
====================================================================
Parámetros de las dos pasadas que corrigen la densidad de los edificios
residenciales que OSM deja como casa baja (`res_low_house`):

  1. Altura: si el edificio trae `building:levels` o `height`, manda la altura.
  2. Morfología: si no la trae, se mira cuánto de su contorno comparte con otros
     edificios y cuánto suelo está construido alrededor.

Los valores salen de calibrar contra Amberes, Beverlo, Kiel y Minneapolis
(ver docs/plans/2026-09-24-densidad-residencial-morfologia.md). Los tests no
dependen de ellos: construyen su propia configuración.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MorphologyConfig:
    # ── Geometría ──
    # Distancia a la que dos contornos se consideran pegados (errores de
    # digitalización: medianeras dibujadas con un hueco de unos centímetros).
    touch_tolerance_m: float = 0.5
    # Tramo compartido mínimo con un vecino para contarlo (descarta esquinas que
    # se tocan en un punto y roces de un par de metros).
    min_shared_length_m: float = 3.0
    # Radio del círculo en el que se mide la cobertura de suelo construido.
    coverage_radius_m: float = 60.0

    # Edificios accesorios: cuentan para la cobertura pero no como pared
    # compartida (un garaje pegado a una casa no la vuelve casa en hilera).
    accessory_buildings: tuple[str, ...] = (
        "garage", "garages", "carport", "shed", "roof", "hut", "greenhouse",
        "kiosk", "toilets", "service", "outbuilding", "farm_auxiliary",
    )

    # ── Pasada de altura ──
    # Niveles efectivos = max(building:levels, round(height / 3)).
    generic_levels_med_min: int = 3   # building=yes en zona residencial
    house_levels_med_min: int = 4     # building=house: 3 pisos todavía es casa
    levels_high_min: int = 7          # torre: alta densidad

    # ── Pasada de morfología ──
    # Fracción del perímetro pegada a otros edificios para considerarlo adosado.
    shared_frac_min: float = 0.25
    # Cobertura del entorno a partir de la cual un adosado es densidad media
    # (cascos antiguos, manzanas cerradas).
    coverage_med_min: float = 0.45
    # Cobertura mínima para casas en hilera (por debajo, se queda casa baja).
    coverage_row_min: float = 0.20
    # Footprint máximo de una casa en hilera; más grande y en cobertura media
    # se trata como densidad media.
    row_area_max_m2: float = 250.0


DEFAULT = MorphologyConfig()
