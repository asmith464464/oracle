"""
Oracle Route Planner - Solves the boat routing puzzle for map1.json

To modify cycles, edit: src/cycles.py
To run: python main.py
"""

import sys

from src.tasks import TaskManager
from src.simulator import RouteSimulator
from src.heuristic import CycleHeuristic, add_shrines_to_route
from src.grid import HexGrid
from src.cycles import SHRINE_TILES
from src.visualiser import HexGridVisualiser

# Hardcoded constants for map1.json
MAP_PATH = "data/maps/map1.json"
COLOURS = ["pink", "blue", "green"]


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
        
        # 4. Simulate initial route to see which shrines were encountered
        simulator = RouteSimulator(grid, task_manager)
        initial_result = simulator.simulate_route(route, [])
        shrines_built_during_cycles = len(initial_result.shrines_built)
        
        # 5. Add extra shrines only if we need more to reach 3
        target_shrines = 3
        if shrines_built_during_cycles < target_shrines:
            visited_tiles = set(route)
            already_built = set(initial_result.shrines_built)
            optimised_route, extra_shrine_positions = add_shrines_to_route(
                route, grid, visited_tiles, already_built, target_shrines - shrines_built_during_cycles
            )
        else:
            optimised_route = route
            extra_shrine_positions = []
        
        # 6. Simulate final route execution
        all_shrine_positions = list(set(initial_result.shrines_built + extra_shrine_positions))
        simulation_result = simulator.simulate_route(optimised_route, all_shrine_positions)
        
        # 6. Display results
        print("\n" + "="*50)
        print(f"Route: {simulation_result.total_moves} moves, {simulation_result.total_turns} turns")
        print(f"Tasks: {len(simulation_result.completed_tasks)}/15 completed")
        print(f"Shrines: {len(simulation_result.shrines_built)}/{len(SHRINE_TILES)} built")
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