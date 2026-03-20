"""
Pygame renderer for the hex grid.

Draws a pointy-top hex grid that fills the window.
hex_size is recalculated dynamically on every draw call so the grid
scales correctly when the window is resized.
"""

import math
import pygame
from core.hex_grid import Hex, hex_to_pixel, pixel_to_hex, hexes_within, extend_vector
from core.vector_movement import Vessel
from core.world import World

_COLS   = 20   # default grid columns
_ROWS   = 15   # default grid rows
_MARGIN = 30   # pixel margin around the grid

_ZOOM_MULTIPLIERS = [1.0, 0.5]


def _sysfont(size: int, bold: bool = False) -> pygame.font.Font:
    """Return the first available Unicode-capable monospace font."""
    available = set(pygame.font.get_fonts())
    for name in ("dejavusansmono", "menlo", "consolas", "monospace"):
        if name in available:
            return pygame.font.SysFont(name, size, bold=bold)
    return pygame.font.SysFont(None, size, bold=bold)


# ── colours ──────────────────────────────────────────────────────────────────

COLOUR_BG           = ( 10,  10,  10)
COLOUR_GRID         = ( 30,  60,  30)
COLOUR_HIGHLIGHT    = (200, 200,  80)
COLOUR_LABEL        = (100, 130, 100)

COLOUR_THRUST_HINT  = ( 80, 160,  80)
COLOUR_HUD          = (255, 255, 255)
COLOUR_TARGET       = ( 70, 150, 150)   # dim cyan — distinct from hints and gravity
COLOUR_IMPACT       = (220,  40,  40)   # bold red — destroyed vessel X

COLOUR_WORLD        = (180, 120,  40)
COLOUR_GRAVITY_FILL = ( 60,  35,  10)
COLOUR_GRAVITY_RING = (180,  90,  20)

# Vessel colour scheme
_VESSEL_SCHEME = dict(
    past    = ( 20,  40,  90),
    present = ( 60, 120, 220),
    future  = (120, 180, 255),
    vector  = (100, 160, 220),
)


# ── layout helpers ────────────────────────────────────────────────────────────

def _compute_hex_size(screen_w: int, screen_h: int,
                      cols: int, rows: int, margin: int) -> float:
    available_w = screen_w - 2 * margin
    available_h = screen_h - 2 * margin
    size_from_w = available_w / (math.sqrt(3) * (cols + 0.5))
    size_from_h = available_h / (1.5 * rows + 0.5)
    return min(size_from_w, size_from_h)


def _compute_origin(screen_w: int, screen_h: int,
                    hex_size: float, cols: int, rows: int) -> tuple[float, float]:
    grid_w = math.sqrt(3) * hex_size * (cols + 0.5)
    grid_h = hex_size * (1.5 * rows + 0.5)
    left = (screen_w - grid_w) / 2
    top  = (screen_h - grid_h) / 2
    return (
        left + math.sqrt(3) / 2 * hex_size,
        top  + hex_size,
    )


def _arrow(surface: pygame.Surface, colour, start, end,
           width: int = 2, head_size: float = 8.0) -> None:
    """Draw a line with an arrowhead at end."""
    sx, sy = int(start[0]), int(start[1])
    ex, ey = int(end[0]),   int(end[1])
    pygame.draw.line(surface, colour, (sx, sy), (ex, ey), width)
    angle = math.atan2(ey - sy, ex - sx)
    for offset in (math.radians(150), math.radians(-150)):
        hx = ex + head_size * math.cos(angle + offset)
        hy = ey + head_size * math.sin(angle + offset)
        pygame.draw.line(surface, colour, (ex, ey), (int(hx), int(hy)), width)


