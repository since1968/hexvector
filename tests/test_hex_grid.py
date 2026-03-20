"""
Tests for core/hex_grid.py — hex distance and neighbour functions.

Run with:
    python3 -m unittest tests/test_hex_grid.py -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.hex_grid import Hex, distance, neighbors, hexes_within, best_direction_toward


class TestHexDistance(unittest.TestCase):

    # ── TEST 1 ────────────────────────────────────────────────────────────────

    def test_distance_to_self_is_zero(self):
        """Distance from any hex to itself is 0."""
        self.assertEqual(distance(Hex(0, 0), Hex(0, 0)), 0)
        self.assertEqual(distance(Hex(5, 5), Hex(5, 5)), 0)
        self.assertEqual(distance(Hex(19, 13), Hex(19, 13)), 0)

    # ── TEST 2 ────────────────────────────────────────────────────────────────

    def test_distance_to_all_six_neighbors_is_one(self):
        """Every hex returned by neighbors() is exactly 1 step away.

        Uses Hex(5, 4) (even row) as the origin.  The six neighbours in
        odd-r offset coordinates are:
          Hex(6,4)  Hex(5,3)  Hex(4,3)
          Hex(4,4)  Hex(4,5)  Hex(5,5)
        """
        origin = Hex(5, 4)
        expected_neighbors = [
            Hex(6, 4),  # NE
            Hex(5, 3),  # E
            Hex(4, 3),  # SE
            Hex(4, 4),  # SW
            Hex(4, 5),  # W
            Hex(5, 5),  # NW
        ]
        for n in expected_neighbors:
            with self.subTest(neighbor=n):
                self.assertEqual(distance(origin, n), 1)

    # ── TEST 3 ────────────────────────────────────────────────────────────────

    def test_distance_is_symmetric(self):
        """distance(A, B) == distance(B, A) for non-adjacent pairs."""
        pairs = [
            (Hex(0, 0),  Hex(10, 7)),
            (Hex(3, 2),  Hex(8, 9)),
            (Hex(1, 1),  Hex(15, 10)),
            (Hex(0, 13), Hex(19, 0)),
        ]
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertEqual(distance(a, b), distance(b, a))

    # ── TEST 4 ────────────────────────────────────────────────────────────────

    def test_distance_across_grid(self):
        """Distance between opposite corners of a 20×14 grid is 26.

        Hex(0, 0)  → cube (0, 0, 0)
        Hex(19,13) → cube (13, −26, 13)
        distance   = (|0−13| + |0−(−26)| + |0−13|) / 2
                   = (13 + 26 + 13) / 2 = 26
        """
        self.assertEqual(distance(Hex(0, 0), Hex(19, 13)), 26)

    def test_distance_known_pairs(self):
        """Spot-check several manually computed distances."""
        # Hex(0,0)→Hex(10,7): cube(0,0,0)→(7,−14,7); dist=(7+14+7)/2=14
        self.assertEqual(distance(Hex(0, 0),  Hex(10, 7)), 14)
        # Hex(3,2)→Hex(8,9): cube(2,−4,2)→(4,−13,9); dist=(2+9+7)/2=9
        self.assertEqual(distance(Hex(3, 2),  Hex(8, 9)),   9)
        # Hex(1,1)→Hex(15,10): cube(1,−2,1)→(10,−20,10); dist=(9+18+9)/2=18
        self.assertEqual(distance(Hex(1, 1),  Hex(15, 10)), 18)

    # ── TEST 5 ────────────────────────────────────────────────────────────────

    def test_distance_is_always_non_negative(self):
        """distance() never returns a negative value regardless of direction."""
        pairs = [
            (Hex(10, 7), Hex(0,  0)),   # upper-left of origin
            (Hex(10, 7), Hex(19, 0)),   # upper-right
            (Hex(10, 7), Hex(0,  13)),  # lower-left
            (Hex(10, 7), Hex(19, 13)),  # lower-right
            (Hex(10, 7), Hex(10, 0)),   # directly above
            (Hex(10, 7), Hex(10, 13)),  # directly below
        ]
        for a, b in pairs:
            with self.subTest(a=a, b=b):
                self.assertGreaterEqual(distance(a, b), 0)

    # ── TEST 6 ────────────────────────────────────────────────────────────────

    def test_neighbors_returns_exactly_six(self):
        """neighbors() always returns a list of exactly 6 hexes."""
        self.assertEqual(len(neighbors(Hex(10, 7))),  6)
        self.assertEqual(len(neighbors(Hex(5,  4))),  6)
        self.assertEqual(len(neighbors(Hex(0,  0))),  6)
        self.assertEqual(len(neighbors(Hex(19, 13))), 6)

    # ── TEST 7 ────────────────────────────────────────────────────────────────

    def test_edge_hex_neighbors_include_off_grid(self):
        """neighbors() does not clip to grid boundaries.

        The implementation returns all 6 geometric neighbours unconditionally.
        For a corner hex like Hex(0, 0) several neighbours have negative
        coordinates and lie outside the 20×14 playing area.

        Hex(0, 0) neighbours in odd-r offset:
          Hex( 1,  0)  — on grid
          Hex( 0, -1)  — off grid (row < 0)
          Hex(-1, -1)  — off grid
          Hex(-1,  0)  — off grid (col < 0)
          Hex(-1,  1)  — off grid
          Hex( 0,  1)  — on grid
        """
        result = neighbors(Hex(0, 0))
        self.assertEqual(len(result), 6)

        on_grid  = [h for h in result if h.col >= 0 and h.row >= 0]
        off_grid = [h for h in result if h.col < 0  or h.row < 0]

        # Two neighbours are within the grid, four are outside it.
        self.assertEqual(len(on_grid),  2)
        self.assertEqual(len(off_grid), 4)

        # The two valid neighbours are confirmed.
        self.assertIn(Hex(1, 0), on_grid)
        self.assertIn(Hex(0, 1), on_grid)


class TestHexesWithin(unittest.TestCase):
    """Tests for hexes_within() — the thrust-zone calculation used by the UI."""

    def test_radius_0_returns_only_center(self):
        """Radius 0 returns exactly the center hex."""
        center = Hex(5, 4)
        result = hexes_within(center, 0)
        self.assertEqual(result, {center})

    def test_radius_1_returns_center_plus_six_neighbors(self):
        """Radius 1 = center + its 6 neighbors = 7 hexes."""
        center = Hex(5, 4)
        result = hexes_within(center, 1)
        self.assertEqual(len(result), 7)
        self.assertIn(center, result)
        for n in neighbors(center):
            self.assertIn(n, result)

    def test_all_hexes_within_radius_are_at_most_that_distance(self):
        """Every hex in the result is within the requested radius."""
        center = Hex(10, 7)
        for radius in range(1, 7):   # 1G through 6G
            with self.subTest(radius=radius):
                result = hexes_within(center, radius)
                for h in result:
                    self.assertLessEqual(distance(center, h), radius)

    def test_hex_count_matches_formula(self):
        """Number of hexes within radius r = 3r² + 3r + 1."""
        center = Hex(10, 7)
        for r in range(0, 7):   # 0G through 6G
            with self.subTest(radius=r):
                expected = 3 * r * r + 3 * r + 1
                self.assertEqual(len(hexes_within(center, r)), expected)

    def test_radius_6_contains_all_hexes_at_distance_6(self):
        """All six 'corners' of the radius-6 zone are included (6G missile case)."""
        center = Hex(10, 7)
        result = hexes_within(center, 6)
        # spot-check: every neighbor of every neighbor up to depth 6 must be in set
        # just verify count and that no hex exceeds distance 6
        self.assertEqual(len(result), 3 * 36 + 3 * 6 + 1)  # 127 hexes
        for h in result:
            self.assertLessEqual(distance(center, h), 6)

    def test_reachable_zone_excludes_nothing_within_radius(self):
        """For each r, every hex at exactly distance r is included."""
        center = Hex(10, 7)
        for r in range(1, 7):
            with self.subTest(radius=r):
                zone = hexes_within(center, r)
                # build ring at distance exactly r and confirm all are present
                ring_at_r = {h for h in zone if distance(center, h) == r}
                expected_ring_size = 6 * r
                self.assertEqual(len(ring_at_r), expected_ring_size)


class TestThrustPathfinding(unittest.TestCase):
    """Tests for the click-to-future pathfinding used in the UI (issue #25).

    Verifies that best_direction_toward steps can reach any hex within G
    distance of a start hex, for G values 1 through 6.
    """

    def _path_to(self, start: Hex, goal: Hex, max_steps: int) -> list[Hex]:
        """Simulate applying best_direction_toward up to max_steps times."""
        from core.hex_grid import step
        pos = start
        path = [pos]
        for _ in range(max_steps):
            if pos == goal:
                break
            d = best_direction_toward(pos, goal)
            if d is None:
                break
            pos = step(pos, d)
            path.append(pos)
        return path

    def test_1g_can_reach_all_neighbors(self):
        """1G ship can reach all 6 neighbors of natural_future."""
        center = Hex(10, 7)
        for n in neighbors(center):
            with self.subTest(neighbor=n):
                path = self._path_to(center, n, 1)
                self.assertEqual(path[-1], n)

    def test_2g_can_reach_all_hexes_within_2(self):
        """2G ship can reach any hex within distance 2."""
        center = Hex(10, 7)
        for h in hexes_within(center, 2):
            if h == center:
                continue
            with self.subTest(target=h):
                path = self._path_to(center, h, 2)
                self.assertEqual(path[-1], h,
                    f"Could not reach {h} in 2 steps from {center}, path={path}")

    def test_4g_can_reach_all_hexes_within_4(self):
        """4G craft (Cutter, Fighter) can reach any hex within distance 4."""
        center = Hex(10, 7)
        for h in hexes_within(center, 4):
            if h == center:
                continue
            with self.subTest(target=h):
                path = self._path_to(center, h, 4)
                self.assertEqual(path[-1], h)

    def test_5g_can_reach_all_hexes_within_5(self):
        """5G craft (Pinnace) can reach any hex within distance 5."""
        center = Hex(10, 7)
        for h in hexes_within(center, 5):
            if h == center:
                continue
            with self.subTest(target=h):
                path = self._path_to(center, h, 5)
                self.assertEqual(path[-1], h)

    def test_6g_can_reach_all_hexes_within_6(self):
        """6G craft/missile can reach any hex within distance 6 (max in game)."""
        center = Hex(10, 7)
        for h in hexes_within(center, 6):
            if h == center:
                continue
            with self.subTest(target=h):
                path = self._path_to(center, h, 6)
                self.assertEqual(path[-1], h,
                    f"Could not reach {h} in 6 steps from {center}, path={path}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
