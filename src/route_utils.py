"""Common helpers for building and fixing hex-grid routes."""

from __future__ import annotations

from typing import List, Optional

from .map_model import HexGrid
from .distance_utils import DistanceCalculator


def append_path(route: List[str], path: Optional[List[str]]) -> None:
    if not path:
        return
    if route and route[-1] == path[0]:
        route.extend(path[1:])
    else:
        route.extend(path)


def combine_detour(to_path: Optional[List[str]], from_path: Optional[List[str]]) -> Optional[List[str]]:
    if not to_path or not from_path:
        return None
    to_segment = to_path[1:]
    from_segment = from_path[1:-1] if len(from_path) > 1 else []
    return to_segment + from_segment


def repair_route(grid: HexGrid, distance_calc: DistanceCalculator, route: List[str]) -> List[str]:
    """Insert shortest paths between non-adjacent tiles in route."""
    if not route:
        return []

    repaired: List[str] = [route[0]]

    for next_tile in route[1:]:
        current_tile = repaired[-1]

        # Skip duplicate tiles
        if next_tile == current_tile:
            continue

        # Check if tiles are adjacent
        current_tile_obj = grid.get_tile(current_tile)
        if current_tile_obj and next_tile in current_tile_obj.neighbors:
            repaired.append(next_tile)
            continue

        # Insert shortest path between non-adjacent tiles
        bridge = distance_calc.get_shortest_path(current_tile, next_tile)
        if not bridge:
            raise ValueError(f"No path from {current_tile} to {next_tile}")
        append_path(repaired, bridge)

    return repaired


def ensure_return_to_zeus(grid: HexGrid, distance_calc: DistanceCalculator, route: List[str]) -> List[str]:
    """Guarantee the route ends at Zeus; append the final leg when needed."""
    if not route:
        return route

    zeus_tile = grid.get_zeus_tile()
    if not zeus_tile:
        return route

    if route[-1] == zeus_tile.id:
        return route

    return_path = distance_calc.get_shortest_path(route[-1], zeus_tile.id)
    if not return_path:
        raise ValueError(
            f"Unable to return from {route[-1]} to Zeus"
        )

    append_path(route, return_path)
    return route