# ── renderer ─────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, screen: pygame.Surface,
                 cols: int = _COLS, rows: int = _ROWS):
        self.screen = screen
        self.cols = cols
        self.rows = rows
        self.highlighted: Hex | None = None
        self.show_labels: bool = False
        self.zoom_level: int = 0

        # Infinite-scroll camera pan (pixel offset applied to the grid origin)
        self.camera: list[float] = [0.0, 0.0]

        self._font     = _sysfont(10)
        self._font_hud = _sysfont(18)

    def toggle_labels(self) -> None:
        self.show_labels = not self.show_labels

    def toggle_zoom(self) -> None:
        self.zoom_level = 1 - self.zoom_level

    # ── camera / pan ──────────────────────────────────────────────────────────

    def pan(self, dx: float, dy: float) -> None:
        """Shift the camera by (dx, dy) pixels."""
        self.camera[0] += dx
        self.camera[1] += dy

    def center_on(self, h: Hex) -> None:
        """Set camera so hex h is centred in the viewport."""
        sw, sh = self.screen.get_size()
        size = _compute_hex_size(sw, sh, self.cols, self.rows, _MARGIN)
        size *= _ZOOM_MULTIPLIERS[self.zoom_level]
        ox, oy = _compute_origin(sw, sh, size, self.cols, self.rows)
        px, py = hex_to_pixel(h, size, (ox, oy))
        self.camera[0] = sw / 2 - px
        self.camera[1] = sh / 2 - py

    # ── layout ────────────────────────────────────────────────────────────────

    def _layout(self) -> tuple[float, tuple[float, float]]:
        """Return (hex_size, origin) for the current window and camera."""
        sw, sh = self.screen.get_size()
        size = _compute_hex_size(sw, sh, self.cols, self.rows, _MARGIN)
        size *= _ZOOM_MULTIPLIERS[self.zoom_level]
        ox, oy = _compute_origin(sw, sh, size, self.cols, self.rows)
        return size, (ox + self.camera[0], oy + self.camera[1])

    def _visible_hexes(self, size: float,
                       origin: tuple[float, float]) -> list[Hex]:
        """Return all hexes whose centres fall inside (or just outside) the viewport."""
        sw, sh = self.screen.get_size()
        corners = [
            pixel_to_hex(0,  0,  size, origin),
            pixel_to_hex(sw, 0,  size, origin),
            pixel_to_hex(0,  sh, size, origin),
            pixel_to_hex(sw, sh, size, origin),
        ]
        pad = 2
        min_col = min(h.col for h in corners) - pad
        max_col = max(h.col for h in corners) + pad
        min_row = min(h.row for h in corners) - pad
        max_row = max(h.row for h in corners) + pad
        return [
            Hex(col, row)
            for row in range(min_row, max_row + 1)
            for col in range(min_col, max_col + 1)
        ]

    def _hex_corners(self, h: Hex, size: float,
                     origin: tuple[float, float]) -> list[tuple[float, float]]:
        cx, cy = hex_to_pixel(h, size, origin)
        return [
            (cx + size * math.cos(math.radians(60 * i - 30)),
             cy + size * math.sin(math.radians(60 * i - 30)))
            for i in range(6)
        ]

    def hex_at(self, pixel_pos: tuple[int, int]) -> Hex:
        """Return the hex at pixel_pos on the infinite canvas."""
        size, origin = self._layout()
        return pixel_to_hex(pixel_pos[0], pixel_pos[1], size, origin)

    def handle_click(self, pixel_pos: tuple[int, int]) -> Hex:
        """Update highlighted hex and return it."""
        h = self.hex_at(pixel_pos)
        self.highlighted = h
        return h

    # ── drawing ───────────────────────────────────────────────────────────────

    def draw(self, vessels: list[Vessel], worlds: list[World],
             thrust_hints: set[Hex] | None = None) -> None:
        if thrust_hints is None:
            thrust_hints = set()

        size, origin = self._layout()
        self.screen.fill(COLOUR_BG)

        gravity_hexes: set[Hex] = set()
        for w in worlds:
            gravity_hexes.update(w.gravity_hexes.keys())

        # Grid
        for h in self._visible_hexes(size, origin):
            corners = self._hex_corners(h, size, origin)
            is_highlighted = (h == self.highlighted)

            # Fill
            if is_highlighted:
                pygame.draw.polygon(self.screen, COLOUR_HIGHLIGHT, corners)
            elif h in gravity_hexes:
                pygame.draw.polygon(self.screen, COLOUR_GRAVITY_FILL, corners)

            # Outline
            if h in thrust_hints:
                pygame.draw.polygon(self.screen, COLOUR_THRUST_HINT, corners, 2)
            elif h in gravity_hexes:
                pygame.draw.polygon(self.screen, COLOUR_GRAVITY_RING, corners, 1)
            else:
                pygame.draw.polygon(self.screen, COLOUR_GRID, corners, 1)

            if self.show_labels or is_highlighted:
                cx, cy = hex_to_pixel(h, size, origin)
                colour = COLOUR_HIGHLIGHT if is_highlighted else COLOUR_LABEL
                label = self._font.render(f"{h.col},{h.row}", True, colour)
                lw, lh = label.get_size()
                self.screen.blit(label, (int(cx - lw / 2), int(cy - lh / 2)))

        for w in worlds:
            self._draw_world(w, size, origin)

        for vessel in vessels:
            if vessel.destroyed:
                self._draw_impact(vessel, size, origin)
            else:
                self._draw_vessel(vessel, size, origin)

    def draw_target(self, target_hex: Hex) -> None:
        """Render the target hex: dim cyan outline and centred X."""
        size, origin = self._layout()
        corners = self._hex_corners(target_hex, size, origin)
        pygame.draw.polygon(self.screen, COLOUR_TARGET, corners, 2)
        cx, cy = hex_to_pixel(target_hex, size, origin)
        label = self._font_hud.render("X", True, COLOUR_TARGET)
        lw, lh = label.get_size()
        self.screen.blit(label, (int(cx - lw / 2), int(cy - lh / 2)))

    def draw_hud(self, vessel: Vessel, label: str, turn: int,
                 target_reached: bool = False) -> None:
        """Render a single-line HUD. Top-left, no background."""
        if vessel.destroyed:
            speed = vessel.speed
            text = f"IMPACT | Speed: {speed} hex{'es' if speed != 1 else ''}/turn"
        elif target_reached:
            text = f"TARGET REACHED | Turn: {turn}"
        else:
            speed = vessel.speed
            text = f"{label} | Speed: {speed} hex{'es' if speed != 1 else ''}/turn | Turn: {turn}"
        surf = self._font_hud.render(text, True, COLOUR_HUD)
        self.screen.blit(surf, (12, 12))

    def _draw_impact(self, vessel: Vessel, size: float,
                     origin: tuple[float, float]) -> None:
        """Draw present hex in blue with a bold red X for a destroyed vessel.

        X lines connect opposite corner pairs of the pointy-top hex:
          corners[0] (upper-right) ↔ corners[3] (lower-left)
          corners[1] (lower-right) ↔ corners[4] (upper-left)
        """
        corners = self._hex_corners(vessel.present, size, origin)
        pygame.draw.polygon(self.screen, _VESSEL_SCHEME['present'], corners)
        pygame.draw.polygon(self.screen, COLOUR_GRID, corners, 1)
        pygame.draw.line(self.screen, COLOUR_IMPACT,
                         (int(corners[0][0]), int(corners[0][1])),
                         (int(corners[3][0]), int(corners[3][1])), 3)
        pygame.draw.line(self.screen, COLOUR_IMPACT,
                         (int(corners[1][0]), int(corners[1][1])),
                         (int(corners[4][0]), int(corners[4][1])), 3)

    def _draw_world(self, world: World, size: float,
                    origin: tuple[float, float]) -> None:
        wx, wy = hex_to_pixel(world.position, size, origin)
        radius = int(size * 0.65)
        pygame.draw.circle(self.screen, COLOUR_WORLD, (int(wx), int(wy)), radius)
        pygame.draw.circle(self.screen, COLOUR_GRAVITY_RING, (int(wx), int(wy)), radius, 2)

        for h in world.gravity_hexes:
            hx, hy = hex_to_pixel(h, size, origin)
            dx, dy = wx - hx, wy - hy
            dist = math.hypot(dx, dy)
            if dist == 0:
                continue
            tip_x = hx + dx * (dist - radius - 3) / dist
            tip_y = hy + dy * (dist - radius - 3) / dist
            _arrow(self.screen, COLOUR_GRAVITY_RING,
                   (hx, hy), (tip_x, tip_y),
                   width=1, head_size=max(3.0, size * 0.2))

    def _draw_vessel(self, vessel: Vessel, size: float,
                     origin: tuple[float, float]) -> None:
        """Draw the three counters and velocity arrows for one vessel."""
        scheme = _VESSEL_SCHEME

        # Past counter — filled dark
        corners = self._hex_corners(vessel.past, size, origin)
        pygame.draw.polygon(self.screen, scheme['past'], corners)
        pygame.draw.polygon(self.screen, COLOUR_GRID, corners, 1)

        # Present counter — filled bright
        corners = self._hex_corners(vessel.present, size, origin)
        pygame.draw.polygon(self.screen, scheme['present'], corners)
        pygame.draw.polygon(self.screen, COLOUR_GRID, corners, 1)

        # Future counter — outline only
        corners = self._hex_corners(vessel.future, size, origin)
        pygame.draw.polygon(self.screen, scheme['future'], corners, 2)

        # Velocity arrows
        past_px    = hex_to_pixel(vessel.past,    size, origin)
        present_px = hex_to_pixel(vessel.present, size, origin)
        future_px  = hex_to_pixel(vessel.future,  size, origin)

        dim = tuple(max(0, c - 60) for c in scheme['vector'])
        pygame.draw.line(self.screen, dim,
                         (int(past_px[0]),    int(past_px[1])),
                         (int(present_px[0]), int(present_px[1])), 1)
        _arrow(self.screen, scheme['vector'], present_px, future_px, width=2)
