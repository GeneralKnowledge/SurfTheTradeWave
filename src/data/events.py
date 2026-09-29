"""Event and rumour templates for procedural generation."""

from __future__ import annotations

from dataclasses import dataclass

from src.game.events import EventScope, MarketEvent, RumourTruth


@dataclass
class EventTemplate:
    title: str
    description: str
    scope: EventScope
    affected_sectors: list[str] | None = None
    sentiment_effect: float = 0.0
    price_effect: float = 0.0
    growth_effect: float = 0.0
    volatility_effect: float = 0.0
    market_sentiment_effect: float = 0.0
    duration: int = 3
    weight: float = 1.0
    needs_company: bool = False


SECTOR_EVENTS: list[EventTemplate] = [
    EventTemplate(
        title="Copper prices rise sharply",
        description="Global copper prices increase following supply concerns.",
        scope=EventScope.SECTOR,
        affected_sectors=["Mining", "Manufacturing"],
        sentiment_effect=0.15,
        price_effect=0.04,
        duration=5,
    ),
    EventTemplate(
        title="Commodity surplus weighs on miners",
        description="Inventories build as demand softens across industrial metals.",
        scope=EventScope.SECTOR,
        affected_sectors=["Mining"],
        sentiment_effect=-0.12,
        price_effect=-0.035,
        duration=5,
    ),
    EventTemplate(
        title="Technology sector boom",
        description="Investors pile into growth names amid optimism about new products.",
        scope=EventScope.SECTOR,
        affected_sectors=["Technology"],
        sentiment_effect=0.2,
        price_effect=0.05,
        growth_effect=0.01,
        duration=6,
        weight=0.8,
    ),
    EventTemplate(
        title="Tech sell-off gathers pace",
        description="High-valuation technology stocks face renewed scrutiny.",
        scope=EventScope.SECTOR,
        affected_sectors=["Technology"],
        sentiment_effect=-0.18,
        price_effect=-0.045,
        duration=4,
    ),
    EventTemplate(
        title="Energy policy shift announced",
        description="Government outlines new regulations affecting energy producers.",
        scope=EventScope.SECTOR,
        affected_sectors=["Energy"],
        sentiment_effect=-0.1,
        price_effect=-0.03,
        volatility_effect=0.1,
        duration=7,
    ),
    EventTemplate(
        title="Consumer spending surge",
        description="Retail footfall and household spending beat expectations.",
        scope=EventScope.SECTOR,
        affected_sectors=["Retail", "Consumer Staples"],
        sentiment_effect=0.12,
        price_effect=0.03,
        duration=5,
    ),
    EventTemplate(
        title="Consumer slowdown reported",
        description="Shoppers tighten budgets; discretionary sales soften.",
        scope=EventScope.SECTOR,
        affected_sectors=["Retail"],
        sentiment_effect=-0.15,
        price_effect=-0.04,
        duration=5,
    ),
    EventTemplate(
        title="Banking sector under pressure",
        description="Concerns about loan quality weigh on financial stocks.",
        scope=EventScope.SECTOR,
        affected_sectors=["Banking"],
        sentiment_effect=-0.2,
        price_effect=-0.05,
        duration=6,
        weight=0.6,
    ),
    EventTemplate(
        title="Healthcare breakthrough excitement",
        description="Scientific advances lift interest across healthcare names.",
        scope=EventScope.SECTOR,
        affected_sectors=["Healthcare"],
        sentiment_effect=0.18,
        price_effect=0.04,
        duration=5,
    ),
    EventTemplate(
        title="Supply-chain disruption",
        description="Logistics bottlenecks slow manufacturing and transport.",
        scope=EventScope.SECTOR,
        affected_sectors=["Manufacturing", "Transport"],
        sentiment_effect=-0.1,
        price_effect=-0.03,
        duration=6,
    ),
    EventTemplate(
        title="Freight demand rebounds",
        description="Shipping volumes rise, supporting transport operators.",
        scope=EventScope.SECTOR,
        affected_sectors=["Transport"],
        sentiment_effect=0.12,
        price_effect=0.035,
        duration=4,
    ),
]

