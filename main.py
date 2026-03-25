"""
hexvector — entry point.

Opens a window showing a single vessel on a hex grid with one world.
Demonstrates momentum counters, gravity hexes, and thrust hints.

Controls
--------
Click thrust hint hex   aim future position (thrust)
Space / Enter           advance turn (coast if no thrust applied)
Escape                  reset scenario
D                       toggle hex coordinate labels
Q                       quit
"""

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # allow headless import

import pygame
from core.hex_grid import Hex, extend_vector, hexes_within
from core.vector_movement import Vessel
from core.world import World
from ui.renderer import Renderer

WIDTH, HEIGHT = 1200, 900

# Target hex: northeast of the world, positioned to reward a gravity-assist
# approach from the west.  Hex(18, 4) is 7 hexes from the world (Hex(10,7))
# and lies above and to the right — reachable direct or via north-side slingshot.
TARGET_HEX = Hex(18, 4)


def _build_scene() -> tuple[Vessel, World]:
    """Create the initial vessel and world for the demo."""
    # World at grid centre (col 10, row 7 on a 20×15 grid)
    world = World(Hex(10, 7), name="")

    # Vessel moving east, well west of the world
    past    = Hex(3, 7)
    present = Hex(4, 7)
    future  = extend_vector(past, present)   # Hex(5, 7) — momentum carries it east
    vessel  = Vessel(past, present, future, g_factor=1)

    return vessel, world


def _natural_future(vessel: Vessel) -> Hex:
    """Return the post-gravity, pre-thrust future (or geometric extension at start)."""
    if vessel.natural_future is not None:
        return vessel.natural_future
    return extend_vector(vessel.past, vessel.present)


def _thrust_hints(vessel: Vessel) -> set[Hex]:
    """Return the ring of hexes reachable by thrust from natural future."""
    center = _natural_future(vessel)
    return hexes_within(center, vessel.g_factor) - {center}


def _advance(vessel: Vessel, world: World) -> set[Hex]:
    """
    Execute one full turn cycle:
      1. Advance counters (momentum)
      2. Apply gravity to the new present→future path
      3. Detect landing (speed 1) or impact (speed > 1) on world hex
      4. Save post-gravity future as natural_future
      5. Return fresh thrust hints (empty if destroyed)
    """
    vessel.advance()
    world.apply_gravity(vessel)
    if vessel.present == world.position:
        if vessel.speed == 1:
            vessel.land(world.position)
        elif vessel.speed > 1:
            vessel.destroyed = True
            return set()
    vessel.natural_future = vessel.future   # post-gravity, pre-thrust anchor
    return _thrust_hints(vessel)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("hexvector")
    clock  = pygame.time.Clock()

    vessel, world = _build_scene()
    renderer = Renderer(screen)

    # Seed natural_future so hints render correctly before the first advance
    vessel.natural_future = vessel.future
    hints = _thrust_hints(vessel)
    turn = 0
    target_reached = False

    running = True
    while running:
        frozen = vessel.destroyed or target_reached

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not frozen:
                    clicked = renderer.hex_at(event.pos)
                    valid   = hints | {_natural_future(vessel)}
                    if clicked in valid:
                        vessel.future = clicked

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if not frozen:
                        hints = _advance(vessel, world)
                        turn += 1
                        if vessel.present == TARGET_HEX and not vessel.destroyed:
                            target_reached = True
                            hints = set()
                elif event.key == pygame.K_ESCAPE:
                    vessel, world = _build_scene()
                    vessel.natural_future = vessel.future
                    hints = _thrust_hints(vessel)
                    turn = 0
                    target_reached = False
                elif event.key == pygame.K_d:
                    renderer.toggle_labels()
                elif event.key == pygame.K_q:
                    running = False

        renderer.draw([vessel], [world], thrust_hints=hints)
        renderer.draw_target(TARGET_HEX)
        renderer.draw_hud(vessel, "1G Scout", turn, target_reached)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    # Remove the headless override so a real display is used when run directly
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        del os.environ["SDL_VIDEODRIVER"]
    main()
