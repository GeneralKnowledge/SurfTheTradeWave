"""Idle / incremental progression: XP, unlocks, upgrades, prestige."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Company unlock thresholds (player level required to trade).
COMPANY_UNLOCK_LEVEL: dict[str, int] = {
    "ironvale": 1,
    "albion": 1,
    "sterling": 1,
    "highstreet": 1,
    "greengrid": 2,
    "forgeway": 2,
    "swiftline": 3,
    "helixbio": 3,
    "pixelworks": 4,
    "northstar": 5,
}

UPGRADE_NAMES = {
    "offline": "Offline Efficiency",
    "dividends": "Dividend Yield",
    "volume": "Trade Volume",
    "income": "Base Income",
    "auto": "Auto-Pilot",
}

UPGRADE_MAX = {
    "offline": 5,
    "dividends": 5,
    "volume": 5,
    "income": 5,
    "auto": 3,
}

UPGRADE_COSTS = {
    # cost in upgrade points for next level (index = current level)
    "offline": [1, 1, 2, 2, 3],
    "dividends": [1, 1, 2, 2, 3],
    "volume": [1, 1, 2, 2, 3],
    "income": [1, 1, 2, 2, 3],
    "auto": [2, 3, 4],
}


def xp_to_next_level(level: int) -> int:
    """XP required to go from `level` to level+1."""
    return 20 + (level - 1) * 15


@dataclass
class Progression:
    """Screen-Stocks-style meta progression for the human player."""

    level: int = 1
    xp: int = 0
    upgrade_points: int = 1  # start with 1 point to spend
    upgrades: dict[str, int] = field(
        default_factory=lambda: {
            "offline": 0,
            "dividends": 0,
            "volume": 0,
            "income": 0,
            "auto": 0,
        }
    )
    prestige_count: int = 0
    prestige_multiplier: float = 1.0
    # Real-time bookmark for offline gains (unix seconds).
    last_realtime: float | None = None
    total_dividends_earned: float = 0.0
    total_offline_days: int = 0

    def xp_needed(self) -> int:
        return xp_to_next_level(self.level)

    def add_xp(self, amount: int) -> list[int]:
        """Add XP. Returns list of new levels reached (may be empty)."""
        if amount <= 0:
            return []
        gained: list[int] = []
        self.xp += int(amount * self.prestige_multiplier)
        while self.xp >= self.xp_needed():
            self.xp -= self.xp_needed()
            self.level += 1
            self.upgrade_points += 1
            gained.append(self.level)
        return gained

    def is_unlocked(self, company_id: str) -> bool:
        required = COMPANY_UNLOCK_LEVEL.get(company_id, 1)
        return self.level >= required

    def unlocked_company_ids(self) -> list[str]:
        return [
            cid for cid, req in COMPANY_UNLOCK_LEVEL.items() if self.level >= req
        ]

    def next_unlocks(self) -> list[tuple[str, int]]:
        """Upcoming company unlocks (id, level)."""
        upcoming = [
            (cid, req)
            for cid, req in COMPANY_UNLOCK_LEVEL.items()
            if req > self.level
        ]
        upcoming.sort(key=lambda x: x[1])
        return upcoming

    def upgrade_cost(self, key: str) -> int | None:
        level = self.upgrades.get(key, 0)
        costs = UPGRADE_COSTS.get(key, [])
        if level >= UPGRADE_MAX.get(key, 0):
            return None
        if level >= len(costs):
            return None
        return costs[level]

    def can_buy_upgrade(self, key: str) -> bool:
        cost = self.upgrade_cost(key)
        return cost is not None and self.upgrade_points >= cost

    def buy_upgrade(self, key: str) -> bool:
        cost = self.upgrade_cost(key)
        if cost is None or self.upgrade_points < cost:
            return False
        self.upgrade_points -= cost
        self.upgrades[key] = self.upgrades.get(key, 0) + 1
        return True

    # --- derived gameplay stats ---

    def offline_seconds_per_day(self) -> float:
        """Real seconds that equal one simulated day while away."""
        # Base 90s/day; each offline level makes idle faster.
        return max(20.0, 90.0 - self.upgrades.get("offline", 0) * 12.0)

    def max_offline_days(self) -> int:
        return 10 + self.upgrades.get("offline", 0) * 8

    def offline_efficiency(self) -> float:
        """Fraction of dividends / income captured while offline."""
        return 0.35 + self.upgrades.get("offline", 0) * 0.12

    def daily_dividend_rate(self) -> float:
        """Fraction of invested value paid as cash per simulated day."""
        return 0.0004 * self.upgrades.get("dividends", 0) * self.prestige_multiplier

    def daily_base_income(self) -> float:
        level = self.upgrades.get("income", 0)
        return (2.0 + level * 8.0) * self.prestige_multiplier

    def max_trade_shares(self) -> int:
        return 50 + self.upgrades.get("volume", 0) * 40

    def auto_level(self) -> int:
        return self.upgrades.get("auto", 0)

    def can_prestige(self, net_worth: float) -> bool:
        return self.level >= 5 and net_worth >= 25_000

    def prestige(self, net_worth: float) -> bool:
        if not self.can_prestige(net_worth):
            return False
        self.prestige_count += 1
        self.prestige_multiplier = 1.0 + self.prestige_count * 0.15
        self.level = 1
        self.xp = 0
        self.upgrade_points = 1 + self.prestige_count
        self.upgrades = {k: 0 for k in UPGRADE_MAX}
        return True

    def summary(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "xp": self.xp,
            "xp_needed": self.xp_needed(),
            "upgrade_points": self.upgrade_points,
            "upgrades": dict(self.upgrades),
            "prestige_count": self.prestige_count,
            "prestige_multiplier": self.prestige_multiplier,
            "unlocked": self.unlocked_company_ids(),
            "daily_dividend_rate": self.daily_dividend_rate(),
            "daily_base_income": self.daily_base_income(),
            "max_trade_shares": self.max_trade_shares(),
            "auto_level": self.auto_level(),
            "offline_seconds_per_day": self.offline_seconds_per_day(),
            "max_offline_days": self.max_offline_days(),
            "offline_efficiency": self.offline_efficiency(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "xp": self.xp,
            "upgrade_points": self.upgrade_points,
            "upgrades": dict(self.upgrades),
            "prestige_count": self.prestige_count,
            "prestige_multiplier": self.prestige_multiplier,
            "last_realtime": self.last_realtime,
            "total_dividends_earned": self.total_dividends_earned,
            "total_offline_days": self.total_offline_days,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Progression:
        upgrades = {
            "offline": 0,
            "dividends": 0,
            "volume": 0,
            "income": 0,
            "auto": 0,
        }
        upgrades.update(data.get("upgrades", {}))
        return cls(
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            upgrade_points=data.get("upgrade_points", 1),
            upgrades=upgrades,
            prestige_count=data.get("prestige_count", 0),
            prestige_multiplier=data.get("prestige_multiplier", 1.0),
            last_realtime=data.get("last_realtime"),
            total_dividends_earned=data.get("total_dividends_earned", 0.0),
            total_offline_days=data.get("total_offline_days", 0),
        )
