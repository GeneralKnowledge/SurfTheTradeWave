"""Trader leaderboard and bot activity panel."""

from __future__ import annotations

import pygame

from src.game.bots import BotActivity
from src.ui import colours


class TradersPanel:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.font = pygame.font.SysFont("dejavusans", 14)
        self.font_bold = pygame.font.SysFont("dejavusans", 15, bold=True)
        self.font_small = pygame.font.SysFont("dejavusans", 12)

    def draw(
        self,
        surface: pygame.Surface,
        leaderboard: list[dict],
        activity: list[BotActivity],
    ) -> None:
        pygame.draw.rect(surface, colours.BG_PANEL, self.rect)
        pygame.draw.rect(surface, colours.BORDER, self.rect, 1)

        x = self.rect.x + 10
        y = self.rect.y + 8
        surface.blit(self.font_bold.render("TRADERS", True, colours.TEXT), (x, y))
        y += 22

        for row in leaderboard[:7]:
            rank = row["rank"]
            name = row["name"]
            if len(name) > 14:
                name = name[:13] + "…"
            worth = row["net_worth"]
            is_player = row["is_player"]
            colour = colours.ACCENT if is_player else colours.TEXT
            persona = "" if is_player else f" ({row['persona'][:3]})"
            line = f"#{rank} {name}{persona}"
            surface.blit(self.font_small.render(line, True, colour), (x, y))
            surface.blit(
                self.font_small.render(f"£{worth:,.0f}", True, colour),
                (x + 210, y),
            )
            y += 16

        y += 8
        surface.blit(self.font_bold.render("BOT ACTIVITY", True, colours.TEXT), (x, y))
        y += 20
        if not activity:
            surface.blit(
                self.font_small.render("No trades yet — advance a day", True, colours.TEXT_DIM),
                (x, y),
            )
            return

        for item in activity[:6]:
            colour = colours.UP if item.side == "BUY" else colours.DOWN
            text = item.summary
            if len(text) > 48:
                text = text[:45] + "..."
            surface.blit(
                self.font_small.render(f"D{item.day} {text}", True, colour),
                (x, y),
            )
            y += 15
            if y > self.rect.bottom - 14:
                break
