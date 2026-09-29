"""Top-level simulation combining market and player."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.game.company import Company
from src.game.market import Market
from src.game.player import Player
from src.game import trading


@dataclass
class Simulation:
    """Owns market + player and exposes the public game API."""

    seed: int = 42
    market: Market = field(init=False)
    player: Player = field(default_factory=Player)
    debug_mode: bool = False
    auto_run: bool = False
    auto_speed_ms: int = 400

    def __post_init__(self) -> None:
        self.market = Market(seed=self.seed)

    @property
    def day(self) -> int:
        return self.market.day

    @property
    def companies(self) -> dict[str, Company]:
        return self.market.companies

    def step(self) -> dict[str, Any]:
        """Advance one day and update portfolio snapshots."""
        result = self.market.step()
        # Daily change is relative to value at previous close.
        # Snapshot is taken after prices move so next day's daily_change works.
        # Before snapshot, daily_change still reflects move vs prior day.
        return result

    def end_of_day_snapshot(self) -> None:
        self.player.snapshot_value(self.companies)

    def advance(self, days: int = 1) -> list[dict[str, Any]]:
        results = []
        for _ in range(days):
            results.append(self.step())
            self.end_of_day_snapshot()
        return results

    def buy(self, company_id: str, shares: int) -> trading.TradeResult:
        company = self.market.get_company(company_id)
        return trading.buy(self.player, company, shares)

    def sell(self, company_id: str, shares: int) -> trading.TradeResult:
        company = self.market.get_company(company_id)
        return trading.sell(self.player, company, shares)

    def portfolio_summary(self) -> dict[str, float]:
        return self.player.summary(self.companies)

    def position_details(self) -> list[dict[str, Any]]:
        return self.player.portfolio.position_details(self.companies)

    def news(self, limit: int = 12) -> list:
        return self.market.events.news_feed[:limit]

    def to_dict(self) -> dict[str, Any]:
        market_data = self.market.to_dict()
        market_data["rng"] = self.market.serialize_rng()
        # Remove partial rng fields from to_dict if present.
        market_data.pop("rng_state", None)
        market_data.pop("rng_version", None)
        market_data.pop("rng_gauss", None)
        return {
            "seed": self.seed,
            "debug_mode": self.debug_mode,
            "market": market_data,
            "player": self.player.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Simulation:
        sim = cls(seed=data["seed"], debug_mode=data.get("debug_mode", False))
        sim.market = Market.from_dict(data["market"])
        sim.player = Player.from_dict(data["player"])
        return sim