COMPANY_EVENTS: list[EventTemplate] = [
    EventTemplate(
        title="{company} announces major new product",
        description="Investors appear optimistic about the launch pipeline.",
        scope=EventScope.COMPANY,
        sentiment_effect=0.25,
        price_effect=0.06,
        growth_effect=0.02,
        duration=4,
        needs_company=True,
    ),
    EventTemplate(
        title="{company} product setback",
        description="A key product faces delays and customer complaints.",
        scope=EventScope.COMPANY,
        sentiment_effect=-0.22,
        price_effect=-0.055,
        duration=4,
        needs_company=True,
    ),
    EventTemplate(
        title="{company} CEO resigns",
        description="Leadership uncertainty unsettles shareholders.",
        scope=EventScope.COMPANY,
        sentiment_effect=-0.15,
        price_effect=-0.04,
        volatility_effect=0.15,
        duration=5,
        needs_company=True,
        weight=0.7,
    ),
    EventTemplate(
        title="{company} wins major contract",
        description="A multi-year deal is expected to boost future revenue.",
        scope=EventScope.COMPANY,
        sentiment_effect=0.2,
        price_effect=0.05,
        growth_effect=0.015,
        duration=5,
        needs_company=True,
    ),
    EventTemplate(
        title="{company} reports strong earnings",
        description="Profits and guidance exceed quiet expectations.",
        scope=EventScope.COMPANY,
        sentiment_effect=0.18,
        price_effect=0.045,
        duration=3,
        needs_company=True,
    ),
    EventTemplate(
        title="{company} issues profit warning",
        description="Management cuts outlook citing softer demand.",
        scope=EventScope.COMPANY,
        sentiment_effect=-0.25,
        price_effect=-0.07,
        duration=4,
        needs_company=True,
    ),
    EventTemplate(
        title="Factory accident at {company}",
        description="Operations disrupted; investigation underway.",
        scope=EventScope.COMPANY,
        sentiment_effect=-0.12,
        price_effect=-0.035,
        duration=4,
        needs_company=True,
        weight=0.5,
    ),
    EventTemplate(
        title="Cyberattack hits {company}",
        description="Systems outage raises concerns about data and reputation.",
        scope=EventScope.COMPANY,
        sentiment_effect=-0.18,
        price_effect=-0.04,
        volatility_effect=0.1,
        duration=3,
        needs_company=True,
        weight=0.5,
    ),
]

MARKET_EVENTS: list[EventTemplate] = [
    EventTemplate(
        title="Interest rates cut",
        description="Borrowing costs fall, lifting risk appetite across markets.",
        scope=EventScope.MARKET,
        market_sentiment_effect=0.15,
        price_effect=0.025,
        duration=5,
        weight=0.6,
    ),
    EventTemplate(
        title="Interest rates raised",
        description="Higher rates cool valuations and investor enthusiasm.",
        scope=EventScope.MARKET,
        market_sentiment_effect=-0.15,
        price_effect=-0.03,
        duration=5,
        weight=0.6,
    ),
    EventTemplate(
        title="Banking crisis fears",
        description="Stress in the financial system rattles the whole market.",
        scope=EventScope.MARKET,
        affected_sectors=["Banking"],
        market_sentiment_effect=-0.3,
        price_effect=-0.06,
        volatility_effect=0.2,
        duration=7,
        weight=0.3,
    ),
    EventTemplate(
        title="Broad market optimism",
        description="Investors turn constructive amid improving economic data.",
        scope=EventScope.MARKET,
        market_sentiment_effect=0.12,
        price_effect=0.02,
        duration=4,
    ),
]

