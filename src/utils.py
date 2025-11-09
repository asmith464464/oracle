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
    adjacency: List[List[int]] = []
    for row in distances:
        neighbor_indices = np.where(row <= neighbor_threshold)[0]
        adjacency.append(neighbor_indices.tolist())
    return adjacency


def _select_land_tile(
    available_water: Set[int],
    reserved_water: Set[int],
    neighbor_lookup: List[List[int]],
    land_indices: Set[int],
    center_index: int,
    lattice_points: Optional[np.ndarray] = None,
) -> Optional[int]:
    """Select a water tile that can be converted to land while keeping adjacency to water.
    
    Prefers tiles further from center to spread out land tiles.
    """
    candidates = [idx for idx in available_water if idx not in reserved_water]
    if not candidates:
        return None

    # Filter to candidates that maintain water connectivity
    valid_candidates = []
    for idx in candidates:
        if any(n != center_index and n not in land_indices for n in neighbor_lookup[idx]):
            valid_candidates.append(idx)
    
    if not valid_candidates:
        valid_candidates = candidates
    
    # Prefer candidates further from center for better spread, but with randomness
    if lattice_points is not None and len(lattice_points) > center_index:
        center_pos = lattice_points[center_index]
        # Calculate distances from center
        distances = [(idx, np.linalg.norm(lattice_points[idx] - center_pos)) for idx in valid_candidates]
        
        # Use weighted random selection favoring further tiles
        # Weight = distance^2 to strongly prefer outer tiles while maintaining some randomness
        total_weight = sum(dist ** 2 for _, dist in distances)
        if total_weight > 0:
            r = random.uniform(0, float(total_weight))
            cumulative = 0
            for idx, dist in distances:
                cumulative += dist ** 2
                if cumulative >= r:
                    return idx
        
        # Fallback if all distances are 0
        random.shuffle(valid_candidates)
        return valid_candidates[0]
    
    random.shuffle(valid_candidates)
    return valid_candidates[0]


def _reserve_adjacent_water(
    tile_index: int,
    reserved_water: Set[int],
    neighbor_lookup: List[List[int]],
    land_indices: Set[int],
    center_index: int,
) -> bool:
    """Reserve a neighboring water tile to guarantee access for the selected land tile."""
    neighbors = neighbor_lookup[tile_index][:]
    random.shuffle(neighbors)

    for neighbor in neighbors:
        if neighbor == center_index or neighbor in land_indices:
            continue
        if neighbor not in reserved_water:
            reserved_water.add(neighbor)
            return True

    return False


def _add_land_tile(
    available_water: Set[int],
    reserved_water: Set[int],
    land_indices: Set[int],
    neighbor_lookup: List[List[int]],
    center_index: int,
    required_land_tiles: int,
    land_assignments: Dict[int, Tuple[TileType, Optional[str]]],
    tile_type: TileType,
    colours: Optional[str],
    lattice_points: Optional[np.ndarray] = None,
) -> bool:
    """Helper to add a land tile with common validation."""
    remaining_slots = required_land_tiles - len(land_assignments)
    convertible = len(available_water - reserved_water)
    if convertible < remaining_slots:
        return False

    idx = _select_land_tile(
        available_water,
        reserved_water,
        neighbor_lookup,
        land_indices,
        center_index,
        lattice_points,
    )
    if idx is None:
        return False

    available_water.remove(idx)
    land_indices.add(idx)
    land_assignments[idx] = (tile_type, colours)
    
    return _reserve_adjacent_water(
        idx,
        reserved_water,
        neighbor_lookup,
        land_indices,
        center_index,
    )


