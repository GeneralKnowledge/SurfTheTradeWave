"""NPC trader bots that simulate other players in the market."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.game.company import Company
from src.game.player import Player
from src.game import trading


class BotPersona(Enum):
    VALUE = "value"  # buy cheap vs fair value, sell rich
    MOMENTUM = "momentum"  # chase recent winners
    GROWTH = "growth"  # prefer high-growth / techy names
    PANIC = "panic"  # dump on fear, FOMO on boom
    NOISE = "noise"  # small random trades


@dataclass
class BotActivity:
    """One visible bot trade for the activity feed."""

    day: int
    bot_id: str
    bot_name: str
    side: str
    company_id: str
    company_name: str
    shares: int
    price: float

    @property
    def summary(self) -> str:
        return (
            f"{self.bot_name} {self.side.lower()} {self.shares} "
            f"{self.company_name} @ £{self.price:.2f}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "bot_id": self.bot_id,
            "bot_name": self.bot_name,
            "side": self.side,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "shares": self.shares,
            "price": self.price,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BotActivity:
        return cls(**data)


@dataclass
class BotTrader:
    """A seeded NPC trader with a simple strategy persona."""

    bot_id: str
    name: str
    persona: BotPersona
    trader: Player = field(default_factory=Player)
    aggression: float = 0.55  # chance / size multiplier

    def net_worth(self, companies: dict[str, Company]) -> float:
        return self.trader.total_value(companies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "name": self.name,
            "persona": self.persona.value,
            "trader": self.trader.to_dict(),
            "aggression": self.aggression,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BotTrader:
        return cls(
            bot_id=data["bot_id"],
            name=data["name"],
            persona=BotPersona(data["persona"]),
            trader=Player.from_dict(data["trader"]),
            aggression=data.get("aggression", 0.55),
        )


DEFAULT_BOT_SPECS: list[tuple[str, str, BotPersona, float, float]] = [
    # bot_id, name, persona, aggression, starting_cash
    ("bot_valeria", "Valeria Vale", BotPersona.VALUE, 0.6, 12_000),
    ("bot_max", "Max Momentum", BotPersona.MOMENTUM, 0.75, 10_000),
    ("bot_grow", "Greta Growth", BotPersona.GROWTH, 0.65, 11_000),
    ("bot_panic", "Perry Panic", BotPersona.PANIC, 0.8, 9_000),
    ("bot_noise", "Ned Noise", BotPersona.NOISE, 0.45, 10_000),
    ("bot_iris", "Iris Index", BotPersona.VALUE, 0.4, 15_000),
]


@dataclass
class BotManager:
    """Runs all NPC traders each day and aggregates order flow."""

    bots: list[BotTrader] = field(default_factory=list)
    activity_feed: list[BotActivity] = field(default_factory=list)
    max_activity: int = 40
    # Accumulated net notional (+buy / -sell) applied into price movement.
    pending_flow: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.bots:
            self.bots = self._spawn_default_bots()

    @staticmethod
    def _spawn_default_bots() -> list[BotTrader]:
        bots: list[BotTrader] = []
        for bot_id, name, persona, aggression, cash in DEFAULT_BOT_SPECS:
            bots.append(
                BotTrader(
                    bot_id=bot_id,
                    name=name,
                    persona=persona,
                    trader=Player(cash=cash, previous_total_value=cash),
                    aggression=aggression,
                )
            )
        return bots

    def act(
        self,
        market,
        day: int | None = None,
    ) -> tuple[dict[str, float], list[BotActivity]]:
        """Bots trade against current prices. Returns (flow_notional, activities)."""
        companies = market.companies
        company_list = market.company_list()
        rng = market.rng
        trade_day = market.day if day is None else day
        activities: list[BotActivity] = []
        flow: dict[str, float] = {cid: 0.0 for cid in companies}

        # Shuffle bot order for fairness; seeded.
        order = list(range(len(self.bots)))
        rng.shuffle(order)

        for idx in order:
            bot = self.bots[idx]
            trades = self._decide_trades(bot, market, company_list, rng)
            for company, side, shares in trades:
                try:
                    if side == "BUY":
                        result = trading.buy(bot.trader, company, shares)
                        flow[company.id] += result.total
                    else:
                        result = trading.sell(bot.trader, company, shares)
                        flow[company.id] -= result.total
                except trading.TradeError:
                    continue
                activities.append(
                    BotActivity(
                        day=trade_day,
                        bot_id=bot.bot_id,
                        bot_name=bot.name,
                        side=side,
                        company_id=company.id,
                        company_name=company.name,
                        shares=result.shares,
                        price=result.price,
                    )
                )

        for bot in self.bots:
            bot.trader.snapshot_value(companies)

        self.pending_flow = flow
        if activities:
            self.activity_feed = (activities + self.activity_feed)[: self.max_activity]
        return flow, activities

    def _decide_trades(
        self,
        bot: BotTrader,
        market,
        company_list: list[Company],
        rng,
    ) -> list[tuple[Company, str, int]]:
        """Return list of (company, side, shares) intentions."""
        if rng.random() > 0.35 + bot.aggression * 0.5:
            return []

        # Most days: 1 trade; aggressive bots sometimes 2.
        n_trades = 1
        if bot.aggression > 0.7 and rng.random() < 0.35:
            n_trades = 2

        trades: list[tuple[Company, str, int]] = []
        for _ in range(n_trades):
            decision = self._pick_one(bot, market, company_list, rng)
            if decision:
                trades.append(decision)
        return trades

    def _pick_one(
        self,
        bot: BotTrader,
        market,
        company_list: list[Company],
        rng,
    ) -> tuple[Company, str, int] | None:
        persona = bot.persona
        state = market.economy.state.value

        scored: list[tuple[float, Company, str]] = []
        for company in company_list:
            gap = (company.fair_value - company.share_price) / max(company.share_price, 0.01)
            change = company.daily_change
            buy_score = 0.0
            sell_score = 0.0

            if persona == BotPersona.VALUE:
                buy_score = gap * 3.0
                sell_score = -gap * 3.0
            elif persona == BotPersona.MOMENTUM:
                buy_score = change * 8.0
                sell_score = -change * 6.0
            elif persona == BotPersona.GROWTH:
                buy_score = company.growth_rate * 4.0 + gap * 1.0 + company.sentiment
                sell_score = -company.growth_rate * 2.0
                if company.sector == "Technology":
                    buy_score += 0.4
            elif persona == BotPersona.PANIC:
                if state in {"RECESSION", "CRISIS", "UNCERTAIN"}:
                    sell_score = 1.2 + abs(change) * 4.0
                    buy_score = -0.5
                elif state == "BOOM":
                    buy_score = 0.8 + change * 3.0
                    sell_score = -0.2
                else:
                    buy_score = gap
                    sell_score = -gap * 0.5
                # Dump holdings that dropped hard.
                if change < -0.03:
                    sell_score += 1.0
            else:  # NOISE
                buy_score = rng.uniform(-0.5, 1.0)
                sell_score = rng.uniform(-0.5, 1.0)

            # Prefer selling what they own when sell looks good.
            owned = bot.trader.portfolio.shares_owned(company.id)
            if owned > 0:
                scored.append((sell_score + 0.15, company, "SELL"))
            if bot.trader.cash > company.share_price:
                scored.append((buy_score, company, "BUY"))

        if not scored:
            return None

        # Softmax-ish: pick among top candidates with noise.
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]
        # Filter weak signals.
        top = [t for t in top if t[0] > 0.05]
        if not top:
            return None
        weights = [max(0.01, t[0]) for t in top]
        pick = rng.choices(top, weights=weights, k=1)[0]
        _, company, side = pick

        if side == "BUY":
            max_shares = trading.max_affordable(bot.trader, company)
            if max_shares <= 0:
                return None
            # Spend a fraction of cash.
            budget_frac = 0.08 + bot.aggression * 0.12
            target_spend = bot.trader.cash * budget_frac
            shares = max(1, min(max_shares, int(target_spend / company.share_price)))
            shares = min(shares, 80)
            return company, "BUY", shares

        owned = bot.trader.portfolio.shares_owned(company.id)
        if owned <= 0:
            return None
        sell_frac = 0.15 + bot.aggression * 0.25
        if persona == BotPersona.PANIC and state in {"CRISIS", "RECESSION"}:
            sell_frac = min(1.0, sell_frac + 0.35)
        shares = max(1, int(owned * sell_frac))
        shares = min(shares, owned)
        return company, "SELL", shares

    def leaderboard(self, player: Player, companies: dict[str, Company]) -> list[dict[str, Any]]:
        rows = [
            {
                "id": "player",
                "name": "You",
                "persona": "player",
                "net_worth": player.total_value(companies),
                "cash": player.cash,
                "is_player": True,
            }
        ]
        for bot in self.bots:
            rows.append(
                {
                    "id": bot.bot_id,
                    "name": bot.name,
                    "persona": bot.persona.value,
                    "net_worth": bot.net_worth(companies),
                    "cash": bot.trader.cash,
                    "is_player": False,
                }
            )
        rows.sort(key=lambda r: r["net_worth"], reverse=True)
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        return rows

    def to_dict(self) -> dict[str, Any]:
        return {
            "bots": [b.to_dict() for b in self.bots],
            "activity_feed": [a.to_dict() for a in self.activity_feed],
            "max_activity": self.max_activity,
            "pending_flow": dict(self.pending_flow),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BotManager:
        return cls(
            bots=[BotTrader.from_dict(b) for b in data.get("bots", [])],
            activity_feed=[BotActivity.from_dict(a) for a in data.get("activity_feed", [])],
            max_activity=data.get("max_activity", 40),
            pending_flow=dict(data.get("pending_flow", {})),
        )


def flow_to_price_effects(
    flow: dict[str, float],
    companies: dict[str, Company],
) -> dict[str, float]:
    """Convert net notional flow into bounded daily price pressure per company."""
    effects: dict[str, float] = {}
    for cid, notional in flow.items():
        company = companies.get(cid)
        if not company:
            continue
        # Fictional daily liquidity ~ a few thousand shares of turnover.
        liquidity = max(5_000.0, company.share_price * 2_500.0)
        pressure = (notional / liquidity) * 0.2
        effects[cid] = max(-0.035, min(0.035, pressure))
    return effects
