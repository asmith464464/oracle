"""Model definitions used by the shrine optimizer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShrineOpportunity:
    shrine_tile_id: str
    route_position: int
    detour_cost: int
    wasted_moves_used: int

    def efficiency_score(self) -> float:
        if self.detour_cost == 0:
            return float("inf")
        return self.wasted_moves_used / self.detour_cost
