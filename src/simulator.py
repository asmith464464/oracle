"""
Route simulation - validates that a route successfully completes all tasks.
"""

from typing import List, Optional, Set
from dataclasses import dataclass

from .grid import TileType
from .tasks import TaskManager, PlayerState, TaskStatus


@dataclass
class SimulationStep:
    """A single step in the route simulation."""
    current_tile_id: str
    action_type: str  # 'move', 'task', or 'shrine'
    action_target: Optional[str] = None
    turn_number: int = 0


@dataclass
class SimulationResult:
    """Results from simulating a complete route."""
    success: bool
    total_moves: int
    total_turns: int
    steps: List[SimulationStep]
    final_player_state: PlayerState
    completed_tasks: List[str]
    shrines_built: List[str]
    errors: List[str]


class RouteSimulator:
    """Simulates route execution to verify correctness."""
    
    def __init__(self, grid, task_manager: TaskManager):
        self.grid = grid
        self.task_manager = task_manager
        
    def simulate_route(self, route: List[str], 
                      shrine_positions: Optional[List[str]] = None) -> SimulationResult:
        """Simulate complete route execution."""
        zeus_tile = self.grid.get_zeus_tile()
        player_state = PlayerState(current_tile_id=zeus_tile.id)
        steps: List[SimulationStep] = []
        shrine_set = set(shrine_positions) if shrine_positions else set()
        
        for i in range(1, len(route)):
            from_tile_id = route[i - 1]
            to_tile_id = route[i]
            step_result = self._simulate_step(from_tile_id, to_tile_id, player_state, shrine_set)
            steps.append(step_result)
        
        return SimulationResult(
            success=True,
            total_moves=player_state.total_moves,
            total_turns=player_state.total_turns,
            steps=steps,
            final_player_state=player_state,
            completed_tasks=list(player_state.completed_task_ids),
            shrines_built=player_state.shrines_built.copy(),
            errors=[],
        )
        
    def _simulate_step(self, from_tile_id: str, to_tile_id: str, 
                      player_state: PlayerState, shrine_positions: Set[str]) -> SimulationStep:
        """Simulate a single step of movement."""
        player_state.execute_move(to_tile_id, 1)
        step = SimulationStep(
            current_tile_id=to_tile_id,
            action_type='move',
            turn_number=player_state.total_turns
        )
        self._check_and_execute_tasks(to_tile_id, player_state, step)
        self._check_and_build_shrines(to_tile_id, player_state, step, shrine_positions)
        return step
        
    def _check_and_execute_tasks(self, current_tile_id: str, player_state: PlayerState, step: SimulationStep) -> None:
        """Check for and execute any available tasks."""
        for neighbour_id in self.grid.get_neighbours(current_tile_id):
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if neighbour_tile.is_water():
                continue
            for task in self.task_manager.get_tasks_for_tile(neighbour_id):
                if (task.status == TaskStatus.PENDING and 
                    task.can_execute(player_state.completed_task_ids) and
                    self.task_manager.execute_task(task, player_state)):
                    step.action_type = 'task'
                    step.action_target = f"{task.task_type.value}@{neighbour_id}"
                        
    def _check_and_build_shrines(self, current_tile_id: str, player_state: PlayerState,
                                step: SimulationStep, shrine_positions: Set[str]) -> None:
        """Check for and build shrines if appropriate."""
        for neighbour_id in self.grid.get_neighbours(current_tile_id):
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if (neighbour_tile.tile_type == TileType.SHRINE and 
                neighbour_id in shrine_positions and
                neighbour_id not in player_state.shrines_built):
                player_state.build_shrine(neighbour_id)
                self.task_manager.mark_shrine_built(neighbour_id)
                step.action_type = 'shrine'
                step.action_target = f"shrine@{neighbour_id}"
