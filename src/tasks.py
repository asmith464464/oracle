"""
Task and player state classes, task selection, and dependency management.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .grid import Tile, TileType, HexGrid
from .cycles import CYCLE_DEFINITIONS


STATUE_ITEM = "statue"
OFFERING_ITEM = "offering"

# Hardcoded shrine tiles for map1.json
MAP1_SHRINE_TILES = [
    "tile_003", "tile_016", "tile_023", "tile_029", "tile_050",
    "tile_058", "tile_076", "tile_079", "tile_084", "tile_091",
    "tile_096", "tile_103"
]

__all__ = [
    "STATUE_ITEM",
    "OFFERING_ITEM",
    "TaskStatus",
    "Task",
    "CargoItem",
    "PlayerState",
    "TaskManager",
    "TaskCycle",
]


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass
class Task:
    """Represents a task that needs to be completed."""

    id: str
    tile_id: str
    task_type: TileType
    colour: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    
    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if task can be executed given completed tasks."""
        return all(dep_id in completed_tasks for dep_id in self.dependencies)

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED


# CargoItem is a tuple: (item_type: str, colour: Optional[str])
CargoItem = Tuple[str, Optional[str]]


@dataclass 
class PlayerState:
    """Represents the current state of the player/boat."""
    current_tile_id: str
    total_moves: int = 0
    total_turns: int = 0
    
    # Inventory and progress tracking
    cargo: List[Tuple[str, Optional[str]]] = field(default_factory=list)
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

    def add_cargo(self, item_type: str, colour: Optional[str] = None) -> bool:
        """Attempt to store an item in cargo; return True on success."""
        if len(self.cargo) >= self.CARGO_CAPACITY:
            return False
        self.cargo.append((item_type, colour))
        return True

    def remove_cargo(self, item_type: str, colour: Optional[str] = None) -> bool:
        """Remove the first matching cargo item."""
        for idx, (i_type, i_colour) in enumerate(self.cargo):
            if i_type == item_type and (colour is None or i_colour == colour):
                self.cargo.pop(idx)
                return True
        return False

    def has_item(self, item_type: str, colour: Optional[str] = None) -> bool:
        """Check if cargo contains a matching item."""
        return any(
            i_type == item_type and (colour is None or i_colour == colour)
            for i_type, i_colour in self.cargo
        )

    def complete_task(self, task: Task) -> None:
        """Mark a task as completed and update player state."""
        self.completed_task_ids.add(task.id)

        if task.task_type == TileType.STATUE_SOURCE:
            self.add_cargo(STATUE_ITEM, task.colour)
        elif task.task_type == TileType.STATUE_ISLAND:
            self.remove_cargo(STATUE_ITEM, task.colour)
        elif task.task_type == TileType.OFFERING:
            self.add_cargo(OFFERING_ITEM, task.colour)
        elif task.task_type == TileType.TEMPLE:
            self.remove_cargo(OFFERING_ITEM, task.colour)
            
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
        self.completed_shrines: Set[str] = set()
        
    def assign_colours(self, colours: List[str]) -> None:
        """Assign the 3 colours for this run."""
        if len(colours) != 3:
            raise ValueError("Exactly 3 colours must be assigned")
        self.selected_colours = colours.copy()
        
    def select_tasks_for_colours(self) -> Dict[str, List[Task]]:
        """Generate tasks dynamically from cycle definitions in cycles.py."""
        selected_tasks: Dict[str, List[Task]] = {}
        self.tasks.clear()
        self.tasks_by_tile.clear()
        self.completed_shrines.clear()

        # Helper to create and register a task
        def create_task(tile_id: str, task_type: TileType, colour: str, 
                       dependencies: Optional[List[str]] = None) -> Task:
            task = Task(
                id=f"{tile_id}:{task_type.value}:{colour}",
                tile_id=tile_id,
                task_type=task_type,
                colour=colour,
                dependencies=dependencies or [],
            )
            self.tasks[task.id] = task
            self.tasks_by_tile.setdefault(task.tile_id, []).append(task)
            return task

        # Generate tasks from CYCLE_DEFINITIONS in cycles.py
        # Tasks are assigned colours based on logical task groups (hardcoded for map1.json)
        # Cycles are for routing optimization, not colour grouping
        self.cycle_tile_orders = CYCLE_DEFINITIONS
        
        # Hardcoded colour assignments for map1.json tasks
        # These ensure dependencies work regardless of cycle order
        TILE_COLOUR_MAP = {
            # Pink group
            "tile_020": "pink", "tile_053": "pink", "tile_071": "pink",
            "tile_063": "pink", "tile_112": "pink",
            # Blue group  
            "tile_028": "blue", "tile_077": "blue", "tile_061": "blue",
            "tile_094": "blue", "tile_015": "blue",
            # Green group
            "tile_105": "green", "tile_009": "green", "tile_108": "green",
            "tile_005": "green", "tile_007": "green",
        }
        
        # First pass: Create all tasks without dependencies
        all_created_tasks: List[Task] = []
        for tile_ids in CYCLE_DEFINITIONS:
            for tile_id in tile_ids:
                tile = self.grid.get_tile(tile_id)
                if not tile:
                    continue
                
                # Look up the hardcoded colour for this tile
                assigned_colour = TILE_COLOUR_MAP.get(tile_id)
                if not assigned_colour:
                    raise ValueError(f"Tile {tile_id} not in hardcoded colour map")
                
                # Verify this colour is available on the tile
                if assigned_colour not in tile.colours:
                    raise ValueError(f"Colour '{assigned_colour}' not available for {tile_id} (available: {tile.colours})")
                
                # Create task without dependencies initially
                task = create_task(tile_id, tile.tile_type, assigned_colour, [])
                all_created_tasks.append(task)
                selected_tasks.setdefault(assigned_colour, []).append(task)
        
        # Second pass: Set up dependencies based on task types and colours
        # Find statue sources and offerings per colour
        statue_sources: Dict[str, Task] = {}
        offerings: Dict[str, Task] = {}
        
        for task in all_created_tasks:
            if task.colour:
                if task.task_type == TileType.STATUE_SOURCE:
                    statue_sources[task.colour] = task
                elif task.task_type == TileType.OFFERING:
                    offerings[task.colour] = task
        
        # Now set dependencies for islands and temples
        for task in all_created_tasks:
            if task.colour:
                if task.task_type == TileType.STATUE_ISLAND:
                    if task.colour in statue_sources:
                        task.dependencies = [statue_sources[task.colour].id]
                elif task.task_type == TileType.TEMPLE:
                    if task.colour in offerings:
                        task.dependencies = [offerings[task.colour].id]

        return selected_tasks
        
    def get_available_tasks(self, player_state: PlayerState) -> List[Task]:
        """Get tasks that can currently be executed."""
        return [
            task for task in self.tasks.values()
            if task.status != TaskStatus.COMPLETED and task.can_execute(player_state.completed_task_ids)
        ]
        
    def get_shrine_candidates(self) -> List[Tile]:
        """Get potential shrine build locations from map1.json hardcoded list."""
        excluded_tiles = {task.tile_id for task in self.tasks.values()}
        excluded_tiles.update(self.completed_shrines)
        return [tile for tile_id in MAP1_SHRINE_TILES 
                if tile_id not in excluded_tiles and (tile := self.grid.get_tile(tile_id))]

    def get_tasks_for_tile(self, tile_id: str) -> List[Task]:
        """Return all tasks associated with the provided tile."""
        return list(self.tasks_by_tile.get(tile_id, []))

    def mark_shrine_built(self, shrine_id: str) -> None:
        self.completed_shrines.add(shrine_id)

    def execute_task(self, task: Task, player_state: PlayerState) -> bool:
        """Execute a task and update game state."""
        if task.status == TaskStatus.COMPLETED or not task.can_execute(player_state.completed_task_ids):
            return False
            
        # Check if player is adjacent to task tile
        task_tile = self.grid.get_tile(task.tile_id)
        current_tile = self.grid.get_tile(player_state.current_tile_id)
        if not task_tile or not current_tile or task.tile_id not in self.grid.get_neighbours(player_state.current_tile_id):
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
        task.mark_completed()
        return True


# Simplified cycle data model

@dataclass
class TaskCycle:
    """Collection of tasks grouped into a cycle with their route."""
    tasks: List[Task]
    internal_route: List[str] = field(default_factory=list)