"""
Hex grid using odd-r offset coordinates.

Hex(col, row) maps directly to a rectangular grid:
  col increases to the right
  row increases downward
  odd rows are shifted right by half a hex width (standard wargame layout)

All internal distance/neighbour math converts to cube coordinates temporarily,
then converts the result back to offset.  The caller never sees cube coords.
"""

import math
from typing import NamedTuple


class Hex(NamedTuple):
    col: int
    row: int


# ── internal cube-coordinate helpers ────────────────────────────────────────

def _offset_to_cube(h: Hex) -> tuple[int, int, int]:
    """Odd-r offset → cube (x, y, z)."""
    x = h.col - (h.row - (h.row & 1)) // 2
    z = h.row
    y = -x - z
    return (x, y, z)


def _cube_to_offset(x: int, y: int, z: int) -> Hex:
    """Cube (x, y, z) → odd-r offset."""
    col = x + (z - (z & 1)) // 2
    row = z
    return Hex(col, row)


def _cube_round(fx: float, fy: float, fz: float) -> tuple[int, int, int]:
    """Round fractional cube coordinates to the nearest cube hex."""
    x, y, z = round(fx), round(fy), round(fz)
    dx, dy, dz = abs(x - fx), abs(y - fy), abs(z - fz)
    if dx > dy and dx > dz:
        x = -y - z
    elif dy > dz:
        y = -x - z
    else:
        z = -x - y
    return (x, y, z)


# ── six neighbour directions expressed in cube coordinates ───────────────────

_CUBE_DIRECTIONS = [
    ( 1, -1,  0),   # NE
    ( 1,  0, -1),   # E
    ( 0,  1, -1),   # SE
    (-1,  1,  0),   # SW
    (-1,  0,  1),   # W
    ( 0, -1,  1),   # NW
]


# ── public API ───────────────────────────────────────────────────────────────

def distance(a: Hex, b: Hex) -> int:
    """Hex distance between two offset-coordinate hexes."""
    ax, ay, az = _offset_to_cube(a)
    bx, by, bz = _offset_to_cube(b)
    return (abs(ax - bx) + abs(ay - by) + abs(az - bz)) // 2


def neighbors(h: Hex) -> list[Hex]:
    """Return the six neighbours of hex h."""
    cx, cy, cz = _offset_to_cube(h)
    return [
        _cube_to_offset(cx + dx, cy + dy, cz + dz)
        for dx, dy, dz in _CUBE_DIRECTIONS
    ]


def hex_to_pixel(h: Hex, size: float,
                 origin: tuple[float, float] = (0.0, 0.0)) -> tuple[float, float]:
    """
    Convert offset hex coordinates to pixel centre coordinates.

    size   : circumradius (centre-to-corner) in pixels
    origin : pixel coordinates of hex (0, 0)

    Odd rows are shifted right by half a hex width, producing a
    rectangular grid layout.
    """
    x = size * math.sqrt(3) * (h.col + 0.5 * (h.row & 1))
    y = size * 1.5 * h.row
    return (x + origin[0], y + origin[1])


def pixel_to_hex(px: float, py: float, size: float,
                 origin: tuple[float, float] = (0.0, 0.0)) -> Hex:
    """
    Convert pixel coordinates to the nearest hex in offset coordinates.

    Converts to fractional axial coords, applies cube rounding, then
    converts the result back to offset.
    """
    px -= origin[0]
    py -= origin[1]

    # Fractional axial coordinates
    fq = (math.sqrt(3) / 3 * px - 1 / 3 * py) / size
    fr = (2 / 3 * py) / size
    fs = -fq - fr

    # _cube_round expects (x, y, z); in axial notation x=q, y=s, z=r,
    # so the arguments are (fq, fs, fr) — not (fq, fr, fs).
    x, y, z = _cube_round(fq, fs, fr)
    return _cube_to_offset(x, y, z)


def hex_line(a: Hex, b: Hex) -> list[Hex]:
    """
    Return the hexes on a straight line from a to b, excluding a, including b.

    Uses linear interpolation in cube coordinates.  Used for path-tracing
    (e.g. checking which gravity hexes a moving ship passes through).
    """
    n = distance(a, b)
    if n == 0:
        return []
    ax, ay, az = _offset_to_cube(a)
    bx, by, bz = _offset_to_cube(b)
    result = []
    for i in range(1, n + 1):
        t = i / n
        fx = ax + (bx - ax) * t
        fy = ay + (by - ay) * t
        fz = az + (bz - az) * t
        x, y, z = _cube_round(fx, fy, fz)
        result.append(_cube_to_offset(x, y, z))
    return result


def extend_vector(past: Hex, present: Hex) -> Hex:
    """
    Return the hex reached by extending the past→present vector one step.

    Used in movement step C: place the future counter at the end of the
    line drawn from past through present, extended an equal distance.
    """
    px, py, pz = _offset_to_cube(past)
    cx, cy, cz = _offset_to_cube(present)
    return _cube_to_offset(2 * cx - px, 2 * cy - py, 2 * cz - pz)


def step(h: Hex, direction: int) -> Hex:
    """
    Return the neighbor of h in the given direction.

    Directions: 0=NE, 1=E, 2=SE, 3=SW, 4=W, 5=NW
    """
    cx, cy, cz = _offset_to_cube(h)
    dx, dy, dz = _CUBE_DIRECTIONS[direction]
    return _cube_to_offset(cx + dx, cy + dy, cz + dz)


def direction_to(a: Hex, b: Hex) -> int | None:
    """
    Return the direction index (0–5) from hex a to adjacent hex b,
    or None if b is not adjacent to a.
    """
    ax, ay, az = _offset_to_cube(a)
    bx, by, bz = _offset_to_cube(b)
    diff = (bx - ax, by - ay, bz - az)
    try:
        return _CUBE_DIRECTIONS.index(diff)
    except ValueError:
        return None


def hexes_within(center: Hex, radius: int) -> set[Hex]:
    """
    Return all hexes at hex distance <= radius from center.

    Uses cube-coordinate iteration: for each (dx, dy, dz) triple with
    |dx|+|dy|+|dz| <= 2*radius and dx+dy+dz==0, add the offset hex.
    Result includes center (distance 0).
    """
    cx, cy, cz = _offset_to_cube(center)
    result: set[Hex] = set()
    for dx in range(-radius, radius + 1):
        for dy in range(max(-radius, -dx - radius), min(radius, -dx + radius) + 1):
            dz = -dx - dy
            result.add(_cube_to_offset(cx + dx, cy + dy, cz + dz))
    return result


def best_direction_toward(a: Hex, b: Hex) -> int | None:
    """
    Return the direction (0–5) from a that moves one step closest to b.

    Picks the neighbour of a with the smallest hex distance to b.
    Returns None if a == b (already at destination).
    """
    if a == b:
        return None
    best_dir = 0
    best_dist = float('inf')
    for d in range(6):
        neighbour = step(a, d)
        dist = distance(neighbour, b)
        if dist < best_dist:
            best_dist = dist
            best_dir = d
    return best_dir
