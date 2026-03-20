"""
World counter and gravity for a hex-grid physics sandbox.

A world occupies one hex.  The six surrounding hexes are gravity hexes,
each with an imaginary arrow pointing toward the world centre.

When a ship moves through a gravity hex (its present counter passes through
it during movement), the future counter is displaced one hex toward the world.
Effects are cumulative and mandatory: two gravity hexes entered = two
displacements.
"""

from core.hex_grid import Hex, neighbors, step, hex_line


class World:
    def __init__(self, position: Hex, name: str = ""):
        self.position = position
        self.name = name

        # Build mapping: gravity hex → direction toward this world (0–5).
        # neighbors() returns hexes in _CUBE_DIRECTIONS order, so direction i
        # points FROM world TO neighbor[i].  The reverse (toward world) is (i+3)%6.
        self._gravity: dict[Hex, int] = {
            h: (i + 3) % 6
            for i, h in enumerate(neighbors(position))
        }

    @property
    def gravity_hexes(self) -> dict[Hex, int]:
        """Return {hex: toward_world_direction} for the six surrounding hexes."""
        return self._gravity

    def apply_gravity(self, vessel) -> int:
        """
        Apply mandatory gravity to vessel after vessel.advance().

        Traces the straight-line path the present counter took this turn
        (from vessel.past to vessel.present) and displaces vessel.future
        one hex toward this world for each gravity hex entered.

        Returns the number of gravity hexes traversed (0, 1, or 2 typically).
        """
        path = hex_line(vessel.past, vessel.present)
        count = 0
        for h in path:
            if h in self._gravity:
                vessel.future = step(vessel.future, self._gravity[h])
                count += 1
        return count
