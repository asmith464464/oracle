"""
Graph representation, node classes, and adjacency handling for hex-grid maps.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json


class TileType(Enum):
    """Enumeration of tile types on the hex grid."""
    WATER = "water"
    MONSTER = "monster"
    OFFERING = "offering"
    STATUE_SOURCE = "statue_source"
    STATUE_ISLAND = "statue_island"
    TEMPLE = "temple"
    SHRINE = "shrine"


@dataclass
class Tile:
    """Represents a single tile on the hex grid."""
    id: str
    tile_type: TileType
    coords: Tuple[int, int]
    neighbours: List[str]
    colours: Tuple[str, ...] = field(default_factory=tuple)

    def is_water(self) -> bool:
        """Check if this tile is water (traversable)."""
        return self.tile_type == TileType.WATER

    def to_dict(self, include_neighbours: bool = True) -> Dict:
        """Convert tile to dictionary for JSON serialization."""
        data = {
            'id': self.id,
            'type': self.tile_type.value,
            'colours': list(self.colours),
            'coords': self.coords,
        }
        if include_neighbours:
            data['neighbours'] = self.neighbours
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Tile':
        """Create tile from dictionary."""
        return cls(
            id=data['id'],
            tile_type=TileType(data['type']),
            colours=tuple(data.get('colours', [])),
            coords=tuple(data['coords']),
            neighbours=data.get('neighbours', [])
        )


class HexGrid:
    """Represents the hex-grid map with tiles and pathfinding capabilities."""
    
    def __init__(self):
        self.tiles: Dict[str, Tile] = {}
        self.zeus_tile_id: str = ""  # Starting/ending position
        
    def add_tile(self, tile: Tile) -> None:
        """Add a tile to the grid."""
        self.tiles[tile.id] = tile
        
    def get_tile(self, tile_id: str) -> Optional[Tile]:
        """Get a tile by ID."""
        return self.tiles.get(tile_id)
        
    def get_water_tiles(self) -> List[Tile]:
        """Get all water tiles (traversable)."""
        return [tile for tile in self.tiles.values() if tile.is_water()]
        
    def get_task_tiles(self) -> List[Tile]:
        """Get all task tiles (land)."""
        return [tile for tile in self.tiles.values() if not tile.is_water()]
        
    def get_tiles_by_type(self, tile_type: TileType) -> List[Tile]:
        """Get all tiles of a specific type."""
        return [tile for tile in self.tiles.values() if tile.tile_type == tile_type]
        
    def get_tiles_by_colour(self, colour: str) -> List[Tile]:
        """Get all tiles of a specific colour."""
        return [tile for tile in self.tiles.values() if colour in tile.colours]
        
    def get_neighbours(self, tile_id: str) -> List[Tile]:
        """Get neighbouring tiles of a given tile."""
        tile = self.get_tile(tile_id)
        if not tile:
            return []
        return [self.tiles[neighbour_id] for neighbour_id in tile.neighbours if neighbour_id in self.tiles]
        
    def get_adjacent_water_tiles(self, tile_id: str) -> List[Tile]:
        """Get water tiles adjacent to a given tile."""
        neighbours = self.get_neighbours(tile_id)
        return [tile for tile in neighbours if tile.is_water()]
        
    def set_zeus_tile(self, tile_id: str) -> None:
        """Set the starting/ending tile (Zeus)."""
        if tile_id in self.tiles:
            self.zeus_tile_id = tile_id
        else:
            raise ValueError(f"Tile {tile_id} not found in grid")
            
    def get_zeus_tile(self) -> Optional[Tile]:
        """Get the Zeus tile (starting/ending position)."""
        return self.get_tile(self.zeus_tile_id)
        
    def validate_grid(self) -> List[str]:
        """Validate the grid structure and return list of issues."""
        issues = []
        
        # Check if Zeus tile is set
        if not self.zeus_tile_id:
            issues.append("Zeus tile not set")
        elif self.zeus_tile_id not in self.tiles:
            issues.append(f"Zeus tile {self.zeus_tile_id} not found in grid")
            
        # Check neighbour references
        for tile_id, tile in self.tiles.items():
            for neighbour_id in tile.neighbours:
                if neighbour_id not in self.tiles:
                    issues.append(f"Tile {tile_id} references non-existent neighbour {neighbour_id}")
                    
        # Check that all water tiles are connected
        water_tiles = {tile.id for tile in self.get_water_tiles()}
        if water_tiles:
            connected = {next(iter(water_tiles))}
            stack = list(connected)
            
            while stack:
                current_id = stack.pop()
                current_tile = self.get_tile(current_id)
                if current_tile:
                    for neighbour_id in current_tile.neighbours:
                        if neighbour_id in water_tiles and neighbour_id not in connected:
                            connected.add(neighbour_id)
                            stack.append(neighbour_id)
                            
            if len(connected) != len(water_tiles):
                issues.append("Not all water tiles are connected")

        per_colour_requirements = {
            TileType.MONSTER: 2,
            TileType.OFFERING: 2,
            TileType.STATUE_SOURCE: 1,
            TileType.STATUE_ISLAND: 3,
            TileType.TEMPLE: 1,
        }

        available_colours = sorted(self.get_available_colours())
        colour_counts: Dict[str, Dict[TileType, int]] = {
            colour: {tile_type: 0 for tile_type in per_colour_requirements}
            for colour in available_colours
        }

        for tile in self.tiles.values():
            if tile.tile_type not in per_colour_requirements:
                continue
            for colour in tile.colours:
                if colour not in colour_counts:
                    colour_counts[colour] = {
                        tile_type: 0 for tile_type in per_colour_requirements
                    }
                colour_counts[colour][tile.tile_type] += 1

        for colour, counts in colour_counts.items():
            for tile_type, required in per_colour_requirements.items():
                if counts.get(tile_type, 0) < required:
                    issues.append(
                        f"Colour '{colour}' has {counts.get(tile_type, 0)} "
                        f"{tile_type.value.replace('_', ' ')} tiles; {required} required"
                    )
                
        return issues
        
    def to_json(self, filepath: str, include_neighbours: bool = True) -> None:
        """Save grid to JSON file."""
        data = {
            'zeus_tile': self.zeus_tile_id,
            'tiles': [tile.to_dict(include_neighbours=include_neighbours) for tile in self.tiles.values()]
        }
        if not include_neighbours:
            data['infer_neighbours'] = True
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    @classmethod
    def from_json(cls, filepath: str) -> 'HexGrid':
        """Load grid from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        grid = cls()
        tile_entries = data.get('tiles', [])
        infer_neighbours = data.get('infer_neighbours', False)
        neighbours_missing = any('neighbours' not in tile_data for tile_data in tile_entries)

        for tile_data in tile_entries:
            tile = Tile.from_dict(tile_data)
            grid.add_tile(tile)
        
        if infer_neighbours or neighbours_missing:
            grid.recompute_neighbours_from_coords()

        # Set Zeus tile
        if 'zeus_tile' in data:
            grid.set_zeus_tile(data['zeus_tile'])

        grid.ensure_task_accessibility()
            
        return grid
        
    def get_available_colours(self) -> Set[str]:
        """Get all colours present in the grid."""
        colours = set()
        for tile in self.tiles.values():
            for colour in tile.colours:
                colours.add(colour)
        return colours

    def ensure_task_accessibility(self) -> None:
        """Ensure every task tile has at least one adjacent water tile."""
        task_tiles = list(self.get_task_tiles())

        for tile in task_tiles:
            neighbours = self.get_neighbours(tile.id)
            if any(neighbour.is_water() for neighbour in neighbours):
                continue

            converted = False
            for neighbour in neighbours:
                if neighbour.tile_type != TileType.WATER:
                    neighbour.tile_type = TileType.WATER
                    neighbour.colours = tuple()
                    converted = True
                    break

            if converted:
                continue

            if tile.id == self.zeus_tile_id and neighbours:
                continue

            tile.tile_type = TileType.WATER
            tile.colours = tuple()

    def recompute_neighbours_from_coords(self) -> None:
        """Rebuild neighbour lists based solely on stored coordinates."""
        coord_to_id = {tuple(tile.coords): tile_id for tile_id, tile in self.tiles.items()}
        even_row_offsets = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
        odd_row_offsets = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]

        for tile in self.tiles.values():
            col, row = tile.coords
            offsets = even_row_offsets if row % 2 == 0 else odd_row_offsets
            tile.neighbours = sorted([
                neighbour_id for dx, dy in offsets
                if (neighbour_id := coord_to_id.get((col + dx, row + dy)))
            ])
        
    def __str__(self) -> str:
        """String representation of the grid."""
        water_count = len(self.get_water_tiles())
        task_count = len(self.get_task_tiles())
        return f"HexGrid: {len(self.tiles)} tiles ({water_count} water, {task_count} tasks)"