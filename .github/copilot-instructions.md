# Oracle Route Planner - Hardcoded for map1.json

## Core Purpose

Solve the Oracle boating puzzle for **map1.json only** with hardcoded colours **pink, blue, green**. This is a streamlined, single-map solver optimized for simplicity and understandability.

## The Challenge

Complete 15 tasks across 3 colours (5 tasks per colour) on a fixed hex-grid map:
- **Pink tasks**: Monster at tile_020, Offering at tile_053, Statue from tile_071, Deliver to island tile_063, Offer at temple tile_112
- **Blue tasks**: Monster at tile_028, Offering at tile_077, Statue from tile_061, Deliver to island tile_094, Offer at temple tile_015
- **Green tasks**: Monster at tile_105, Offering at tile_009, Statue from tile_108, Deliver to island tile_005, Offer at temple tile_007

Additional objectives:
- Build 3 shrines (any of the available shrine tiles)
- Return to Zeus tile (tile_043)

Boat movement:
- Travels on water tiles only, up to 3 moves per turn
- Cargo capacity: 2 items (statues or offerings)
- Tasks execute when adjacent to land tiles

## Architecture

### Hardcoded Components

**Map**: `data/maps/map1.json` - fixed 118-tile map with Zeus at tile_043

**Colours**: `["pink", "blue", "green"]` - no other colour combinations supported

**Task Selection** (`tasks.py`): Hardcoded tile IDs for all 15 tasks (5 per colour)

**Clustering** (`cycle_clustering.py`): Precomputed 4 geographic clusters:
1. Northwest: Green monster/offering/statue/temple (tiles 105, 009, 108, 007)
2. West/Center: Pink tasks (tiles 020, 053, 071, 063, 112)
3. East: Blue tasks (tiles 028, 077, 061, 094, 015)
4. North: Green statue island (tile 005)

**Validation** (`map_model.py`): Simple existence check for 15 required tiles + Zeus + 3 shrines

### Pipeline

```
load map1.json  assign red/blue/green  select 15 tasks  cluster into 4 groups  
route through clusters  insert shrines  simulate  visualize (optional)
```

**Key files**:
- `main.py` - Entry point with 3 args: --visualize, --max-shrines, --save-results
- `tasks.py` - Hardcoded task definitions and cargo management
- `cycle_clustering.py` - Fixed 4-cluster structure
- `heuristic.py` - Routes through clusters greedily
- `simulator.py` - Validates moves and task execution
- `map_model.py` - Tile graph and basic validation

### What Was Removed

- Map generation code (~140 lines from `utils.py`)
- Random colour selection
- Dynamic clustering algorithms (k-means)
- Generic grid validation
- Command-line arguments for maps/colours/seeds/cycles
- Support for arbitrary tile distributions
- Files: `debug_tasks.py`, `example_map.json`, `map2.json`

## Development Workflow

### Running

```powershell
# Basic run
python main.py

# With visualization
python main.py --visualize

# Custom shrine count
python main.py --max-shrines 5

# Save results
python main.py --save-results output.json
```

### Testing Changes

After modifying heuristic or routing code:
1. Run `python main.py --visualize` to see route visually
2. Check console output for total moves/turns
3. Verify all 15 tasks + 3 shrines completed + return to Zeus

### Common Tasks

**Modify clustering**: Edit `cluster_tasks()` in `cycle_clustering.py` to change tile groupings

**Adjust routing**: See `heuristic.py` for cycle ordering and pathfinding logic

**Change task assignments**: Update tile IDs in `select_tasks_for_colours()` in `tasks.py`

**Optimize shrine placement**: See `shrine_optimizer.py` for insertion logic

## Key Constraints

### Hardcoded Assumptions

- Map must be `map1.json` with exact tile layout
- Colours must be pink/blue/green in that order
- Task tiles must exist at specific IDs (see task selection in `tasks.py`)
- Zeus tile is always `tile_043`
- Minimum 3 shrine tiles available

### Task Dependencies

- **Statue delivery** requires picking up statue first (e.g., tile_071 before tile_063 for pink)
- **Temple offering** requires collecting offering first (e.g., tile_053 before tile_112 for pink)
- **Monsters** have no dependencies

### Cargo Rules

- Max 2 items in cargo
- Statues and offerings are separate item types
- Each item is colour-specific (pink statue ≠ blue statue)

## Code Style

- Functions <50 lines
- Descriptive names: `select_tasks_for_colours()` not `select()`
- Type hints on public methods
- Dataclasses for structured data
- No mutable default arguments

## Critical Patterns

### Task Execution

```python
# Tasks are defined per tile and colour
task_id = "tile_020:monster:pink"
tile_id = "tile_020"
colour = "pink"

# Boat must be adjacent to execute
current_tile.neighbours contains tile_id → execute task
```

### Route Structure

Routes are lists of tile IDs representing boat positions:
```python
route = ["tile_043", "tile_042", "tile_041", ...]  # Zeus  task tiles  Zeus
```

Simulator steps through route, executing adjacent tasks and tracking cargo state.

### Shrine Insertion

Shrines insert during "wasted moves" (when <3 moves remain in a turn). `ShrineOptimizer` scans route for opportunities and modifies in-place.

## Troubleshooting

**"Missing required tile"**: map1.json may be corrupted - restore from git

**"Insufficient colours"**: Code expects exactly pink/blue/green - check `COLOURS` in `main.py`

**Route validation failures**: Check simulator output for which move/task failed

**Import errors**: Ensure running from project root with proper Python path

## Project Structure

```
data/maps/map1.json          # The only map
main.py                      # Entry point (hardcoded)
src/
  tasks.py                   # Hardcoded task selection
  cycle_clustering.py        # Fixed 4 clusters
  heuristic.py               # Cycle routing
  map_model.py               # Tile graph + validation
  simulator.py               # Move/task validation
  distance_utils.py          # A* pathfinding
  route_utils.py             # Path repair utilities
  shrine_optimizer.py        # Shrine insertion
  utils.py                   # Logging, JSON I/O
  visualizer.py              # Optional display
```

**Everything now assumes map1.json and pink/blue/green**. No generalization, no dynamic selection, maximum simplicity.
