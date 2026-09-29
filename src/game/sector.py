"""Sector model for market simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Sector:
    """A market sector with shared economic conditions."""

    name: str
    sentiment: float = 0.0
    growth: float = 0.02
    volatility: float = 0.3

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sentiment": self.sentiment,
            "growth": self.growth,
            "volatility": self.volatility,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sector:
        return cls(
            name=data["name"],
            sentiment=data.get("sentiment", 0.0),
            growth=data.get("growth", 0.02),
            volatility=data.get("volatility", 0.3),
        )


DEFAULT_SECTORS: list[Sector] = [
    Sector(name="Mining", sentiment=0.0, growth=0.03, volatility=0.55),
    Sector(name="Technology", sentiment=0.1, growth=0.08, volatility=0.65),
    Sector(name="Consumer Staples", sentiment=0.05, growth=0.015, volatility=0.2),
    Sector(name="Energy", sentiment=0.0, growth=0.04, volatility=0.5),
    Sector(name="Banking", sentiment=0.0, growth=0.025, volatility=0.4),
    Sector(name="Healthcare", sentiment=0.05, growth=0.045, volatility=0.35),
    Sector(name="Manufacturing", sentiment=0.0, growth=0.03, volatility=0.4),
    Sector(name="Transport", sentiment=-0.05, growth=0.02, volatility=0.45),
    Sector(name="Retail", sentiment=0.0, growth=0.035, volatility=0.4),
]
