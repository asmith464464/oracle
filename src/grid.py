"""
Graph representation, node classes, and adjacency handling for hex-grid maps.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import networkx as nx

class TileType(Enum):
    """Enumeration of tile types on the hex grid."""
    WATER = "water"
    MONSTER = "monster"
    OFFERING = "offering"
    STATUE_SOURCE = "statue_source"
    STATUE_ISLAND = "statue_island"
    TEMPLE = "temple"
    SHRINE = "shrine"


# Hex grid neighbor offsets (axial coordinates)
HEX_OFFSETS_EVEN = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
HEX_OFFSETS_ODD = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]


@dataclass
class Tile:
    """Represents a single tile on the hex grid."""
    id: str
    tile_type: TileType
    coords: Tuple[int, int]
    colours: Tuple[str, ...] = field(default_factory=tuple)

    def is_water(self) -> bool:
        """Check if this tile is water (traversable)."""
        return self.tile_type == TileType.WATER

    @classmethod
    def from_dict(cls, data: Dict) -> 'Tile':
        """Create tile from dictionary."""
        return cls(
            id=data['id'],
            tile_type=TileType(data['type']),
            colours=tuple(data.get('colours', [])),
            coords=tuple(data['coords'])
        )


# Hardcoded constants for map1.json
ZEUS_TILE_ID = "tile_043"


class HexGrid:
    """Represents the hex-grid map with tiles and pathfinding capabilities."""
    
    def __init__(self):
        self.tiles: Dict[str, Tile] = {}
        self.zeus_tile_id: str = ZEUS_TILE_ID  # Starting/ending position for map1.json
        self._coord_to_id: Dict[Tuple[int, int], str] = {}
        
    def add_tile(self, tile: Tile) -> None:
        """Add a tile to the grid."""
        self.tiles[tile.id] = tile
        self._coord_to_id[tile.coords] = tile.id
        
    def get_tile(self, tile_id: str) -> Optional[Tile]:
        """Get a tile by ID."""
        return self.tiles.get(tile_id)
    
    def get_neighbours(self, tile_id: str) -> List[str]:
        """Get neighbour IDs for a tile, computed from coordinates."""
        tile = self.get_tile(tile_id)
        if not tile:
            return []
        
        col, row = tile.coords
        offsets = HEX_OFFSETS_EVEN if row % 2 == 0 else HEX_OFFSETS_ODD
        return sorted([
            self._coord_to_id[neighbour_coord]
            for dx, dy in offsets
            if (neighbour_coord := (col + dx, row + dy)) in self._coord_to_id
        ])
        
    def set_zeus_tile(self, tile_id: str) -> None:
        """Set the starting/ending tile (Zeus)."""
        if tile_id in self.tiles:
            self.zeus_tile_id = tile_id
            
    def get_zeus_tile(self) -> Optional[Tile]:
        """Get the Zeus tile (starting/ending position)."""
        return self.get_tile(self.zeus_tile_id)
            
    @classmethod
    def from_json(cls, filepath: str) -> 'HexGrid':
        """Load grid from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        grid = cls()
        for tile_data in data.get('tiles', []):
            tile = Tile.from_dict(tile_data)
            grid.add_tile(tile)

        # Set Zeus tile
        if 'zeus_tile' in data:
            grid.set_zeus_tile(data['zeus_tile'])
            
        return grid
        
    def __str__(self) -> str:
        """String representation of the grid."""
        water_count = sum(1 for t in self.tiles.values() if t.is_water())
        task_count = sum(1 for t in self.tiles.values() if not t.is_water())
        return f"HexGrid: {len(self.tiles)} tiles ({water_count} water, {task_count} tasks)"

class DistanceCalculator:
    """Handles shortest path calculations on the hex grid."""
    
    def __init__(self, grid: HexGrid):
        self.grid = grid
        self.water_graph = self._build_water_graph()
        
    def _build_water_graph(self) -> nx.Graph:
        """Build graph connecting all water tiles from coordinates."""
        graph = nx.Graph()
        
        # Add all water tiles as nodes
        water_tiles = {tile.id: tile for tile in self.grid.tiles.values() if tile.is_water()}
        for tile_id in water_tiles:
            graph.add_node(tile_id)
        
        # Add edges between adjacent water tiles using coordinates
        for tile_id, tile in water_tiles.items():
            col, row = tile.coords
            offsets = HEX_OFFSETS_EVEN if row % 2 == 0 else HEX_OFFSETS_ODD
            
            for dx, dy in offsets:
                neighbour_coord = (col + dx, row + dy)
                if neighbour_coord in self.grid._coord_to_id:
                    neighbour_id = self.grid._coord_to_id[neighbour_coord]
                    if neighbour_id in water_tiles and tile_id < neighbour_id:  # Avoid duplicate edges
                        graph.add_edge(tile_id, neighbour_id, weight=1)
        
        return graph
            
    def get_shortest_path(self, from_tile_id: str, to_tile_id: str) -> Optional[List[str]]:
        """Get shortest path between two water tiles."""
        try:
            return nx.shortest_path(
                self.water_graph, from_tile_id, to_tile_id, weight='weight'
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
            
    def find_nearest_water_tiles(self, task_tile_id: str) -> List[Tuple[str, int]]:
        """Find water tiles adjacent to a task tile, with distances to other tiles."""
        adjacent_water = []
        for neighbour_id in self.grid.get_neighbours(task_tile_id):
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if neighbour_tile and neighbour_tile.is_water():
                adjacent_water.append((neighbour_id, 0))
        return adjacent_water