"""Market-wide economic state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MarketState(Enum):
    BOOM = "BOOM"
    NORMAL = "NORMAL"
    UNCERTAIN = "UNCERTAIN"
    RECESSION = "RECESSION"
    CRISIS = "CRISIS"


# Effects applied as multipliers / additives during pricing.
STATE_EFFECTS: dict[MarketState, dict[str, float]] = {
    MarketState.BOOM: {
        "price_pressure": 0.002,
        "volatility_mult": 0.9,
        "sentiment_drift": 0.015,
        "valuation_mult": 1.08,
        "sector_growth_boost": 0.008,
    },
    MarketState.NORMAL: {
        "price_pressure": 0.0,
        "volatility_mult": 1.0,
        "sentiment_drift": 0.0,
        "valuation_mult": 1.0,
        "sector_growth_boost": 0.0,
    },
    MarketState.UNCERTAIN: {
        "price_pressure": -0.001,
        "volatility_mult": 1.3,
        "sentiment_drift": -0.01,
        "valuation_mult": 0.95,
        "sector_growth_boost": -0.005,
    },
    MarketState.RECESSION: {
        "price_pressure": -0.004,
        "volatility_mult": 1.4,
        "sentiment_drift": -0.025,
        "valuation_mult": 0.85,
        "sector_growth_boost": -0.012,
    },
    MarketState.CRISIS: {
        "price_pressure": -0.01,
        "volatility_mult": 1.8,
        "sentiment_drift": -0.05,
        "valuation_mult": 0.7,
        "sector_growth_boost": -0.025,
    },
}


# Transition probabilities keyed by current state.
TRANSITION_PROBS: dict[MarketState, dict[MarketState, float]] = {
    MarketState.BOOM: {
        MarketState.BOOM: 0.70,
        MarketState.NORMAL: 0.25,
        MarketState.UNCERTAIN: 0.05,
    },
    MarketState.NORMAL: {
        MarketState.NORMAL: 0.75,
        MarketState.BOOM: 0.10,
        MarketState.UNCERTAIN: 0.12,
        MarketState.RECESSION: 0.03,
    },
    MarketState.UNCERTAIN: {
        MarketState.UNCERTAIN: 0.45,
        MarketState.NORMAL: 0.30,
        MarketState.RECESSION: 0.15,
        MarketState.BOOM: 0.05,
        MarketState.CRISIS: 0.05,
    },
    MarketState.RECESSION: {
        MarketState.RECESSION: 0.55,
        MarketState.UNCERTAIN: 0.25,
        MarketState.NORMAL: 0.12,
        MarketState.CRISIS: 0.08,
    },
    MarketState.CRISIS: {
        MarketState.CRISIS: 0.40,
        MarketState.RECESSION: 0.40,
        MarketState.UNCERTAIN: 0.20,
    },
}


@dataclass
class Economy:
    """Tracks overall market conditions."""

    state: MarketState = MarketState.NORMAL
    days_in_state: int = 0
    overall_sentiment: float = 0.0

    def effects(self) -> dict[str, float]:
        return STATE_EFFECTS[self.state]

    def maybe_transition(self, rng) -> MarketState | None:
        """Possibly transition market state. Returns new state if changed."""
        self.days_in_state += 1
        # Prefer staying put for at least a few days.
        if self.days_in_state < 3:
            return None

        probs = TRANSITION_PROBS[self.state]
        roll = rng.random()
        cumulative = 0.0
        for next_state, prob in probs.items():
            cumulative += prob
            if roll <= cumulative:
                if next_state != self.state:
                    old = self.state
                    self.state = next_state
                    self.days_in_state = 0
                    return old
                return None
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "days_in_state": self.days_in_state,
            "overall_sentiment": self.overall_sentiment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Economy:
        return cls(
            state=MarketState(data.get("state", "NORMAL")),
            days_in_state=data.get("days_in_state", 0),
            overall_sentiment=data.get("overall_sentiment", 0.0),
        )
