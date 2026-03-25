"""
Vector movement for a hex-grid physics sandbox.

Each turn a vessel executes these steps:
  A. past    ← present
  B. present ← future
  C. future  ← extend(past→present vector)   [automatic momentum]
  D. apply_thrust(direction) up to G times    [optional course change]

Gravity (applied before thrust) is handled in world.py.
"""

from core.hex_grid import Hex, extend_vector, step, distance


class Vessel:
    """
    A ship tracked by three hex counters.

    Attributes
    ----------
    past, present, future : Hex
        The three position counters.
    g_factor : int
        Maximum thrust hexes available per turn.
    thrust_used : int
        Thrust hexes already applied this turn.
    natural_future : Hex | None
        Post-gravity, pre-thrust future for this turn.  Set after all
        gravity displacement has been applied; used by thrust-hint display
        so hints stay anchored on the gravity-corrected position.
    """

    def __init__(self, past: Hex, present: Hex, future: Hex,
                 g_factor: int = 1):
        self.past = past
        self.present = present
        self.future = future
        self.g_factor = g_factor
        self.thrust_used = 0
        self.natural_future: Hex | None = None
        self.destroyed: bool = False

    # ── movement ────────────────────────────────────────────────────────────

    def advance(self) -> None:
        """
        Execute movement steps A–C (momentum):
          A. past    ← present
          B. present ← future
          C. future  ← extend(past→present vector)

        Resets the thrust budget for the new turn.
        """
        new_past    = self.present
        new_present = self.future
        new_future  = extend_vector(self.present, self.future)

        self.past    = new_past
        self.present = new_present
        self.future  = new_future
        self.thrust_used = 0

    def land(self, world_hex: Hex) -> None:
        """Collapse all three counters to the world hex. Velocity becomes zero."""
        self.past    = world_hex
        self.present = world_hex
        self.future  = world_hex
        self.thrust_used = 0

    def apply_thrust(self, direction: int) -> bool:
        """
        Step D: deflect the future counter one hex in direction (0–5).

        Returns True if thrust was applied; False if G budget is exhausted.
        Directions: 0=NE, 1=E, 2=SE, 3=SW, 4=W, 5=NW
        """
        if self.thrust_used >= self.g_factor:
            return False
        self.future = step(self.future, direction)
        self.thrust_used += 1
        return True

    # ── derived properties ───────────────────────────────────────────────────

    @property
    def thrust_remaining(self) -> int:
        return self.g_factor - self.thrust_used

    @property
    def speed(self) -> int:
        """Hexes moved per turn (distance from past to present)."""
        return distance(self.past, self.present)
