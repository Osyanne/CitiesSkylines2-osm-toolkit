"""Mapping YAML loader — translates city-specific zoning codes to CS2 zones."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class UnknownCodeStrategy(Enum):
    SKIP = "skip"
    DEFAULT = "default"


@dataclass(frozen=True)
class Mapping:
    """Per-city zoning code → CS2 zone translation table."""

    city: str
    source_url: str
    source_field: str
    crs_in: str
    last_validated: str
    mappings: dict[str, str]
    unmapped_strategy: UnknownCodeStrategy
    default_zone: Optional[str] = None

    def translate(self, code: str) -> Optional[str]:
        """Translate a city zoning code to a CS2 zone key, or None if unmapped + SKIP."""
        if code in self.mappings:
            return self.mappings[code]
        if self.unmapped_strategy is UnknownCodeStrategy.DEFAULT:
            return self.default_zone
        return None


def load_mapping(path: Path) -> Mapping:
    """Load a city's mapping YAML and return a Mapping object."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    unmapped = data.get("unmapped", "skip")
    if isinstance(unmapped, str) and unmapped == "skip":
        strategy = UnknownCodeStrategy.SKIP
        default = None
    elif isinstance(unmapped, dict) and "default" in unmapped:
        strategy = UnknownCodeStrategy.DEFAULT
        default = unmapped["default"]
    else:
        raise ValueError(f"Invalid 'unmapped' field in {path}: {unmapped!r}")

    return Mapping(
        city=data["city"],
        source_url=data["source_url"],
        source_field=data["source_field"],
        crs_in=data["crs_in"],
        last_validated=str(data["last_validated"]),
        mappings=dict(data["mappings"]),
        unmapped_strategy=strategy,
        default_zone=default,
    )
