"""High-level coordinator for shrine insertion and reporting."""

import logging
from typing import Dict, List, Tuple

from .map_model import HexGrid
from .tasks import TaskManager
from .distance_utils import DistanceCalculator
from .shrine_logic import (
    add_remaining_shrines,
    find_shrine_opportunities,
    insert_shrines_into_route,
    select_optimal_shrines,
)
from .route_utils import repair_route, ensure_return_to_zeus


class ShrineOptimizer:
    """Handles shrine insertion logic and optimization."""
    
    def __init__(self, grid: HexGrid, task_manager: TaskManager):
        self.grid = grid
        self.task_manager = task_manager
        self.distance_calc = DistanceCalculator(grid)
        
    def optimize_shrine_placement(
        self,
        route: List[str],
        max_shrines: int = 3,
    ) -> Tuple[List[str], List[str]]:
        """
        Optimize shrine placement in the given route.
        
        Args:
            route: Original route path
            max_shrines: Maximum number of shrines to build
            
        Returns:
            Tuple of (optimized_route, shrine_positions)
        """
        if not route or max_shrines <= 0:
            return route, []
            
        # Find shrine candidates
        shrine_candidates = self.task_manager.get_shrine_candidates()
        required_shrines = self.task_manager.remaining_shrine_requirement()
        if required_shrines <= 0:
            return route, []

        target_shrines = required_shrines
        if max_shrines < required_shrines:
            logging.warning(
                "Shrine quota (%s) exceeds max_shrines argument (%s); enforcing quota",
                required_shrines,
                max_shrines,
            )

        if len(shrine_candidates) < target_shrines:
            raise ValueError(
                f"Only {len(shrine_candidates)} shrine tiles available but {target_shrines} required"
            )
            
        # Analyze route for wasted moves and opportunities
        opportunities = find_shrine_opportunities(self.distance_calc, route, shrine_candidates)

        # Select best shrine placements
        selected_shrines = select_optimal_shrines(opportunities, target_shrines)
        
        # Insert shrines into route
        optimized_route, shrine_positions = insert_shrines_into_route(
            self.grid,
            self.distance_calc,
            route,
            selected_shrines,
        )
        optimized_route = repair_route(self.grid, self.distance_calc, optimized_route)
            
        # Handle remaining shrines with minimal detours
        if len(shrine_positions) < target_shrines:
            remaining_shrines = target_shrines - len(shrine_positions)
            optimized_route, additional_shrines = add_remaining_shrines(
                self.grid,
                self.distance_calc,
                optimized_route,
                shrine_candidates,
                shrine_positions,
                remaining_shrines,
            )
            shrine_positions.extend(additional_shrines)

        if len(shrine_positions) < target_shrines:
            missing = target_shrines - len(shrine_positions)
            raise ValueError(f"Unable to schedule {missing} required shrine(s)")

        self.task_manager.register_scheduled_shrines(shrine_positions)
        optimized_route = ensure_return_to_zeus(self.grid, self.distance_calc, optimized_route)

        return optimized_route, shrine_positions