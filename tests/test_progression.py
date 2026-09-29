"""Progression, unlocks, upgrades, offline idle tests."""

import pytest

from src.game.progression import Progression, COMPANY_UNLOCK_LEVEL
from src.game.simulation import LockedCompanyError, Simulation
from src.game.save import load_game, save_game


def test_starting_unlocks():
    prog = Progression()
    unlocked = set(prog.unlocked_company_ids())
    assert "ironvale" in unlocked
    assert "albion" in unlocked
    assert "pixelworks" not in unlocked
    assert "northstar" not in unlocked


def test_level_up_unlocks_companies():
    sim = Simulation(seed=1)
    assert not sim.progression.is_unlocked("greengrid")
    sim.progression.level = 2
    assert sim.progression.is_unlocked("greengrid")
    sim.progression.level = 5
    assert sim.progression.is_unlocked("northstar")
    assert set(sim.progression.unlocked_company_ids()) == set(COMPANY_UNLOCK_LEVEL)


def test_cannot_trade_locked_company():
    sim = Simulation(seed=2)
    with pytest.raises(LockedCompanyError):
        sim.buy("northstar", 1)


def test_xp_and_upgrade_points():
    prog = Progression()
    start_points = prog.upgrade_points
    levels = prog.add_xp(prog.xp_needed())
    assert levels == [2]
    assert prog.level == 2
    assert prog.upgrade_points == start_points + 1


def test_buy_upgrades_and_effects():
    sim = Simulation(seed=3)
    sim.progression.upgrade_points = 10
    assert sim.buy_upgrade("dividends")
    assert sim.progression.upgrades["dividends"] == 1
    assert sim.progression.daily_dividend_rate() > 0
    assert sim.buy_upgrade("volume")
    assert sim.progression.max_trade_shares() > 50
    assert sim.buy_upgrade("income")
    assert sim.progression.daily_base_income() > 2.0
    assert sim.buy_upgrade("offline")
    assert sim.progression.offline_seconds_per_day() < 90.0


def test_passive_income_on_advance():
    sim = Simulation(seed=4)
    sim.progression.upgrade_points = 5
    sim.buy_upgrade("income")
    sim.buy_upgrade("income")
    before = sim.player.cash
    sim.advance(5)
    assert sim.player.cash > before


def test_trade_volume_cap():
    sim = Simulation(seed=5)
    with pytest.raises(Exception):
        sim.buy("ironvale", 10_000)


def test_offline_gains_advance_days():
    sim = Simulation(seed=6)
    sim.progression.upgrade_points = 5
    sim.buy_upgrade("offline")
    # Pretend we were away long enough for several days.
    seconds = sim.progression.offline_seconds_per_day() * 5 + 1
    sim.progression.last_realtime = 1_000_000.0
    report = sim.apply_offline_gains(now=1_000_000.0 + seconds)
    assert report["days"] == 5
    assert sim.day == 5
    assert sim.progression.total_offline_days == 5


def test_offline_capped():
    sim = Simulation(seed=7)
    sim.progression.last_realtime = 0.0
    # Huge gap — should clamp to max_offline_days.
    report = sim.apply_offline_gains(now=10_000_000.0)
    assert report["days"] == sim.progression.max_offline_days()


def test_auto_pilot_buys_dips():
    sim = Simulation(seed=8)
    sim.progression.upgrade_points = 10
    assert sim.buy_upgrade("auto")
    # Force a dip on an unlocked name and ensure auto can act after a step.
    company = sim.companies["ironvale"]
    company.previous_price = 50.0
    company.share_price = 40.0  # -20% daily change signal
    # Give cash and run many days; auto may fire when dips occur naturally too.
    fired = False
    for _ in range(80):
        # Re-assert a dip each morning before step's price update uses previous.
        for c in sim.unlocked_companies():
            c.previous_price = c.share_price * 1.05
        result = sim.step()
        sim.end_of_day_snapshot()
        if result.get("auto_trades"):
            fired = True
            break
    assert fired


def test_prestige_requires_threshold_then_resets():
    sim = Simulation(seed=9)
    assert not sim.prestige()
    sim.progression.level = 5
    sim.player.cash = 30_000
    sim.progression.upgrade_points = 5
    sim.buy_upgrade("dividends")
    assert sim.prestige()
    assert sim.progression.prestige_count == 1
    assert sim.progression.level == 1
    assert sim.progression.upgrades["dividends"] == 0
    assert sim.progression.prestige_multiplier > 1.0


def test_save_load_progression(tmp_path):
    sim = Simulation(seed=10)
    sim.advance(30)
    sim.progression.upgrade_points = 3
    sim.buy_upgrade("offline")
    path = tmp_path / "prog.json"
    save_game(sim, path)
    loaded = load_game(path)
    assert loaded.progression.level == sim.progression.level
    assert loaded.progression.upgrades["offline"] == 1
    assert loaded.progression.xp == sim.progression.xp
