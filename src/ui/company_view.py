"""Selected company details, chart, and trade controls."""

from __future__ import annotations

import pygame

from src.game.company import Company
from src.game.player import Player
from src.ui import colours
from src.ui.chart import draw_line_chart


class Button:
    def __init__(self, rect: pygame.Rect, label: str, key: str) -> None:
        self.rect = rect
        self.label = label
        self.key = key
        self.hover = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        colour = colours.BUTTON_HOVER if self.hover else colours.BUTTON
        if self.key in {"buy", "sell"}:
            colour = colours.ACCENT_DIM if self.hover else colours.BUTTON
        pygame.draw.rect(surface, colour, self.rect, border_radius=3)
        pygame.draw.rect(surface, colours.BORDER, self.rect, 1, border_radius=3)
        text = font.render(self.label, True, colours.TEXT)
        surface.blit(
            text,
            (
                self.rect.centerx - text.get_width() // 2,
                self.rect.centery - text.get_height() // 2,
            ),
        )

    def hit(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


class CompanyView:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.history_days: int | None = 30
        self.quantity_text = "10"
        self.active_input = False
        self.font = pygame.font.SysFont("dejavusans", 15)
        self.font_small = pygame.font.SysFont("dejavusans", 13)
        self.font_bold = pygame.font.SysFont("dejavusans", 17, bold=True)
        self.message = ""
        self.message_colour = colours.TEXT_DIM

        bx = rect.x + 12
        by = rect.bottom - 42
        self.buttons = [
            Button(pygame.Rect(bx, by, 70, 28), "BUY", "buy"),
            Button(pygame.Rect(bx + 80, by, 70, 28), "SELL", "sell"),
            Button(pygame.Rect(bx + 260, by, 50, 28), "7D", "hist7"),
            Button(pygame.Rect(bx + 315, by, 50, 28), "30D", "hist30"),
            Button(pygame.Rect(bx + 370, by, 50, 28), "ALL", "histall"),
        ]
        self.qty_rect = pygame.Rect(bx + 160, by, 80, 28)

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        self.active_input = self.qty_rect.collidepoint(pos)
        for button in self.buttons:
            if button.hit(pos):
                if button.key == "hist7":
                    self.history_days = 7
                    return None
                if button.key == "hist30":
                    self.history_days = 30
                    return None
                if button.key == "histall":
                    self.history_days = None
                    return None
                return button.key
        return None

    def handle_hover(self, pos: tuple[int, int]) -> None:
        for button in self.buttons:
            button.hover = button.hit(pos)

    def handle_key(self, event: pygame.event.Event) -> None:
        if not self.active_input:
            return
        if event.key == pygame.K_BACKSPACE:
            self.quantity_text = self.quantity_text[:-1]
        elif event.unicode.isdigit() and len(self.quantity_text) < 8:
            self.quantity_text += event.unicode

    def quantity(self) -> int:
        try:
            return max(0, int(self.quantity_text or "0"))
        except ValueError:
            return 0

    def set_message(self, text: str, ok: bool = True) -> None:
        self.message = text
        self.message_colour = colours.UP if ok else colours.DOWN

    def draw(
        self,
        surface: pygame.Surface,
        company: Company | None,
        player: Player,
        debug: bool = False,
    ) -> None:
        pygame.draw.rect(surface, colours.BG_PANEL, self.rect)
        pygame.draw.rect(surface, colours.BORDER, self.rect, 1)

        if company is None:
            surface.blit(
                self.font.render("Select a company", True, colours.TEXT_DIM),
                (self.rect.x + 12, self.rect.y + 12),
            )
            return

        info = company.public_info()
        y = self.rect.y + 10
        surface.blit(
            self.font_bold.render(info["name"], True, colours.TEXT),
            (self.rect.x + 12, y),
        )
        y += 24
        change = info["daily_change_pct"]
        ch_colour = colours.UP if change >= 0 else colours.DOWN
        sign = "+" if change >= 0 else ""
        lines = [
            f"Sector: {info['sector']}",
            f"Price: £{info['share_price']:.2f}  ({sign}{change:.2f}%)",
            f"Revenue: £{info['revenue']/1e9:.2f}B   Profit: £{info['profit']/1e6:.1f}M",
            (
                f"Growth: {info['growth_rate']*100:.1f}%   "
                f"Profitability: {info['profitability']*100:.1f}%"
            ),
            (
                f"Debt: £{info['debt']/1e9:.2f}B   "
                f"Sentiment: {info['sentiment']:+.2f}"
            ),
        ]
        for line in lines:
            colour = ch_colour if "Price:" in line else colours.TEXT_DIM
            surface.blit(self.font_small.render(line, True, colour), (self.rect.x + 12, y))
            y += 18

        owned = player.portfolio.shares_owned(company.id)
        surface.blit(
            self.font_small.render(f"You own: {owned} shares", True, colours.ACCENT),
            (self.rect.x + 12, y),
        )
        y += 22

        chart_rect = pygame.Rect(
            self.rect.x + 12,
            y,
            self.rect.width - 24,
            self.rect.bottom - y - 90,
        )
        label = (
            "ALL"
            if self.history_days is None
            else f"{self.history_days}D"
        )
        draw_line_chart(
            surface,
            chart_rect,
            company.history_slice(self.history_days),
            label=label,
        )

        if debug:
            m = company.last_movement
            dbg = (
                f"FV £{company.fair_value:.2f} | "
                f"F {m.fundamental_effect*100:+.2f}% "
                f"S {m.sector_effect*100:+.2f}% "
                f"E {m.event_effect*100:+.2f}% "
                f"Sent {m.sentiment_effect*100:+.2f}% "
                f"Mkt {m.market_effect*100:+.2f}% "
                f"N {m.noise_effect*100:+.2f}%"
            )
            surface.blit(
                self.font_small.render(dbg, True, colours.WARN),
                (self.rect.x + 12, chart_rect.bottom + 4),
            )

        # Quantity input
        pygame.draw.rect(surface, colours.INPUT_BG, self.qty_rect)
        border = colours.ACCENT if self.active_input else colours.BORDER
        pygame.draw.rect(surface, border, self.qty_rect, 1)
        surface.blit(
            self.font.render(self.quantity_text or "", True, colours.TEXT),
            (self.qty_rect.x + 8, self.qty_rect.y + 5),
        )
        surface.blit(
            self.font_small.render("QTY", True, colours.TEXT_DIM),
            (self.qty_rect.x, self.qty_rect.y - 16),
        )

        for button in self.buttons:
            button.draw(surface, self.font)

        if self.message:
            surface.blit(
                self.font_small.render(self.message, True, self.message_colour),
                (self.rect.x + 430, self.rect.bottom - 36),
            )
