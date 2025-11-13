"""
Task and player state classes, task selection, and dependency management.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .map_model import Tile, TileType, HexGrid


STATUE_ITEM = "statue"
OFFERING_ITEM = "offering"

__all__ = [
    "STATUE_ITEM",
    "OFFERING_ITEM",
    "TaskStatus",
    "Task",
    "CargoItem",
    "PlayerState",
    "TaskManager",
]


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    COMPLETED = "completed"
    AVAILABLE = "available"
    BLOCKED = "blocked"


@dataclass
class Task:
    """Represents a task that needs to be completed."""

    id: str
    tile_id: str
    task_type: TileType
    colour: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    max_uses: int = 1
    uses_completed: int = 0
    
    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if task can be executed given completed tasks."""
        return all(dep_id in completed_tasks for dep_id in self.dependencies)

    def remaining_uses(self) -> int:
        """Number of times this task can still be executed."""
        return self.max_uses - self.uses_completed

    def record_execution(self) -> None:
        """Update internal counters after a successful execution."""
        self.uses_completed += 1
        if self.remaining_uses() <= 0:
            self.status = TaskStatus.COMPLETED
        else:
            self.status = TaskStatus.PENDING


@dataclass(frozen=True)
class CargoItem:
    """Represents an item stored in the ship's cargo slots."""

    item_type: str
    colour: Optional[str] = None


@dataclass 
class PlayerState:
    """Represents the current state of the player/boat."""
    current_tile_id: str
    total_moves: int = 0
    total_turns: int = 0
    
    # Inventory and progress tracking
    cargo: List[CargoItem] = field(default_factory=list)
    completed_task_ids: Set[str] = field(default_factory=set)
    shrines_built: List[str] = field(default_factory=list)
    
    CARGO_CAPACITY = 2  # Maximum cargo slots
    
    def execute_move(self, to_tile_id: str, moves: int = 1) -> None:
        """Execute a move to another tile."""
        self.current_tile_id = to_tile_id
        self.total_moves += moves
        
        # Update turns if we've used all moves
        if self.total_moves % 3 == 0:
            self.total_turns += 1

    def add_cargo(self, item: CargoItem) -> bool:
        """Attempt to store an item in cargo; return True on success."""
        if len(self.cargo) >= self.CARGO_CAPACITY:
            return False
        self.cargo.append(item)
        return True

    def remove_cargo(self, item_type: str, colour: Optional[str] = None) -> bool:
        """Remove the first matching cargo item."""
        for idx, item in enumerate(self.cargo):
            if item.item_type != item_type:
                continue
            if colour is not None and item.colour != colour:
                continue
            self.cargo.pop(idx)
            return True
        return False

    def has_item(self, item_type: str, colour: Optional[str] = None) -> bool:
        """Check if cargo contains a matching item."""
        return any(
            item.item_type == item_type and (colour is None or item.colour == colour)
            for item in self.cargo
        )

    def complete_task(self, task: Task) -> None:
        """Mark a task as completed and update player state."""
        self.completed_task_ids.add(task.id)

        if task.task_type == TileType.STATUE_SOURCE:
            if not self.add_cargo(CargoItem(STATUE_ITEM, task.colour)):
                raise RuntimeError("Attempted to take a statue without cargo space")
        elif task.task_type == TileType.STATUE_ISLAND:
            if not self.remove_cargo(STATUE_ITEM, task.colour):
                raise RuntimeError("No matching statue to deliver at island")
        elif task.task_type == TileType.OFFERING:
            if not self.add_cargo(CargoItem(OFFERING_ITEM, task.colour)):
                raise RuntimeError("Attempted to take an offering without cargo space")
        elif task.task_type == TileType.TEMPLE:
            if not self.remove_cargo(OFFERING_ITEM, task.colour):
                raise RuntimeError("No offering available for temple delivery")
            
    def build_shrine(self, tile_id: str) -> None:
        """Build a shrine at the specified tile."""
        self.shrines_built.append(tile_id)


