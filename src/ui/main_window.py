"""Main Pygame window for the stock market simulation."""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from src.game.economy import MarketState
from src.game.save import default_save_path, load_game, save_game
from src.game.simulation import Simulation
from src.game.trading import TradeError
from src.ui import colours
from src.ui.company_view import Button, CompanyView
from src.ui.market_view import MarketView
from src.ui.news_panel import NewsPanel


class MainWindow:
    def __init__(self, seed: int = 42, debug: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption("SurfTheTradeWave — Fictional Market")
        self.screen = pygame.display.set_mode((colours.WINDOW_WIDTH, colours.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.sim = Simulation(seed=seed, debug_mode=debug)
        self.font = pygame.font.SysFont("dejavusans", 16)
        self.font_bold = pygame.font.SysFont("dejavusans", 18, bold=True)
        self.font_small = pygame.font.SysFont("dejavusans", 13)
        self.font_title = pygame.font.SysFont("dejavusans", 22, bold=True)

        m = colours.MARGIN
        self.market_view = MarketView(pygame.Rect(m, 110, 620, 340))
        self.company_view = CompanyView(pygame.Rect(m, 460, 620, 308))
        self.news_panel = NewsPanel(pygame.Rect(640, 110, 528, 400))

        companies = self.sim.market.company_list()
        if companies:
            self.market_view.selected_id = companies[0].id

        self.control_buttons = [
            Button(pygame.Rect(640, 530, 90, 32), "PAUSE", "pause"),
            Button(pygame.Rect(740, 530, 90, 32), "NEXT", "next"),
            Button(pygame.Rect(840, 530, 90, 32), "5 DAYS", "day5"),
            Button(pygame.Rect(940, 530, 100, 32), "30 DAYS", "day30"),
            Button(pygame.Rect(1050, 530, 90, 32), "FAST", "fast"),
            Button(pygame.Rect(640, 575, 90, 32), "SAVE", "save"),
            Button(pygame.Rect(740, 575, 90, 32), "LOAD", "load"),
            Button(pygame.Rect(840, 575, 100, 32), "DEBUG", "debug"),
            Button(pygame.Rect(950, 575, 100, 32), "+100D", "day100"),
        ]
        self.status = "Ready. Press NEXT DAY or FAST to simulate."
        self.paused = True
        self.fast = False
        self._accum = 0.0

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

            if self.fast and not self.paused:
                self._accum += dt
                while self._accum >= self.sim.auto_speed_ms:
                    self._accum -= self.sim.auto_speed_ms
                    self._advance(1)

            self._draw()
            pygame.display.flip()

        pygame.quit()

    def _selected_company(self):
        cid = self.market_view.selected_id
        if cid and cid in self.sim.companies:
            return self.sim.companies[cid]
        return None

    def _advance(self, days: int) -> None:
        self.sim.advance(days)
        self.status = f"Advanced {days} day(s). Day {self.sim.day}."

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

        for button in self.control_buttons:
            if button.hit(pos):
                self._control(button.key)
                return

    def _on_hover(self, pos: tuple[int, int]) -> None:
        self.company_view.handle_hover(pos)
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
        elif key == "save":
            path = default_save_path(1)
            save_game(self.sim, path)
            self.status = f"Saved to {path}."
        elif key == "load":
            path = default_save_path(1)
            if Path(path).exists():
                self.sim = load_game(path)
                companies = self.sim.market.company_list()
                if companies:
                    self.market_view.selected_id = companies[0].id
                self.status = f"Loaded {path}."
            else:
                self.status = "No save file found."
        elif key == "debug":
            self.sim.debug_mode = not self.sim.debug_mode
            self.status = f"Debug mode {'ON' if self.sim.debug_mode else 'OFF'}."

    def _draw(self) -> None:
        self.screen.fill(colours.BG)
        self._draw_header()
        self._draw_portfolio()
        self.market_view.draw(self.screen, self.sim.market.company_list())
        self.company_view.draw(
            self.screen,
            self._selected_company(),
            self.sim.player,
            debug=self.sim.debug_mode,
        )
        self.news_panel.draw(self.screen, self.sim.news())
        self._draw_controls()
        self._draw_positions()

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
        self.screen.blit(
            self.font_small.render(f"Seed {self.sim.seed}", True, colours.TEXT_DIM),
            (400, 22),
        )
        mode = "FAST" if self.fast else ("PAUSED" if self.paused else "LIVE")
        self.screen.blit(
            self.font.render(mode, True, colours.WARN if self.paused else colours.UP),
            (500, 20),
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

    def _draw_controls(self) -> None:
        for button in self.control_buttons:
            button.draw(self.screen, self.font)
        self.screen.blit(
            self.font_small.render(self.status, True, colours.TEXT_DIM),
            (640, 620),
        )
        help_text = "Space: pause  N: next day  D: debug  Click qty box to type"
        self.screen.blit(
            self.font_small.render(help_text, True, colours.TEXT_DIM),
            (640, 642),
        )

    def _draw_positions(self) -> None:
        panel = pygame.Rect(640, 665, 528, 100)
        pygame.draw.rect(self.screen, colours.BG_PANEL, panel)
        pygame.draw.rect(self.screen, colours.BORDER, panel, 1)
        self.screen.blit(
            self.font.render("POSITIONS", True, colours.TEXT),
            (panel.x + 10, panel.y + 6),
        )
        details = self.sim.position_details()
        if not details:
            self.screen.blit(
                self.font_small.render("No holdings", True, colours.TEXT_DIM),
                (panel.x + 10, panel.y + 32),
            )
            return
        y = panel.y + 28
        for pos in details[:3]:
            pnl = pos["profit_loss"]
            colour = colours.UP if pnl >= 0 else colours.DOWN
            line = (
                f"{pos['company_name'][:18]:18}  "
                f"{pos['shares']:>4} @ £{pos['average_cost']:.2f}  "
                f"now £{pos['current_price']:.2f}  "
                f"P/L {pnl:+.0f}"
            )
            self.screen.blit(
                self.font_small.render(line, True, colour),
                (panel.x + 10, y),
            )
            y += 18


def run_game(seed: int = 42, debug: bool = False) -> None:
    window = MainWindow(seed=seed, debug=debug)
    window.run()


if __name__ == "__main__":
    run_game()
