"""
Helper functions: coordinate conversions, logging, random colour assignment.
"""

import random
import logging
from typing import List, Tuple, Dict, Optional, Set
import json
from pathlib import Path

import numpy as np
from hexalattice import hexalattice

from .map_model import HexGrid, Tile, TileType


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Set up logging configuration."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def generate_random_colours(num_colours: int = 3, 
                          available_colours: Optional[List[str]] = None,
                          deterministic: bool = False) -> List[str]:
    """Generate random colour selection.
    
    Args:
        num_colours: Number of colours to select
        available_colours: Available colours to choose from
        deterministic: If True, sort and take first N instead of random sampling
    """
    if available_colours is None:
        available_colours = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'cyan', 'magenta']
    
    if len(available_colours) < num_colours:
        raise ValueError(f"Not enough available colours ({len(available_colours)}) for selection ({num_colours})")
    
    if deterministic:
        return sorted(available_colours)[:num_colours]
    return random.sample(available_colours, num_colours)


def _build_lattice_neighbors(points: np.ndarray) -> List[List[int]]:
    """Create adjacency lists for each lattice point based on geometric proximity."""
    total = len(points)
    if total == 0:
        return []

    distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
    np.fill_diagonal(distances, np.inf)

    finite_distances = distances[np.isfinite(distances)]
    if finite_distances.size == 0:
        return [[] for _ in range(total)]

    neighbor_threshold = float(finite_distances.min()) * 1.05
    return [np.where(row <= neighbor_threshold)[0].tolist() for row in distances]





