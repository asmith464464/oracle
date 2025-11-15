# Oracle Heuristic Route Planner - AI Agent GuidelinesPurpose



## Core PurposeSolve the Oracle boating puzzle under the “three colours, three shrines” brief while keeping the heuristic code lean and modular.



Solve the "Oracle boating puzzle" by computing optimal hex-grid routes that complete colour-specific tasks while building shrines opportunistically. The system uses cycle-based geographic clustering to minimize travel turns.Scenario Rules



## Architecture Overview- Exactly three colours are selected per run from `pink`, `blue`, `green`, `red`, `black`, `yellow`. In each map there should be enough representation across the tiles to be able to complete tasks for any 3 of the 6 colours.

- For each colour there should be: 2 different monster tiles, 2 different offerings, 3 different statue islands, only one temple, only one statue source tile that you can visit. For shrines, colour is irrelevant, you can build a shrine on any colour shrine tile.

### Pipeline Flow- For each of the 3 chosen colours, must complete the following tasks: 1 monster to defeat, 1 offering to collect, 1 statue to load, 1 statue island to deliver to, and 1 temple for the offering delivery. Extra tiles of the same type exist but only one needs to be visited for the assigned colour.

```- Tiles can belong to multiple colours. A task is valid only when its colour appears in the tile's `colours` list. Statue islands are always 3 colours, offerings are always 2 colours, monsters can be either 1 or 2 colours.

HexGrid → TaskManager → CycleHeuristic → ShrineOptimizer → RouteSimulator → Visualizer- Exact tile distribution for all 6 colours:

  (map)     (selection)    (routing)      (insertion)        (validation)     (optional)  - Monster tiles: 9 total (6 with 1 colour, 3 with 2 colours) = 2 available per colour

```  - Offering tiles: 6 total (each with exactly 2 colours) = 2 available per colour

  - Statue source tiles: 6 total (each with exactly 1 colour) = 1 per colour

**Critical separation**: Heuristic generates routes purely from spatial/dependency constraints. Simulator validates legality and tracks state changes. Visualizer consumes output without influencing decisions.  - Temple tiles: 6 total (each with exactly 1 colour) = 1 per colour

  - Statue island tiles: 6 total (each with exactly 3 colours) = 3 available per colour

### Core Components  - Shrine tiles: 3 total (no colours)

  - Zeus tile: 1 (starting/ending position, no tasks)

- **`HexGrid`** (`map_model.py`): Graph of hex tiles with `Tile` nodes (water=traversable, land=tasks). Each tile has `coords`, `tile_type`, `colours` tuple, and `neighbors` list. Zeus tile marks start/end.- The boat moves exclusively on water hexes, up to three steps per turn, and interacts with adjacent land tiles.

- The ship carries at most two cargo items (statues or offerings). Task sequencing must respect this capacity.

- **`TaskManager`** (`tasks.py`): Selects exactly one tile per required task type per colour. Tracks dependencies (e.g., statue pickup before delivery), cargo state via `PlayerState`, and shrine requirements.- Core objectives: defeat three monsters, deliver three statues, deliver three offerings, build three shrines (any colour shrine tiles), and finish back at the Zeus tile.



- **`CycleHeuristic`** (`heuristic.py`): Clusters tasks by hex-coordinate proximity into `TaskCycle` objects. Uses `CYCLE_DISTANCE_THRESHOLD=6` and `MAX_CYCLE_TASKS=5` for balanced spatial grouping. Connects cycles with shortest paths. Ignores cargo during clustering for clean separation.Cycle Planning Heuristic



- **`ShrineOptimizer`** (`shrine_optimizer.py`): Post-processes routes to insert shrines during wasted moves (when <3 moves remain in turn). Delegates logic to `shrine_logic.py` functions.- `TaskManager` pre-selects the required tasks for the chosen colours and tracks dependencies.

- `CycleHeuristic` builds localized **cycles**: it anchors on the first task in a cycle and only adds further tasks whose water-access distance stays within the cycle distance threshold and whose execution is feasible for the current cargo state.

- **`RouteSimulator`** (`simulator.py`): Step-by-step route execution. Validates moves are adjacent water tiles, executes tasks when adjacent to land tiles, enforces cargo capacity (max 2 items), and confirms all objectives met.- When the next candidate lies beyond the threshold or the cycle reaches the task cap, the cycle closes and a new one begins. Single-task cycles are acceptable when tasks are isolated.

- Cycles connect via longer legs; connectors should not overlap visually with the cycle’s internal path.

- **`DistanceCalculator`** (`distance_utils.py`): Cached A* pathfinding on water tiles using NetworkX. All route planning uses this—never Manhattan distance for actual paths.

Visualization Expectations

### Data Flow Patterns

- Visual outputs must never influence heuristic choices. They consume the solved data only.

