"""Company model and price-history tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PricePoint:
    """A single historical price observation."""

    day: int
    price: float


@dataclass
class PriceMovement:
    """Breakdown of why a price changed on a given day."""

    fundamental_effect: float = 0.0
    sector_effect: float = 0.0
    event_effect: float = 0.0
    sentiment_effect: float = 0.0
    market_effect: float = 0.0
    flow_effect: float = 0.0
    noise_effect: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.fundamental_effect
            + self.sector_effect
            + self.event_effect
            + self.sentiment_effect
            + self.market_effect
            + self.flow_effect
            + self.noise_effect
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "fundamental_effect": self.fundamental_effect,
            "sector_effect": self.sector_effect,
            "event_effect": self.event_effect,
            "sentiment_effect": self.sentiment_effect,
            "market_effect": self.market_effect,
            "flow_effect": self.flow_effect,
            "noise_effect": self.noise_effect,
            "total": self.total,
        }


@dataclass
class Company:
    """A fictional publicly traded company."""

    id: str
    name: str
    sector: str
    share_price: float
    shares_outstanding: int
    revenue: float
    profit: float
    debt: float
    growth_rate: float
    profitability: float
    volatility: float
    sentiment: float
    reputation: float
    commodity_exposure: float
    sector_sensitivity: float = 1.0
    fair_value: float = 0.0
    fundamental_base: float = 0.0
    previous_price: float = 0.0
    price_history: list[PricePoint] = field(default_factory=list)
    last_movement: PriceMovement = field(default_factory=PriceMovement)

    def __post_init__(self) -> None:
        if self.previous_price <= 0:
            self.previous_price = self.share_price
        if self.fundamental_base <= 0:
            self.fundamental_base = self.share_price
        if self.fair_value <= 0:
            self.fair_value = self.share_price
        if not self.price_history:
            self.price_history.append(PricePoint(day=0, price=self.share_price))

    @property
    def daily_change(self) -> float:
        if self.previous_price <= 0:
            return 0.0
        return (self.share_price - self.previous_price) / self.previous_price

    @property
    def daily_change_pct(self) -> float:
        return self.daily_change * 100.0

    @property
    def market_cap(self) -> float:
        return self.share_price * self.shares_outstanding

    def record_price(self, day: int) -> None:
        self.price_history.append(PricePoint(day=day, price=self.share_price))

    def history_slice(self, days: int | None = None) -> list[PricePoint]:
        if days is None or days >= len(self.price_history):
            return list(self.price_history)
        return list(self.price_history[-days:])

    def apply_price(self, new_price: float, movement: PriceMovement) -> None:
        self.previous_price = self.share_price
        self.share_price = max(0.01, new_price)
        self.last_movement = movement

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "sector": self.sector,
            "share_price": self.share_price,
            "shares_outstanding": self.shares_outstanding,
            "revenue": self.revenue,
            "profit": self.profit,
            "debt": self.debt,
            "growth_rate": self.growth_rate,
            "profitability": self.profitability,
            "volatility": self.volatility,
            "sentiment": self.sentiment,
            "reputation": self.reputation,
            "commodity_exposure": self.commodity_exposure,
            "sector_sensitivity": self.sector_sensitivity,
            "fair_value": self.fair_value,
            "fundamental_base": self.fundamental_base,
            "previous_price": self.previous_price,
            "price_history": [{"day": p.day, "price": p.price} for p in self.price_history],
            "last_movement": self.last_movement.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Company:
        history = [
            PricePoint(day=p["day"], price=p["price"]) for p in data.get("price_history", [])
        ]
        movement_data = data.get("last_movement", {})
        movement = PriceMovement(
            fundamental_effect=movement_data.get("fundamental_effect", 0.0),
            sector_effect=movement_data.get("sector_effect", 0.0),
            event_effect=movement_data.get("event_effect", 0.0),
            sentiment_effect=movement_data.get("sentiment_effect", 0.0),
            market_effect=movement_data.get("market_effect", 0.0),
            flow_effect=movement_data.get("flow_effect", 0.0),
            noise_effect=movement_data.get("noise_effect", 0.0),
        )
        return cls(
            id=data["id"],
            name=data["name"],
            sector=data["sector"],
            share_price=data["share_price"],
            shares_outstanding=data["shares_outstanding"],
            revenue=data["revenue"],
            profit=data["profit"],
            debt=data["debt"],
            growth_rate=data["growth_rate"],
            profitability=data["profitability"],
            volatility=data["volatility"],
            sentiment=data["sentiment"],
            reputation=data["reputation"],
            commodity_exposure=data["commodity_exposure"],
            sector_sensitivity=data.get("sector_sensitivity", 1.0),
            fair_value=data.get("fair_value", data["share_price"]),
            fundamental_base=data.get("fundamental_base", data["share_price"]),
            previous_price=data.get("previous_price", data["share_price"]),
            price_history=history,
            last_movement=movement,
        )

    def public_info(self) -> dict[str, Any]:
        """Player-visible company information (no fair value)."""
        return {
            "id": self.id,
            "name": self.name,
            "sector": self.sector,
            "share_price": self.share_price,
            "daily_change": self.daily_change,
            "daily_change_pct": self.daily_change_pct,
            "revenue": self.revenue,
            "profit": self.profit,
            "growth_rate": self.growth_rate,
            "debt": self.debt,
            "profitability": self.profitability,
            "sentiment": self.sentiment,
            "reputation": self.reputation,
        }
