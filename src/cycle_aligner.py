"""
Cycle alignment and post-processing utilities.
"""

from typing import List, Optional

from .map_model import HexGrid
from .heuristic_models import TaskCycle


class CycleAligner:
    """Handles cycle alignment and route reconciliation."""
    
    def __init__(self, grid: HexGrid):
        self.grid = grid
    
    def realign_cycles_to_route(self, cycles: List[TaskCycle], route: List[str]) -> None:
        """Reconcile cycle segments with the final repaired route."""
        if not route or not cycles:
            return
        
        search_start = 0
        
        for cycle in cycles:
            entry_idx = self._locate_tile(route, cycle.entry_tile, search_start)
            if entry_idx is None:
                entry_idx = self._find_task_index(route, cycle, search_start, reverse=False)
            
            if entry_idx is None:
                cycle.entry_index = None
                cycle.exit_index = None
                cycle.internal_route = []
                continue
            
            exit_idx = self._locate_tile(route, cycle.exit_tile, entry_idx)
            if exit_idx is None:
                exit_idx = self._find_task_index(route, cycle, entry_idx, reverse=True)
            
            if exit_idx is None or exit_idx < entry_idx:
                exit_idx = entry_idx
            
            cycle.entry_index = entry_idx
            cycle.exit_index = exit_idx
            cycle.internal_route = route[entry_idx : exit_idx + 1]
            cycle.total_distance = max(0, len(cycle.internal_route) - 1)
            search_start = exit_idx
    
    def _locate_tile(self, route: List[str], tile_id: Optional[str], start: int) -> Optional[int]:
        """Return the first index of tile_id in route at or after start."""
        if tile_id is None:
            return None
        try:
            return route.index(tile_id, max(0, start))
        except ValueError:
            return None
    
    def _find_task_index(self, route: List[str], cycle: TaskCycle, start: int, 
                        reverse: bool = False) -> Optional[int]:
        """Locate index of any tile adjacent to a task, searching forward or backward."""
        task_ids = cycle.get_task_tile_ids()
        task_set = set(task_ids)
        
        if reverse:
            indices = range(len(route) - 1, max(0, start) - 1, -1)
        else:
            indices = range(max(0, start), len(route))
        
        for idx in indices:
            tile_id = route[idx]
            if tile_id in task_set:
                return idx
            
            tile = self.grid.get_tile(tile_id)
            if tile and any(task_id in tile.neighbors for task_id in task_ids):
                return idx
        
        return None
