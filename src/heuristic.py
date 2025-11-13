"""
Core cycle-based heuristic for route optimization.
"""

import math
from typing import Dict, List, Tuple

from .map_model import HexGrid
from .tasks import Task, TaskManager
from .distance_utils import DistanceCalculator
from .heuristic_models import TaskCycle
from .route_utils import repair_route, ensure_return_to_zeus, append_path
from .cycle_clustering import CycleClusterer
from .cycle_dependencies import CycleDependencyAnalyzer
from .route_builder import RouteBuilder
from .cycle_aligner import CycleAligner


class CycleHeuristic:
    """Implements the cycle-based heuristic for route optimization."""

    CYCLE_DISTANCE_THRESHOLD = 6  # Max hex distance to nearest task when adding to cluster
    MAX_CYCLE_TASKS = 8  # Target smaller cycles for better spatial separation

    def __init__(self, grid: HexGrid, task_manager: TaskManager):
        self.grid = grid
        self.task_manager = task_manager
        self.distance_calc = DistanceCalculator(grid)
        self.cycles: List[TaskCycle] = []
        
        # Helper components
        self.clusterer = CycleClusterer(grid, self.CYCLE_DISTANCE_THRESHOLD, self.MAX_CYCLE_TASKS)
        self.route_builder = RouteBuilder(grid, self.distance_calc)
        self.cycle_aligner = CycleAligner(grid)

    def solve(self) -> Tuple[List[str], Dict]:
        """Generate a complete route that satisfies the three-cycle brief."""
        zeus_tile = self.grid.get_zeus_tile()
        if not zeus_tile:
            raise ValueError("Zeus tile not configured on grid")

        selected_tasks = list(self.task_manager.tasks.values())
        if not selected_tasks:
            empty_route = [zeus_tile.id]
            stats = self._calculate_statistics(empty_route)
            return empty_route, stats

        base_route, cycles = self._build_route_with_cycles(selected_tasks, zeus_tile.id)

        self.cycles = cycles

        repaired_route = repair_route(self.grid, self.distance_calc, base_route)
        repaired_route = ensure_return_to_zeus(self.grid, self.distance_calc, repaired_route)
        repaired_route = repair_route(self.grid, self.distance_calc, repaired_route)
        self.cycle_aligner.realign_cycles_to_route(self.cycles, repaired_route)

        stats = self._calculate_statistics(repaired_route)
        return repaired_route, stats

    def solve_with_custom_cycles(self, cycle_tile_ids: List[List[str]]) -> Tuple[List[str], Dict]:
        """Generate route using user-specified cycles.
        
        Args:
            cycle_tile_ids: List of lists, where each inner list contains tile IDs for one cycle
            
        Returns:
            Tuple of (route, statistics)
        """
        zeus_tile = self.grid.get_zeus_tile()
        if not zeus_tile:
            raise ValueError("Zeus tile not configured on grid")

        # Convert tile IDs to Task objects
        all_tasks = list(self.task_manager.tasks.values())
        task_by_tile = {task.tile_id: task for task in all_tasks}
        
        # Build task clusters from tile IDs
        task_clusters = []
        for cycle_tiles in cycle_tile_ids:
            cluster = []
            for tile_id in cycle_tiles:
                if tile_id not in task_by_tile:
                    raise ValueError(f"Tile {tile_id} is not a task tile or not in selected colours")
                cluster.append(task_by_tile[tile_id])
            if cluster:
                task_clusters.append(cluster)
        
        if not task_clusters:
            empty_route = [zeus_tile.id]
            stats = self._calculate_statistics(empty_route)
            return empty_route, stats
        
        # Build route through the custom cycles
        route: List[str] = [zeus_tile.id]
        cycles: List[TaskCycle] = []
        current_tile = zeus_tile.id
        
        for cluster_tasks in task_clusters:
            cycle_entry_idx = len(route) - 1
            visited_tasks = []
            pending = {t.id: t for t in cluster_tasks}
            
            # Visit all tasks in this cluster by proximity
            while pending:
                # Find closest task
                best_task = None
                best_path = None
                best_dist = float('inf')
                
                for task in pending.values():
                    path = self.route_builder._best_path_to_task(current_tile, task)
                    if path and len(path) < best_dist:
                        best_dist = len(path)
                        best_task = task
                        best_path = path
                
                if not best_path or not best_task:
                    break
                
                # Add path (excluding current tile)
                route.extend(best_path[1:])
                current_tile = best_task.tile_id
                visited_tasks.append(best_task)
                del pending[best_task.id]
            
            # Create cycle record
            cycle_exit_idx = len(route) - 1
            internal_route = route[cycle_entry_idx:cycle_exit_idx + 1]
            cycles.append(TaskCycle(
                tasks=visited_tasks,
                entry_index=cycle_entry_idx,
                exit_index=cycle_exit_idx,
                internal_route=internal_route,
                connector_to_next=[]
            ))
        
        self.cycles = cycles
        
        # Repair route and finalize
        repaired_route = repair_route(self.grid, self.distance_calc, route)
        repaired_route = ensure_return_to_zeus(self.grid, self.distance_calc, repaired_route)
        repaired_route = repair_route(self.grid, self.distance_calc, repaired_route)
        
        # Add connectors between cycles
        for i in range(len(cycles) - 1):
            connector_start = cycles[i].exit_index
            connector_end = cycles[i + 1].entry_index
            if connector_start is not None and connector_end is not None and connector_start < connector_end:
                cycles[i].connector_to_next = repaired_route[connector_start:connector_end + 1]
        
        self.cycle_aligner.realign_cycles_to_route(self.cycles, repaired_route)

        stats = self._calculate_statistics(repaired_route)
        return repaired_route, stats



    def _build_route_with_cycles(
        self, tasks: List[Task], start_tile: str
    ) -> Tuple[List[str], List[TaskCycle]]:
        """Build route by visiting spatially-clustered cycles, ordered by cargo dependencies."""
        # Build a map of tile_id to all tasks for that tile
        tasks_by_tile = {}
        for task in tasks:
            tasks_by_tile.setdefault(task.tile_id, []).append(task)
        
        # Use one task per tile for clustering (visiting a tile once completes all its tasks)
        deduplicated_tasks = [tasks_by_tile[tile_id][0] for tile_id in tasks_by_tile]
        
        # Step 1: Cluster tasks by spatial proximity only
        task_clusters = self.clusterer.cluster_tasks(deduplicated_tasks)
        
        # Step 2: Build preliminary cycles without routing yet
        preliminary_cycles = [
            TaskCycle(tasks=[task for cluster_task in cluster_tasks 
                           for task in tasks_by_tile[cluster_task.tile_id]])
            for cluster_tasks in task_clusters if cluster_tasks
        ]
        
        # Step 3: Reorder cycles based on cargo dependencies
        ordered_cycles = CycleDependencyAnalyzer.topological_sort(preliminary_cycles)
        
        # Step 4: Build route through ordered cycles
        route: List[str] = [start_tile]
        cycles: List[TaskCycle] = []
        current_tile = start_tile
        
        for cycle in ordered_cycles:
            # Get unique task tiles for this cycle
            task_tiles_set = {task.tile_id for task in cycle.tasks}
            cluster_tasks = [task for task in deduplicated_tasks if task.tile_id in task_tiles_set]
            
            if not cluster_tasks:
                continue
            
            # Find entry point to this cluster (closest task to current position)
            entry_task, entry_path = self.route_builder._find_nearest_task(current_tile, cluster_tasks)
            if not entry_task or not entry_path:
                continue
            
            # Travel to cluster (this is the connector, not part of internal route)
            append_path(route, entry_path)
            cycle_entry_idx = len(route) - 1  # Mark where cycle actually starts
            
            visited_tasks = [entry_task]
            pending = {t.id: t for t in cluster_tasks if t.id != entry_task.id}
            current_tile = route[-1]
            
            # Visit remaining tasks in this cluster by proximity (internal to cycle)
            while pending:
                best_task, best_path = self.route_builder._find_nearest_task(current_tile, list(pending.values()))
                if not best_task or not best_path:
                    break
                
                append_path(route, best_path)
                current_tile = route[-1]
                visited_tasks.append(best_task)
                pending.pop(best_task.id)
            
            # Create cycle with internal route (excluding connector)
            # Include ALL tasks for each visited tile (multi-color tiles have multiple tasks)
            all_cycle_tasks = [task for visited_task in visited_tasks 
                             for task in tasks_by_tile[visited_task.tile_id]]
            
            cycle_exit_idx = len(route) - 1
            final_cycle = TaskCycle(tasks=all_cycle_tasks)
            final_cycle.entry_index = cycle_entry_idx
            final_cycle.exit_index = cycle_exit_idx
            final_cycle.internal_route = route[cycle_entry_idx:cycle_exit_idx + 1]
            final_cycle.entry_tile = route[cycle_entry_idx]
            final_cycle.exit_tile = route[cycle_exit_idx]
            final_cycle.total_distance = cycle_exit_idx - cycle_entry_idx
            
            # Store connector from previous position to this cycle's entry
            if cycles:  # Not the first cycle
                prev_exit = cycles[-1].exit_index
                cycles[-1].connector_to_next = route[prev_exit:cycle_entry_idx + 1]
            
            cycles.append(final_cycle)
        
        return route, cycles


    def _calculate_statistics(self, route: List[str]) -> Dict:
        """Calculate high-level metrics for the constructed route."""
        total_moves = max(0, len(route) - 1)
        total_turns = math.ceil(total_moves / 3) if total_moves else 0

        return {
            "total_moves": total_moves,
            "total_turns": total_turns,
            "route_length": len(route),
            "cycles_formed": len(self.cycles),
            "tasks_per_cycle": [len(cycle.tasks) for cycle in self.cycles],
            "cycle_distances": [cycle.total_distance for cycle in self.cycles],
        }

    def get_cycle_summary(self) -> List[Dict]:
        """Expose cycle metadata in a structure compatible with visualizers."""
        summary: List[Dict] = []

        for idx, cycle in enumerate(self.cycles):
            summary.append(
                {
                    "cycle_id": idx,
                    "task_count": len(cycle.tasks),
                    "task_types": [task.task_type.value for task in cycle.tasks],
                    "task_ids": [task.tile_id for task in cycle.tasks],
                    "cycle_colours": sorted(
                        {task.colour for task in cycle.tasks if task.colour}
                    ),
                    "entry_tile": cycle.entry_tile,
                    "exit_tile": cycle.exit_tile,
                    "segment_distance": cycle.total_distance,
                }
            )

        return summary

