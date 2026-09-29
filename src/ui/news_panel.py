"""News feed panel."""

from __future__ import annotations

import pygame

from src.game.events import NewsItem
from src.ui import colours


class NewsPanel:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.font = pygame.font.SysFont("dejavusans", 14)
        self.font_bold = pygame.font.SysFont("dejavusans", 15, bold=True)
        self.font_small = pygame.font.SysFont("dejavusans", 12)

    def draw(self, surface: pygame.Surface, news: list[NewsItem]) -> None:
        pygame.draw.rect(surface, colours.BG_PANEL, self.rect)
        pygame.draw.rect(surface, colours.BORDER, self.rect, 1)
        surface.blit(
            self.font_bold.render("NEWS", True, colours.TEXT),
            (self.rect.x + 12, self.rect.y + 8),
        )

        y = self.rect.y + 34
        for item in news[:8]:
            prefix = "RUMOUR" if item.is_rumour else "NEWS"
            colour = colours.WARN if item.is_rumour else colours.ACCENT
            surface.blit(
                self.font_small.render(f"D{item.day} {prefix}", True, colour),
                (self.rect.x + 12, y),
            )
            y += 14
            title = item.title
            if len(title) > 52:
                title = title[:49] + "..."
            surface.blit(
                self.font.render(title, True, colours.TEXT),
                (self.rect.x + 12, y),
            )
            y += 18
            desc = item.description
            if len(desc) > 58:
                desc = desc[:55] + "..."
            surface.blit(
                self.font_small.render(desc, True, colours.TEXT_DIM),
                (self.rect.x + 12, y),
            )
            y += 22
            if y > self.rect.bottom - 20:
                break
