"""Top-level simulation combining market, player, bots, and idle progression."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.game.bots import BotManager, flow_to_price_effects
from src.game.company import Company
from src.game.market import Market
from src.game.player import Player
from src.game.progression import Progression, UPGRADE_NAMES
from src.game import trading


class LockedCompanyError(trading.TradeError):
    """Raised when the player tries to trade a locked company."""


@dataclass
class Simulation:
    """Owns market + player + bots + progression and exposes the public game API."""

    seed: int = 42
    market: Market = field(init=False)
    player: Player = field(default_factory=Player)
    bots: BotManager = field(default_factory=BotManager)
    progression: Progression = field(default_factory=Progression)
    debug_mode: bool = False
    auto_run: bool = False
    auto_speed_ms: int = 400
    last_levels_gained: list[int] = field(default_factory=list)
    last_offline_report: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.market = Market(seed=self.seed)
        if self.progression.last_realtime is None:
            self.progression.last_realtime = time.time()

    @property
    def day(self) -> int:
        return self.market.day

    @property
    def companies(self) -> dict[str, Company]:
        return self.market.companies

    def unlocked_companies(self) -> list[Company]:
        return [
            c
            for c in self.market.company_list()
            if self.progression.is_unlocked(c.id)
        ]

    def step(self, *, offline: bool = False) -> dict[str, Any]:
        """Advance one day: bots trade, market moves, then player passive income."""
        trade_day = self.market.day + 1
        flow_notional, activities = self.bots.act(self.market, day=trade_day)
        flow_effects = flow_to_price_effects(flow_notional, self.companies)
        result = self.market.step(flow_pressure=flow_effects)
        result["bot_activity"] = activities
        result["flow_effects"] = flow_effects

        income_mult = self.progression.offline_efficiency() if offline else 1.0
        passive = self._apply_passive_income(income_mult)
        result["passive"] = passive

        auto_trades = self._maybe_auto_trade()
        result["auto_trades"] = auto_trades

        levels = self.progression.add_xp(2)
        result["levels_gained"] = levels
        if levels:
            self.last_levels_gained = levels
        return result

    def end_of_day_snapshot(self) -> None:
        self.player.snapshot_value(self.companies)

    def advance(self, days: int = 1, *, offline: bool = False) -> list[dict[str, Any]]:
        results = []
        for _ in range(days):
            results.append(self.step(offline=offline))
            self.end_of_day_snapshot()
        self.touch_realtime()
        return results

    def _apply_passive_income(self, efficiency: float = 1.0) -> dict[str, float]:
        invested = self.player.invested_value(self.companies)
        dividends = invested * self.progression.daily_dividend_rate() * efficiency
        base = self.progression.daily_base_income() * efficiency
        total = dividends + base
        self.player.cash += total
        self.progression.total_dividends_earned += dividends
        return {"dividends": dividends, "base_income": base, "total": total}

    def _maybe_auto_trade(self) -> list[dict[str, Any]]:
        """Simple auto-pilot: buy small dips on unlocked names when cash allows."""
        level = self.progression.auto_level()
        if level <= 0:
            return []
        trades: list[dict[str, Any]] = []
        # Higher auto level = more aggressive dip buying.
        dip_threshold = -0.015 if level == 1 else (-0.01 if level == 2 else -0.005)
        budget_frac = 0.04 + level * 0.03
        candidates = [
            c
            for c in self.unlocked_companies()
            if c.daily_change <= dip_threshold and c.share_price > 0
        ]
        if not candidates:
            return []
        # Prefer the biggest dip.
        candidates.sort(key=lambda c: c.daily_change)
        company = candidates[0]
        budget = self.player.cash * budget_frac
        max_shares = min(
            self.progression.max_trade_shares(),
            trading.max_affordable(self.player, company),
            int(budget / company.share_price) if company.share_price else 0,
        )
        shares = max(0, max_shares)
        if shares <= 0:
            return []
        try:
            result = trading.buy(self.player, company, shares)
            self.progression.add_xp(3)
            trades.append(
                {
                    "side": "BUY",
                    "company_id": company.id,
                    "company_name": company.name,
                    "shares": result.shares,
                    "price": result.price,
                }
            )
        except trading.TradeError:
            return []
        return trades

    def buy(self, company_id: str, shares: int) -> trading.TradeResult:
        if not self.progression.is_unlocked(company_id):
            raise LockedCompanyError("Company is locked — level up to unlock")
        company = self.market.get_company(company_id)
        max_shares = self.progression.max_trade_shares()
        if shares > max_shares:
            raise trading.TradeError(f"Trade volume capped at {max_shares} shares")
        result = trading.buy(self.player, company, shares)
        levels = self.progression.add_xp(5)
        if levels:
            self.last_levels_gained = levels
        self.touch_realtime()
        return result

    def sell(self, company_id: str, shares: int) -> trading.TradeResult:
        if not self.progression.is_unlocked(company_id):
            raise LockedCompanyError("Company is locked — level up to unlock")
        company = self.market.get_company(company_id)
        max_shares = self.progression.max_trade_shares()
        if shares > max_shares:
            raise trading.TradeError(f"Trade volume capped at {max_shares} shares")
        result = trading.sell(self.player, company, shares)
        levels = self.progression.add_xp(5)
        if levels:
            self.last_levels_gained = levels
        self.touch_realtime()
        return result

    def buy_upgrade(self, key: str) -> bool:
        ok = self.progression.buy_upgrade(key)
        if ok:
            self.touch_realtime()
        return ok

    def prestige(self) -> bool:
        ok = self.progression.prestige(self.player.total_value(self.companies))
        if ok:
            self.touch_realtime()
        return ok

    def touch_realtime(self, now: float | None = None) -> None:
        self.progression.last_realtime = time.time() if now is None else now

    def apply_offline_gains(self, now: float | None = None) -> dict[str, Any]:
        """Convert elapsed real time into simulated days + reduced passive income."""
        now = time.time() if now is None else now
        last = self.progression.last_realtime
        if last is None:
            self.progression.last_realtime = now
            report = {"days": 0, "passive_total": 0.0, "elapsed_seconds": 0.0}
            self.last_offline_report = report
            return report

        elapsed = max(0.0, now - last)
        seconds_per_day = self.progression.offline_seconds_per_day()
        days = int(elapsed / seconds_per_day)
        days = min(days, self.progression.max_offline_days())
        # Always refresh bookmark so tiny gaps don't accumulate forever wrongly.
        self.progression.last_realtime = now
        if days <= 0:
            report = {"days": 0, "passive_total": 0.0, "elapsed_seconds": elapsed}
            self.last_offline_report = report
            return report

        before = self.player.total_value(self.companies)
        results = self.advance(days, offline=True)
        self.progression.total_offline_days += days
        passive_total = sum(r.get("passive", {}).get("total", 0.0) for r in results)
        after = self.player.total_value(self.companies)
        report = {
            "days": days,
            "elapsed_seconds": elapsed,
            "passive_total": passive_total,
            "net_worth_before": before,
            "net_worth_after": after,
            "net_change": after - before,
        }
        self.last_offline_report = report
        return report

    def portfolio_summary(self) -> dict[str, float]:
        return self.player.summary(self.companies)

    def position_details(self) -> list[dict[str, Any]]:
        return self.player.portfolio.position_details(self.companies)

    def news(self, limit: int = 12) -> list:
        return self.market.events.news_feed[:limit]

    def bot_activity(self, limit: int = 10) -> list:
        return self.bots.activity_feed[:limit]

    def leaderboard(self) -> list[dict[str, Any]]:
        return self.bots.leaderboard(self.player, self.companies)

    def progression_summary(self) -> dict[str, Any]:
        summary = self.progression.summary()
        summary["upgrade_labels"] = dict(UPGRADE_NAMES)
        summary["can_prestige"] = self.progression.can_prestige(
            self.player.total_value(self.companies)
        )
        return summary

    def to_dict(self) -> dict[str, Any]:
        market_data = self.market.to_dict()
        market_data["rng"] = self.market.serialize_rng()
        market_data.pop("rng_state", None)
        market_data.pop("rng_version", None)
        market_data.pop("rng_gauss", None)
        return {
            "seed": self.seed,
            "debug_mode": self.debug_mode,
            "market": market_data,
            "player": self.player.to_dict(),
            "bots": self.bots.to_dict(),
            "progression": self.progression.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Simulation:
        sim = cls(seed=data["seed"], debug_mode=data.get("debug_mode", False))
        sim.market = Market.from_dict(data["market"])
        sim.player = Player.from_dict(data["player"])
        if "bots" in data:
            sim.bots = BotManager.from_dict(data["bots"])
        if "progression" in data:
            sim.progression = Progression.from_dict(data["progression"])
        return sim
