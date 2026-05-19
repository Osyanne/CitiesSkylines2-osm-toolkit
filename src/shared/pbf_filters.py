"""
pbf_filters.py
==============
Structured filter specs para extracción PBF. Reemplazan Overpass QL strings
con datos estructurados que el pbf_client puede ejecutar contra un .osm.pbf.

Vocabulario:
- TagMatcher: predicado sobre tags de un elemento OSM
- Clause: "una clause de la query" — qué geometrías + qué tag filters (OR de tag matchers)
- SpatialJoin: post-procesado "elementos de target_clause que estén a buffer_m
  metros o menos de algún elemento de anchor_clause"
- FilterSpec: query completa — múltiples clauses nombradas (union deduplicada
  por (type, id)) + spatial joins opcionales

Diseñado para ser sibling de las funciones build_queries(bbox) existentes:
build_pbf_filters(bbox) retorna dict[str, FilterSpec] con las mismas keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


GeomType = Literal["node", "way", "relation"]
VALID_GEOM_TYPES: set[str] = {"node", "way", "relation"}


class FilterSpecError(ValueError):
    """Filter spec inválido."""


@dataclass(frozen=True)
class TagMatcher:
    """
    Predicado sobre el dict de tags de un elemento OSM.

    Reglas:
    - {"key": "value"}        — tag key existe Y igual a value
    - {"key": True}           — tag key existe (cualquier valor, incl. "")
    - {"key": [v1, v2, ...]}  — tag key existe Y valor está en la lista
    - Múltiples keys en el mismo TagMatcher: TODAS deben cumplirse (AND)
    """
    spec: dict[str, str | bool | list[str]]

    def __post_init__(self) -> None:
        if not self.spec:
            raise FilterSpecError("TagMatcher.spec no puede estar vacío")

    def matches(self, tags: dict[str, str]) -> bool:
        for key, expected in self.spec.items():
            actual = tags.get(key)
            if actual is None:
                return False
            if expected is True:
                continue  # presence-only
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False
        return True


@dataclass(frozen=True)
class Clause:
    """
    Una clause: qué tipos de geometría buscar + qué tag matchers aplicar (OR).

    Un elemento matchea la clause si:
    - su tipo está en geom_types, Y
    - al menos un TagMatcher en tag_filters retorna True para sus tags
    """
    geom_types: list[GeomType]
    tag_filters: list[TagMatcher]

    def __post_init__(self) -> None:
        if not self.geom_types:
            raise FilterSpecError("Clause.geom_types no puede estar vacío")
        for gt in self.geom_types:
            if gt not in VALID_GEOM_TYPES:
                raise FilterSpecError(f"geom_type inválido: {gt!r}")
        if not self.tag_filters:
            raise FilterSpecError("Clause.tag_filters no puede estar vacío")

    def matches(self, geom_type: str, tags: dict[str, str]) -> bool:
        if geom_type not in self.geom_types:
            return False
        return any(m.matches(tags) for m in self.tag_filters)


@dataclass(frozen=True)
class SpatialJoin:
    """
    Post-procesado: 'devolver solo elementos de target_clause que estén a
    buffer_m metros o menos de algún elemento de anchor_clause'.

    Replica el patrón Overpass `(nodes A)->.x; way(around.x:5);`.
    """
    anchor_clause: str
    target_clause: str
    buffer_m: float

    def __post_init__(self) -> None:
        if self.buffer_m < 0:
            raise FilterSpecError(f"buffer_m no puede ser negativo: {self.buffer_m}")
        if not self.anchor_clause or not self.target_clause:
            raise FilterSpecError("anchor_clause y target_clause son obligatorios")


@dataclass(frozen=True)
class FilterSpec:
    """
    Query completa: múltiples clauses nombradas (union deduplicada por
    (type, id)) + spatial joins opcionales aplicados post-extracción.
    """
    clauses: dict[str, Clause]
    spatial_joins: list[SpatialJoin] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.clauses:
            raise FilterSpecError("FilterSpec.clauses no puede estar vacío")
        clause_names = set(self.clauses.keys())
        for sj in self.spatial_joins:
            if sj.anchor_clause not in clause_names:
                raise FilterSpecError(
                    f"SpatialJoin.anchor_clause '{sj.anchor_clause}' no está en clauses"
                )
            if sj.target_clause not in clause_names:
                raise FilterSpecError(
                    f"SpatialJoin.target_clause '{sj.target_clause}' no está en clauses"
                )
