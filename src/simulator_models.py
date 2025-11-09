"""Data containers for the route simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .tasks import PlayerState


@dataclass
class SimulationStep:
    step_number: int
    current_tile_id: str
    action_type: str
    action_target: Optional[str] = None
    moves_used: int = 0
    turn_number: int = 0
    player_state_snapshot: Optional[Dict] = None

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"Step {self.step_number}: {self.action_type} at {self.current_tile_id}"


@dataclass
class SimulationResult:
    success: bool
    total_moves: int
    total_turns: int
    steps: List[SimulationStep]
    final_player_state: PlayerState
    completed_tasks: List[str]
    shrines_built: List[str]
    errors: List[str]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        status = "SUCCESS" if self.success else "FAILED"
        return f"Simulation {status}: {self.total_moves} moves, {self.total_turns} turns"
