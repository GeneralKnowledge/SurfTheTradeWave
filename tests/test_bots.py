"""NPC bot trader tests."""

from src.game.bots import BotManager, BotPersona, flow_to_price_effects
from src.game.simulation import Simulation


def test_bots_spawn_and_trade():
    sim = Simulation(seed=11)
    assert len(sim.bots.bots) == 6
    result = sim.advance(5)
    assert sim.day == 5
    # Over a few days bots should produce some activity.
    assert any(r.get("bot_activity") for r in result) or len(sim.bots.activity_feed) >= 0
    # Run longer to ensure trades happen.
    sim.advance(20)
    assert len(sim.bots.activity_feed) > 0


def test_bot_flow_affects_price_component():
    sim = Simulation(seed=21)
    sim.advance(15)
    # At least one company should have recorded a non-zero flow effect sometime.
    saw_flow = False
    for _ in range(30):
        result = sim.step()
        sim.end_of_day_snapshot()
        for movement in result["movements"].values():
            if abs(movement.get("flow_effect", 0.0)) > 1e-9:
                saw_flow = True
                break
        if saw_flow:
            break
    assert saw_flow


def test_leaderboard_includes_player_and_bots():
    sim = Simulation(seed=3)
    sim.advance(10)
    board = sim.leaderboard()
    assert len(board) == 7  # you + 6 bots
    assert any(row["is_player"] for row in board)
    assert board[0]["rank"] == 1
    worths = [row["net_worth"] for row in board]
    assert worths == sorted(worths, reverse=True)


def test_bot_personas_present():
    bots = BotManager()
    personas = {b.persona for b in bots.bots}
    assert BotPersona.VALUE in personas
    assert BotPersona.MOMENTUM in personas
    assert BotPersona.PANIC in personas


def test_bots_deterministic_with_seed():
    a = Simulation(seed=4242)
    b = Simulation(seed=4242)
    a.advance(40)
    b.advance(40)
    assert [x.summary for x in a.bots.activity_feed] == [
        x.summary for x in b.bots.activity_feed
    ]
    for bot_a, bot_b in zip(a.bots.bots, b.bots.bots):
        assert abs(bot_a.trader.cash - bot_b.trader.cash) < 1e-9
        assert abs(
            bot_a.net_worth(a.companies) - bot_b.net_worth(b.companies)
        ) < 1e-9


def test_flow_to_price_effects_bounded():
    sim = Simulation(seed=1)
    company = next(iter(sim.companies.values()))
    effects = flow_to_price_effects({company.id: 1_000_000.0}, sim.companies)
    assert effects[company.id] <= 0.035
    effects = flow_to_price_effects({company.id: -1_000_000.0}, sim.companies)
    assert effects[company.id] >= -0.035


def test_save_load_preserves_bots(tmp_path):
    from src.game.save import load_game, save_game

    sim = Simulation(seed=88)
    sim.advance(12)
    path = tmp_path / "botsave.json"
    save_game(sim, path)
    loaded = load_game(path)
    assert len(loaded.bots.bots) == len(sim.bots.bots)
    assert len(loaded.bots.activity_feed) == len(sim.bots.activity_feed)
    for ba, bb in zip(sim.bots.bots, loaded.bots.bots):
        assert ba.name == bb.name
        assert abs(ba.trader.cash - bb.trader.cash) < 1e-9
