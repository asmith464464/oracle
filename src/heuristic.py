"""
Core cycle-based heuristic for route optimization.
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple

from .map_model import HexGrid
from .tasks import Task, TaskManager
from .distance_utils import DistanceCalculator
from .heuristic_models import TaskCycle
from .route_utils import append_path, repair_route, ensure_return_to_zeus


class CycleHeuristic:
    """Implements the cycle-based heuristic for route optimization."""

    CYCLE_DISTANCE_THRESHOLD = 6  # Max hex distance to nearest task when adding to cluster
    MAX_CYCLE_TASKS = 8  # Target smaller cycles for better spatial separation

    def __init__(self, grid: HexGrid, task_manager: TaskManager):
        self.grid = grid
        self.task_manager = task_manager
        self.distance_calc = DistanceCalculator(grid)
        self.cycles: List[TaskCycle] = []
        self._task_distance_cache: Dict[Tuple[str, str], Optional[int]] = {}

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
        self._realign_cycles_to_route(repaired_route)

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
                    path = self._best_path_to_task(current_tile, task)
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
        
        self._realign_cycles_to_route(repaired_route)

        stats = self._calculate_statistics(repaired_route)
        return repaired_route, stats

    def _cluster_tasks_by_proximity(self, tasks: List[Task]) -> List[List[Task]]:
        """Group tasks into spatially-balanced clusters using k-means-like approach."""
        if not tasks:
            return []
        
        n_tasks = len(tasks)
        distance_matrix = np.zeros((n_tasks, n_tasks))
        
        # Build distance matrix between task land tiles
        for i in range(n_tasks):
            for j in range(i + 1, n_tasks):
                dist = self._task_land_distance(tasks[i].tile_id, tasks[j].tile_id)
                if dist is None:
                    dist = 999
                distance_matrix[i, j] = dist
                distance_matrix[j, i] = dist
        
        # Estimate number of clusters needed (aim for ~3-4 tasks per cluster to allow flexibility)
        target_clusters = max(2, (n_tasks + 3) // 4)
        
        # Pick initial seeds: maximally spread out tasks
        seeds = []
        remaining = set(range(n_tasks))
        
        # First seed: arbitrary (deterministic)
        first_seed = min(remaining)
        seeds.append(first_seed)
        remaining.remove(first_seed)
        
        # Subsequent seeds: maximize minimum distance to existing seeds
        while len(seeds) < target_clusters and remaining:
            best_candidate = None
            best_min_dist = -1
            
            for candidate in sorted(remaining):
                min_dist_to_seeds = min(distance_matrix[candidate, seed] for seed in seeds)
                if min_dist_to_seeds > best_min_dist or (min_dist_to_seeds == best_min_dist and (best_candidate is None or candidate < best_candidate)):
                    best_min_dist = min_dist_to_seeds
                    best_candidate = candidate
            
            if best_candidate is not None:
                seeds.append(best_candidate)
                remaining.remove(best_candidate)
        
        # Assign each remaining task to nearest cluster, respecting distance threshold
        clusters = {seed: [seed] for seed in seeds}
        
        for task_idx in sorted(remaining):
            # Find nearest cluster where task is within threshold distance
            best_cluster = None
            best_min_dist = float('inf')
            
            for seed in seeds:
                if len(clusters[seed]) >= self.MAX_CYCLE_TASKS:
                    continue  # Cluster is full
                
                # Calculate minimum distance to any task in this cluster
                min_dist_to_cluster = min(distance_matrix[task_idx, t] for t in clusters[seed])
                
                # Only consider clusters where task is close enough
                if min_dist_to_cluster <= self.CYCLE_DISTANCE_THRESHOLD:
                    if min_dist_to_cluster < best_min_dist or (min_dist_to_cluster == best_min_dist and (best_cluster is None or seed < best_cluster)):
                        best_min_dist = min_dist_to_cluster
                        best_cluster = seed
            
            if best_cluster is not None:
                clusters[best_cluster].append(task_idx)
            else:
                # No cluster within threshold - create new single-task cluster
                clusters[task_idx] = [task_idx]
        
        # Convert to list of task lists
        result = [[tasks[i] for i in cluster] for cluster in clusters.values()]
        return result

    def _build_route_with_cycles(
        self, tasks: List[Task], start_tile: str
    ) -> Tuple[List[str], List[TaskCycle]]:
        """Build route by visiting spatially-clustered cycles. Ignores cargo/dependencies for clean visualization."""
        # Build a map of tile_id to all tasks for that tile
        tasks_by_tile = {}
        for task in tasks:
            if task.tile_id not in tasks_by_tile:
                tasks_by_tile[task.tile_id] = []
            tasks_by_tile[task.tile_id].append(task)
        
        # Use one task per tile for clustering (visiting a tile once completes all its tasks)
        unique_tasks = {}
        for task in tasks:
            if task.tile_id not in unique_tasks:
                unique_tasks[task.tile_id] = task
        deduplicated_tasks = list(unique_tasks.values())
        
        # Cluster tasks by spatial proximity only
        task_clusters = self._cluster_tasks_by_proximity(deduplicated_tasks)
        
        # Route through each cluster, visiting all tasks greedily by distance
        route: List[str] = [start_tile]
        cycles: List[TaskCycle] = []
        current_tile = start_tile
        
        for cluster_tasks in task_clusters:
            connector_start_idx = len(route) - 1
            visited_tasks = []
            pending = {t.id: t for t in cluster_tasks}
            
            # Find entry point to this cluster (closest task to current position)
            entry_task = None
            entry_path = None
            entry_dist = float('inf')
            
            for task in pending.values():
                path = self._best_path_to_task(current_tile, task)
                if path and len(path) < entry_dist:
                    entry_dist = len(path)
                    entry_task = task
                    entry_path = path
            
            if not entry_task or not entry_path:
                continue
            
            # Travel to cluster (this is the connector, not part of internal route)
            append_path(route, entry_path)
            current_tile = route[-1]
            cycle_entry_idx = len(route) - 1  # Mark where cycle actually starts
            visited_tasks.append(entry_task)
            pending.pop(entry_task.id)
            
            # Visit remaining tasks in this cluster by proximity (internal to cycle)
            while pending:
                best_task = None
                best_path = None
                best_dist = float('inf')
                
                for task in pending.values():
                    path = self._best_path_to_task(current_tile, task)
                    if path and len(path) < best_dist:
                        best_dist = len(path)
                        best_task = task
                        best_path = path
                
                if not best_task or not best_path:
                    break
                
                append_path(route, best_path)
                current_tile = route[-1]
                visited_tasks.append(best_task)
                pending.pop(best_task.id)
            
            # Create cycle with internal route (excluding connector)
            # Include ALL tasks for each visited tile (multi-color tiles have multiple tasks)
            if visited_tasks:
                all_cycle_tasks = []
                for task in visited_tasks:
                    all_cycle_tasks.extend(tasks_by_tile[task.tile_id])
                
                cycle_exit_idx = len(route) - 1
                cycle = TaskCycle(tasks=all_cycle_tasks)
                cycle.entry_index = cycle_entry_idx
                cycle.exit_index = cycle_exit_idx
                cycle.internal_route = route[cycle_entry_idx:cycle_exit_idx + 1]
                cycle.entry_tile = route[cycle_entry_idx]
                cycle.exit_tile = route[cycle_exit_idx]
                cycle.total_distance = cycle_exit_idx - cycle_entry_idx
                
                # Store connector from previous position to this cycle's entry
                if cycles:  # Not the first cycle
                    prev_exit = cycles[-1].exit_index
                    cycles[-1].connector_to_next = route[prev_exit:cycle_entry_idx + 1]
                
                cycles.append(cycle)
        
        return route, cycles
    
    def _best_path_to_task(self, current_tile: str, task: Task) -> Optional[List[str]]:
        candidates = self._adjacent_water_ids(task.tile_id)
        best_path: Optional[List[str]] = None

        for candidate in candidates:
            path = self.distance_calc.get_shortest_path(current_tile, candidate)
            if path and (not best_path or (len(path), candidate) < (len(best_path), best_path[-1])):
                best_path = path

        return best_path

    def _adjacent_water_ids(self, tile_id: str) -> List[str]:
        """Get sorted list of adjacent water tile IDs."""
        tile = self.grid.get_tile(tile_id)
        if not tile:
            return []
        water_ids: List[str] = []
        for neighbor_id in tile.neighbors:
            neighbor_tile = self.grid.get_tile(neighbor_id)
            if neighbor_tile and neighbor_tile.is_water():
                water_ids.append(neighbor_id)
        water_ids.sort()
        return water_ids

    def _task_land_distance(self, first_tile_id: str, second_tile_id: str) -> Optional[int]:
        """Calculate hex distance between two land tiles (for clustering)."""
        if first_tile_id == second_tile_id:
            return 0

        key: Tuple[str, str]
        if first_tile_id <= second_tile_id:
            key = (first_tile_id, second_tile_id)
        else:
            key = (second_tile_id, first_tile_id)
        if key in self._task_distance_cache:
            return self._task_distance_cache[key]

        # Use hex coordinate distance for clustering (Manhattan distance on hex grid)
        first_tile = self.grid.get_tile(first_tile_id)
        second_tile = self.grid.get_tile(second_tile_id)
        
        if not first_tile or not second_tile:
            self._task_distance_cache[key] = None
            return None
        
        # Hex Manhattan distance
        q1, r1 = first_tile.coords
        q2, r2 = second_tile.coords
        distance = abs(q1 - q2) + abs(r1 - r2)
        
        self._task_distance_cache[key] = distance
        return distance

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

    def _realign_cycles_to_route(self, route: List[str]) -> None:
        """Reconcile cycle segments with the final repaired route."""
        if not route or not self.cycles:
            return

        search_start = 0

        for idx, cycle in enumerate(self.cycles):
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
        """Return the first index of ``tile_id`` in ``route`` at or after ``start``."""
        if tile_id is None:
            return None
        try:
            return route.index(tile_id, max(0, start))
        except ValueError:
            return None

    def _find_task_index(self, route: List[str], cycle: TaskCycle, start: int, reverse: bool = False) -> Optional[int]:
        """Locate index of any tile adjacent to a task, searching forward or backward."""
        task_ids = cycle.get_task_tile_ids()
        task_set = set(task_ids)
        indices = range(len(route) - 1, max(0, start) - 1, -1) if reverse else range(max(0, start), len(route))
        
        for idx in indices:
            tile_id = route[idx]
            if tile_id in task_set or (tile := self.grid.get_tile(tile_id)) and any(task_id in tile.neighbors for task_id in task_ids):
                return idx
        return None

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

    def __str__(self) -> str:
        """String representation of heuristic solver."""
        return f"CycleHeuristic: {len(self.cycles)} cycles, {len(self.task_manager.tasks)} tasks"

