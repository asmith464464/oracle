"""Route simulation, player state updates, and move/turn computation."""

from typing import Dict, List, Optional, Tuple, Set

from .map_model import HexGrid, TileType
from .tasks import TaskManager, PlayerState, TaskStatus, STATUE_ITEM, OFFERING_ITEM
from .simulator_models import SimulationResult, SimulationStep


class RouteSimulator:
    """Simulates route execution and validates correctness."""
    
    def __init__(self, grid: HexGrid, task_manager: TaskManager):
        self.grid = grid
        self.task_manager = task_manager
        
    def simulate_route(self, route: List[str], 
                      shrine_positions: Optional[List[str]] = None) -> SimulationResult:
        """
        Simulate complete route execution.
        
        Args:
            route: List of tile IDs representing the route
            shrine_positions: List of shrine tile IDs to build
            
        Returns:
            Complete simulation results
        """
        if not route:
            return self._error_result("Empty route provided")
            
        # Initialize simulation state
        zeus_tile = self.grid.get_zeus_tile()
        if not zeus_tile or route[0] != zeus_tile.id:
            return self._error_result("Route must start at Zeus tile")
            
        player_state = PlayerState(current_tile_id=zeus_tile.id)
        steps: List[SimulationStep] = []
        errors: List[str] = []
        shrine_set = set(shrine_positions) if shrine_positions else set()
        
        # Simulate each step of the route
        for i in range(1, len(route)):
            from_tile_id = route[i - 1]
            to_tile_id = route[i]
            
            step_result = self._simulate_step(
                from_tile_id, to_tile_id, player_state, shrine_set, i
            )
            
            steps.append(step_result)

            if step_result.action_type == 'error':
                errors.append(f"Step {i}: {step_result.action_target}")
                break

        if errors:
            success = False
        else:
            success = self._validate_final_state(player_state, route, errors)
        
        return SimulationResult(
            success=success,
            total_moves=player_state.total_moves,
            total_turns=player_state.total_turns,
            steps=steps,
            final_player_state=player_state,
            completed_tasks=list(player_state.completed_task_ids),
            shrines_built=player_state.shrines_built.copy(),
            errors=errors,
        )
        
    def _simulate_step(self, from_tile_id: str, to_tile_id: str, 
                      player_state: PlayerState, shrine_positions: Set[str],
                      step_number: int) -> SimulationStep:
        """Simulate a single step of movement."""
        from_tile = self.grid.get_tile(from_tile_id)
        to_tile = self.grid.get_tile(to_tile_id)
        
        # Validate tiles exist
        if not from_tile or not to_tile:
            return SimulationStep(
                step_number=step_number,
                current_tile_id=from_tile_id,
                action_type='error',
                action_target='Invalid tile in route'
            )
            
        # Validate adjacency
        if to_tile_id not in from_tile.neighbours:
            return SimulationStep(
                step_number=step_number,
                current_tile_id=from_tile_id,
                action_type='error',
                action_target=f'Tiles {from_tile_id}->{to_tile_id} are not adjacent'
            )

        # Validate destination is water or Zeus
        if to_tile_id != self.grid.zeus_tile_id and not to_tile.is_water():
            return SimulationStep(
                step_number=step_number,
                current_tile_id=from_tile_id,
                action_type='error',
                action_target=f'Move to non-water tile {to_tile_id} is not allowed'
            )
            
        # Execute the move
        player_state.execute_move(to_tile_id, 1)
        
        step = SimulationStep(
            step_number=step_number,
            current_tile_id=to_tile_id,
            action_type='move',
            moves_used=1,
            turn_number=player_state.total_turns
        )
        
        # Check for task completion
        self._check_and_execute_tasks(to_tile_id, player_state, step)
        
        # Check for shrine building
        self._check_and_build_shrines(to_tile_id, player_state, step, shrine_positions)
        
        return step
        
    def _check_and_execute_tasks(self, current_tile_id: str, 
                                player_state: PlayerState, 
                                step: SimulationStep) -> None:
        """Check for and execute any available tasks."""
        current_tile = self.grid.get_tile(current_tile_id)
        if not current_tile:
            return
            
        # Check adjacent tiles for tasks
        for neighbour_id in current_tile.neighbours:
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if not neighbour_tile or neighbour_tile.is_water():
                continue

            for task in self.task_manager.get_tasks_for_tile(neighbour_id):
                if (task.status == TaskStatus.PENDING and 
                    task.can_execute(player_state.completed_task_ids) and
                    self.task_manager.execute_task(task, player_state)):
                    step.action_type = 'task'
                    step.action_target = f"{task.task_type.value}@{neighbour_id}"
                    # Continue checking for more tasks - don't return early
                        
    def _check_and_build_shrines(self, current_tile_id: str,
                                player_state: PlayerState,
                                step: SimulationStep,
                                shrine_positions: Set[str]) -> None:
        """Check for and build shrines if appropriate."""
        current_tile = self.grid.get_tile(current_tile_id)
        if not current_tile:
            return
            
        # Check adjacent tiles for shrine building opportunities
        for neighbour_id in current_tile.neighbours:
            neighbour_tile = self.grid.get_tile(neighbour_id)
            if (neighbour_tile and 
                neighbour_tile.tile_type == TileType.SHRINE and 
                neighbour_id in shrine_positions and
                neighbour_id not in player_state.shrines_built):
                
                player_state.build_shrine(neighbour_id)
                self.task_manager.mark_shrine_built(neighbour_id)
                step.action_type = 'shrine'
                step.action_target = f"shrine@{neighbour_id}"
                # Continue checking for more shrines - don't return early

    def _validate_final_state(self, player_state: PlayerState, 
                            route: List[str], errors: List[str]) -> bool:
        """Validate that the final state meets all requirements."""
        success = True
        
        # Check if route ends at Zeus
        zeus_tile = self.grid.get_zeus_tile()
        if zeus_tile and route[-1] != zeus_tile.id:
            errors.append("Route does not end at Zeus tile")
            success = False
            
        # Check if all required tasks are completed
        if not self.task_manager.all_tasks_completed():
            incomplete_tasks = [
                task for task in self.task_manager.tasks.values()
                if task.status != TaskStatus.COMPLETED
            ]
            errors.append(f"Incomplete tasks: {[t.tile_id for t in incomplete_tasks]}")
            success = False
            
        # Check inventory consistency
        if player_state.has_item(STATUE_ITEM):
            errors.append("Player still has statue at end of route")
            success = False
            
        if player_state.has_item(OFFERING_ITEM):
            errors.append("Player still has undelivered offerings")
            success = False

        if self.task_manager.remaining_shrine_requirement() > 0:
            errors.append(
                f"Shrine requirement not met: {self.task_manager.remaining_shrine_requirement()} remaining"
            )
            success = False
            
        return success
        
    def validate_route_legality(self, route: List[str]) -> Tuple[bool, List[str]]:
        """Validate that a route is legal (all moves are valid)."""
        errors = []
        
        if not route:
            return False, ["Empty route"]
            
        # Check each move in the route
        for i in range(1, len(route)):
            from_tile_id = route[i - 1]
            to_tile_id = route[i]
            
            from_tile = self.grid.get_tile(from_tile_id)
            to_tile = self.grid.get_tile(to_tile_id)
            
            if not from_tile:
                errors.append(f"Invalid tile at position {i-1}: {from_tile_id}")
                continue
                
            if not to_tile:
                errors.append(f"Invalid tile at position {i}: {to_tile_id}")
                continue
                
            # Check if both tiles are water (traversable)
            if to_tile_id not in from_tile.neighbours:
                errors.append(f"Move {i}: {from_tile_id}->{to_tile_id} not adjacent")
                continue

            if to_tile_id != self.grid.zeus_tile_id and not to_tile.is_water():
                errors.append(f"Move {i}: Destination {to_tile_id} is not water")
                
        return len(errors) == 0, errors

    def _error_result(self, message: str) -> SimulationResult:
        return SimulationResult(
            success=False,
            total_moves=0,
            total_turns=0,
            steps=[],
            final_player_state=PlayerState(""),
            completed_tasks=[],
            shrines_built=[],
            errors=[message],
        )