def create_example_map(
    width: int = 10,
    height: int = 8,
    water_ratio: float = 0.6,
    max_attempts: int = 60,
) -> HexGrid:
    """Create an example hex grid map with simple random tile placement."""
    if width <= 0 or height <= 0:
        raise ValueError("Map dimensions must be positive")

    # Build hex lattice structure
    lattice_points, _ = hexalattice.create_hex_grid(
        nx=width, ny=height, do_plot=False, align_to_origin=True
    )
    neighbor_lookup = _build_lattice_neighbors(np.asarray(lattice_points, dtype=float))

    total_tiles = width * height
    tile_ids = [f"tile_{i:03d}" for i in range(total_tiles)]
    tile_coords = {i: (i % width, i // width) for i in range(total_tiles)}
    
    center_index = (height // 2) * width + (width // 2)
    center_tile_id = tile_ids[center_index]

    # Validate map size
    if total_tiles < 46:  # 36 land + 3 shrines + some water
        raise ValueError("Map dimensions too small for required task allocation")

    # Define exact tile distribution (6 colours each)
    all_colours = ['red', 'blue', 'green', 'yellow', 'purple', 'pink']
    
    for attempt in range(1, max_attempts + 1):
        grid = HexGrid()
        
        # Randomly select 36 non-center tiles for land
        available_indices = [i for i in range(total_tiles) if i != center_index]
        random.shuffle(available_indices)
        land_indices = set(available_indices[:36])
        
        # Build tile specs: exactly 36 tiles with predefined colour patterns
        tile_specs = []
        
        # 6 statue sources + 6 temples (1 per colour)
        for colour in all_colours:
            tile_specs.extend([(TileType.STATUE_SOURCE, colour), (TileType.TEMPLE, colour)])
        
        # 6 single-colour monsters + 3 dual-colour monsters
        tile_specs.extend((TileType.MONSTER, colour) for colour in all_colours)
        tile_specs.extend([
            (TileType.MONSTER, f"{all_colours[i]},{all_colours[i+3]}")
            for i in range(3)
        ])
        
        # 6 dual-colour offerings
        offering_pairs = [(0,1), (0,2), (1,3), (2,4), (3,5), (4,5)]
        tile_specs.extend(
            (TileType.OFFERING, f"{all_colours[i]},{all_colours[j]}")
            for i, j in offering_pairs
        )
        
        # 6 triple-colour statue islands
        island_triplets = [(0,1,2), (0,3,4), (0,4,5), (1,3,5), (1,2,4), (2,3,5)]
        tile_specs.extend(
            (TileType.STATUE_ISLAND, f"{all_colours[i]},{all_colours[j]},{all_colours[k]}")
            for i, j, k in island_triplets
        )
        
        # 3 shrines (no colours)
        tile_specs.extend((TileType.SHRINE, None) for _ in range(3))
        
        # Assign tile specs to random land indices
        land_list = list(land_indices)
        for idx_pos, (tile_type, colour_str) in enumerate(tile_specs):
            tile_idx = land_list[idx_pos]
            
            # Parse colour string into tuple
            colours = tuple(colour_str.split(',')) if colour_str and ',' in colour_str else \
                     (colour_str,) if colour_str else ()
            
            grid.add_tile(Tile(
                id=tile_ids[tile_idx],
                tile_type=tile_type,
                coords=tile_coords[tile_idx],
                neighbors=[tile_ids[n] for n in neighbor_lookup[tile_idx]],
                colours=colours
            ))
        
        # Create water tiles for non-land indices
        existing_tile_ids = set(grid.tiles.keys())
        for idx in range(total_tiles):
            if tile_ids[idx] not in existing_tile_ids:
                grid.add_tile(Tile(
                    id=tile_ids[idx],
                    tile_type=TileType.WATER,
                    coords=tile_coords[idx],
                    neighbors=[tile_ids[n] for n in neighbor_lookup[idx]],
                    colours=()
                ))
        
        grid.set_zeus_tile(center_tile_id)
        grid.ensure_task_accessibility()  # Converts tiles to water if needed
        
        # Validate
        issues = grid.validate_grid()
        eligible_colours = find_colours_with_required_tasks(grid)
        if len(eligible_colours) < 6:
            issues.append(f"Only {len(eligible_colours)} eligible colours (need 6)")
        
        if not issues:
            return grid
        
        logging.warning(
            "Map generation attempt %s failed: %s", attempt, issues
        )
    
    raise ValueError("Unable to generate valid map after multiple attempts")


def load_map_from_json(filepath: str) -> HexGrid:
    """Load a hex grid map from JSON file."""
    return HexGrid.from_json(filepath)


def format_route_summary(route: List[str], total_moves: int, total_turns: int,
                        completed_tasks: List[str], shrines_built: List[str]) -> str:
    """Format a human-readable route summary."""
    lines = [
        "Route Summary:",
        f"  Total moves: {total_moves}",
        f"  Total turns: {total_turns}",
        f"  Route length: {len(route)} positions",
        f"  Tasks completed: {len(completed_tasks)}",
        f"  Shrines built: {len(shrines_built)}",
    ]
    
    if completed_tasks:
        lines.append(f"  Completed tasks: {', '.join(completed_tasks[:5])}")
        if len(completed_tasks) > 5:
            lines.append(f"    ... and {len(completed_tasks) - 5} more")
    
    if shrines_built:
        lines.append(f"  Shrines built: {', '.join(shrines_built)}")
    
    return '\n'.join(lines)


def calculate_efficiency_metrics(total_moves: int, total_turns: int,
                               tasks_completed: int, shrines_built: int) -> Dict[str, float]:
    """Calculate efficiency metrics for a route."""
    metrics = {}
    
    # Basic efficiency
    metrics['moves_per_turn'] = total_moves / max(1, total_turns)
    metrics['tasks_per_turn'] = tasks_completed / max(1, total_turns)
    metrics['moves_per_task'] = total_moves / max(1, tasks_completed)
    
    # Optimization scores
    metrics['turn_efficiency'] = min(1.0, total_moves / (total_turns * 3))  # How well we use each turn
    metrics['task_density'] = tasks_completed / max(1, total_moves)  # Tasks per move
    
    # Shrine efficiency
    metrics['shrine_efficiency'] = shrines_built / max(1, total_turns)
    
    return metrics


def export_results_to_json(results: Dict, filepath: str) -> None:
    """Export results to JSON file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)


def generate_unique_id() -> str:
    """Generate a unique identifier for runs."""
    import time
    return f"run_{int(time.time())}_{random.randint(1000, 9999)}"


def create_colour_assignment_report(grid: HexGrid, selected_colours: List[str]) -> Dict:
    """Create a report on colour assignment and task distribution."""
    distribution = {}
    for colour in selected_colours:
        tiles = grid.get_tiles_by_colour(colour)
        type_dist = {}
        for tile in tiles:
            type_dist[tile.tile_type.value] = type_dist.get(tile.tile_type.value, 0) + 1
        distribution[colour] = type_dist
    
    return {
        'selected_colours': selected_colours,
        'available_colours': list(grid.get_available_colours()),
        'distribution': distribution
    }


def find_colours_with_required_tasks(
    grid: HexGrid,
    required_types: Optional[Set[TileType]] = None,
) -> List[str]:
    """Return colours that provide at least one tile for each required task type."""
    if required_types is None:
        required_types = {TileType.MONSTER, TileType.OFFERING, TileType.STATUE_SOURCE, TileType.STATUE_ISLAND, TileType.TEMPLE}
    
    return [
        colour for colour in grid.get_available_colours()
        if required_types.issubset({tile.tile_type for tile in grid.get_tiles_by_colour(colour)})
    ]
