"""Buy/sell trading logic with validation."""

from __future__ import annotations

from dataclasses import dataclass

from .company import Company
from .player import Player
from .portfolio import Position


class TradeError(ValueError):
    """Raised when a trade cannot be executed."""


@dataclass
class TradeResult:
    company_id: str
    side: str  # "BUY" or "SELL"
    shares: int
    price: float
    total: float


def buy(player: Player, company: Company, shares: int) -> TradeResult:
    """Buy shares at the current market price."""
    if shares <= 0:
        raise TradeError("Cannot trade a non-positive quantity")
    cost = shares * company.share_price
    if cost > player.cash + 1e-9:
        raise TradeError("Insufficient cash for purchase")

    player.cash -= cost
    existing = player.portfolio.get_position(company.id)
    if existing:
        total_shares = existing.shares + shares
        total_cost = existing.cost_basis + cost
        existing.shares = total_shares
        existing.average_purchase_price = total_cost / total_shares
    else:
        player.portfolio.positions[company.id] = Position(
            company_id=company.id,
            shares=shares,
            average_purchase_price=company.share_price,
        )
    return TradeResult(
        company_id=company.id,
        side="BUY",
        shares=shares,
        price=company.share_price,
        total=cost,
    )


def sell(player: Player, company: Company, shares: int) -> TradeResult:
    """Sell shares at the current market price."""
    if shares <= 0:
        raise TradeError("Cannot trade a non-positive quantity")
    existing = player.portfolio.get_position(company.id)
    owned = existing.shares if existing else 0
    if shares > owned:
        raise TradeError("Cannot sell more shares than owned")

    proceeds = shares * company.share_price
    player.cash += proceeds
    remaining = owned - shares
    if remaining == 0:
        del player.portfolio.positions[company.id]
    else:
        assert existing is not None
        existing.shares = remaining
    return TradeResult(
        company_id=company.id,
        side="SELL",
        shares=shares,
        price=company.share_price,
        total=proceeds,
    )


def max_affordable(player: Player, company: Company) -> int:
    if company.share_price <= 0:
        return 0
    return int(player.cash // company.share_price)
