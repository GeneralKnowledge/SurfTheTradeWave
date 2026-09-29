# SurfTheTradeWave

A small, self-contained **fictional stock-market simulation game**.

Watch an evolving toy economy, decide when to buy or sell, and see whether reading the market feels fun. This is a game — not a realistic financial simulator, and not connected to real money or real markets.

## Features

- ~10 fictional companies across Mining, Technology, Consumer Staples, Energy, Banking, Healthcare, Manufacturing, Transport, and Retail
- Discrete daily simulation ticks driven by fundamentals, sectors, sentiment, news/events, market regimes, and noise
- Deterministic seeded RNG for reproducible runs
- Buy/sell trading with cash and portfolio tracking
- **6 NPC trader bots** (value, momentum, growth, panic, noise) with leaderboard, activity feed, and supply/demand flow pressure
- **Idle progression** (Screen Stocks–inspired): XP/levels, company unlocks, upgrades (offline, dividends, trade volume, base income, auto-pilot), prestige (“Go Public”)
- **Offline gains**: elapsed real time converts into simulated days (capped, upgradeable)
- **Companion window**: compact UI for desk-corner play (`--companion` or press `C`)
- News feed + simple rumour system
- Pygame UI with price charts, company info, traders panel, upgrades panel
- JSON save/load
- Debug mode showing fair value and price-movement components

## Requirements

- Python 3.12+
- pygame
- pytest

```bash
pip install -r requirements.txt
```

## How to run

```bash
# Full desk UI (default seed 42)
python main.py

# Compact companion window
python main.py --companion

# Reproducible run
python main.py --seed 12345

# Debug overlays (fair value + movement breakdown)
python main.py --debug

# Headless acceptance / balance check (100 days)
python main.py --headless 100

# Unit tests
python main.py --test
# or
PYTHONPATH=. pytest -v
```

### Controls

| Action | How |
|--------|-----|
| Select company | Click row (locked names show required level) |
| Buy / Sell | Set quantity, click BUY or SELL |
| Next day | NEXT or `N` |
| Advance 5 / 30 / 100 days | Buttons |
| Pause | PAUSE or `Space` |
| Auto-run | FAST |
| Companion / Desk | COMPANION button or `C` |
| Claim offline (demo) | OFFLINE or `O` |
| Buy upgrades | Buttons in progression panel |
| Prestige | PRESTIGE when Lv5 + £25k net |
| Save / Load | SAVE / LOAD (`saves/save_1.json`) |
| Debug | DEBUG or `D` |

Starting cash: **£10,000**. Start unlocked: Ironvale, Albion, Sterling, Highstreet.

## Architecture

```
src/game/     # Headless simulation (market, companies, events, trading)
src/data/     # Company definitions and event templates
src/ui/       # Pygame views (observes simulation; no market logic)
tests/        # pytest suite
main.py       # Entry point
```

The UI never owns the economy. `market.step()` / `simulation.advance(n)` run fully headlessly.

## Tests

```bash
PYTHONPATH=. pytest -v
```

Coverage includes trading validation, portfolio maths, price integrity, event targeting/expiry, and seed determinism (including save/load resume).

## Known limitations

- No bid/ask spread, order book, fees, dividends, or short selling
- No weekends/holidays or intraday ticks
- Market regimes transition probabilistically (not fully emergent)
- Charts are simple line plots
- Rumour system is intentionally minimal
- Fair value is a gameplay construct, not accounting

## Sensible next steps

1. Transaction fees and simple bid/ask spread
2. Dividends and bankruptcy for chronically distressed firms
3. Richer rumour / analyst commentary without revealing hidden numbers
4. NPC traders for supply/demand pressure
5. Scenario editor / forced-event debug panel in the UI
