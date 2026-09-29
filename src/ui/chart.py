"""Price chart drawing helpers."""

from __future__ import annotations

import pygame

from src.game.company import PricePoint
from src.ui import colours


def draw_line_chart(
    surface: pygame.Surface,
    rect: pygame.Rect,
    points: list[PricePoint],
    *,
    label: str = "",
) -> None:
    pygame.draw.rect(surface, colours.BG_ALT, rect)
    pygame.draw.rect(surface, colours.BORDER, rect, 1)

    if len(points) < 2:
        _text(surface, "Not enough history", rect.x + 10, rect.y + 10, colours.TEXT_DIM)
        return

    prices = [p.price for p in points]
    min_p = min(prices)
    max_p = max(prices)
    if abs(max_p - min_p) < 1e-9:
        max_p = min_p + 1.0

    pad = 8
    chart = pygame.Rect(
        rect.x + pad,
        rect.y + pad + 16,
        rect.width - pad * 2,
        rect.height - pad * 2 - 28,
    )

    coords = []
    n = len(points)
    for i, point in enumerate(points):
        x = chart.x + int(i * (chart.width - 1) / max(1, n - 1))
        y_ratio = (point.price - min_p) / (max_p - min_p)
        y = chart.bottom - int(y_ratio * chart.height)
        coords.append((x, y))

    # Fill under line lightly.
    fill = coords + [(coords[-1][0], chart.bottom), (coords[0][0], chart.bottom)]
    fill_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    local = [(x - rect.x, y - rect.y) for x, y in fill]
    pygame.draw.polygon(fill_surf, (*colours.ACCENT, 40), local)
    surface.blit(fill_surf, rect.topleft)

    color = colours.UP if prices[-1] >= prices[0] else colours.DOWN
    pygame.draw.lines(surface, color, False, coords, 2)

    _text(surface, f"{label}  £{min_p:.2f} – £{max_p:.2f}", rect.x + 8, rect.y + 4, colours.TEXT_DIM)
    _text(
        surface,
        f"£{prices[-1]:.2f}",
        rect.right - 70,
        rect.y + 4,
        colour=color,
    )


_font_cache: dict[int, pygame.font.Font] = {}


def _font(size: int = 14) -> pygame.font.Font:
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("dejavusans", size)
    return _font_cache[size]


def _text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    colour: tuple[int, int, int] = colours.TEXT,
) -> None:
    surface.blit(_font().render(text, True, colour), (x, y))
