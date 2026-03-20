# hexvector — CLAUDE.md

## What This Is

A standalone hex-grid vector movement engine with gravity well support,
extracted from a larger project. This is a physics sandbox, not a game.
It demonstrates Newtonian vector mechanics on a hex grid: momentum,
thrust, and gravitational deflection near planetary bodies.

This project was inspired by the vector movement system in Mayday
(Game Designers' Workshop, 1978), a science fiction board game of
spaceship combat.

This project is intentionally minimal. There is no combat, no weapons,
no scenarios, no factions. If you find yourself adding any of those
things, stop and check with the user first.

---

## Design Intent

This is a teaching tool, not a game. The goal is to let users discover
Newtonian vector mechanics by doing — not by reading about them. Features
should create conditions for discovery, not explain the physics explicitly.

The target hex is the primary example of this principle: the user is shown
a destination and a turn counter, nothing more. The insight that a gravity
assist reaches the target faster is meant to arrive as a surprise. Do not
add features that explain or hint at the optimal path.

---

## Dependencies
```
pygame==2.6.1
pillow==12.1.1
```

Python 3.12. Install with:
```
pip install -r requirements.txt
```

---

## Physics Model

**Three-counter vector system:**
Each ship has three position markers: past, present, and future.
- Past and present define the current velocity vector
- Extending past→present forward by the same distance gives the
  natural future position (momentum, no thrust required)
- Thrust shifts the future marker up to G hexes in any direction

**Thrust:**
A ship's drives are rated in G — units of acceleration. Each G allows
the pilot to shift the future position marker one hex in any direction
from its current position. A 1G ship may shift the future marker one
hex per turn; a 2G ship may shift it up to two hexes (in any
combination of directions). This shift is applied after the natural
future position is calculated from momentum — thrust moves the future
marker from wherever momentum placed it, not from the present position.

For the purposes of this project, ships have a G rating of 1 unless
otherwise specified.

**Gravity:**
Worlds occupy a single hex. The six surrounding hexes are gravity hexes.
When a ship's present→future path crosses a gravity hex, the future
marker is displaced one hex toward the world. This is:
- Mandatory — the pilot cannot resist it
- Cumulative — crossing two gravity hexes displaces twice
- Applied to the upcoming move (present→future path), not the
  completed move (past→present path)

**Landing:**
A ship may land on a world by moving onto the world hex at speed 1
(one hex per turn). On landing, all three counters collapse to the
world hex — past, present, and future are all set to the world hex,
velocity resets to zero.

**Launching:**
A landed ship (all three counters on world hex, speed 0) may apply
thrust to an adjacent hex as its future position. The ship is now
committed to entering a gravity hex on the next move.

---

## Architecture
```
core/
  hex_grid.py         # Hex math: distance, neighbors, pixel conversion,
                      #   hex_line, best_direction_toward, hexes_within
  vector_movement.py  # Vessel class: past/present/future, advance(),
                      #   apply_thrust(), speed, thrust_remaining
  world.py            # World class: gravity hexes, apply_gravity()
ui/
  renderer.py         # Pygame renderer: hex grid, vessel overlay,
                      #   gravity visualization, thrust hints, HUD
main.py               # Game loop, input handling
tests/
  test_hex_grid.py
  test_vector_movement.py
```

---

## What Is and Isn't In Scope

**In scope:**
- Hex grid rendering and interaction
- Vector movement for one ship
- Gravity well deflection
- Thrust hint visualization (reachable future hexes)
- World placement
- Landing and launching
- Ship destruction on high-speed planetary impact (speed > 1 hex/turn)
- Target hex: a destination marker with arrival detection
- Turn counter in HUD

**Out of scope — do not add without explicit direction:**
- Combat of any kind
- Weapons, missiles, damage
- Computer programs or ship stats
- Scenarios or victory conditions
- Factions or named ship types
- Any content derived from Mayday or Traveller rules text

---

## IP Notes

This project was inspired by the vector movement system in Mayday
(Game Designers' Workshop, 1978). The physics — Newtonian mechanics
on a hex grid — is not owned by anyone. No rules text, tables, ship
statistics, or scenario content from any copyrighted game is
reproduced here.

The Traveller game in all forms is owned by Mongoose Publishing.
Copyright 1977–2025 Mongoose Publishing. Traveller is a registered
trademark of Mongoose Publishing.

This project is non-commercial. See README.md for full disclaimer.

---

## Aesthetic

- Dark near-black background
- Dark green hex grid
- Monospaced terminal typography
- Radar/scope feel — not a video game, not a paper map
- Past position: dark fill
- Present position: bright fill
- Future position: outline only
- Gravity hexes: dark orange fill with directional arrows toward world
- Thrust hints: bright outlined ring of reachable hexes

This aesthetic is settled. Do not revise it without direction.

---

## Working Notes

- Hex coordinates are odd-r offset: Hex(col, row)
- Pointy-top hex orientation
- `hex_line(a, b)` traces the path between two hexes — critical for
  gravity calculation
- Gravity is applied against the present→future path, not past→present
- All three counters must be collapsed to world hex on landing
- The thrust hint disk is `hexes_within(natural_future, g_factor)`
  minus the natural future hex itself
  
---

## Working Style (for Claude)

- You have permission to make and run edits without asking for confirmation
  on each step. Prefer action over check-ins for routine operations.
- Fixing whitespace, comment formatting, and newline style is always
  pre-approved. Do it without prompting.
- If you break something, say so clearly and fix it. Don't ask permission
  to attempt a fix.
- Only pause and ask when you hit a genuine ambiguity about scope or
  intent — not for mechanical housekeeping.