def create_example_map(
    width: int = 10,
    height: int = 8,
    water_ratio: float = 0.6,
    max_attempts: int = 60,
) -> HexGrid:
    """Create an example hex grid map for testing using hexalattice helpers."""

    if width <= 0 or height <= 0:
        raise ValueError("Map dimensions must be positive")

    lattice_points, _ = hexalattice.create_hex_grid(
        nx=width,
        ny=height,
        do_plot=False,
        align_to_origin=True,
    )
    lattice_points = np.asarray(lattice_points, dtype=float)
    neighbor_lookup = _build_lattice_neighbors(lattice_points)

    tile_ids = [f"tile_{index:03d}" for index in range(width * height)]
    tile_neighbors = {
        tile_ids[idx]: [tile_ids[n_idx] for n_idx in neighbor_lookup[idx]]
        for idx in range(len(tile_ids))
    }
    tile_coords = {idx: (idx % width, idx // width) for idx in range(len(tile_ids))}

    center_index = (height // 2) * width + (width // 2)
    center_tile_id = tile_ids[center_index]

    per_colour_requirements = {
        TileType.MONSTER: 2,
        TileType.OFFERING: 2,
        TileType.STATUE_SOURCE: 1,
        TileType.STATUE_ISLAND: 3,
        TileType.TEMPLE: 1,
    }
    shrine_count = 3
    total_tiles = width * height
    required_land_per_colour = sum(per_colour_requirements.values())
    # Need enough tiles for at least 3 colours with full requirements
    # Plus some extra tiles for distributing other colours
    min_required_tiles = required_land_per_colour * 3 + shrine_count + 10
    if total_tiles <= min_required_tiles:
        raise ValueError("Map dimensions too small for required task allocation")

    for attempt in range(1, max_attempts + 1):
        grid = HexGrid()

        available_water: Set[int] = {idx for idx in range(total_tiles) if idx != center_index}
        reserved_water: Set[int] = set()
        land_indices: Set[int] = set()
        
        # Create exact tile distribution:
        # 9 monsters, 6 offerings, 6 statue sources, 6 temples, 6 statue islands, 3 shrines
        land_assignments: Dict[int, Tuple[TileType, Optional[str]]] = {}
        all_colours = ['red', 'blue', 'green', 'yellow', 'purple', 'pink']
        success = True
        
        # Calculate land tiles needed: 9+6+6+6+6+3 = 36 tiles
        required_land_tiles = 36
        
        # Define all tile specifications: (tile_type, colour_spec)
        tile_specs = []
        
        # Phase 1: Single-colour tiles (statue sources and temples)
        for colour in all_colours:
            tile_specs.extend([(TileType.STATUE_SOURCE, colour), (TileType.TEMPLE, colour)])
        
        # Phase 2: Single-colour monsters (6 total)
        tile_specs.extend((TileType.MONSTER, colour) for colour in all_colours)
        
        # Phase 3: Dual-colour monsters (3 total)
        tile_specs.extend((TileType.MONSTER, f"{all_colours[i]},{all_colours[i+3]}") for i in range(3))
        
        # Phase 4: Dual-colour offerings (6 total)
        offering_pairs = [(0,1), (0,2), (1,3), (2,4), (3,5), (4,5)]
        tile_specs.extend((TileType.OFFERING, f"{all_colours[i]},{all_colours[j]}") for i, j in offering_pairs)
        
        # Phase 5: Triple-colour statue islands (6 total)
        island_triplets = [(0,1,2), (0,3,4), (0,4,5), (1,3,5), (1,2,4), (2,3,5)]
        tile_specs.extend((TileType.STATUE_ISLAND, f"{all_colours[i]},{all_colours[j]},{all_colours[k]}") for i, j, k in island_triplets)
        
        # Phase 6: Shrines (3 total, no colours)
        tile_specs.extend((TileType.SHRINE, None) for _ in range(shrine_count))
        
        # Create all tiles
        for tile_type, colours in tile_specs:
            if not _add_land_tile(
                available_water, reserved_water, land_indices,
                neighbor_lookup, center_index, required_land_tiles,
                land_assignments, tile_type, colours, lattice_points,
            ):
                success = False
                break
        
        if not success or len(land_assignments) != required_land_tiles:
            continue

        for idx, tile_id in enumerate(tile_ids):
            if idx == center_index:
                tile_type = TileType.WATER
                colour_str = None
            elif idx in land_assignments:
                tile_type, colour_str = land_assignments[idx]
            else:
                tile_type = TileType.WATER
                colour_str = None

            # Parse comma-separated colours
            if colour_str and ',' in colour_str:
                colour_tuple = tuple(colour_str.split(','))
            elif colour_str:
                colour_tuple = (colour_str,)
            else:
                colour_tuple = ()

            tile = Tile(
                id=tile_id,
                tile_type=tile_type,
                coords=tile_coords[idx],
                neighbors=list(tile_neighbors[tile_id]),
                colours=colour_tuple,
            )
            grid.add_tile(tile)

        grid.set_zeus_tile(center_tile_id)
        grid.ensure_task_accessibility()

        issues = grid.validate_grid()
        unreachable_tasks = [
            tile.id
            for tile in grid.get_task_tiles()
            if not any(neighbor.is_water() for neighbor in grid.get_neighbors(tile.id))
        ]
        if unreachable_tasks:
            issues.append(
                f"Task tiles without adjacent water: {len(unreachable_tasks)}"
            )
        eligible_colours = find_colours_with_required_tasks(grid)
        if len(eligible_colours) < 6:
            issues.append(
                f"Insufficient eligible colours with required tasks: {len(eligible_colours)} (need exactly 6)"
            )

        if not issues:
            # Success! Map has exactly 6 colours with complete task sets
            return grid

        logging.warning(
            "Example map generation attempt %s failed validation: issues=%s eligible_colours=%s",
            attempt,
            issues,
            len(eligible_colours),
        )

    raise ValueError("Unable to generate a valid example map after multiple attempts")


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
