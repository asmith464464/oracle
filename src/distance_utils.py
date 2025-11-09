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
        self.graph, self.water_graph, self._tile_is_water = self._build_graphs()
        self._distance_cache: Dict[Tuple[str, str], Optional[int]] = {}
        self._path_cache: Dict[Tuple[str, str], Optional[List[str]]] = {}
        
    def _build_graphs(self) -> Tuple[nx.Graph, nx.Graph, Dict[str, bool]]:
        """Build traversal graphs for water-only and mixed tile routing."""
        full_graph = nx.Graph()
        water_flags: Dict[str, bool] = {}

        def _register_tile(tile: Tile) -> None:
            full_graph.add_node(tile.id, is_water=tile.is_water())
            water_flags[tile.id] = tile.is_water()

        for tile in self.grid.tiles.values():
            _register_tile(tile)

        for tile in self.grid.tiles.values():
            for neighbor_id in tile.neighbors:
                neighbor_tile = self.grid.get_tile(neighbor_id)
                if not neighbor_tile:
                    continue

                if tile.is_water() and neighbor_tile.is_water():
                    full_graph.add_edge(tile.id, neighbor_id, weight=1)
                elif tile.is_water() or neighbor_tile.is_water():
                    # Permit transitions between land endpoints and adjacent water.
                    full_graph.add_edge(tile.id, neighbor_id, weight=1)

        water_nodes = [tile_id for tile_id, is_water in water_flags.items() if is_water]
        water_graph = full_graph.subgraph(water_nodes).copy()

        return full_graph, water_graph, water_flags
        
    def get_shortest_distance(self, from_tile_id: str, to_tile_id: str) -> Optional[int]:
        """Get shortest distance between two water tiles."""
        cache_key = (from_tile_id, to_tile_id)
        
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]
        graph = self._select_graph(from_tile_id, to_tile_id)

        try:
            distance = int(
                nx.shortest_path_length(
                    graph, from_tile_id, to_tile_id, weight='weight'
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
        graph = self._select_graph(from_tile_id, to_tile_id)
            
        try:
            path = nx.shortest_path(
                graph, from_tile_id, to_tile_id, weight='weight'
            )
            self._path_cache[cache_key] = path
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self._path_cache[cache_key] = None
            return None
            
    def get_distances_from_tile(self, from_tile_id: str) -> Dict[str, int]:
        """Get shortest distances from one tile to all other water tiles."""
        graph = self.water_graph if self._tile_is_water.get(from_tile_id) else self.graph
        try:
            distances = nx.single_source_shortest_path_length(
                graph, from_tile_id
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
        for neighbor_id in task_tile.neighbors:
            neighbor_tile = self.grid.get_tile(neighbor_id)
            if neighbor_tile and neighbor_tile.is_water():
                adjacent_water.append((neighbor_id, 0))  # Distance 0 since we're adjacent
                
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
                    
    def __str__(self) -> str:
        """String representation of distance calculator."""
        return f"DistanceCalculator: {self.graph.number_of_nodes()} tiles, {self.graph.number_of_edges()} connections"

    def _select_graph(self, from_tile_id: str, to_tile_id: str) -> nx.Graph:
        if self._tile_is_water.get(from_tile_id) and self._tile_is_water.get(to_tile_id):
            return self.water_graph
        return self.graph