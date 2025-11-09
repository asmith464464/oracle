# Oracle Heuristic Route Planner

A Python project that computes efficient routes to complete all tasks on a hex-grid map, minimizing the number of turns.

## Overview

Develop a Python project that computes an efficient route to complete all tasks on a hex-grid map, minimizing the number of turns.

Each run will consider 3 dynamically chosen colours.

Optional shrine builds can be inserted during unused movement steps.

The route must start and end at the starting tile (Zeus).

Visualization is optional and serves only to debug or document the heuristic; it should not affect route computation.

Map and Tiles
The map is a hex-grid graph with nodes representing tiles.

Tiles are either water (traversable) or land (task tile).

Every land tile is a task tile.

Each tile stores:

id – unique identifier

type – 'water' or task type ('monster', 'offering', 'statue_source', 'statue_island', 'temple', 'shrine')

colour – assigned colour for task tiles (None for water tiles)

coords – (x, y) coordinates for visualization

neighbors – list of adjacent water tile IDs

Task Distribution per Colour


For each selected colour:

Task Type

Count

Notes

Monster

2

Must be fought when adjacent

Offering

2

Must be collected when adjacent

Statue Source

1

Pick up when adjacent

Statue Island

3

Deliver after pickup

Temple

1

Deliver offerings after collection

Shrine Tile

3 total

Optional, can be built in wasted moves

The 3 colours are either selected by the user or assigned randomly at the start of a run.

Dependent tasks (e.g., deliveries) are always included even if their tile colour differs.

Movement Rules
Each turn: up to 3 moves along water tiles.

Tasks are performed when the boat is adjacent to the task tile.

Turns = ceil(total_moves / 3).

Heuristic Requirements
Task Selection

For tasks with multiple options (e.g., 2 monster tiles), select exactly one tile per colour.

Cycle Formation

Cluster geographically close tasks into small cycles.

Determine an efficient visiting order within each cycle.

Cycle Connection

Connect cycles using shortest paths, respecting dependencies (pickup → delivery).

Shrine Insertion

Insert shrines in wasted-move turns.

If shrines remain after completing all other tasks, plan minimal detours.

Route Completion

Ensure the route ends at the starting tile.

Output: total moves, turns, completed tasks, shrine placements.

## Features

- **Hex-grid Pathfinding**: Navigate water tiles to reach task tiles
- **Task Management**: Handle multiple task types (monsters, offerings, statues, temples, shrines)
- **Dynamic Color Assignment**: Work with 3 dynamically chosen colors per run
- **Cycle-based Heuristic**: Optimize routes using geographical clustering
- **Shrine Optimization**: Insert optional shrine builds during unused moves
- **Visualization**: Optional debugging and documentation aid


## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the main program:
```bash
python main.py
```

3. Run tests:
```bash
pytest tests/
```

## Usage

The system can load maps from JSON files or generate them randomly. Each run considers 3 dynamically chosen colors and computes an optimal route that starts and ends at the Zeus tile.

### Task Types per Color

- **Monster**: 2 tiles (must fight when adjacent)
- **Offering**: 2 tiles (must collect when adjacent)  
- **Statue Source**: 1 tile (pickup when adjacent)
- **Statue Island**: 3 tiles (deliver after pickup)
- **Temple**: 1 tile (deliver offerings after collection)
- **Shrine**: 3 tiles total (optional, built during wasted moves)

### Movement Rules

- Each turn allows up to 3 moves along water tiles
- Tasks are performed when adjacent to task tiles
- Total turns = ceil(total_moves / 3)

## Algorithm

1. **Task Selection**: Choose one tile per color for tasks with multiple options
2. **Cycle Formation**: Cluster geographically close tasks
3. **Cycle Connection**: Connect cycles with shortest paths, respecting dependencies
4. **Shrine Insertion**: Add shrines during wasted moves
5. **Route Completion**: Ensure route returns to starting tile

## Development

Use the Jupyter notebook in `notebooks/development.ipynb` for prototyping and testing new features.