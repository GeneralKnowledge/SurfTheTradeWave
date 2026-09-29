"""Event system tests."""

from src.game.economy import MarketState
from src.game.events import EventScope, EventSystem, MarketEvent
from src.game.market import Market


def test_events_affect_targets():
    market = Market(seed=10)
    northstar = market.get_company("northstar")
    before = northstar.share_price
    event = MarketEvent(
        title="Northstar product launch",
        description="Major product announced.",
        scope=EventScope.COMPANY,
        affected_companies=["northstar"],
        sentiment_effect=0.5,
        price_effect=0.2,
        duration=3,
    )
    market.force_event(event)
    market.step()
    after = market.get_company("northstar").share_price
    # Strong positive event should lift price on average for this forced case.
    assert after > before
    assert market.get_company("northstar").sentiment > 0


def test_events_expire():
    system = EventSystem()
    event = MarketEvent(
        title="Short blip",
        description="Brief.",
        scope=EventScope.MARKET,
        price_effect=0.01,
        duration=2,
    )
    system.add_event(event, day=1)
    assert len(system.active_events) == 1
    expired = system.tick()
    assert expired == []
    assert len(system.active_events) == 1
    expired = system.tick()
    assert len(expired) == 1
    assert len(system.active_events) == 0


def test_sector_event_affects_sector_companies():
    market = Market(seed=22)
    tech_ids = [c.id for c in market.company_list() if c.sector == "Technology"]

    event = MarketEvent(
        title="Technology boom",
        description="Tech soars.",
        scope=EventScope.SECTOR,
        affected_sectors=["Technology"],
        sentiment_effect=0.4,
        price_effect=0.15,
        duration=4,
    )
    market.force_event(event)

    # Direct effect targeting: tech gets impact, staples does not.
    for cid in tech_ids:
        company = market.get_company(cid)
        assert market.events.company_event_effect(cid, company.sector) > 0
    assert market.events.company_event_effect("albion", "Consumer Staples") == 0.0

    # Immediate sentiment shock applied to tech names.
    for cid in tech_ids:
        assert market.get_company(cid).sentiment > 0



def test_news_generated_without_numbers():
    market = Market(seed=5)
    event = MarketEvent(
        title="Copper prices rise sharply",
        description="Supply concerns.",
        scope=EventScope.SECTOR,
        affected_sectors=["Mining"],
        price_effect=0.05,
        duration=2,
    )
    news = market.events.add_event(event, day=1)
    assert "%" not in news.description
    assert "0.05" not in news.description
    assert news.title == "Copper prices rise sharply"


def test_market_wide_crisis_news_path():
    market = Market(seed=8)
    market.force_market_state(MarketState.CRISIS)
    market.step()
    assert market.economy.state == MarketState.CRISIS
