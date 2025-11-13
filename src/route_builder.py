"""
Route building through cycles using greedy nearest-neighbour strategy.
"""

from typing import Dict, List, Optional

from .tasks import Task
from .map_model import HexGrid
from .distance_utils import DistanceCalculator
from .route_utils import append_path


class RouteBuilder:
    """Builds routes through task cycles using greedy pathfinding."""
    
    def __init__(self, grid: HexGrid, distance_calc: DistanceCalculator):
        self.grid = grid
        self.distance_calc = distance_calc
    
    def visit_tasks_greedily(self, tasks: List[Task], start_tile: str) -> List[str]:
        """
        Visit all tasks in greedy order (nearest neighbour).
        
        Args:
            tasks: Tasks to visit
            start_tile: Starting tile ID
            
        Returns:
            Route as list of tile IDs
        """
        route: List[str] = [start_tile]
        current_tile = start_tile
        pending = {t.id: t for t in tasks}
        
        while pending:
            best_task, best_path = self._find_nearest_task(current_tile, list(pending.values()))
            
            if not best_task or not best_path:
                break
            
            append_path(route, best_path)
            current_tile = route[-1]
            pending.pop(best_task.id)
        
        return route
    
    def _find_nearest_task(self, current_tile: str, 
                          tasks: List[Task]) -> tuple[Optional[Task], Optional[List[str]]]:
        """Find the nearest task and path to it."""
        best_task = None
        best_path = None
        best_dist = float('inf')
        
        for task in tasks:
            path = self._best_path_to_task(current_tile, task)
            if path and len(path) < best_dist:
                best_dist = len(path)
                best_task = task
                best_path = path
        
        return best_task, best_path
    
    def _best_path_to_task(self, current_tile: str, task: Task) -> Optional[List[str]]:
        """Find best path to a task (via any adjacent water tile)."""
        candidates = self._adjacent_water_ids(task.tile_id)
        best_path: Optional[List[str]] = None
        
        for candidate in candidates:
            path = self.distance_calc.get_shortest_path(current_tile, candidate)
            if path and (not best_path or 
                        (len(path), candidate) < (len(best_path), best_path[-1])):
                best_path = path
        
        return best_path
    
    def _adjacent_water_ids(self, tile_id: str) -> List[str]:
        """Get sorted list of adjacent water tile IDs."""
        tile = self.grid.get_tile(tile_id)
        if not tile:
            return []
        
        water_ids = []
        for neighbour_id in tile.neighbours:
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if neighbour_tile and neighbour_tile.is_water():
                water_ids.append(neighbour_id)
        
        water_ids.sort()
        return water_ids
