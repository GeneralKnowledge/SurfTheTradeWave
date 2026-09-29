"""Automated tests for trading logic."""

import pytest

from src.game.company import Company
from src.game.player import Player, STARTING_CASH
from src.game.trading import TradeError, buy, sell, max_affordable


def _company(price: float = 10.0) -> Company:
    return Company(
        id="testco",
        name="Test Co",
        sector="Technology",
        share_price=price,
        shares_outstanding=1_000_000,
        revenue=100_000_000,
        profit=10_000_000,
        debt=20_000_000,
        growth_rate=0.05,
        profitability=0.1,
        volatility=0.4,
        sentiment=0.0,
        reputation=0.5,
        commodity_exposure=0.0,
    )


def test_buy_reduces_cash():
    player = Player()
    company = _company(10.0)
    result = buy(player, company, 100)
    assert result.total == 1000.0
    assert player.cash == STARTING_CASH - 1000.0
    assert player.portfolio.shares_owned("testco") == 100
    assert player.portfolio.get_position("testco").average_purchase_price == 10.0


def test_sell_increases_cash():
    player = Player()
    company = _company(10.0)
    buy(player, company, 100)
    company.share_price = 12.0
    result = sell(player, company, 40)
    assert result.total == 480.0
    assert player.portfolio.shares_owned("testco") == 60
    assert abs(player.cash - (STARTING_CASH - 1000 + 480)) < 1e-9


def test_cannot_overspend():
    player = Player(cash=50.0)
    company = _company(10.0)
    with pytest.raises(TradeError):
        buy(player, company, 10)


def test_cannot_sell_nonexistent():
    player = Player()
    company = _company(10.0)
    with pytest.raises(TradeError):
        sell(player, company, 1)


def test_cannot_trade_negative():
    player = Player()
    company = _company(10.0)
    with pytest.raises(TradeError):
        buy(player, company, 0)
    with pytest.raises(TradeError):
        buy(player, company, -5)


def test_average_cost_updates():
    player = Player()
    company = _company(10.0)
    buy(player, company, 100)
    company.share_price = 20.0
    buy(player, company, 100)
    pos = player.portfolio.get_position("testco")
    assert pos.shares == 200
    assert abs(pos.average_purchase_price - 15.0) < 1e-9


def test_max_affordable():
    player = Player(cash=95.0)
    company = _company(10.0)
    assert max_affordable(player, company) == 9
