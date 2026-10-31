"""
morphology_config.py — Umbrales de la densidad residencial inferida
====================================================================
Parámetros de las dos pasadas que corrigen la densidad de los edificios
residenciales que OSM deja como casa baja (`res_low_house`):

  1. Altura: si el edificio trae `building:levels` o `height`, manda la altura,
     salvo que esté pegado a sus vecinos, sea chico y tenga hasta 3 pisos: hilera.
  2. Morfología: si no la trae, se mira cuánto de su contorno comparte con otros
     edificios y cuánto suelo está construido alrededor.

Los valores salen de calibrar contra Amberes, Beverlo, Kiel y Minneapolis
(ver docs/plans/2026-09-24-densidad-residencial-morfologia.md); los de la altura,
contra el catastro de Filadelfia y Nueva York (METHODOLOGY.md §19). Los tests no
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
    # Niveles efectivos = max(building:levels, round((height - height_roof_m) / 3)).
    # La altura medida llega a lo alto del techo: en el catastro de Filadelfia y Nueva
    # York, los edificios de 2, 3 y 4 pisos miden ~8,5, ~11,7 y ~14,8 m.
    height_roof_m: float = 2.5
    generic_levels_med_min: int = 3   # building=yes en zona residencial
    house_levels_med_min: int = 4     # building=house: 3 pisos todavía es casa
    levels_high_min: int = 7          # torre: alta densidad
    # Pegado a sus vecinos, de hasta estos pisos y este footprint, es hilera aunque la
    # altura llegue a media. Las hileras de los dos catastros miden 54–109 m²; los
    # edificios sin ascensor de 5 o más familias de Nueva York, 92–179 m².
    height_row_levels_max: int = 3
    height_row_area_max_m2: float = 150.0

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
