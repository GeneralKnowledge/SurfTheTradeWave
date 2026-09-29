"""Portfolio valuation tests."""

from src.game.company import Company
from src.game.player import Player, STARTING_CASH
from src.game.trading import buy


def _make_company(cid: str, name: str, price: float) -> Company:
    return Company(
        id=cid,
        name=name,
        sector="Retail",
        share_price=price,
        shares_outstanding=1_000_000,
        revenue=50_000_000,
        profit=5_000_000,
        debt=10_000_000,
        growth_rate=0.03,
        profitability=0.1,
        volatility=0.3,
        sentiment=0.0,
        reputation=0.5,
        commodity_exposure=0.0,
    )


def test_portfolio_value_and_pnl():
    player = Player()
    a = _make_company("a", "A Corp", 10.0)
    b = _make_company("b", "B Corp", 20.0)
    companies = {"a": a, "b": b}

    buy(player, a, 100)  # cost 1000
    buy(player, b, 50)  # cost 1000

    a.share_price = 12.0
    b.share_price = 18.0

    invested = player.invested_value(companies)
    assert abs(invested - (100 * 12 + 50 * 18)) < 1e-9

    # Position PnL: +200 on A, -100 on B = +100
    assert abs(player.portfolio.profit_loss(companies) - 100.0) < 1e-9

    total = player.total_value(companies)
    assert abs(total - (STARTING_CASH - 2000 + invested)) < 1e-9

    details = player.portfolio.position_details(companies)
    assert len(details) == 2
    by_id = {d["company_id"]: d for d in details}
    assert abs(by_id["a"]["profit_loss"] - 200.0) < 1e-9
    assert abs(by_id["b"]["profit_loss"] - (-100.0)) < 1e-9


def test_daily_change_tracks_snapshot():
    player = Player()
    company = _make_company("a", "A Corp", 10.0)
    companies = {"a": company}
    buy(player, company, 100)
    player.snapshot_value(companies)
    company.share_price = 11.0
    assert abs(player.daily_change(companies) - 100.0) < 1e-9
