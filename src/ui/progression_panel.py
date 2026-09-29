"""Upgrades / level / prestige panel."""

from __future__ import annotations

import pygame

from src.game.progression import UPGRADE_NAMES, UPGRADE_MAX
from src.ui import colours
from src.ui.company_view import Button


class ProgressionPanel:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.font = pygame.font.SysFont("dejavusans", 13)
        self.font_bold = pygame.font.SysFont("dejavusans", 14, bold=True)
        self.font_small = pygame.font.SysFont("dejavusans", 12)
        self.buttons: list[Button] = []
        self._rebuild_buttons()

    def _rebuild_buttons(self) -> None:
        self.buttons = []
        x = self.rect.x + 8
        y = self.rect.y + 78
        for i, key in enumerate(["offline", "dividends", "volume", "income", "auto"]):
            bx = x + (i % 3) * 170
            by = y + (i // 3) * 36
            self.buttons.append(
                Button(pygame.Rect(bx, by, 160, 28), f"+ {UPGRADE_NAMES[key][:10]}", f"up_{key}")
            )
        self.buttons.append(
            Button(
                pygame.Rect(self.rect.x + 8, self.rect.bottom - 34, 120, 28),
                "PRESTIGE",
                "prestige",
            )
        )

    def set_rect(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self._rebuild_buttons()

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        if not self.rect.collidepoint(pos):
            return None
        for button in self.buttons:
            if button.hit(pos):
                return button.key
        return None

    def handle_hover(self, pos: tuple[int, int]) -> None:
        for button in self.buttons:
            button.hover = button.hit(pos)

    def draw(self, surface: pygame.Surface, summary: dict) -> None:
        pygame.draw.rect(surface, colours.BG_PANEL, self.rect)
        pygame.draw.rect(surface, colours.BORDER, self.rect, 1)

        x = self.rect.x + 10
        y = self.rect.y + 8
        surface.blit(
            self.font_bold.render(
                f"LEVEL {summary['level']}   XP {summary['xp']}/{summary['xp_needed']}",
                True,
                colours.TEXT,
            ),
            (x, y),
        )
        y += 18
        # XP bar
        bar = pygame.Rect(x, y, self.rect.width - 20, 8)
        pygame.draw.rect(surface, colours.BG_ALT, bar)
        fill_w = int(bar.width * (summary["xp"] / max(1, summary["xp_needed"])))
        pygame.draw.rect(surface, colours.ACCENT, pygame.Rect(bar.x, bar.y, fill_w, bar.height))
        y += 14
        surface.blit(
            self.font_small.render(
                f"Points: {summary['upgrade_points']}   "
                f"Prestige x{summary['prestige_multiplier']:.2f} "
                f"({summary['prestige_count']}x)   "
                f"Max trade: {summary['max_trade_shares']}",
                True,
                colours.TEXT_DIM,
            ),
            (x, y),
        )

        upgrades = summary["upgrades"]
        for button in self.buttons:
            if button.key.startswith("up_"):
                key = button.key[3:]
                lvl = upgrades.get(key, 0)
                mx = UPGRADE_MAX.get(key, 0)
                button.label = f"{UPGRADE_NAMES[key][:11]} {lvl}/{mx}"
            button.draw(surface, self.font)

        if summary.get("can_prestige"):
            hint = "Go Public ready"
            colour = colours.WARN
        else:
            hint = "Prestige at Lv5 + £25k net"
            colour = colours.TEXT_DIM
        surface.blit(
            self.font_small.render(hint, True, colour),
            (self.rect.x + 140, self.rect.bottom - 28),
        )