class TaskManager:
    """Manages task selection, dependencies, and execution."""
    
    def __init__(self, grid: HexGrid):
        self.grid = grid
        self.tasks: Dict[str, Task] = {}
        self.tasks_by_tile: Dict[str, List[Task]] = {}
        self.selected_colours: List[str] = []
        self.required_shrine_count: int = 3
        self.scheduled_shrines: List[str] = []
        self.completed_shrines: Set[str] = set()
        
    def assign_colours(self, colours: List[str]) -> None:
        """Assign the 3 colours for this run."""
        if len(colours) != 3:
            raise ValueError("Exactly 3 colours must be assigned")
        self.selected_colours = colours.copy()
        
    def select_tasks_for_colours(self) -> Dict[str, List[Task]]:
        """Select tasks for each assigned colour based on task distribution."""
        if not self.selected_colours:
            raise ValueError("Colours must be assigned before selecting tasks")

        selected_tasks: Dict[str, List[Task]] = {}
        self.tasks.clear()
        self.tasks_by_tile.clear()
        self.scheduled_shrines.clear()
        self.completed_shrines.clear()

        # Helper to create and register a task
        def create_task(tile: Tile, task_type: TileType, colour: str, 
                       dependencies: Optional[List[str]] = None) -> Task:
            task = Task(
                id=f"{tile.id}:{task_type.value}:{colour}",
                tile_id=tile.id,
                task_type=task_type,
                colour=colour,
                dependencies=dependencies or [],
            )
            self.tasks[task.id] = task
            self.tasks_by_tile.setdefault(task.tile_id, []).append(task)
            return task

        for colour in self.selected_colours:
            colour_tiles = self.grid.get_tiles_by_colour(colour)
            tiles_by_type: Dict[TileType, List[Tile]] = {}
            for tile in colour_tiles:
                tiles_by_type.setdefault(tile.tile_type, []).append(tile)

            # Pick first tile (sorted by ID) for each type
            def pick_tile(tile_type: TileType) -> Tile:
                candidates = sorted(tiles_by_type.get(tile_type, []), key=lambda t: t.id)
                if not candidates:
                    raise ValueError(f"Colour '{colour}' is missing {tile_type.value} tile")
                return candidates[0]

            # Create all tasks for this colour in dependency order
            monster_task = create_task(pick_tile(TileType.MONSTER), TileType.MONSTER, colour)
            offering_task = create_task(pick_tile(TileType.OFFERING), TileType.OFFERING, colour)
            statue_source_task = create_task(pick_tile(TileType.STATUE_SOURCE), TileType.STATUE_SOURCE, colour)
            statue_island_task = create_task(pick_tile(TileType.STATUE_ISLAND), TileType.STATUE_ISLAND, colour, [statue_source_task.id])
            temple_task = create_task(pick_tile(TileType.TEMPLE), TileType.TEMPLE, colour, [offering_task.id])
            
            selected_tasks[colour] = [monster_task, offering_task, statue_source_task, statue_island_task, temple_task]

        return selected_tasks
        
    def get_available_tasks(self, player_state: PlayerState) -> List[Task]:
        """Get tasks that can currently be executed."""
        available = []
        for task in self.tasks.values():
            if (
                task.status != TaskStatus.COMPLETED
                and task.remaining_uses() > 0
                and task.can_execute(player_state.completed_task_ids)
            ):
                available.append(task)
        return available
        
    def get_shrine_candidates(self) -> List[Tile]:
        """Get potential shrine build locations."""
        shrine_tiles = self.grid.get_tiles_by_type(TileType.SHRINE)
        excluded_tiles = {task.tile_id for task in self.tasks.values()}
        excluded_tiles.update(self.scheduled_shrines)
        excluded_tiles.update(self.completed_shrines)
        return [tile for tile in shrine_tiles if tile.id not in excluded_tiles]

    def get_tasks_for_tile(self, tile_id: str) -> List[Task]:
        """Return all tasks associated with the provided tile."""
        return list(self.tasks_by_tile.get(tile_id, []))

    def set_required_shrine_count(self, count: int) -> None:
        if count < 0:
            raise ValueError("Shrine count must be non-negative")
        self.required_shrine_count = count

    def get_required_shrine_count(self) -> int:
        return self.required_shrine_count

    def register_scheduled_shrines(self, shrine_ids: List[str]) -> None:
        for shrine_id in shrine_ids:
            if shrine_id not in self.scheduled_shrines:
                self.scheduled_shrines.append(shrine_id)

    def mark_shrine_built(self, shrine_id: str) -> None:
        self.completed_shrines.add(shrine_id)

    def remaining_shrine_requirement(self) -> int:
        completed = len(self.completed_shrines)
        scheduled = sum(1 for shrine_id in self.scheduled_shrines if shrine_id not in self.completed_shrines)
        return max(0, self.required_shrine_count - completed - scheduled)
        
    def execute_task(self, task: Task, player_state: PlayerState) -> bool:
        """Execute a task and update game state."""
        if task.remaining_uses() <= 0 or not task.can_execute(player_state.completed_task_ids):
            return False
            
        # Check if player is adjacent to task tile
        task_tile = self.grid.get_tile(task.tile_id)
        current_tile = self.grid.get_tile(player_state.current_tile_id)
        if not task_tile or not current_tile or task.tile_id not in current_tile.neighbors:
            return False
            
        # Check specific task requirements
        cargo_required = {
            TileType.STATUE_SOURCE: None,  # Pickup - needs space
            TileType.OFFERING: None,       # Pickup - needs space
            TileType.STATUE_ISLAND: (STATUE_ITEM, task.colour),
            TileType.TEMPLE: (OFFERING_ITEM, task.colour),
        }
        
        if task.task_type in cargo_required:
            requirement = cargo_required[task.task_type]
            if requirement is None:  # Pickup tasks
                if len(player_state.cargo) >= PlayerState.CARGO_CAPACITY:
                    return False
                if task.colour and task.colour not in task_tile.colours:
                    return False
            else:  # Delivery tasks
                item_type, colour = requirement
                if not player_state.has_item(item_type, colour):
                    return False
                
        # Execute the task
        player_state.complete_task(task)
        task.record_execution()
        return True
        
    def all_tasks_completed(self) -> bool:
        """Check if all tasks are completed."""
        return all(task.status == TaskStatus.COMPLETED for task in self.tasks.values())
        
    def get_task_summary(self) -> Dict[str, int]:
        """Get summary of task completion status."""
        summary = {}
        for status in TaskStatus:
            summary[status.value] = sum(
                1 for task in self.tasks.values() 
                if task.status == status
            )
        return summary