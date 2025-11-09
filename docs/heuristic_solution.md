# Cycle Heuristic Overview

This document summarizes how the current heuristic assembles routes for the Oracle boating scenario. The focus is on `src/heuristic.py`, with supporting references to the distance and task utilities.

## High-Level Flow

`CycleHeuristic.solve` orchestrates the solution:

1. **Route planning** — `_build_route_with_cycles` walks the pending tasks, choosing the next feasible task that minimises travel from the current position while respecting cargo limits.
2. **Cycle formation** — the same loop grows a `TaskCycle` around an anchor tile; the cycle closes when the next task lies beyond the distance threshold or the cycle hits the task cap.
3. **Route repair** — `repair_route` (from `src/route_utils.py`) enforces water adjacency both before and after `_ensure_return_to_zeus` appends the closing leg.
4. **Statistics** — `_calculate_statistics` records movement totals and cycle composition for downstream reporting and visualisation.

The solver returns the final route plus the statistics dictionary; `self.cycles` holds the cycle metadata for visualisation.

## Route Planning and Cycle Grouping

`_build_route_with_cycles` maintains:

- `pending`: the tasks chosen by `TaskManager.select_tasks_for_colours`.
- `_PlanningState`: a lightweight inventory mirror of the simulator (two cargo slots, dependency tracking).
- `current_cycle`: an in-progress `TaskCycle` and its partial route segment.
- `cycle_anchor_tile`: the tile id that seeds the current cycle.

Each iteration:

1. Filters pending tasks to those whose dependencies are satisfied and whose execution fits the current cargo (`_state_allows_task`).
2. Invokes `_select_next_task`, which applies two rules:
	- Only consider tasks within the cycle distance threshold of the anchor (unless starting a new cycle).
	- Prefer the candidate with the shortest water path from the boat, using `_best_path_to_task` and `DistanceCalculator` to probe adjacent water tiles.
3. Appends the chosen path via `append_path`, updates the planning state through `_apply_task_effects`, and removes the task from `pending`.

If the next candidate violates the distance threshold or the cycle already contains `MAX_CYCLE_TASKS` tasks, `_finalize_cycle` snapshots the working data into a `TaskCycle`, resets the anchor, and starts a new cycle. This approach allows single-task cycles for isolated tiles while keeping dense pockets together.

### Distance Caching

`_task_land_distance` caches the shortest water distance between task tiles so repeated anchor checks stay cheap. Distances include the nearest water tiles surrounding each task.

## Route Repair and Realignment

After the initial pass, `solve`:

1. Calls `repair_route` to fill any water gaps introduced by straight-line planning.
2. Ensures the trip returns to Zeus with `_ensure_return_to_zeus` and runs `repair_route` again.
3. Uses `_realign_cycles_to_route` to recalculate each cycle’s entry/exit indices against the repaired route so visualisers display the correct segments.

## Statistics and Reporting

`_calculate_statistics` reports:

- `total_moves`, `total_turns`, `route_length` — movement metrics.
- `cycles_formed`, `tasks_per_cycle`, `cycle_distances` — composition metrics for each cycle.

`get_cycle_summary` exposes a serialisable view of every `TaskCycle` (id, task list, colours present, entry/exit tiles, distance) for visualisation and exports.

## Related Components

- `src/tasks.py` — `TaskManager` selects tasks per colour, applies dependency rules, and exposes tile lookups.
- `src/distance_utils.py` — `DistanceCalculator` wraps NetworkX shortest-path queries for water tiles and adjacency discovery.
- `src/route_utils.py` — `append_path` and `repair_route` guarantee valid water traversal.

Together these modules keep the heuristic self-contained: planning logic lives in `CycleHeuristic`, data access stays in model/manager classes, and rendering logic remains optional in `src/visualizer.py`.