1. **Task Selection**: `TaskManager.select_tasks_for_colours()` deterministically picks first tile (sorted by ID) for each task type per colour.- Multi-colour tiles show segmented borders coloured per tile `colours` entry. Cycle connectors render as dotted lines with a contrasting outline to avoid blending with the main route.

- The solver must function without any graphical output.

2. **Cycle Formation**: `CycleHeuristic._cluster_tasks_by_proximity()` uses k-means-like spatial clustering on hex coordinates, then `_build_route_with_cycles()` visits tasks within each cluster greedily by distance.

Development Principles

3. **Multi-colour Tiles**: Tasks exist per colour on a tile. Visiting a tile completes all its tasks simultaneously (see `_build_route_with_cycles` where `tasks_by_tile` aggregates all tasks).

1. Keep heuristic logic separate from data loading, simulation, and rendering utilities. Avoid circular dependencies and shared mutable globals.

4. **Route Repair**: `repair_route()` fixes non-adjacent moves by inserting shortest paths. Called after cycle formation and after shrine insertion.2. Prefer straightforward, declarative code. Reuse existing helpers instead of reimplementing standard-library behaviour.

3. Keep functions short and purposeful with descriptive names and minimal parameters. Document intent with concise docstrings and targeted inline comments.

## Scenario Rules4. Implement changes incrementally; optimise only when a proven need arises.

5. Ensure the entire system (heuristic + simulator) runs headless, including shrine placement, reporting, and exports.
### Tile Distribution (All 6 Colours)
- **Monster tiles**: 9 total (6 with 1 colour, 3 with 2 colours) = 2 available per colour
- **Offering tiles**: 6 total (each with exactly 2 colours) = 2 available per colour
- **Statue source tiles**: 6 total (each with exactly 1 colour) = 1 per colour
- **Temple tiles**: 6 total (each with exactly 1 colour) = 1 per colour
- **Statue island tiles**: 6 total (each with exactly 3 colours) = 3 available per colour
- **Shrine tiles**: 3 total (no colours—any can be used)
- **Zeus tile**: 1 (starting/ending position, no tasks)

### Per-Run Requirements (3 Selected Colours)
For each chosen colour, complete:
1. Defeat 1 monster (pick from 2 available tiles)
2. Collect 1 offering (pick from 2 available tiles)
3. Pick up 1 statue from statue source (only 1 tile available)
4. Deliver statue to 1 statue island (pick from 3 available)
5. Deliver offering to 1 temple (only 1 tile available)

Plus: Build 3 shrines (any of the 3 shrine tiles) and return to Zeus.

### Movement & Cargo
- Boat moves on water tiles only, up to 3 moves per turn
- Tasks execute when adjacent to land tiles
- Cargo capacity: 2 items max (statues or offerings)
- Dependencies: must pick up before delivering

## Development Workflows

### Running the System
```powershell
# Standard run with visualization
python main.py --generate-map --seed 42 --visualize

# Custom colours (must have required tiles)
python main.py --colours red blue green --seed 42

# Custom cycles (override clustering heuristic)
python main.py --cycles-file test_cycles.json

# Save results for analysis
python main.py --seed 42 --save-results output.json
```

### Map Generation
Use `create_example_map()` in `utils.py` to generate valid maps. Ensures:
- Correct tile distribution per colour (see counts above)
- Water connectivity via graph traversal
- Task accessibility via `ensure_task_accessibility()` (every land tile has ≥1 adjacent water)

Validation: `HexGrid.validate_grid()` returns list of issues or empty list if valid.

### Debugging Routes
- `RouteSimulator.simulation_result.errors` lists validation failures
- `--visualize` shows cycle boundaries (solid) vs. connectors (dotted)
- Check `completed_tasks` vs `selected_tasks` in results JSON
- Verify cargo state throughout with `player_state_snapshot` in each `SimulationStep`

## Key Conventions

### Tile Identification
- **Tile IDs**: Strings like `"tile_042"`. Never use integer indices.
- **Colours**: Immutable tuples in `Tile.colours`. Check membership: `colour in tile.colours`
- **Types**: `TileType` enum—`WATER` is traversable; others are tasks

### Task IDs
Format: `"{tile_id}:{task_type}:{colour}"` (e.g., `"tile_042:monster:red"`)
- Multi-colour tiles generate separate tasks per colour
- Use `TaskManager.get_tasks_for_tile()` to get all tasks at a location

### Pathfinding Rules
- **For actual routes**: Always use `DistanceCalculator.get_shortest_path(from_id, to_id)` 
- **For clustering only**: `_task_land_distance()` computes hex coordinate distance
- Never compute routes with Manhattan distance—use A* on water graph

