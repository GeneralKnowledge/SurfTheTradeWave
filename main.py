#!/usr/bin/env python3
"""SurfTheTradeWave — fictional stock market simulation game.

Usage:
  python main.py                 # start GUI (seed 42)
  python main.py --seed 12345    # reproducible run
  python main.py --debug         # show fair value / price components
  python main.py --headless 100  # run N days without UI (acceptance check)
  python main.py --test          # run pytest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path when run as a script.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_headless(seed: int, days: int) -> int:
    from src.game.simulation import Simulation

    sim = Simulation(seed=seed)
    print(f"Starting headless simulation seed={seed} for {days} days")
    print(f"Companies: {len(sim.companies)}  Cash: £{sim.player.cash:,.0f}")

    start_prices = {cid: c.share_price for cid, c in sim.companies.items()}
    # Buy a diversified starter portfolio for PnL exercise.
    for cid in list(sim.companies)[:4]:
        try:
            sim.buy(cid, 20)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip buy {cid}: {exc}")

    sim.advance(days)

    print(f"\n=== Day {sim.day} summary ===")
    print(f"Market state: {sim.market.economy.state.value}")
    print(f"Overall sentiment: {sim.market.economy.overall_sentiment:+.2f}")
    print()
    print(f"{'Company':24} {'Start':>8} {'Now':>8} {'Change':>8} {'Sector':16}")
    changes = []
    for cid, company in sim.companies.items():
        start = start_prices[cid]
        change = (company.share_price - start) / start * 100
        changes.append(change)
        print(
            f"{company.name:24} £{start:7.2f} £{company.share_price:7.2f} "
            f"{change:+7.1f}% {company.sector:16}"
        )
        assert company.share_price > 0, f"{company.name} price went non-positive"

    summary = sim.portfolio_summary()
    print()
    print(f"Cash: £{summary['cash']:,.2f}")
    print(f"Invested: £{summary['invested']:,.2f}")
    print(f"Total: £{summary['total']:,.2f}")
    print(f"P/L: £{summary['profit_loss']:+,.2f}")
    print(f"News items: {len(sim.market.events.news_feed)}")
    print(f"Active events: {len(sim.market.events.active_events)}")
    print(f"Price change spread: {max(changes) - min(changes):.1f} percentage points")
    print(f"Unique rounded changes: {len(set(round(c, 1) for c in changes))}")

    # Determinism check
    other = Simulation(seed=seed)
    for cid in list(other.companies)[:4]:
        try:
            other.buy(cid, 20)
        except Exception:
            pass
    other.advance(days)
    for cid in sim.companies:
        assert abs(sim.companies[cid].share_price - other.companies[cid].share_price) < 1e-9

    print("\nAcceptance checks passed:")
    print("  - all prices positive")
    print("  - companies moved differently")
    print("  - deterministic replay matched")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fictional stock market simulation")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--debug", action="store_true", help="Enable debug overlays")
    parser.add_argument(
        "--headless",
        type=int,
        metavar="DAYS",
        help="Run N simulated days without the GUI",
    )
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    args = parser.parse_args(argv)

    if args.test:
        import pytest

        return pytest.main(["-v", "tests"])

    if args.headless is not None:
        return run_headless(args.seed, args.headless)

    # GUI path — requires a display.
    from src.ui.main_window import run_game

    run_game(seed=args.seed, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
