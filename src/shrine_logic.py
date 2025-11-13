"""Shared helper logic for shrine optimization workflows."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from .distance_utils import DistanceCalculator
from .map_model import HexGrid
from .route_utils import append_path, combine_detour, repair_route
from .shrine_models import ShrineOpportunity


def find_shrine_opportunities(
    distance_calc: DistanceCalculator,
    route: Sequence[str],
    shrine_candidates: Iterable,
) -> List[ShrineOpportunity]:
    """Locate shrine builds that fit inside existing wasted moves."""
    opportunities: List[ShrineOpportunity] = []
    
    # Pre-compute water access for each shrine once
    shrine_water_access = {
        shrine.id: distance_calc.find_nearest_water_tiles(shrine.id)
        for shrine in shrine_candidates
    }

    for index in range(len(route) - 1):
        current_pos = route[index]
        next_pos = route[index + 1]

        moves_to_next = distance_calc.get_shortest_distance(current_pos, next_pos)
        if moves_to_next is None:
            continue

        current_turn_moves = (index % 3) + 1
        remaining_moves = 3 - current_turn_moves
        if remaining_moves <= moves_to_next:
            continue

        wasted_moves = remaining_moves - moves_to_next
        for shrine_tile in shrine_candidates:
            for water_pos, _ in shrine_water_access[shrine_tile.id]:
                to_shrine = distance_calc.get_shortest_distance(current_pos, water_pos)
                from_shrine = distance_calc.get_shortest_distance(water_pos, next_pos)
                if to_shrine is None or from_shrine is None:
                    continue

                total_detour = to_shrine + from_shrine - moves_to_next
                if total_detour <= wasted_moves:
                    opportunities.append(
                        ShrineOpportunity(
                            shrine_tile_id=shrine_tile.id,
                            route_position=index,
                            detour_cost=max(0, total_detour),
                            wasted_moves_used=min(wasted_moves, to_shrine + from_shrine),
                        )
                    )

    return opportunities


def select_optimal_shrines(
    opportunities: List[ShrineOpportunity],
    max_shrines: int,
) -> List[ShrineOpportunity]:
    """Pick the best shrine placements by efficiency without conflicts."""
    if not opportunities:
        return []

    opportunities.sort(key=lambda opp: opp.efficiency_score(), reverse=True)

    selected: List[ShrineOpportunity] = []
    used_shrines = set()
    used_positions = set()

    for opportunity in opportunities:
        if len(selected) >= max_shrines:
            break
        if opportunity.shrine_tile_id in used_shrines:
            continue
        if opportunity.route_position in used_positions:
            continue

        selected.append(opportunity)
        used_shrines.add(opportunity.shrine_tile_id)
        used_positions.add(opportunity.route_position)

    return selected


def insert_shrines_into_route(
    grid: HexGrid,
    distance_calc: DistanceCalculator,
    route: Sequence[str],
    shrine_opportunities: List[ShrineOpportunity],
) -> Tuple[List[str], List[str]]:
    """Insert shrine detours into the existing route."""
    if not shrine_opportunities:
        return list(route), []

    new_route = list(route)
    shrine_positions: List[str] = []

    for opportunity in sorted(shrine_opportunities, key=lambda opp: opp.route_position, reverse=True):
        pos = opportunity.route_position
        shrine_tile = grid.get_tile(opportunity.shrine_tile_id)
        if not shrine_tile:
            continue

        shrine_water = distance_calc.find_nearest_water_tiles(shrine_tile.id)
        if not shrine_water:
            continue

        best_water_pos = shrine_water[0][0]
        current_pos = new_route[pos]
        next_pos = new_route[pos + 1]

        detour = combine_detour(
            distance_calc.get_shortest_path(current_pos, best_water_pos),
            distance_calc.get_shortest_path(best_water_pos, next_pos),
        )
        if not detour:
            continue

        new_route[pos + 1 : pos + 1] = detour
        shrine_positions.append(opportunity.shrine_tile_id)

    return new_route, shrine_positions


def add_remaining_shrines(
    grid: HexGrid,
    distance_calc: DistanceCalculator,
    route: Sequence[str],
    shrine_candidates: Iterable,
    already_placed: Sequence[str],
    remaining_count: int,
) -> Tuple[List[str], List[str]]:
    """Append extra shrines near the route endpoint with minimal travel."""
    if remaining_count <= 0:
        return list(route), []

    available = [shrine for shrine in shrine_candidates if shrine.id not in already_placed]
    if not available:
        return list(route), []

    end_position = route[-1]
    
    # Rank shrines by distance to end position
    ranked = [
        (shrine.id, min(
            (distance_calc.get_shortest_distance(end_position, water_pos) or float("inf"))
            for water_pos, _ in distance_calc.find_nearest_water_tiles(shrine.id)
        ), min(
            distance_calc.find_nearest_water_tiles(shrine.id),
            key=lambda x: distance_calc.get_shortest_distance(end_position, x[0]) or float("inf"),
            default=(None, None)
        )[0])
        for shrine in available
    ]
    
    # Filter out shrines with no valid water access
    ranked = [(shrine_id, dist, water_pos) for shrine_id, dist, water_pos in ranked 
             if water_pos is not None and dist != float("inf")]
    ranked.sort(key=lambda item: item[1])

    extended_route = list(route)
    added: List[str] = []

    for shrine_id, _, water_pos in ranked[:remaining_count]:
        to_shrine = distance_calc.get_shortest_path(extended_route[-1], water_pos)
        if to_shrine:
            append_path(extended_route, to_shrine)
            added.append(shrine_id)

    return repair_route(grid, distance_calc, extended_route), added
