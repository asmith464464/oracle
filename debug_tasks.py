"""Debug task selection and cycle assignment."""
import random
from src.heuristic import CycleHeuristic
from src.tasks import TaskManager
from src.utils import create_example_map, find_colours_with_required_tasks

random.seed(42)
grid = create_example_map(width=12, height=10, water_ratio=0.6)
valid_colours = find_colours_with_required_tasks(grid)
colours = sorted(valid_colours)[:3]

print(f'Colors: {colours}\n')

tm = TaskManager(grid)
tm.assign_colours(colours)
colour_tasks = tm.select_tasks_for_colours()

print('Selected tasks by colour:')
for colour, tasks in colour_tasks.items():
    print(f'  {colour}: {[(t.tile_id, t.task_type.value) for t in tasks]}')

all_selected = [t for tasks in colour_tasks.values() for t in tasks]
print(f'\nTotal selected: {len(all_selected)} tasks')
print(f'Selected tile_ids: {sorted(set(t.tile_id for t in all_selected))}')
print(f'Selected task IDs: {sorted(t.id for t in all_selected)}')

# Run heuristic
heur = CycleHeuristic(grid, tm)
route, stats = heur.solve()

# Check what's in cycles
cycle_task_ids = set()
cycle_tasks = []
for c in heur.cycles:
    for t in c.tasks:
        cycle_task_ids.add(t.tile_id)
        cycle_tasks.append(t)

print(f'\nTasks in cycles: {sorted(cycle_task_ids)}')
print(f'Total in cycles: {len(cycle_task_ids)}')
print(f'Cycle task IDs: {sorted(t.id for t in cycle_tasks)}')

# Find missing
selected_tile_ids = set(t.tile_id for t in all_selected)
missing = selected_tile_ids - cycle_task_ids
print(f'\nMissing from cycles: {missing if missing else "None"}')

# Check task manager tasks
print(f'\nTask manager has {len(tm.tasks)} tasks')
print(f'Task manager task IDs: {sorted(tm.tasks.keys())}')
