"""
Tests for core/vector_movement.py — Vessel momentum and thrust.

All coordinates are Hex(col, row) in odd-r offset.  Direction constants
match core/hex_grid._CUBE_DIRECTIONS:
    0=NE (+1,-1, 0)   same row, col+1 (on even rows)
    1=E  (+1, 0,-1)
    2=SE ( 0,+1,-1)   row+1, col same (on even rows)
    3=SW (-1,+1, 0)   same row, col-1 (on even rows)  ← opposite of NE
    4=W  (-1, 0,+1)
    5=NW ( 0,-1,+1)

Run with:
    python3 -m unittest tests/test_vector_movement.py -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.hex_grid import Hex
from core.vector_movement import Vessel


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_vessel(past, present, future, g_factor=1):
    """Convenience wrapper — constructs a Vessel with the three counters."""
    return Vessel(past=past, present=present, future=future, g_factor=g_factor)


class TestCoasting(unittest.TestCase):

    # ── TEST 1 ────────────────────────────────────────────────────────────────

    def test_straight_line_coasting_one_turn(self):
        """Vessel without thrust continues in the same direction for one turn.

        Initial state (moving NE, speed 1):
            past=Hex(5,5)  present=Hex(6,5)  future=Hex(7,5)

        advance() computes new_future = extend_vector(present=Hex(6,5),
        future=Hex(7,5)).  In cube: (4,-9,5)→(5,-10,5); extending gives
        (6,-11,5) → Hex(8,5).

        Expected after advance (no thrust):
            past=Hex(6,5)  present=Hex(7,5)  future=Hex(8,5)
        """
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5))
        v.advance()
        self.assertEqual(v.past,    Hex(6, 5))
        self.assertEqual(v.present, Hex(7, 5))
        self.assertEqual(v.future,  Hex(8, 5))

    def test_straight_line_coasting_second_turn(self):
        """Vessel continues in the same direction for a second consecutive turn.

        Continuing the scenario from test_straight_line_coasting_one_turn:
        after the first advance the state is
            past=Hex(6,5)  present=Hex(7,5)  future=Hex(8,5)

        A second advance (still no thrust) extends
        extend_vector(Hex(7,5), Hex(8,5)).  In cube: (5,-10,5)→(6,-11,5);
        extending gives (7,-12,5) → Hex(9,5).

        Expected after second advance:
            past=Hex(7,5)  present=Hex(8,5)  future=Hex(9,5)

        The column increments by 1 every turn — momentum is preserved.
        """
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5))
        v.advance()  # turn 1
        v.advance()  # turn 2 — no thrust either turn
        self.assertEqual(v.past,    Hex(7, 5))
        self.assertEqual(v.present, Hex(8, 5))
        self.assertEqual(v.future,  Hex(9, 5))

    # ── TEST 2 ────────────────────────────────────────────────────────────────

    def test_speed_preserved_without_thrust(self):
        """Speed 2 is maintained exactly over three consecutive coast turns.

        Initial state (moving NE, speed 2):
            past=Hex(3,5)  present=Hex(5,5)  future=Hex(7,5)
          distance(past, present) = 2

        Each advance shifts present forward by 2 columns (same row).
        Expected present positions: Hex(7,5) → Hex(9,5) → Hex(11,5).
        Speed (= distance(past, present)) must equal 2 throughout.
        """
        v = make_vessel(Hex(3, 5), Hex(5, 5), Hex(7, 5), g_factor=2)
        self.assertEqual(v.speed, 2)

        v.advance()
        self.assertEqual(v.speed,   2)
        self.assertEqual(v.present, Hex(7, 5))

        v.advance()
        self.assertEqual(v.speed,   2)
        self.assertEqual(v.present, Hex(9, 5))

        v.advance()
        self.assertEqual(v.speed,   2)
        self.assertEqual(v.present, Hex(11, 5))


class TestThrust(unittest.TestCase):

    # ── TEST 3 ────────────────────────────────────────────────────────────────

    def test_thrust_deflects_future_by_one_hex(self):
        """1G thrust in a different direction moves the future counter exactly one hex.

        Setup: vessel moving NE (speed 1).
          Initial:  past=Hex(5,5)  present=Hex(6,5)  future=Hex(7,5)

        After advance(): past=Hex(6,5), present=Hex(7,5), future=Hex(8,5)
          (natural coast, as verified in TEST 1 above).

        Apply 1G thrust in direction 2 (SE).
          step(Hex(8,5), 2):  cube(6,-11,5) + (0,+1,-1) = (6,-10,4)
                              → _cube_to_offset → Hex(8,4)

        The future should move from the natural Hex(8,5) to Hex(8,4).
        The column is unchanged; only the row is deflected by one.
        """
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5), g_factor=2)
        v.advance()

        natural_future = Hex(8, 5)
        self.assertEqual(v.future, natural_future)  # verify coast first

        result = v.apply_thrust(2)  # SE
        self.assertTrue(result)
        self.assertEqual(v.future, Hex(8, 4))

    # ── TEST 4 ────────────────────────────────────────────────────────────────

    def test_thrust_budget_decrements_and_resets(self):
        """G remaining decrements with each thrust application and resets on advance.

        A 2G vessel starts each turn with thrust_remaining == 2.
        After one thrust: thrust_remaining == 1.
        After two thrusts: thrust_remaining == 0.
        A third apply_thrust() must return False (budget exhausted).
        After advance() the budget resets to 2.
        """
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5), g_factor=2)
        self.assertEqual(v.thrust_remaining, 2)

        ok = v.apply_thrust(0)      # first thrust
        self.assertTrue(ok)
        self.assertEqual(v.thrust_remaining, 1)

        ok = v.apply_thrust(0)      # second thrust — exhausts budget
        self.assertTrue(ok)
        self.assertEqual(v.thrust_remaining, 0)

        ok = v.apply_thrust(0)      # third attempt — should be rejected
        self.assertFalse(ok)
        self.assertEqual(v.thrust_remaining, 0)

        v.advance()                 # new turn: budget resets
        self.assertEqual(v.thrust_remaining, 2)

    # ── TEST 5 ────────────────────────────────────────────────────────────────

    def test_stationary_vessel_stays_put(self):
        """A stopped vessel (speed 0) remains stationary without thrust.

        When past == present == future, extend_vector returns the same hex
        (the null vector extended is still null).  advance() should leave all
        three counters on the same hex; speed remains 0.
        """
        v = make_vessel(Hex(5, 5), Hex(5, 5), Hex(5, 5))
        self.assertEqual(v.speed, 0)

        v.advance()
        self.assertEqual(v.past,    Hex(5, 5))
        self.assertEqual(v.present, Hex(5, 5))
        self.assertEqual(v.future,  Hex(5, 5))
        self.assertEqual(v.speed,   0)

    # ── TEST 6 ────────────────────────────────────────────────────────────────

    def test_thrust_cannot_exceed_g_rating(self):
        """A 1G vessel cannot apply more than one hex of thrust per turn.

        apply_thrust() returns False when the G budget is already exhausted.
        The future counter must not move after a rejected thrust call —
        the vessel reflects only the allowed thrust.
        """
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5), g_factor=1)

        ok = v.apply_thrust(0)      # NE — consumes the single G
        self.assertTrue(ok)
        future_after_one_thrust = v.future   # record where future landed

        ok = v.apply_thrust(3)      # SW — should be rejected
        self.assertFalse(ok)
        self.assertEqual(v.future, future_after_one_thrust)  # unchanged

        self.assertEqual(v.thrust_remaining, 0)

    # ── TEST 7 ────────────────────────────────────────────────────────────────

    def test_direction_reversal_requires_multiple_turns(self):
        """Inertia forces several turns of opposing thrust before direction reverses.

        Initial state: vessel moving NE (speed 1, g_factor=1).
          past=Hex(5,5)  present=Hex(6,5)  future=Hex(7,5)

        Each turn we apply 1G of SW thrust (direction 3 — opposite of NE).

        Turn 1 trace:
          advance()       → past=Hex(6,5)  present=Hex(7,5)  future=Hex(8,5)
          thrust SW       → future=Hex(7,5)
          speed = distance(Hex(6,5), Hex(7,5)) = 1  ← still moving right

        Turn 2 trace:
          advance()       → past=Hex(7,5)  present=Hex(7,5)  future=Hex(7,5)
          thrust SW       → future=Hex(6,5)
          speed = distance(Hex(7,5), Hex(7,5)) = 0  ← ship stopped

        Turn 3 trace:
          advance()       → past=Hex(7,5)  present=Hex(6,5)  future=Hex(5,5)
          speed = distance(Hex(7,5), Hex(6,5)) = 1  ← now moving left

        The present column increases (right) in turn 1, halts in turn 2, and
        then decreases (left) in turn 3 — demonstrating that inertia requires
        three full turns to reverse a speed-1 vessel with 1G of thrust.
        """
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5), g_factor=1)

        # ── Turn 1 ──────────────────────────────────────────────────────────
        v.advance()
        self.assertEqual(v.present, Hex(7, 5),
                         "Turn 1: ship advances right despite opposing thrust")
        v.apply_thrust(3)   # SW
        self.assertEqual(v.speed, 1,
                         "Turn 1: speed is still 1 after advance — inertia")

        # ── Turn 2 ──────────────────────────────────────────────────────────
        v.advance()
        self.assertEqual(v.speed, 0,
                         "Turn 2: ship has slowed to a stop")
        self.assertEqual(v.present, Hex(7, 5),
                         "Turn 2: present did not advance (speed was 0 entering)")
        v.apply_thrust(3)   # SW

        # ── Turn 3 ──────────────────────────────────────────────────────────
        v.advance()
        self.assertEqual(v.speed, 1,
                         "Turn 3: ship is moving again (now leftward)")
        self.assertLess(v.present.col, Hex(7, 5).col,
                        "Turn 3: present column is left of the stopped position")


class TestLanding(unittest.TestCase):

    def test_landing_collapses_all_counters_and_zeros_speed(self):
        """After land(), all three counters equal the world hex and speed is 0.

        Setup: vessel at speed 1 with present already on the world hex
        (simulates the state just before land() is called in _advance).

        land(world_hex) must set past = present = future = world_hex.
        speed = distance(world_hex, world_hex) = 0.
        """
        world_hex = Hex(5, 5)
        v = make_vessel(Hex(4, 5), world_hex, Hex(6, 5))
        self.assertEqual(v.speed, 1)   # confirm approaching at speed 1

        v.land(world_hex)

        self.assertEqual(v.past,    world_hex)
        self.assertEqual(v.present, world_hex)
        self.assertEqual(v.future,  world_hex)
        self.assertEqual(v.speed,   0)


class TestDestroyed(unittest.TestCase):

    def test_destroyed_is_false_on_init(self):
        """Vessel.destroyed is False immediately after construction."""
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5))
        self.assertFalse(v.destroyed)

    def test_destroyed_can_be_set_true(self):
        """Vessel.destroyed can be set to True (e.g. on high-speed impact)."""
        v = make_vessel(Hex(5, 5), Hex(6, 5), Hex(7, 5))
        v.destroyed = True
        self.assertTrue(v.destroyed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
