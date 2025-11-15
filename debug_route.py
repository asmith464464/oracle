from src.grid import HexGrid
from src.tasks import TaskManager
from src.heuristic import CycleHeuristic

grid = HexGrid.from_json('data/maps/map1.json')
tm = TaskManager(grid)
tm.assign_colours(['pink', 'blue', 'green'])
tm.select_tasks_for_colours()

h = CycleHeuristic(grid, tm)
route, stats = h.solve()

print(f"Zeus: {grid.zeus_tile_id}")
print(f"\nFirst 50 route tiles: {route[:50]}")

for i, cycle in enumerate(h.cycles):
    print(f"\n{'='*60}")
    print(f"Cycle {i} (viz color: {['red', 'blue', 'green'][i]}):")
    print(f"  Task tiles (from cycles.py): {[t.tile_id for t in cycle.tasks]}")
    first_task_tile = cycle.tasks[0].tile_id
    last_task_tile = cycle.tasks[-1].tile_id
    first_task_neighbours = grid.get_neighbours(first_task_tile)
    last_task_neighbours = grid.get_neighbours(last_task_tile)
    print(f"  First task {first_task_tile} neighbours: {first_task_neighbours}")
    print(f"  Last task {last_task_tile} neighbours: {last_task_neighbours}")
    if cycle.internal_route:
        first_tile = cycle.internal_route[0]
        last_tile = cycle.internal_route[-1]
        print(f"  internal_route: {first_tile} -> ... -> {last_tile} ({len(cycle.internal_route)} tiles)")
        print(f"  internal_route: {cycle.internal_route}")
