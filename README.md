# Oracle Route Planner

Solves the Oracle boating puzzle for map1.json by finding an efficient route through 15 tasks organized into 3 cycles.

## What This Does

This solver navigates a boat through a hex-grid map to complete 15 tasks (5 per color: pink, blue, green) and visit 3 shrines. The boat travels on water tiles and completes tasks when adjacent to land tiles. The route starts and ends at Zeus (tile_043).

The solver uses a cycle-based approach: tasks are grouped geographically into 3 cycles, visited sequentially using shortest water paths.

## How To Run

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the solver:
```bash
python main.py
```

The output shows total moves, turns, and a visualization of the route.

## How To Modify Cycles

The key to optimizing the route is changing how tasks are grouped and ordered. See **`docs/CYCLES.md`** for a complete guide on modifying cycle definitions.

Quick start:
1. Edit `src/cycles.py`
2. Modify the `CYCLE_DEFINITIONS` list (respecting dependency constraints)
3. Run `python main.py` to see your new route

## Project Structure

- **`src/cycles.py`** - Cycle definitions (MODIFY HERE for experimentation)
- **`src/heuristic.py`** - Route building logic through cycles
- **`src/tasks.py`** - Task definitions and cargo management
- **`src/simulator.py`** - Route validation
- **`src/visualiser.py`** - Visualization output
- **`data/maps/map1.json`** - The hex-grid map
- **`docs/CYCLES.md`** - Guide to modifying cycles