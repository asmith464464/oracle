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
    if not route:
        return []

    repaired: List[str] = [route[0]]
    zeus = grid.zeus_tile_id

    for next_tile in route[1:]:
        current_tile = repaired[-1]

        if next_tile == current_tile:
            continue

        next_obj = grid.get_tile(next_tile)
        if next_obj and not next_obj.is_water() and next_tile != zeus:
            if _reroute_via_water(grid, distance_calc, repaired, current_tile, next_tile):
                continue
            raise ValueError(
                f"Route includes land tile {next_tile} that is unreachable from {current_tile}"
            )

        if _tiles_adjacent(grid, current_tile, next_tile):
            repaired.append(next_tile)
            continue

        bridge = distance_calc.get_shortest_path(current_tile, next_tile)
        if not bridge:
            raise ValueError(f"No adjacent path from {current_tile} to {next_tile}")
        append_path(repaired, bridge)

    return repaired


def _tiles_adjacent(grid: HexGrid, first: str, second: str) -> bool:
    tile = grid.get_tile(first)
    return bool(tile and second in tile.neighbors)


def _reroute_via_water(
    grid: HexGrid,
    distance_calc: DistanceCalculator,
    route: List[str],
    current_tile: str,
    land_tile: str,
) -> bool:
    for neighbor in grid.get_adjacent_water_tiles(land_tile):
        bridge = distance_calc.get_shortest_path(current_tile, neighbor.id)
        if bridge:
            append_path(route, bridge)
            return True
    return False


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
