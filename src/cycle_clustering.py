"""
Spatial clustering of tasks into cycles using k-means-like approach.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

from .tasks import Task
from .map_model import HexGrid


class CycleClusterer:
    """Handles spatial clustering of tasks into cycles."""
    
    def __init__(self, grid: HexGrid, distance_threshold: int = 6, max_tasks: int = 8):
        self.grid = grid
        self.distance_threshold = distance_threshold
        self.max_tasks = max_tasks
        self._distance_cache: Dict[Tuple[str, str], Optional[int]] = {}
    
    def cluster_tasks(self, tasks: List[Task]) -> List[List[Task]]:
        """Group tasks into spatially-balanced clusters using k-means-like approach."""
        if not tasks:
            return []
        
        n_tasks = len(tasks)
        distance_matrix = self._build_distance_matrix(tasks)
        target_clusters = max(2, (n_tasks + 3) // 4)
        
        seeds = self._select_cluster_seeds(tasks, distance_matrix, target_clusters)
        clusters = self._assign_tasks_to_clusters(tasks, distance_matrix, seeds)
        
        return [[tasks[i] for i in cluster] for cluster in clusters.values()]
    
    def _build_distance_matrix(self, tasks: List[Task]) -> np.ndarray:
        """Build distance matrix between task land tiles."""
        n_tasks = len(tasks)
        distance_matrix = np.zeros((n_tasks, n_tasks))
        
        for i in range(n_tasks):
            for j in range(i + 1, n_tasks):
                dist = self._hex_distance(tasks[i].tile_id, tasks[j].tile_id)
                if dist is None:
                    dist = 999
                distance_matrix[i, j] = dist
                distance_matrix[j, i] = dist
        
        return distance_matrix
    
    def _select_cluster_seeds(self, tasks: List[Task], distance_matrix: np.ndarray, 
                             target_clusters: int) -> List[int]:
        """Pick initial seeds: maximally spread out tasks."""
        seeds = []
        remaining = set(range(len(tasks)))
        
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
                if min_dist_to_seeds > best_min_dist or \
                   (min_dist_to_seeds == best_min_dist and 
                    (best_candidate is None or candidate < best_candidate)):
                    best_min_dist = min_dist_to_seeds
                    best_candidate = candidate
            
            if best_candidate is not None:
                seeds.append(best_candidate)
                remaining.remove(best_candidate)
        
        return seeds
    
    def _assign_tasks_to_clusters(self, tasks: List[Task], distance_matrix: np.ndarray,
                                  seeds: List[int]) -> Dict[int, List[int]]:
        """Assign each remaining task to nearest cluster, respecting distance threshold."""
        clusters = {seed: [seed] for seed in seeds}
        remaining = set(range(len(tasks))) - set(seeds)
        
        for task_idx in sorted(remaining):
            best_cluster = self._find_best_cluster(task_idx, distance_matrix, clusters, seeds)
            
            if best_cluster is not None:
                clusters[best_cluster].append(task_idx)
            else:
                # No cluster within threshold - create new single-task cluster
                clusters[task_idx] = [task_idx]
        
        return clusters
    
    def _find_best_cluster(self, task_idx: int, distance_matrix: np.ndarray,
                          clusters: Dict[int, List[int]], seeds: List[int]) -> Optional[int]:
        """Find nearest cluster where task is within threshold distance."""
        best_cluster = None
        best_min_dist = float('inf')
        
        for seed in seeds:
            if len(clusters[seed]) >= self.max_tasks:
                continue  # Cluster is full
            
            # Calculate minimum distance to any task in this cluster
            min_dist_to_cluster = min(distance_matrix[task_idx, t] for t in clusters[seed])
            
            # Only consider clusters where task is close enough
            if min_dist_to_cluster <= self.distance_threshold:
                if min_dist_to_cluster < best_min_dist or \
                   (min_dist_to_cluster == best_min_dist and 
                    (best_cluster is None or seed < best_cluster)):
                    best_min_dist = min_dist_to_cluster
                    best_cluster = seed
        
        return best_cluster
    
    def _hex_distance(self, first_tile_id: str, second_tile_id: str) -> Optional[int]:
        """Calculate hex coordinate distance between two land tiles."""
        if first_tile_id == second_tile_id:
            return 0
        
        # Use canonical ordering for cache key
        key = (first_tile_id, second_tile_id) if first_tile_id <= second_tile_id else \
              (second_tile_id, first_tile_id)
        
        if key in self._distance_cache:
            return self._distance_cache[key]
        
        first_tile = self.grid.get_tile(first_tile_id)
        second_tile = self.grid.get_tile(second_tile_id)
        
        if not first_tile or not second_tile:
            self._distance_cache[key] = None
            return None
        
        # Hex Manhattan distance
        q1, r1 = first_tile.coords
        q2, r2 = second_tile.coords
        distance = abs(q1 - q2) + abs(r1 - r2)
        
        self._distance_cache[key] = distance
        return distance