### Determinism
When `--seed` is set:
- Task selection sorts candidates by `tile.id` and picks first
- Clustering breaks ties by smallest index
- Colour generation uses sorted order instead of `random.sample`

### Cargo Management
```python
# CargoItem is immutable; PlayerState.cargo is a list
player_state.add_cargo(CargoItem("statue", "red"))
player_state.remove_cargo("statue", "red")  # First match removed
player_state.cargo_full()  # True when len(cargo) == 2
```

## Critical Patterns

### Cycle vs. Connector Distinction
```python
# TaskCycle structure:
cycle.internal_route      # Tiles visited within the cycle
cycle.connector_to_next   # Path from this cycle's exit to next cycle's entry
cycle.entry_index         # Where cycle starts in full route
cycle.exit_index          # Where cycle ends in full route
```

Visualizer renders these differently (solid vs dotted) to show geographic clustering.

### Route Repair Process
After generating routes or inserting shrines, always call:
```python
repaired_route = repair_route(grid, distance_calc, route)
```

This fixes non-adjacent jumps by inserting shortest paths. Called in:
- `CycleHeuristic.solve()` after cycle formation
- `ShrineOptimizer.optimize_shrine_placement()` after insertion

### Multi-Colour Task Execution
When boat is adjacent to a multi-colour tile:
```python
# Simulator checks all tasks for that tile
for task in task_manager.get_tasks_for_tile(neighbor_id):
    if task.can_execute(player_state.completed_task_ids):
        task_manager.execute_task(task, player_state)
```

All valid tasks execute in a single step.

## Common Pitfalls

1. **Clustering distance ≠ pathfinding distance**: Hex coordinate distance is for k-means spatial grouping only. Actual route segments use A* through water tiles.

2. **Shrines modify route length**: After `ShrineOptimizer`, route may be longer. Always re-check Zeus return and re-run `repair_route()`.

3. **Custom cycles must include all tasks**: When using `--cycles` or `--cycles-file`, every task tile selected by `TaskManager` must appear in exactly one cycle.

4. **Tile validation before task execution**: Simulator checks `tile_id in current_tile.neighbors` and that target colour is in `tile.colours` tuple.

5. **Seed affects multiple stages**: Random seed controls colour selection, map generation, and task selection. Without seed, results are non-deterministic.

## Code Style

- Functions <50 lines with single responsibility
- Descriptive names: `_cluster_tasks_by_proximity` not `_cluster`
- Type hints on all public APIs: `def solve() -> Tuple[List[str], Dict]:`
- Dataclasses for structured data (`@dataclass` for `Task`, `Tile`, `PlayerState`, etc.)
- Validation returns `(bool, List[str])` for success + error messages
- Avoid mutable default arguments; use `field(default_factory=list)`

## Integration Points

### Map I/O
```python
# Load with automatic neighbor inference
grid = HexGrid.from_json("map.json")

# Save (optionally exclude neighbors if inferrable from coords)
grid.to_json("output.json", include_neighbors=False)
```

### Task Dependencies
```python
# Set during task creation in TaskManager.select_tasks_for_colours()
statue_island_task = Task(
    dependencies=[statue_source_task.id]  # Must pick up first
)

# Checked during execution
if task.can_execute(player_state.completed_task_ids):
    # All dependencies in completed set
```

### Simulation Output
```python
result = simulator.simulate_route(route, shrine_positions)
# result.success: bool
# result.errors: List[str]
# result.steps: List[SimulationStep] with action_type in ['move', 'task', 'shrine', 'error']
# result.final_player_state: PlayerState with cargo, completed_task_ids, etc.
```

### Statistics & Metrics
Results include:
- `total_moves` / `total_turns` (turns = ceil(moves / 3))
- `cycles_formed`, `tasks_per_cycle`, `cycle_distances`
- `efficiency_metrics`: moves/turn ratio, task density, etc.

## Project Structure
```
src/
├── map_model.py          # HexGrid, Tile, TileType
├── tasks.py              # TaskManager, Task, PlayerState, CargoItem
├── heuristic.py          # CycleHeuristic (main route planning)
├── heuristic_models.py   # TaskCycle dataclass
├── distance_utils.py     # DistanceCalculator (A* pathfinding)
├── route_utils.py        # repair_route, append_path
├── shrine_optimizer.py   # ShrineOptimizer (coordinator)
├── shrine_logic.py       # Shrine insertion algorithms
├── shrine_models.py      # ShrineOpportunity dataclass
├── simulator.py          # RouteSimulator, validation
├── simulator_models.py   # SimulationResult, SimulationStep
├── visualizer.py         # HexGridVisualizer (optional)
└── utils.py              # Map generation, logging, helpers
```

`main.py` orchestrates the full pipeline. Modify heuristics in `heuristic.py`, task logic in `tasks.py`, or shrine insertion in `shrine_logic.py`.
