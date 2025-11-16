"""
Oracle Route Planner - Solves the boat routing puzzle for map1.json

To modify cycles, edit: src/cycles.py
To run: python main.py
"""

import sys

from src.tasks import TaskManager
from src.simulator import RouteSimulator
from src.heuristic import CycleHeuristic, add_shrines_to_route
from src.grid import HexGrid, TileType
from src.visualiser import HexGridVisualiser

# Hardcoded constants for map1.json
MAP_PATH = "data/maps/map1.json"
COLOURS = ["pink", "blue", "green"]
TARGET_SHRINES = 3


def main():
    """Run the Oracle route planner."""
    try:
        # 1. Load map1.json
        grid = HexGrid.from_json(MAP_PATH)
        
        # 2. Create tasks and load cycles from cycles.py
        task_manager = TaskManager(grid)
        task_manager.assign_colours(COLOURS)
        task_manager.select_tasks_for_colours()
        
        # 3. Build route through cycles
        heuristic = CycleHeuristic(grid, task_manager)
        route, stats = heuristic.solve()
        
        # 4. Simulate cycle route - shrines will be built opportunistically if encountered
        simulator = RouteSimulator(grid, task_manager)
        cycle_result = simulator.simulate_route(route)
        shrines_built = len(cycle_result.shrines_built)
        
        # 5. If we need more shrines, find nearest unbuilt ones and add to route
        if shrines_built < TARGET_SHRINES:
            optimised_route = add_shrines_to_route(
                route, grid, set(cycle_result.shrines_built), TARGET_SHRINES - shrines_built
            )
            # Re-simulate with the extended route
            task_manager_fresh = TaskManager(grid)
            task_manager_fresh.assign_colours(COLOURS)
            task_manager_fresh.select_tasks_for_colours()
            simulator = RouteSimulator(grid, task_manager_fresh)
            simulation_result = simulator.simulate_route(optimised_route)
        else:
            optimised_route = route
            simulation_result = cycle_result
        
        # 6. Display results
        print("\n" + "="*50)
        print(f"Route: {simulation_result.total_moves} moves, {simulation_result.total_turns} turns")
        print(f"Tasks: {len(simulation_result.completed_tasks)}/15 completed")
        print(f"Shrines: {len(simulation_result.shrines_built)}/{TARGET_SHRINES} built")
        print(f"Shrines built: {simulation_result.shrines_built}")
        print("="*50)
        
        # 7. Visualise
        visualiser = HexGridVisualiser(grid)
        completed_tiles = [task_manager.tasks[t].tile_id for t in simulation_result.completed_tasks if t in task_manager.tasks]
        selected_tiles = sorted({t.tile_id for t in task_manager.tasks.values()})
        visualiser.show_all_visualisations(
            optimised_route, heuristic.cycles, stats, completed_tiles,
            simulation_result.shrines_built, selected_tiles, COLOURS
        )
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())