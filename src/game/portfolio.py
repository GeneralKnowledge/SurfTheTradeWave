"""Portfolio positions and valuation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .company import Company


@dataclass
class Position:
    """Shares held in a single company."""

    company_id: str
    shares: int
    average_purchase_price: float

    @property
    def cost_basis(self) -> float:
        return self.shares * self.average_purchase_price

    def current_value(self, price: float) -> float:
        return self.shares * price

    def profit_loss(self, price: float) -> float:
        return self.current_value(price) - self.cost_basis

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "shares": self.shares,
            "average_purchase_price": self.average_purchase_price,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Position:
        return cls(
            company_id=data["company_id"],
            shares=data["shares"],
            average_purchase_price=data["average_purchase_price"],
        )


@dataclass
class Portfolio:
    """Collection of stock positions."""

    positions: dict[str, Position] = field(default_factory=dict)

    def get_position(self, company_id: str) -> Position | None:
        return self.positions.get(company_id)

    def shares_owned(self, company_id: str) -> int:
        pos = self.positions.get(company_id)
        return pos.shares if pos else 0

    def invested_value(self, companies: dict[str, Company]) -> float:
        total = 0.0
        for company_id, pos in self.positions.items():
            company = companies.get(company_id)
            if company:
                total += pos.current_value(company.share_price)
        return total

    def total_cost_basis(self) -> float:
        return sum(pos.cost_basis for pos in self.positions.values())

    def profit_loss(self, companies: dict[str, Company]) -> float:
        return self.invested_value(companies) - self.total_cost_basis()

    def position_details(self, companies: dict[str, Company]) -> list[dict[str, Any]]:
        details = []
        for company_id, pos in self.positions.items():
            company = companies.get(company_id)
            if not company:
                continue
            price = company.share_price
            details.append(
                {
                    "company_id": company_id,
                    "company_name": company.name,
                    "shares": pos.shares,
                    "average_cost": pos.average_purchase_price,
                    "current_price": price,
                    "current_value": pos.current_value(price),
                    "profit_loss": pos.profit_loss(price),
                }
            )
        return details

    def to_dict(self) -> dict[str, Any]:
        return {
            "positions": {cid: pos.to_dict() for cid, pos in self.positions.items()}
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Portfolio:
        positions = {
            cid: Position.from_dict(pdata)
            for cid, pdata in data.get("positions", {}).items()
        }
        return cls(positions=positions)
