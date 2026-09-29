"""Event and news system for the market simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EventScope(Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MARKET = "market"


class RumourTruth(Enum):
    TRUE = "true"
    PARTIAL = "partial"
    FALSE = "false"


@dataclass
class NewsItem:
    """A player-visible news headline."""

    day: int
    title: str
    description: str
    is_rumour: bool = False
    company_ids: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "title": self.title,
            "description": self.description,
            "is_rumour": self.is_rumour,
            "company_ids": list(self.company_ids),
            "sectors": list(self.sectors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewsItem:
        return cls(
            day=data["day"],
            title=data["title"],
            description=data["description"],
            is_rumour=data.get("is_rumour", False),
            company_ids=list(data.get("company_ids", [])),
            sectors=list(data.get("sectors", [])),
        )


@dataclass
class MarketEvent:
    """Structured market event with hidden numerical effects."""

    title: str
    description: str
    scope: EventScope
    affected_sectors: list[str] = field(default_factory=list)
    affected_companies: list[str] = field(default_factory=list)
    sentiment_effect: float = 0.0
    price_effect: float = 0.0
    growth_effect: float = 0.0
    volatility_effect: float = 0.0
    market_sentiment_effect: float = 0.0
    duration: int = 1
    days_remaining: int | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    is_rumour: bool = False
    rumour_truth: RumourTruth | None = None

    def __post_init__(self) -> None:
        if isinstance(self.scope, str):
            self.scope = EventScope(self.scope)
        if isinstance(self.rumour_truth, str):
            self.rumour_truth = RumourTruth(self.rumour_truth)
        if self.days_remaining is None:
            self.days_remaining = self.duration

    def tick(self) -> bool:
        """Advance one day. Returns True if still active."""
        assert self.days_remaining is not None
        self.days_remaining -= 1
        return self.days_remaining > 0

    def daily_price_effect(self) -> float:
        """Spread price impact across remaining days, front-loaded slightly."""
        if self.duration <= 0 or self.days_remaining is None:
            return 0.0
        # Front-load: first day gets more of the impact.
        if self.days_remaining == self.duration:
            return self.price_effect * 0.5
        remaining_days = max(1, self.days_remaining)
        remaining_effect = self.price_effect * 0.5
        return remaining_effect / remaining_days

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "scope": self.scope.value,
            "affected_sectors": list(self.affected_sectors),
            "affected_companies": list(self.affected_companies),
            "sentiment_effect": self.sentiment_effect,
            "price_effect": self.price_effect,
            "growth_effect": self.growth_effect,
            "volatility_effect": self.volatility_effect,
            "market_sentiment_effect": self.market_sentiment_effect,
            "duration": self.duration,
            "days_remaining": self.days_remaining,
            "is_rumour": self.is_rumour,
            "rumour_truth": self.rumour_truth.value if self.rumour_truth else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MarketEvent:
        truth = data.get("rumour_truth")
        return cls(
            event_id=data.get("event_id", str(uuid4())),
            title=data["title"],
            description=data["description"],
            scope=EventScope(data["scope"]),
            affected_sectors=list(data.get("affected_sectors", [])),
            affected_companies=list(data.get("affected_companies", [])),
            sentiment_effect=data.get("sentiment_effect", 0.0),
            price_effect=data.get("price_effect", 0.0),
            growth_effect=data.get("growth_effect", 0.0),
            volatility_effect=data.get("volatility_effect", 0.0),
            market_sentiment_effect=data.get("market_sentiment_effect", 0.0),
            duration=data.get("duration", 1),
            days_remaining=data.get("days_remaining", data.get("duration", 1)),
            is_rumour=data.get("is_rumour", False),
            rumour_truth=RumourTruth(truth) if truth else None,
        )

    def to_news(self, day: int) -> NewsItem:
        return NewsItem(
            day=day,
            title=self.title,
            description=self.description,
            is_rumour=self.is_rumour,
            company_ids=list(self.affected_companies),
            sectors=list(self.affected_sectors),
        )


@dataclass
class EventSystem:
    """Manages active events and news history."""

    active_events: list[MarketEvent] = field(default_factory=list)
    news_feed: list[NewsItem] = field(default_factory=list)
    max_news: int = 50

    def add_event(self, event: MarketEvent, day: int) -> NewsItem:
        self.active_events.append(event)
        news = event.to_news(day)
        self.news_feed.insert(0, news)
        if len(self.news_feed) > self.max_news:
            self.news_feed = self.news_feed[: self.max_news]
        return news

    def tick(self) -> list[MarketEvent]:
        """Age events; return those that expired."""
        expired: list[MarketEvent] = []
        still_active: list[MarketEvent] = []
        for event in self.active_events:
            if event.tick():
                still_active.append(event)
            else:
                expired.append(event)
        self.active_events = still_active
        return expired

    def company_event_effect(self, company_id: str, sector: str) -> float:
        """Sum daily price effects relevant to a company."""
        total = 0.0
        for event in self.active_events:
            if event.is_rumour and event.rumour_truth == RumourTruth.FALSE:
                # False rumours may still move price via sentiment, but weakly.
                weight = 0.15
            elif event.is_rumour and event.rumour_truth == RumourTruth.PARTIAL:
                weight = 0.5
            else:
                weight = 1.0

            applies = False
            if event.scope == EventScope.MARKET:
                applies = True
            elif event.scope == EventScope.SECTOR and sector in event.affected_sectors:
                applies = True
            elif event.scope == EventScope.COMPANY and company_id in event.affected_companies:
                applies = True
            elif sector in event.affected_sectors:
                applies = True
            elif company_id in event.affected_companies:
                applies = True

            if applies:
                total += event.daily_price_effect() * weight
        return total

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_events": [e.to_dict() for e in self.active_events],
            "news_feed": [n.to_dict() for n in self.news_feed],
            "max_news": self.max_news,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventSystem:
        return cls(
            active_events=[MarketEvent.from_dict(e) for e in data.get("active_events", [])],
            news_feed=[NewsItem.from_dict(n) for n in data.get("news_feed", [])],
            max_news=data.get("max_news", 50),
        )
