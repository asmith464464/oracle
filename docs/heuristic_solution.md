# Heuristic Overview

This document describes how the current heuristic builds routes for the Oracle boating puzzle. The algorithm is implemented in `src/heuristic.py`.

## High-Level Flow

The `CycleHeuristic.solve()` method orchestrates the solution in 6 clear steps:

1. **Start at Zeus** — Initialize route at the starting tile (tile_043)
2. **Load cycles** — Import cycle definitions from `src/cycles.py`
3. **Build route** — Visit each cycle's tiles sequentially using shortest water paths
4. **Repair route** — Fill any gaps between non-adjacent tiles
5. **Return to Zeus** — Ensure the route ends at the starting tile
6. **Calculate statistics** — Compute moves, turns, and cycle metrics

After the route is built, the `add_shrines_to_route()` function adds 3 hardcoded shrines and returns to Zeus.

## Cycle Definitions

Cycles are defined in **`src/cycles.py`** as a simple list of lists:

```python
CYCLE_DEFINITIONS = [
    ["tile_105", "tile_009", "tile_007", "tile_108", "tile_005"],  # Green tasks
    ["tile_020", "tile_053", "tile_071", "tile_063", "tile_112"],  # Pink tasks
    ["tile_028", "tile_061", "tile_094", "tile_077", "tile_015"],  # Blue tasks
]
```

Each cycle is visited in order. Within each cycle, tiles are visited in the exact order specified.

## Route Building Algorithm

For each cycle:

1. Start from the current boat position
2. For each task tile in the cycle (in order):
   - Find the shortest water path to an adjacent water tile
   - Append this path to the route
   - Update current position
3. Store the cycle's internal route for visualization

The route builder uses `RouteBuilder.best_path_to_task()` which:
- Finds all water tiles adjacent to the target land tile
- Computes shortest paths from current position to each adjacent water tile
- Returns the shortest path found

## Path Finding

All pathfinding uses `DistanceCalculator` from `src/grid.py`, which wraps NetworkX's shortest path algorithm. The calculator works only with water tiles, since the boat can only travel on water.

## Route Repair

After building the initial route, gaps may exist where consecutive tiles aren't adjacent (due to how paths are concatenated). The repair step:

1. Walks through the route
2. When two consecutive tiles aren't adjacent, inserts the shortest path between them
3. Ensures all tiles in the final route are properly connected

## Shrine Insertion

The `add_shrines_to_route()` function (replacing the old `ShrineOptimiser`):

1. Takes 3 hardcoded shrine tiles from `SHRINE_TILES` in `cycles.py`
2. Filters out any already visited during the cycle route
3. Appends shortest paths to the first 3 unvisited shrines
4. Returns to Zeus

This is much simpler than the old optimization logic and makes the code easier to understand and modify.

## Statistics

The solver computes:
- `total_moves` — Total number of tile-to-tile movements
- `total_turns` — Moves divided by 3 (rounded up)
- `route_length` — Number of tiles in the route
- `cycles_formed` — Number of cycles (always 3 for map1.json)
- `tasks_per_cycle` — Task count in each cycle
- `cycle_distances` — Length of each cycle's internal route

## Related Components

- **`src/cycles.py`** — Cycle definitions (modify here to experiment)
- **`src/tasks.py`** — Task creation, dependencies, and cargo management
- **`src/simulator.py`** — Route validation and execution
- **`src/grid.py`** — Map representation and pathfinding utilities
- **`src/visualiser.py`** — Optional visualization (does not affect routing)
