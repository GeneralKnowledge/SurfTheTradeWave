"""Market company list view."""

from __future__ import annotations

import pygame

from src.game.company import Company
from src.ui import colours

ROW_HEIGHT = 28


class MarketView:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.selected_id: str | None = None
        self._row_rects: list[tuple[str, pygame.Rect]] = []
        self.font = pygame.font.SysFont("dejavusans", 15)
        self.font_bold = pygame.font.SysFont("dejavusans", 15, bold=True)
        self.header_font = pygame.font.SysFont("dejavusansmono", 13)

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        if not self.rect.collidepoint(pos):
            return None
        for company_id, row in self._row_rects:
            if row.collidepoint(pos):
                self.selected_id = company_id
                return company_id
        return None

    def draw(self, surface: pygame.Surface, companies: list[Company]) -> None:
        pygame.draw.rect(surface, colours.BG_PANEL, self.rect)
        pygame.draw.rect(surface, colours.BORDER, self.rect, 1)

        title = self.font_bold.render("COMPANY", True, colours.TEXT_DIM)
        surface.blit(title, (self.rect.x + 12, self.rect.y + 8))
        surface.blit(
            self.header_font.render("PRICE", True, colours.TEXT_DIM),
            (self.rect.x + 250, self.rect.y + 10),
        )
        surface.blit(
            self.header_font.render("CHANGE", True, colours.TEXT_DIM),
            (self.rect.x + 340, self.rect.y + 10),
        )
        surface.blit(
            self.header_font.render("SECTOR", True, colours.TEXT_DIM),
            (self.rect.x + 430, self.rect.y + 10),
        )

        self._row_rects = []
        y = self.rect.y + 34
        for company in companies:
            row = pygame.Rect(self.rect.x + 4, y, self.rect.width - 8, ROW_HEIGHT)
            self._row_rects.append((company.id, row))
            if company.id == self.selected_id:
                pygame.draw.rect(surface, colours.SELECTED, row)

            name = self.font.render(company.name, True, colours.TEXT)
            surface.blit(name, (row.x + 8, row.y + 5))

            price = self.font.render(f"£{company.share_price:.2f}", True, colours.TEXT)
            surface.blit(price, (row.x + 246, row.y + 5))

            change = company.daily_change_pct
            colour = colours.UP if change >= 0 else colours.DOWN
            sign = "+" if change >= 0 else ""
            ch = self.font.render(f"{sign}{change:.1f}%", True, colour)
            surface.blit(ch, (row.x + 336, row.y + 5))

            sector = self.font.render(company.sector, True, colours.TEXT_DIM)
            surface.blit(sector, (row.x + 426, row.y + 5))
            y += ROW_HEIGHT
