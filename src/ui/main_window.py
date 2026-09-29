"""Main Pygame window — full desk + compact companion mode."""

from __future__ import annotations

from pathlib import Path

import pygame

from src.game.economy import MarketState
from src.game.save import default_save_path, load_game, save_game
from src.game.simulation import Simulation
from src.game.trading import TradeError
from src.ui import colours
from src.ui.chart import draw_line_chart
from src.ui.company_view import Button, CompanyView
from src.ui.market_view import MarketView
from src.ui.news_panel import NewsPanel
from src.ui.progression_panel import ProgressionPanel
from src.ui.traders_panel import TradersPanel


class MainWindow:
    def __init__(
        self,
        seed: int = 42,
        debug: bool = False,
        companion: bool = False,
    ) -> None:
        pygame.init()
        self.companion = companion
        self.font = pygame.font.SysFont("dejavusans", 16)
        self.font_bold = pygame.font.SysFont("dejavusans", 18, bold=True)
        self.font_small = pygame.font.SysFont("dejavusans", 13)
        self.font_title = pygame.font.SysFont("dejavusans", 22, bold=True)
        self.font_tiny = pygame.font.SysFont("dejavusans", 12)

        size = (
            (colours.COMPANION_WIDTH, colours.COMPANION_HEIGHT)
            if companion
            else (colours.WINDOW_WIDTH, colours.WINDOW_HEIGHT)
        )
        flags = pygame.RESIZABLE if companion else 0
        self.screen = pygame.display.set_mode(size, flags)
        self._set_caption()
        self.clock = pygame.time.Clock()
        self.sim = Simulation(seed=seed, debug_mode=debug)

        self.paused = True
        self.fast = False
        self._accum = 0.0
        self.status = ""
        self._build_layout()

        # Apply offline gains from any previous session timestamp (fresh runs ~0).
        report = self.sim.apply_offline_gains()
        if report.get("days", 0) > 0:
            self.status = (
                f"Welcome back: +{report['days']} offline days "
                f"(£{report['net_change']:+,.0f})"
            )
        else:
            self.status = "Ready. C toggles companion. Idle while away for offline days."

        unlocked = self.sim.unlocked_companies()
        if unlocked:
            self.market_view.selected_id = unlocked[0].id

    def _set_caption(self) -> None:
        mode = "Companion" if self.companion else "Desk"
        pygame.display.set_caption(f"SurfTheTradeWave — {mode}")

    def _build_layout(self) -> None:
        m = colours.MARGIN
        if self.companion:
            w, h = colours.COMPANION_WIDTH, colours.COMPANION_HEIGHT
            self.market_view = MarketView(pygame.Rect(m, 88, w - 2 * m, 168))
            self.company_view = CompanyView(pygame.Rect(m, 265, w - 2 * m, 160))
            # Slim company buttons for companion.
            bx = m + 8
            by = 265 + 160 - 36
            self.company_view.buttons = [
                Button(pygame.Rect(bx, by, 56, 26), "BUY", "buy"),
                Button(pygame.Rect(bx + 62, by, 56, 26), "SELL", "sell"),
                Button(pygame.Rect(bx + 200, by, 40, 26), "7D", "hist7"),
                Button(pygame.Rect(bx + 244, by, 44, 26), "30D", "hist30"),
                Button(pygame.Rect(bx + 292, by, 44, 26), "ALL", "histall"),
            ]
            self.company_view.qty_rect = pygame.Rect(bx + 128, by, 60, 26)
            self.progression_panel = ProgressionPanel(
                pygame.Rect(m, 432, w - 2 * m, 100)
            )
            self.news_panel = NewsPanel(pygame.Rect(0, 0, 1, 1))  # unused
            self.traders_panel = TradersPanel(pygame.Rect(0, 0, 1, 1))
            self.control_buttons = [
                Button(pygame.Rect(m, h - 40, 70, 28), "NEXT", "next"),
                Button(pygame.Rect(m + 78, h - 40, 70, 28), "FAST", "fast"),
                Button(pygame.Rect(m + 156, h - 40, 70, 28), "SAVE", "save"),
                Button(pygame.Rect(m + 234, h - 40, 70, 28), "DESK", "toggle"),
                Button(pygame.Rect(m + 312, h - 40, 84, 28), "OFFLINE", "offline"),
            ]
        else:
            self.market_view = MarketView(pygame.Rect(m, 110, 620, 300))
            self.company_view = CompanyView(pygame.Rect(m, 420, 620, 250))
            self.news_panel = NewsPanel(pygame.Rect(640, 110, 528, 160))
            self.traders_panel = TradersPanel(pygame.Rect(640, 280, 528, 150))
            self.progression_panel = ProgressionPanel(pygame.Rect(640, 440, 528, 125))
            self.control_buttons = [
                Button(pygame.Rect(640, 575, 80, 30), "PAUSE", "pause"),
                Button(pygame.Rect(728, 575, 70, 30), "NEXT", "next"),
                Button(pygame.Rect(806, 575, 70, 30), "5D", "day5"),
                Button(pygame.Rect(884, 575, 70, 30), "30D", "day30"),
                Button(pygame.Rect(962, 575, 70, 30), "FAST", "fast"),
                Button(pygame.Rect(1040, 575, 100, 30), "COMPANION", "toggle"),
                Button(pygame.Rect(640, 612, 80, 30), "SAVE", "save"),
                Button(pygame.Rect(728, 612, 80, 30), "LOAD", "load"),
                Button(pygame.Rect(816, 612, 80, 30), "DEBUG", "debug"),
                Button(pygame.Rect(904, 612, 80, 30), "+100D", "day100"),
                Button(pygame.Rect(992, 612, 100, 30), "OFFLINE", "offline"),
            ]

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._on_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self._on_hover(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self._on_key(event)

            # Auto-pilot speed boost in companion when auto upgrade owned.
            auto_ms = self.sim.auto_speed_ms
            if self.companion and self.sim.progression.auto_level() >= 1 and self.fast:
                auto_ms = max(120, auto_ms - self.sim.progression.auto_level() * 80)

            if self.fast and not self.paused:
                self._accum += dt
                while self._accum >= auto_ms:
                    self._accum -= auto_ms
                    self._advance(1)

            self._draw()
            pygame.display.flip()

        # Bookmark realtime on exit for offline gains next launch.
        self.sim.touch_realtime()
        pygame.quit()

    def _selected_company(self):
        cid = self.market_view.selected_id
        if cid and cid in self.sim.companies:
            return self.sim.companies[cid]
        return None

    def _advance(self, days: int) -> None:
        results = self.sim.advance(days)
        levels = [lvl for r in results for lvl in r.get("levels_gained", [])]
        msg = f"Advanced {days} day(s). Day {self.sim.day}."
        if levels:
            msg += f" Level up → {levels[-1]}!"
        auto = [t for r in results for t in r.get("auto_trades", [])]
        if auto:
            msg += f" Auto bought {auto[-1]['shares']} {auto[-1]['company_name']}."
        self.status = msg

    def _toggle_companion(self) -> None:
        self.companion = not self.companion
        size = (
            (colours.COMPANION_WIDTH, colours.COMPANION_HEIGHT)
            if self.companion
            else (colours.WINDOW_WIDTH, colours.WINDOW_HEIGHT)
        )
        flags = pygame.RESIZABLE if self.companion else 0
        self.screen = pygame.display.set_mode(size, flags)
        self._set_caption()
        selected = self.market_view.selected_id
        self._build_layout()
        self.market_view.selected_id = selected
        self.status = "Companion mode ON." if self.companion else "Desk mode ON."

    def _on_click(self, pos: tuple[int, int]) -> None:
        selected = self.market_view.handle_click(pos)
        if selected:
            self.company_view.set_message("")
            return

        action = self.company_view.handle_click(pos)
        if action == "buy":
            self._trade_buy()
            return
        if action == "sell":
            self._trade_sell()
            return

        prog_action = self.progression_panel.handle_click(pos)
        if prog_action:
            self._progression_action(prog_action)
            return

        for button in self.control_buttons:
            if button.hit(pos):
                self._control(button.key)
                return

    def _on_hover(self, pos: tuple[int, int]) -> None:
        self.company_view.handle_hover(pos)
        self.progression_panel.handle_hover(pos)
        for button in self.control_buttons:
            button.hover = button.hit(pos)

    def _on_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_SPACE:
            self._control("pause")
            return
        if event.key == pygame.K_n:
            self._control("next")
            return
        if event.key == pygame.K_d:
            self._control("debug")
            return
        if event.key == pygame.K_c:
            self._control("toggle")
            return
        if event.key == pygame.K_o:
            self._control("offline")
            return
        self.company_view.handle_key(event)

    def _trade_buy(self) -> None:
        company = self._selected_company()
        if not company:
            return
        qty = self.company_view.quantity()
        try:
            result = self.sim.buy(company.id, qty)
            self.company_view.set_message(
                f"Bought {result.shares} @ £{result.price:.2f}",
                ok=True,
            )
            self.status = f"Bought {result.shares} {company.name}."
            if self.sim.last_levels_gained:
                self.status += f" Level {self.sim.last_levels_gained[-1]}!"
        except TradeError as exc:
            self.company_view.set_message(str(exc), ok=False)

    def _trade_sell(self) -> None:
        company = self._selected_company()
        if not company:
            return
        qty = self.company_view.quantity()
        try:
            result = self.sim.sell(company.id, qty)
            self.company_view.set_message(
                f"Sold {result.shares} @ £{result.price:.2f}",
                ok=True,
            )
            self.status = f"Sold {result.shares} {company.name}."
        except TradeError as exc:
            self.company_view.set_message(str(exc), ok=False)

    def _progression_action(self, key: str) -> None:
        if key == "prestige":
            if self.sim.prestige():
                self.status = (
                    f"Went public! Prestige x{self.sim.progression.prestige_multiplier:.2f}. "
                    "Upgrades reset; keep the multiplier."
                )
            else:
                self.status = "Need Level 5 and £25,000 net worth to prestige."
            return
        if key.startswith("up_"):
            upgrade_key = key[3:]
            if self.sim.buy_upgrade(upgrade_key):
                self.status = f"Upgraded {upgrade_key}."
            else:
                self.status = "Cannot buy that upgrade (points/max)."

    def _control(self, key: str) -> None:
        if key == "pause":
            self.paused = not self.paused
            if self.paused:
                self.fast = False
            self.status = "Paused." if self.paused else "Running..."
        elif key == "next":
            self.paused = True
            self.fast = False
            self._advance(1)
        elif key == "day5":
            self.paused = True
            self.fast = False
            self._advance(5)
        elif key == "day30":
            self.paused = True
            self.fast = False
            self._advance(30)
        elif key == "day100":
            self.paused = True
            self.fast = False
            self._advance(100)
        elif key == "fast":
            self.fast = not self.fast
            self.paused = not self.fast
            self.status = "Fast simulation ON." if self.fast else "Fast simulation OFF."
        elif key == "toggle":
            self._toggle_companion()
        elif key == "offline":
            # Simulate having been away for testing / claim pending.
            # Force a small offline claim by rewinding last_realtime.
            self.sim.progression.last_realtime = (
                (self.sim.progression.last_realtime or 0) - 600
            )
            report = self.sim.apply_offline_gains()
            if report["days"] > 0:
                self.status = (
                    f"Offline claim: +{report['days']} days, "
                    f"£{report['net_change']:+,.0f}"
                )
            else:
                self.status = "No offline days ready yet."
        elif key == "save":
            path = default_save_path(1)
            self.sim.touch_realtime()
            save_game(self.sim, path)
            self.status = f"Saved to {path}."
        elif key == "load":
            path = default_save_path(1)
            if Path(path).exists():
                self.sim = load_game(path)
                report = self.sim.apply_offline_gains()
                companies = self.sim.unlocked_companies()
                if companies:
                    self.market_view.selected_id = companies[0].id
                if report.get("days", 0) > 0:
                    self.status = (
                        f"Loaded + offline {report['days']} days "
                        f"(£{report['net_change']:+,.0f})"
                    )
                else:
                    self.status = f"Loaded {path}."
            else:
                self.status = "No save file found."
        elif key == "debug":
            self.sim.debug_mode = not self.sim.debug_mode
            self.status = f"Debug mode {'ON' if self.sim.debug_mode else 'OFF'}."

    def _draw(self) -> None:
        self.screen.fill(colours.BG)
        if self.companion:
            self._draw_companion()
        else:
            self._draw_desk()

    def _draw_desk(self) -> None:
        self._draw_header()
        self._draw_portfolio()
        unlocked = set(self.sim.progression.unlocked_company_ids())
        self.market_view.draw(self.screen, self.sim.market.company_list(), unlocked)
        self.company_view.draw(
            self.screen,
            self._selected_company(),
            self.sim.player,
            debug=self.sim.debug_mode,
        )
        self.news_panel.draw(self.screen, self.sim.news(limit=4))
        self.traders_panel.draw(
            self.screen,
            self.sim.leaderboard(),
            self.sim.bot_activity(limit=5),
        )
        self.progression_panel.draw(self.screen, self.sim.progression_summary())
        for button in self.control_buttons:
            button.draw(self.screen, self.font_small)
        self.screen.blit(
            self.font_small.render(self.status, True, colours.TEXT_DIM),
            (colours.MARGIN, 740),
        )
        self.screen.blit(
            self.font_tiny.render(
                "C companion  Space pause  N next  O claim offline  D debug",
                True,
                colours.TEXT_DIM,
            ),
            (colours.MARGIN, 758),
        )
        self._draw_positions_strip()

    def _draw_companion(self) -> None:
        w = colours.COMPANION_WIDTH
        summary = self.sim.portfolio_summary()
        prog = self.sim.progression_summary()

        self.screen.blit(self.font_title.render("SurfTheTradeWave", True, colours.ACCENT), (12, 8))
        self.screen.blit(
            self.font_bold.render(f"DAY {self.sim.day}", True, colours.TEXT),
            (12, 36),
        )
        state = self.sim.market.economy.state.value
        self.screen.blit(
            self.font_small.render(f"{state}  Lv{prog['level']}", True, colours.TEXT_DIM),
            (110, 40),
        )
        mode = "FAST" if self.fast else "IDLE"
        self.screen.blit(
            self.font_small.render(mode, True, colours.WARN if not self.fast else colours.UP),
            (w - 70, 40),
        )

        self.screen.blit(
            self.font_small.render(
                f"£{summary['total']:,.0f}   cash £{summary['cash']:,.0f}   "
                f"P/L {summary['profit_loss']:+,.0f}",
                True,
                colours.TEXT,
            ),
            (12, 62),
        )

        unlocked = set(self.sim.progression.unlocked_company_ids())
        # Show unlocked first, then locked.
        companies = sorted(
            self.sim.market.company_list(),
            key=lambda c: (0 if c.id in unlocked else 1, c.name),
        )
        self.market_view.draw(self.screen, companies, unlocked)

        company = self._selected_company()
        # Mini chart only in companion company strip.
        pygame.draw.rect(self.screen, colours.BG_PANEL, self.company_view.rect)
        pygame.draw.rect(self.screen, colours.BORDER, self.company_view.rect, 1)
        if company:
            locked = company.id not in unlocked
            title = company.name + (" (locked)" if locked else "")
            self.screen.blit(
                self.font_bold.render(title, True, colours.LOCKED if locked else colours.TEXT),
                (self.company_view.rect.x + 8, self.company_view.rect.y + 6),
            )
            ch = company.daily_change_pct
            colour = colours.UP if ch >= 0 else colours.DOWN
            self.screen.blit(
                self.font_small.render(
                    f"£{company.share_price:.2f}  {ch:+.1f}%",
                    True,
                    colour,
                ),
                (self.company_view.rect.x + 8, self.company_view.rect.y + 28),
            )
            chart = pygame.Rect(
                self.company_view.rect.x + 8,
                self.company_view.rect.y + 48,
                self.company_view.rect.width - 16,
                70,
            )
            draw_line_chart(self.screen, chart, company.history_slice(30), label="30D")
            for button in self.company_view.buttons:
                button.draw(self.screen, self.font_tiny)
            pygame.draw.rect(self.screen, colours.INPUT_BG, self.company_view.qty_rect)
            pygame.draw.rect(
                self.screen,
                colours.ACCENT if self.company_view.active_input else colours.BORDER,
                self.company_view.qty_rect,
                1,
            )
            self.screen.blit(
                self.font_tiny.render(self.company_view.quantity_text, True, colours.TEXT),
                (self.company_view.qty_rect.x + 6, self.company_view.qty_rect.y + 5),
            )
            if self.company_view.message:
                self.screen.blit(
                    self.font_tiny.render(
                        self.company_view.message,
                        True,
                        self.company_view.message_colour,
                    ),
                    (self.company_view.rect.x + 8, self.company_view.rect.bottom - 48),
                )

        self.progression_panel.draw(self.screen, prog)

        # Mini leaderboard line
        board = self.sim.leaderboard()
        you = next(r for r in board if r["is_player"])
        top = board[0]
        self.screen.blit(
            self.font_tiny.render(
                f"Rank #{you['rank']}/{len(board)}  leader {top['name']} £{top['net_worth']:,.0f}",
                True,
                colours.TEXT_DIM,
            ),
            (12, colours.COMPANION_HEIGHT - 58),
        )
        self.screen.blit(
            self.font_tiny.render(self.status[:58], True, colours.TEXT_DIM),
            (12, colours.COMPANION_HEIGHT - 42),
        )
        for button in self.control_buttons:
            button.draw(self.screen, self.font_tiny)

    def _draw_header(self) -> None:
        title = self.font_title.render("MARKET", True, colours.TEXT)
        self.screen.blit(title, (colours.MARGIN, 14))
        day = self.font_bold.render(f"DAY {self.sim.day}", True, colours.ACCENT)
        self.screen.blit(day, (140, 18))
        state = self.sim.market.economy.state.value
        state_colour = {
            MarketState.BOOM.value: colours.UP,
            MarketState.NORMAL.value: colours.TEXT_DIM,
            MarketState.UNCERTAIN.value: colours.WARN,
            MarketState.RECESSION.value: colours.DOWN,
            MarketState.CRISIS.value: colours.DOWN,
        }.get(state, colours.TEXT_DIM)
        self.screen.blit(
            self.font.render(f"State: {state}", True, state_colour),
            (240, 20),
        )
        prog = self.sim.progression
        self.screen.blit(
            self.font_small.render(
                f"Lv{prog.level}  XP {prog.xp}/{prog.xp_needed()}  "
                f"x{prog.prestige_multiplier:.2f}",
                True,
                colours.ACCENT,
            ),
            (400, 22),
        )
        mode = "FAST" if self.fast else ("PAUSED" if self.paused else "LIVE")
        self.screen.blit(
            self.font.render(mode, True, colours.WARN if self.paused else colours.UP),
            (700, 20),
        )

    def _draw_portfolio(self) -> None:
        summary = self.sim.portfolio_summary()
        y = 52
        items = [
            ("CASH", summary["cash"]),
            ("PORTFOLIO", summary["invested"]),
            ("TOTAL", summary["total"]),
            ("P/L", summary["profit_loss"]),
            ("DAY Δ", summary["daily_change"]),
        ]
        x = colours.MARGIN
        for label, value in items:
            colour = colours.TEXT
            if label in {"P/L", "DAY Δ"}:
                colour = colours.UP if value >= 0 else colours.DOWN
            self.screen.blit(
                self.font_small.render(label, True, colours.TEXT_DIM),
                (x, y),
            )
            sign = "+" if label in {"P/L", "DAY Δ"} and value >= 0 else ""
            self.screen.blit(
                self.font_bold.render(f"{sign}£{value:,.0f}", True, colour),
                (x, y + 16),
            )
            x += 145

    def _draw_positions_strip(self) -> None:
        panel = pygame.Rect(colours.MARGIN, 678, 620, 55)
        pygame.draw.rect(self.screen, colours.BG_PANEL, panel)
        pygame.draw.rect(self.screen, colours.BORDER, panel, 1)
        details = self.sim.position_details()
        self.screen.blit(
            self.font_small.render("POSITIONS", True, colours.TEXT_DIM),
            (panel.x + 8, panel.y + 4),
        )
        if not details:
            self.screen.blit(
                self.font_tiny.render("No holdings — buy unlocked stocks", True, colours.TEXT_DIM),
                (panel.x + 8, panel.y + 24),
            )
            return
        x = panel.x + 8
        y = panel.y + 22
        for pos in details[:3]:
            pnl = pos["profit_loss"]
            colour = colours.UP if pnl >= 0 else colours.DOWN
            line = f"{pos['company_name'][:12]} {pos['shares']} £{pnl:+.0f}"
            self.screen.blit(self.font_tiny.render(line, True, colour), (x, y))
            x += 200


def run_game(seed: int = 42, debug: bool = False, companion: bool = False) -> None:
    window = MainWindow(seed=seed, debug=debug, companion=companion)
    window.run()


if __name__ == "__main__":
    run_game()
