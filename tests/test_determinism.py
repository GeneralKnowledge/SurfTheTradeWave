"""Determinism and save/load tests."""

from src.game.save import load_game, save_game
from src.game.simulation import Simulation


def test_same_seed_same_prices():
    a = Simulation(seed=12345)
    b = Simulation(seed=12345)
    a.advance(50)
    b.advance(50)
    for cid in a.companies:
        assert abs(a.companies[cid].share_price - b.companies[cid].share_price) < 1e-9
        assert a.companies[cid].price_history == b.companies[cid].price_history


def test_same_seed_same_actions():
    a = Simulation(seed=999)
    b = Simulation(seed=999)
    a.advance(10)
    b.advance(10)
    a.buy("ironvale", 20)
    b.buy("ironvale", 20)
    a.advance(15)
    b.advance(15)
    a.sell("ironvale", 5)
    b.sell("ironvale", 5)
    a.advance(20)
    b.advance(20)

    assert a.day == b.day
    assert abs(a.player.cash - b.player.cash) < 1e-9
    for cid in a.companies:
        assert abs(a.companies[cid].share_price - b.companies[cid].share_price) < 1e-9


def test_different_seeds_diverge():
    a = Simulation(seed=1)
    b = Simulation(seed=2)
    a.advance(40)
    b.advance(40)
    prices_a = [c.share_price for c in a.companies.values()]
    prices_b = [c.share_price for c in b.companies.values()]
    assert prices_a != prices_b


def test_save_load_roundtrip(tmp_path):
    sim = Simulation(seed=777)
    sim.advance(25)
    sim.buy("ironvale", 30)
    sim.advance(5)
    path = tmp_path / "save.json"
    save_game(sim, path)

    loaded = load_game(path)
    assert loaded.day == sim.day
    assert loaded.seed == sim.seed
    assert abs(loaded.player.cash - sim.player.cash) < 1e-9
    assert loaded.player.portfolio.shares_owned("ironvale") == 30
    for cid in sim.companies:
        assert abs(loaded.companies[cid].share_price - sim.companies[cid].share_price) < 1e-9

    # Continuing from loaded state should match continuing original if RNG restored.
    sim.advance(10)
    loaded.advance(10)
    for cid in sim.companies:
        assert abs(loaded.companies[cid].share_price - sim.companies[cid].share_price) < 1e-9