RUMOUR_TEMPLATES: list[EventTemplate] = [
    EventTemplate(
        title="Rumour: {company} may be preparing an acquisition",
        description="Unconfirmed reports suggest talks with a smaller competitor.",
        scope=EventScope.COMPANY,
        sentiment_effect=0.08,
        price_effect=0.02,
        duration=3,
        needs_company=True,
        weight=0.8,
    ),
    EventTemplate(
        title="Rumour: {company} faces regulatory probe",
        description="Whispers of an investigation circulate among traders.",
        scope=EventScope.COMPANY,
        sentiment_effect=-0.1,
        price_effect=-0.025,
        duration=3,
        needs_company=True,
        weight=0.7,
    ),
    EventTemplate(
        title="Rumour: breakthrough at {company}",
        description="Sources claim a major technical breakthrough is imminent.",
        scope=EventScope.COMPANY,
        sentiment_effect=0.12,
        price_effect=0.03,
        duration=3,
        needs_company=True,
        weight=0.6,
    ),
]


def _weighted_choice(rng, templates: list[EventTemplate]) -> EventTemplate:
    weights = [t.weight for t in templates]
    total = sum(weights)
    roll = rng.random() * total
    cumulative = 0.0
    for template, weight in zip(templates, weights):
        cumulative += weight
        if roll <= cumulative:
            return template
    return templates[-1]


def instantiate_event(
    template: EventTemplate,
    rng,
    companies: list | None = None,
) -> MarketEvent:
    company_ids: list[str] = []
    title = template.title
    description = template.description

    if template.needs_company and companies:
        company = rng.choice(companies)
        title = template.title.format(company=company.name)
        description = template.description.format(company=company.name)
        company_ids = [company.id]

    return MarketEvent(
        title=title,
        description=description,
        scope=template.scope,
        affected_sectors=list(template.affected_sectors or []),
        affected_companies=company_ids,
        sentiment_effect=template.sentiment_effect,
        price_effect=template.price_effect,
        growth_effect=template.growth_effect,
        volatility_effect=template.volatility_effect,
        market_sentiment_effect=template.market_sentiment_effect,
        duration=template.duration,
        days_remaining=template.duration,
    )


def instantiate_rumour(
    template: EventTemplate,
    rng,
    companies: list,
) -> MarketEvent:
    event = instantiate_event(template, rng, companies)
    event.is_rumour = True
    truth_roll = rng.random()
    if truth_roll < 0.35:
        event.rumour_truth = RumourTruth.TRUE
    elif truth_roll < 0.65:
        event.rumour_truth = RumourTruth.PARTIAL
        event.price_effect *= 0.5
        event.sentiment_effect *= 0.6
    else:
        event.rumour_truth = RumourTruth.FALSE
        # False rumours: small sentiment-only wiggle, little lasting price force.
        event.price_effect *= 0.1
    return event


def generate_daily_events(rng, companies: list, day: int) -> list[MarketEvent]:
    """Maybe spawn 0–2 events for the day."""
    del day  # reserved for future day-aware scheduling
    events: list[MarketEvent] = []

    # Base chance of at least one event.
    if rng.random() < 0.35:
        bucket_roll = rng.random()
        if bucket_roll < 0.45:
            events.append(instantiate_event(_weighted_choice(rng, COMPANY_EVENTS), rng, companies))
        elif bucket_roll < 0.80:
            events.append(instantiate_event(_weighted_choice(rng, SECTOR_EVENTS), rng, companies))
        else:
            events.append(instantiate_event(_weighted_choice(rng, MARKET_EVENTS), rng, companies))

    # Occasional second event.
    if rng.random() < 0.12:
        events.append(instantiate_event(_weighted_choice(rng, SECTOR_EVENTS), rng, companies))

    # Occasional rumour.
    if rng.random() < 0.15:
        events.append(instantiate_rumour(_weighted_choice(rng, RUMOUR_TEMPLATES), rng, companies))

    return events
