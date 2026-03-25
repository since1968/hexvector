"""
Tests for gravity displacement in core/world.py.

Coordinate conventions (odd-r offset, pointy-top, row increases downward):
  Hex(col, row)  —  odd rows are shifted right by half a hex width

World is placed at Hex(5, 5) for all tests.

  Hex(5, 5) → cube: x=3, y=-8, z=5

Gravity hexes of Hex(5, 5), listed in _CUBE_DIRECTIONS order
(i=0..5), with toward-world direction = (i + 3) % 6:

  Hex(6, 5)  toward-world dir 3  cube step (-1,  1,  0)  [SW]
  Hex(6, 4)  toward-world dir 4  cube step (-1,  0,  1)  [W]
  Hex(5, 4)  toward-world dir 5  cube step ( 0, -1,  1)  [NW]
  Hex(4, 5)  toward-world dir 0  cube step ( 1, -1,  0)  [NE]
  Hex(5, 6)  toward-world dir 1  cube step ( 1,  0, -1)  [E]
  Hex(6, 6)  toward-world dir 2  cube step ( 0,  1, -1)  [SE]

Each was verified: stepping from the gravity hex in toward-world direction
returns cube (3,-8,5) = Hex(5,5). ✓

hex_line(a, b) behaviour:
  Loop is range(1, n+1), so i=0 (the origin) is never added.
  Origin is EXCLUDED; destination is INCLUDED.
  This is correct: gravity fires when a hex is *entered*, not departed.

apply_gravity(vessel) is called after vessel.advance().  After advance():
  vessel.past    = old present
  vessel.present = old future
  vessel.future  = extend_vector(old present, old future)

So hex_line(vessel.past, vessel.present) traces the path the ship
just traveled — which is exactly the old present→future path.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.hex_grid import Hex, extend_vector
from core.vector_movement import Vessel
from core.world import World

WORLD = Hex(5, 5)


def _vessel(past: Hex, present: Hex, future: Hex) -> Vessel:
    """Construct a Vessel with exact counter positions (no advance called)."""
    return Vessel(past, present, future)


class TestGravityDisplacement(unittest.TestCase):

    def test_no_displacement_when_path_clear(self):
        """Path entirely outside the gravity ring — future is unchanged.

        hex_line(Hex(0,0), Hex(2,0)):
          row=0 (even); neither Hex(1,0) nor Hex(2,0) is a gravity hex.
        """
        world = World(WORLD)
        v = _vessel(Hex(0, 0), Hex(2, 0), Hex(4, 0))
        count = world.apply_gravity(v)
        self.assertEqual(count, 0)
        self.assertEqual(v.future, Hex(4, 0))

    def test_single_gravity_displacement(self):
        """Path crosses exactly one gravity hex — future displaced once.

        hex_line(Hex(3,4), Hex(5,4))  [n=2]:
          i=1  t=0.5  → cube(2,-6,4) → Hex(4,4)  — not a gravity hex
          i=2  t=1.0  → cube(3,-7,4) → Hex(5,4)  — gravity hex, dir 5 (0,-1,1)

        future Hex(7,4) cube(5,-9,4):
          step (0,-1,1) → (5,-10,5) → col=7, row=5 → Hex(7,5)

        Speed increases from 2 to 3: distance(Hex(5,4), Hex(7,5)) = 3.
        This is the intended impulse behaviour — gravity accelerates the ship.
        """
        world = World(WORLD)
        v = _vessel(Hex(3, 4), Hex(5, 4), Hex(7, 4))
        count = world.apply_gravity(v)
        self.assertEqual(count, 1)
        self.assertEqual(v.future, Hex(7, 5))

    def test_double_gravity_displacement(self):
        """Path crosses two gravity hexes — future displaced twice (cumulative).

        Ship flying past a world has its trajectory bent by two successive
        gravity hexes.

        hex_line(Hex(3,4), Hex(7,4))  [n=4]:
          i=1  t=0.25 → cube(2,-6,4) → Hex(4,4)  — not gravity
          i=2  t=0.50 → cube(3,-7,4) → Hex(5,4)  — gravity hex, dir 5 (0,-1,1)
          i=3  t=0.75 → cube(4,-8,4) → Hex(6,4)  — gravity hex, dir 4 (-1,0,1)
          i=4  t=1.00 → cube(5,-9,4) → Hex(7,4)  — present; not a gravity hex

        future Hex(11,4) cube(9,-13,4):
          step dir 5 (0,-1,1)  → (9,-14,5)  → col=11, row=5 → Hex(11,5)
          step dir 4 (-1,0,1)  → (8,-14,6)  → col=11, row=6 → Hex(11,6)

        Speed increases from 4 to 5: distance(Hex(7,4), Hex(11,6)) = 5.
        The two impulses are aligned to accelerate the ship in this geometry.
        """
        world = World(WORLD)
        v = _vessel(Hex(3, 4), Hex(7, 4), Hex(11, 4))
        count = world.apply_gravity(v)
        self.assertEqual(count, 2)
        self.assertEqual(v.future, Hex(11, 6))

    def test_takeoff_into_gravity_hex(self):
        """1G launch from world hex: gravity returns future to the gravity hex entered.

        Pre-advance state:
          past=Hex(5,5), present=Hex(5,5), future=Hex(6,5)  [1G thrust applied]

        After advance() — simulated by setting counters directly:
          past    = Hex(5,5)  [old present = world]
          present = Hex(6,5)  [old future  = the gravity hex just entered]
          future  = extend_vector(Hex(5,5), Hex(6,5)) = Hex(7,5)
            derivation: past_cube(3,-8,5), present_cube(4,-9,5)
            result = (2*4-3, 2*-9-(-8), 2*5-5) = (5,-10,5) → col=7,row=5

        hex_line(Hex(5,5), Hex(6,5)) = [Hex(6,5)]:
          The origin Hex(5,5) is excluded (ships do not re-enter where they left).
          Hex(6,5) is a gravity hex, dir 3 (-1,1,0).

        future Hex(7,5) cube(5,-10,5):
          step (-1,1,0) → (4,-9,5) → col=6, row=5 → Hex(6,5)

        Result: future == present == Hex(6,5).
        The ship cannot escape on its first launch — gravity returns its
        future marker to the gravity hex it just entered.
        """
        world = World(WORLD)
        v = _vessel(Hex(5, 5), Hex(6, 5), extend_vector(Hex(5, 5), Hex(6, 5)))
        self.assertEqual(v.future, Hex(7, 5))   # confirm extend_vector result
        count = world.apply_gravity(v)
        self.assertEqual(count, 1)
        self.assertEqual(v.future, Hex(6, 5))
        self.assertEqual(v.future, v.present)   # ship is trapped: future == present

    def test_origin_hex_excluded_from_gravity(self):
        """A gravity hex at the origin (past) must NOT trigger displacement.

        hex_line excludes the origin.  If the ship was in a gravity hex last
        turn (past = Hex(6,5)), it does not re-enter that hex this turn.

        hex_line(Hex(6,5), Hex(7,5)) = [Hex(7,5)]:
          Hex(7,5) is not a gravity hex → no displacement.
        """
        world = World(WORLD)
        v = _vessel(Hex(6, 5), Hex(7, 5), Hex(8, 5))
        count = world.apply_gravity(v)
        self.assertEqual(count, 0)
        self.assertEqual(v.future, Hex(8, 5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
