"""Player state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .company import Company
from .portfolio import Portfolio

STARTING_CASH = 10_000.0


@dataclass
class Player:
    """The human trader."""

    cash: float = STARTING_CASH
    portfolio: Portfolio = field(default_factory=Portfolio)
    previous_total_value: float = STARTING_CASH

    def total_value(self, companies: dict[str, Company]) -> float:
        return self.cash + self.portfolio.invested_value(companies)

    def invested_value(self, companies: dict[str, Company]) -> float:
        return self.portfolio.invested_value(companies)

    def profit_loss(self, companies: dict[str, Company]) -> float:
        return self.total_value(companies) - STARTING_CASH

    def daily_change(self, companies: dict[str, Company]) -> float:
        current = self.total_value(companies)
        return current - self.previous_total_value

    def snapshot_value(self, companies: dict[str, Company]) -> None:
        self.previous_total_value = self.total_value(companies)

    def summary(self, companies: dict[str, Company]) -> dict[str, float]:
        return {
            "cash": self.cash,
            "invested": self.invested_value(companies),
            "total": self.total_value(companies),
            "profit_loss": self.profit_loss(companies),
            "daily_change": self.daily_change(companies),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash": self.cash,
            "portfolio": self.portfolio.to_dict(),
            "previous_total_value": self.previous_total_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Player:
        return cls(
            cash=data["cash"],
            portfolio=Portfolio.from_dict(data.get("portfolio", {})),
            previous_total_value=data.get("previous_total_value", data["cash"]),
        )
