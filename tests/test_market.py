"""Market simulation and pricing tests."""

from src.game.economy import MarketState
from src.game.market import Market
from src.game.simulation import Simulation


def test_prices_never_negative():
    market = Market(seed=7)
    for _ in range(200):
        market.step()
    for company in market.company_list():
        assert company.share_price > 0


def test_price_history_recorded():
    market = Market(seed=1)
    market.step()
    market.step()
    for company in market.company_list():
        assert len(company.price_history) >= 3  # day 0 + 2 steps
        assert company.price_history[-1].day == market.day
        assert company.price_history[-1].price == company.share_price


def test_simulation_advances():
    sim = Simulation(seed=99)
    assert sim.day == 0
    sim.advance(5)
    assert sim.day == 5
    assert len(sim.companies) >= 10


def test_companies_do_not_move_identically():
    market = Market(seed=123)
    start = {c.id: c.share_price for c in market.company_list()}
    market.step_days(60)
    changes = []
    for company in market.company_list():
        changes.append((company.share_price - start[company.id]) / start[company.id])
    # Not all identical.
    assert len(set(round(c, 4) for c in changes)) > 1
    # Spread should be meaningful.
    assert max(changes) - min(changes) > 0.05


def test_market_state_affects_prices():
    boom = Market(seed=50)
    crisis = Market(seed=50)
    boom.force_market_state(MarketState.BOOM)
    crisis.force_market_state(MarketState.CRISIS)
    # Keep states locked by resetting days frequently via force.
    for _ in range(30):
        boom.force_market_state(MarketState.BOOM)
        crisis.force_market_state(MarketState.CRISIS)
        boom.step()
        crisis.step()
    boom_avg = sum(c.share_price for c in boom.company_list()) / len(boom.companies)
    crisis_avg = sum(c.share_price for c in crisis.company_list()) / len(crisis.companies)
    assert boom_avg > crisis_avg


def test_movement_components_recorded():
    market = Market(seed=3)
    market.step()
    for company in market.company_list():
        m = company.last_movement
        # Components exist and sum to total.
        assert abs(m.total - (
            m.fundamental_effect
            + m.sector_effect
            + m.event_effect
            + m.sentiment_effect
            + m.market_effect
            + m.noise_effect
        )) < 1e-12


def test_approximately_ten_companies():
    market = Market(seed=1)
    assert 8 <= len(market.companies) <= 12
