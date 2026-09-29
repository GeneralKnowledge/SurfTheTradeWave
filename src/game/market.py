"""Market simulation engine: fundamentals, pricing, sectors, events."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from src.data.companies import create_companies
from src.data.events import generate_daily_events
from src.game.company import Company, PriceMovement
from src.game.economy import Economy, MarketState
from src.game.events import EventSystem, MarketEvent, NewsItem
from src.game.sector import DEFAULT_SECTORS, Sector


def compute_fair_value(company: Company, sector: Sector, economy: Economy) -> float:
    """Gameplay fair-value estimate anchored to each company's fundamental base.

    Multipliers are centred near 1.0 so listing prices stay in a playable range.
    """
    effects = economy.effects()

    growth_score = 1.0 + (company.growth_rate - 0.04) * 1.8
    profit_score = 1.0 + (company.profitability - 0.10) * 1.5
    debt_ratio = company.debt / max(1.0, company.revenue)
    debt_score = max(0.55, 1.0 - (debt_ratio - 0.4) * 0.35)
    confidence = (
        1.0
        + company.sentiment * 0.12
        + (company.reputation - 0.5) * 0.15
        + sector.sentiment * 0.08
    )
    sector_score = 1.0 + (sector.growth - 0.03) * 1.2
    score = growth_score * profit_score * debt_score * confidence * sector_score
    score *= effects["valuation_mult"]
    score = max(0.35, min(2.2, score))

    return max(0.5, company.fundamental_base * score)


@dataclass
class Market:
    """Headless market simulation. Call step() to advance one day."""

    seed: int = 42
    day: int = 0
    companies: dict[str, Company] = field(default_factory=dict)
    sectors: dict[str, Sector] = field(default_factory=dict)
    economy: Economy = field(default_factory=Economy)
    events: EventSystem = field(default_factory=EventSystem)
    paused: bool = False
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if not self.sectors:
            self.sectors = {s.name: Sector(**s.to_dict()) for s in DEFAULT_SECTORS}
        if not self.companies:
            for company in create_companies():
                sector = self.sectors[company.sector]
                company.fair_value = compute_fair_value(company, sector, self.economy)
                self.companies[company.id] = company

    @property
    def rng(self) -> random.Random:
        return self._rng

    def get_company(self, company_id: str) -> Company:
        return self.companies[company_id]

    def company_list(self) -> list[Company]:
        return list(self.companies.values())

    def step(self) -> dict[str, Any]:
        """Advance the market by one simulated day."""
        self.day += 1
        summary: dict[str, Any] = {
            "day": self.day,
            "new_events": [],
            "expired_events": [],
            "state_change": None,
            "movements": {},
        }

        # 1. Evolve fundamentals slightly.
        self._evolve_fundamentals()

        # 2. Evolve sector conditions.
        self._evolve_sectors()

        # 3. Spawn events/news.
        new_events = generate_daily_events(self._rng, self.company_list(), self.day)
        for event in new_events:
            news = self.events.add_event(event, self.day)
            summary["new_events"].append(news)
            self._apply_event_immediate(event)

        # 4. Investor / market sentiment drift.
        self._evolve_sentiment()

        # 5. Maybe transition market state.
        old_state = self.economy.maybe_transition(self._rng)
        if old_state is not None:
            summary["state_change"] = {
                "from": old_state.value,
                "to": self.economy.state.value,
            }
            self.events.news_feed.insert(
                0,
                NewsItem(
                    day=self.day,
                    title=f"Market mood shifts to {self.economy.state.value}",
                    description=(
                        f"Conditions move from {old_state.value} to "
                        f"{self.economy.state.value}."
                    ),
                ),
            )

        # 6. Price movement for each company.
        for company in self.companies.values():
            movement = self._compute_price_movement(company)
            new_price = company.share_price * (1.0 + movement.total)
            company.apply_price(new_price, movement)
            company.record_price(self.day)
            # Mean-revert fair value update after price settles.
            sector = self.sectors[company.sector]
            company.fair_value = compute_fair_value(company, sector, self.economy)
            summary["movements"][company.id] = movement.to_dict()

        # 7. Age events.
        expired = self.events.tick()
        summary["expired_events"] = [e.title for e in expired]

        return summary

    def step_days(self, n: int) -> list[dict[str, Any]]:
        return [self.step() for _ in range(n)]

    def _evolve_fundamentals(self) -> None:
        effects = self.economy.effects()
        for company in self.companies.values():
            sector = self.sectors[company.sector]
            daily_growth = (
                company.growth_rate + sector.growth + effects["sector_growth_boost"]
            ) / 365.0
            noise = self._rng.gauss(0, 0.0015 * company.volatility)
            company.revenue = max(1.0, company.revenue * (1.0 + daily_growth + noise))
            # Fundamental base drifts with business performance (slow).
            company.fundamental_base = max(
                0.5,
                company.fundamental_base * (1.0 + daily_growth * 0.6 + noise * 0.3),
            )
            # Profitability slowly drifts toward sector-linked target.
            target_prof = 0.08 + sector.growth * 0.5
            company.profitability += (target_prof - company.profitability) * 0.01
            company.profitability = max(0.005, min(0.35, company.profitability))
            company.profit = company.revenue * company.profitability
            # Debt slowly changes with growth stress.
            debt_change = self._rng.gauss(0, 0.001)
            company.debt = max(0.0, company.debt * (1.0 + debt_change))
            # Growth rate mean-reverts gently.
            company.growth_rate += (sector.growth - company.growth_rate) * 0.02
            company.growth_rate += self._rng.gauss(0, 0.001 * company.volatility)
            company.growth_rate = max(-0.05, min(0.4, company.growth_rate))

    def _evolve_sectors(self) -> None:
        effects = self.economy.effects()
        for sector in self.sectors.values():
            sector.sentiment += self._rng.gauss(effects["sentiment_drift"], 0.02)
            sector.sentiment = max(-1.0, min(1.0, sector.sentiment))
            sector.growth += self._rng.gauss(effects["sector_growth_boost"] * 0.1, 0.001)
            sector.growth = max(-0.05, min(0.2, sector.growth))
            # Volatility soft mean-reversion.
            sector.volatility += self._rng.gauss(0, 0.005)
            sector.volatility = max(0.1, min(1.0, sector.volatility))

    def _evolve_sentiment(self) -> None:
        effects = self.economy.effects()
        self.economy.overall_sentiment += self._rng.gauss(effects["sentiment_drift"], 0.015)
        self.economy.overall_sentiment = max(-1.0, min(1.0, self.economy.overall_sentiment))
        for company in self.companies.values():
            sector = self.sectors[company.sector]
            drift = (
                effects["sentiment_drift"]
                + sector.sentiment * 0.05
                + self.economy.overall_sentiment * 0.03
            )
            company.sentiment += self._rng.gauss(drift, 0.03 * company.volatility)
            company.sentiment = max(-1.0, min(1.0, company.sentiment))
            # Reputation slowly follows sentiment and profitability.
            company.reputation += (
                (0.5 + company.profitability + company.sentiment * 0.2) / 2.0 - company.reputation
            ) * 0.01
            company.reputation = max(0.1, min(1.0, company.reputation))

    def _apply_event_immediate(self, event: MarketEvent) -> None:
        """Apply one-shot sentiment / growth shocks when an event appears."""
        self.economy.overall_sentiment = max(
            -1.0,
            min(1.0, self.economy.overall_sentiment + event.market_sentiment_effect),
        )
        for sector_name in event.affected_sectors:
            sector = self.sectors.get(sector_name)
            if sector:
                sector.sentiment = max(
                    -1.0, min(1.0, sector.sentiment + event.sentiment_effect * 0.5)
                )
                sector.growth += event.growth_effect * 0.5
                sector.volatility = min(1.0, sector.volatility + event.volatility_effect)

        targets = event.affected_companies
        if not targets and event.affected_sectors:
            targets = [
                c.id for c in self.companies.values() if c.sector in event.affected_sectors
            ]
        if event.scope.value == "market" and not targets:
            targets = list(self.companies.keys())

        for cid in targets:
            company = self.companies.get(cid)
            if not company:
                continue
            company.sentiment = max(
                -1.0, min(1.0, company.sentiment + event.sentiment_effect)
            )
            company.growth_rate += event.growth_effect
            company.volatility = min(1.2, company.volatility + event.volatility_effect * 0.5)

    def _compute_price_movement(self, company: Company) -> PriceMovement:
        sector = self.sectors[company.sector]
        effects = self.economy.effects()
        vol_mult = effects["volatility_mult"]

        # Fundamental pressure toward fair value (gradual).
        gap = (company.fair_value - company.share_price) / max(company.share_price, 0.01)
        fundamental = max(-0.04, min(0.04, gap * 0.05))

        # Sector pressure.
        sector_effect = (
            sector.sentiment * 0.008 + sector.growth * 0.03
        ) * company.sector_sensitivity
        sector_effect = max(-0.03, min(0.03, sector_effect))

        # Event/news impact.
        event_effect = self.events.company_event_effect(company.id, company.sector)
        event_effect = max(-0.08, min(0.08, event_effect))

        # Company sentiment.
        sentiment_effect = company.sentiment * 0.01 * (0.5 + company.volatility)
        sentiment_effect = max(-0.04, min(0.04, sentiment_effect))

        # Market-wide.
        market_effect = effects["price_pressure"] + self.economy.overall_sentiment * 0.006
        market_effect = max(-0.05, min(0.03, market_effect))

        # Random noise scaled by volatility (not a pure random walk driver).
        noise_sigma = 0.006 * company.volatility * sector.volatility * vol_mult
        # Commodity-exposed names get a bit more idiosyncratic noise.
        noise_sigma *= 1.0 + company.commodity_exposure * 0.3
        noise_effect = self._rng.gauss(0, noise_sigma)
        noise_effect = max(-0.04, min(0.04, noise_effect))

        movement = PriceMovement(
            fundamental_effect=fundamental,
            sector_effect=sector_effect,
            event_effect=event_effect,
            sentiment_effect=sentiment_effect,
            market_effect=market_effect,
            noise_effect=noise_effect,
        )
        # Hard daily clamp to keep the prototype numerically stable.
        total = max(-0.12, min(0.12, movement.total))
        if abs(total - movement.total) > 1e-12 and abs(movement.total) > 1e-12:
            scale = total / movement.total
            movement = PriceMovement(
                fundamental_effect=movement.fundamental_effect * scale,
                sector_effect=movement.sector_effect * scale,
                event_effect=movement.event_effect * scale,
                sentiment_effect=movement.sentiment_effect * scale,
                market_effect=movement.market_effect * scale,
                noise_effect=movement.noise_effect * scale,
            )
        return movement

    def force_market_state(self, state: MarketState) -> None:
        self.economy.state = state
        self.economy.days_in_state = 0

    def force_event(self, event: MarketEvent) -> None:
        self.events.add_event(event, self.day)
        self._apply_event_immediate(event)

    def set_company_sentiment(self, company_id: str, sentiment: float) -> None:
        company = self.companies[company_id]
        company.sentiment = max(-1.0, min(1.0, sentiment))

    def debug_snapshot(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "day": self.day,
            "market_state": self.economy.state.value,
            "overall_sentiment": self.economy.overall_sentiment,
            "sectors": {name: s.to_dict() for name, s in self.sectors.items()},
            "companies": {
                cid: {
                    **c.public_info(),
                    "fair_value": c.fair_value,
                    "volatility": c.volatility,
                    "last_movement": c.last_movement.to_dict(),
                }
                for cid, c in self.companies.items()
            },
            "active_events": [e.to_dict() for e in self.events.active_events],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "day": self.day,
            "paused": self.paused,
            "economy": self.economy.to_dict(),
            "sectors": {name: s.to_dict() for name, s in self.sectors.items()},
            "companies": {cid: c.to_dict() for cid, c in self.companies.items()},
            "events": self.events.to_dict(),
            "rng_state": self._rng.getstate()[1],  # MT state tuple as list later
            "rng_version": self._rng.getstate()[0],
            "rng_gauss": self._rng.getstate()[2],
        }

    def serialize_rng(self) -> dict[str, Any]:
        version, state, gauss = self._rng.getstate()
        return {
            "version": version,
            "state": list(state),
            "gauss": gauss,
        }

    def restore_rng(self, data: dict[str, Any]) -> None:
        self._rng.setstate(
            (data["version"], tuple(data["state"]), data["gauss"])
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Market:
        market = cls(seed=data["seed"])
        market.day = data["day"]
        market.paused = data.get("paused", False)
        market.economy = Economy.from_dict(data["economy"])
        market.sectors = {
            name: Sector.from_dict(sdata) for name, sdata in data["sectors"].items()
        }
        market.companies = {
            cid: Company.from_dict(cdata) for cid, cdata in data["companies"].items()
        }
        market.events = EventSystem.from_dict(data["events"])
        if "rng" in data:
            market.restore_rng(data["rng"])
        return market
