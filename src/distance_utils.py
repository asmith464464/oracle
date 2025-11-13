"""
Shortest path calculations and distance utilities for hex-grid navigation.
"""

from typing import Dict, List, Optional, Tuple
import networkx as nx

from .map_model import HexGrid, Tile


class DistanceCalculator:
    """Handles shortest path calculations on the hex grid."""
    
    def __init__(self, grid: HexGrid):
        self.grid = grid
        self.water_graph = self._build_water_graph()
        self._distance_cache: Dict[Tuple[str, str], Optional[int]] = {}
        self._path_cache: Dict[Tuple[str, str], Optional[List[str]]] = {}
        
    def _build_water_graph(self) -> nx.Graph:
        """Build graph connecting all water tiles."""
        graph = nx.Graph()
        
        # Add all water tiles as nodes
        for tile in self.grid.tiles.values():
            if tile.is_water():
                graph.add_node(tile.id)
        
        # Add edges between adjacent water tiles
        for tile in self.grid.tiles.values():
            if not tile.is_water():
                continue
            for neighbour_id in tile.neighbours:
                neighbour_tile = self.grid.get_tile(neighbour_id)
                if neighbour_tile and neighbour_tile.is_water():
                    graph.add_edge(tile.id, neighbour_id, weight=1)
        
        return graph
        
    def get_shortest_distance(self, from_tile_id: str, to_tile_id: str) -> Optional[int]:
        """Get shortest distance between two water tiles."""
        cache_key = (from_tile_id, to_tile_id)
        
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]

        try:
            distance = int(
                nx.shortest_path_length(
                    self.water_graph, from_tile_id, to_tile_id, weight='weight'
                )
            )
            self._distance_cache[cache_key] = distance
            return distance
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self._distance_cache[cache_key] = None
            return None
            
    def get_shortest_path(self, from_tile_id: str, to_tile_id: str) -> Optional[List[str]]:
        """Get shortest path between two water tiles."""
        cache_key = (from_tile_id, to_tile_id)
        
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]
            
        try:
            path = nx.shortest_path(
                self.water_graph, from_tile_id, to_tile_id, weight='weight'
            )
            self._path_cache[cache_key] = path
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self._path_cache[cache_key] = None
            return None
            
    def get_distances_from_tile(self, from_tile_id: str) -> Dict[str, int]:
        """Get shortest distances from one tile to all other water tiles."""
        try:
            distances = nx.single_source_shortest_path_length(
                self.water_graph, from_tile_id
            )
            return distances
        except nx.NodeNotFound:
            return {}
            
    def find_nearest_water_tiles(self, task_tile_id: str) -> List[Tuple[str, int]]:
        """Find water tiles adjacent to a task tile, with distances to other tiles."""
        task_tile = self.grid.get_tile(task_tile_id)
        if not task_tile:
            return []
            
        adjacent_water = []
        for neighbour_id in task_tile.neighbours:
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if neighbour_tile and neighbour_tile.is_water():
                adjacent_water.append((neighbour_id, 0))  # Distance 0 since we're adjacent
                
        return adjacent_water
        
    def is_reachable(self, from_tile_id: str, to_tile_id: str) -> bool:
        """Check if one water tile is reachable from another."""
        return self.get_shortest_distance(from_tile_id, to_tile_id) is not None
        
    def get_reachable_tiles(self, from_tile_id: str, max_distance: int) -> List[str]:
        """Get all water tiles reachable within a maximum distance."""
        distances = self.get_distances_from_tile(from_tile_id)
        return [
            tile_id for tile_id, distance in distances.items() 
            if distance <= max_distance
        ]
        
    def clear_cache(self) -> None:
        """Clear distance and path caches."""
        self._distance_cache.clear()
        self._path_cache.clear()