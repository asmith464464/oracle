"""Core cycle-based heuristic for route optimization."""

import math
from typing import Dict, List, Optional, Tuple, Set

from .grid import HexGrid, DistanceCalculator, TileType
from .tasks import Task, TaskManager, TaskCycle


class RouteBuilder:
    """Builds routes through task cycles using greedy pathfinding."""
    
    def __init__(self, grid: HexGrid, distance_calc: DistanceCalculator):
        self.grid = grid
        self.distance_calc = distance_calc
    
    def best_path_to_task(self, current_tile: str, task: Task) -> Optional[List[str]]:
        """Find best path to a task via any adjacent water tile."""
        tile = self.grid.get_tile(task.tile_id)
        if not tile:
            return None
        
        # Find adjacent water tiles and get best path
        best_path: Optional[List[str]] = None
        for neighbour_id in self.grid.get_neighbours(task.tile_id):
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if neighbour_tile and neighbour_tile.is_water():
                path = self.distance_calc.get_shortest_path(current_tile, neighbour_id)
                if path and (not best_path or len(path) < len(best_path)):
                    best_path = path
        return best_path


class CycleHeuristic:
    """Implements the cycle-based heuristic for route optimization."""

    def __init__(self, grid: HexGrid, task_manager: TaskManager):
        self.grid = grid
        self.task_manager = task_manager
        self.distance_calc = DistanceCalculator(grid)
        self.cycles: List[TaskCycle] = []
        self.route_builder = RouteBuilder(grid, self.distance_calc)

    def solve(self) -> Tuple[List[str], Dict]:
        """Generate a complete route for map1.json pink/blue/green tasks."""
        # Step 1: Start at Zeus tile
        zeus_tile = self.grid.zeus_tile_id
        selected_tasks = list(self.task_manager.tasks.values())
        if not selected_tasks:
            return [zeus_tile], {"total_moves": 0, "total_turns": 0, "route_length": 1, "cycles_formed": 0, "tasks_per_cycle": [], "cycle_distances": []}

        # Step 2: Build lookup tables for tasks
        tile_to_task = {task.tile_id: task for task in selected_tasks}
        tile_tasks = {}
        for task in selected_tasks:
            tile_tasks.setdefault(task.tile_id, []).append(task)
        
        # Step 3: Create cycles from definitions in cycles.py
        cycles = []
        for tile_ids in self.task_manager.cycle_tile_orders:
            cycle_tasks = [tile_to_task[tile_id] for tile_id in tile_ids if tile_id in tile_to_task]
            if cycle_tasks:
                cycles.append(TaskCycle(tasks=cycle_tasks))
        
        # Step 4: Build route by visiting each cycle's tiles sequentially
        route: List[str] = [zeus_tile]
        current_tile = zeus_tile
        
        for cycle in cycles:
            if not cycle.tasks:
                continue
            
            cycle_start_idx = None
            
            # Visit each task in the cycle using shortest water paths
            for task in cycle.tasks:
                path = self.route_builder.best_path_to_task(current_tile, task)
                if path:
                    # Mark where first cycle task begins
                    if cycle_start_idx is None:
                        cycle_start_idx = len(route) + len(path) - 1
                    
                    # Append path without duplicating current position
                    if route[-1] == path[0]:
                        route.extend(path[1:])
                    else:
                        route.extend(path)
                    current_tile = route[-1]
            
            # Store simplified cycle with just tasks and route
            all_cycle_tasks = []
            for task in cycle.tasks:
                all_cycle_tasks.extend(tile_tasks.get(task.tile_id, [task]))
            
            cycle_end_idx = len(route) - 1
            if cycle_start_idx is not None:
                final_cycle = TaskCycle(
                    tasks=all_cycle_tasks,
                    internal_route=route[cycle_start_idx:cycle_end_idx + 1]
                )
            else:
                final_cycle = TaskCycle(
                    tasks=all_cycle_tasks,
                    internal_route=[]
                )
            self.cycles.append(final_cycle)
        
        # Step 5: Repair route by filling gaps between non-adjacent tiles
        repaired = [route[0]]
        for next_tile in route[1:]:
            current = repaired[-1]
            if next_tile == current:
                continue
            current_tile_obj = self.grid.get_tile(current)
            if current_tile_obj and next_tile in self.grid.get_neighbours(current):
                repaired.append(next_tile)
            else:
                bridge = self.distance_calc.get_shortest_path(current, next_tile)
                if bridge:
                    if repaired[-1] == bridge[0]:
                        repaired.extend(bridge[1:])
                    else:
                        repaired.extend(bridge)
        
        # Step 6: Return to Zeus tile
        if repaired[-1] != zeus_tile:
            return_path = self.distance_calc.get_shortest_path(repaired[-1], zeus_tile)
            if return_path:
                if repaired[-1] == return_path[0]:
                    repaired.extend(return_path[1:])
                else:
                    repaired.extend(return_path)
        
        # Calculate statistics
        total_moves = max(0, len(repaired) - 1)
        stats = {
            "total_moves": total_moves,
            "total_turns": math.ceil(total_moves / 3) if total_moves else 0,
            "route_length": len(repaired),
            "cycles_formed": len(self.cycles),
            "tasks_per_cycle": [len(cycle.tasks) for cycle in self.cycles],
            "cycle_distances": [len(cycle.internal_route) - 1 for cycle in self.cycles],
        }
        
        return repaired, stats


def add_shrines_to_route(route: List[str], grid: HexGrid, 
                        already_built: Set[str], count_needed: int) -> List[str]:
    """Add paths to nearest unbuilt shrines to reach the target count."""
    if not route or count_needed <= 0:
        return route
    
    distance_calc = DistanceCalculator(grid)
    zeus_tile = grid.get_zeus_tile()
    
    # Get all shrine tiles from the map
    all_shrines = [tile.id for tile in grid.tiles.values() 
                  if tile.tile_type == TileType.SHRINE and tile.id not in already_built]
    
    if not all_shrines:
        return route
    
    new_route = list(route)
    shrines_added = 0
    
    # Visit nearest shrines until we reach the needed count
    while shrines_added < count_needed and all_shrines:
        current_pos = new_route[-1]
        
        # Find nearest unvisited shrine
        nearest_shrine = None
        min_distance = float('inf')
        
        for shrine_id in all_shrines:
            # Find adjacent water tiles for this shrine
            water_tiles = distance_calc.find_nearest_water_tiles(shrine_id)
            if not water_tiles:
                continue
            
            # Check distance from current position to shrine's adjacent water
            for water_tile, _ in water_tiles:
                path = distance_calc.get_shortest_path(current_pos, water_tile)
                if path and len(path) < min_distance:
                    min_distance = len(path)
                    nearest_shrine = (shrine_id, water_tile)
        
        if not nearest_shrine:
            break
        
        shrine_id, approach_tile = nearest_shrine
        
        # Add path to this shrine
        path = distance_calc.get_shortest_path(current_pos, approach_tile)
        if path:
            if new_route[-1] == path[0]:
                new_route.extend(path[1:])
            else:
                new_route.extend(path)
            all_shrines.remove(shrine_id)
            shrines_added += 1
    
    # Return to Zeus after visiting shrines
    if zeus_tile and new_route[-1] != zeus_tile.id:
        return_path = distance_calc.get_shortest_path(new_route[-1], zeus_tile.id)
        if return_path:
            if new_route[-1] == return_path[0]:
                new_route.extend(return_path[1:])
            else:
                new_route.extend(return_path)
    
    return new_route
