import logging
import json
from typing import List, Tuple
from collections import deque
from itertools import permutations

logging.basicConfig(level=logging.INFO, format='%(message)s')

# Hexagonal grid neighbor offsets (axial coordinates)
HEX_OFFSETS_EVEN = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
HEX_OFFSETS_ODD = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]


class Task:
    """Represents a single task to complete."""
    def __init__(self, id: str, coord: Tuple[int, int], type: str, color: str):
        self.id = id
        self.coord = coord
        self.type = type
        self.color = color


# ============================================================================
# DISTANCE CALCULATION (BFS)
# ============================================================================

def get_adjacent_water_tiles(tile: Tuple[int, int], traversable: set) -> List[Tuple[int, int]]:
    """Find all water tiles adjacent to a given tile."""
    q, r = tile
    offsets = HEX_OFFSETS_EVEN if r % 2 == 0 else HEX_OFFSETS_ODD
    return [(q + dq, r + dr) for dq, dr in offsets if (q + dq, r + dr) in traversable]


def bfs_distance(start: Tuple[int, int], end: Tuple[int, int], traversable: set) -> int:
    """
    Calculate shortest distance from start to any water tile adjacent to end.
    Uses Breadth-First Search (BFS) to guarantee shortest path.
    """
    targets = get_adjacent_water_tiles(end, traversable)
    if not targets:
        return 999999
    
    visited = set()
    queue = deque([(start, 0)])
    
    while queue:
        current, dist = queue.popleft()
        
        if current in targets:
            return dist
        
        if current in visited:
            continue
        
        visited.add(current)
        
        q, r = current
        offsets = HEX_OFFSETS_EVEN if r % 2 == 0 else HEX_OFFSETS_ODD
        for dq, dr in offsets:
            neighbor = (q + dq, r + dr)
            if neighbor in traversable and neighbor not in visited:
                queue.append((neighbor, dist + 1))
    
    return 999999


# ============================================================================
# TASK GROUPING (CYCLE CREATION)
# ============================================================================

def find_nearest_task_to_position(position: Tuple[int, int], tasks: List[Task], traversable: set) -> Task:
    """Find the task closest to a given position."""
    return min(tasks, key=lambda t: bfs_distance(position, t.coord, traversable))


def find_nearest_task_to_group(group: List[Task], ungrouped: List[Task], traversable: set) -> Task:
    """Find the ungrouped task closest to any task in the group."""
    return min(ungrouped, key=lambda t: min(bfs_distance(g.coord, t.coord, traversable) for g in group))


def is_group_too_spread_out(group: List[Task], max_distance: int, traversable: set) -> bool:
    """Check if any two tasks in a group exceed the maximum distance."""
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            dist1 = bfs_distance(group[i].coord, group[j].coord, traversable)
            dist2 = bfs_distance(group[j].coord, group[i].coord, traversable)
            if min(dist1, dist2) > max_distance:
                return True
    return False


def create_task_groups(tasks: List[Task], zeus_coord: Tuple[int, int], max_distance: int, traversable: set) -> List[List[Task]]:
    """
    Group tasks into cycles based on proximity.
    Each group contains tasks that are close together.
    """
    logging.info(f"Creating task groups from {len(tasks)} tasks")
    
    ungrouped = tasks[:]
    groups = []
    
    while ungrouped:
        # Start new group with closest task to Zeus
        initial = find_nearest_task_to_position(zeus_coord, ungrouped, traversable)
        logging.info(f"Starting new group with {initial.id}")
        
        group = [initial]
        ungrouped.remove(initial)
        
        # Keep adding nearest tasks until group becomes too spread out
        while ungrouped:
            nearest = find_nearest_task_to_group(group, ungrouped, traversable)
            test_group = group + [nearest]
            
            if not is_group_too_spread_out(test_group, max_distance, traversable):
                ungrouped.remove(nearest)
                group.append(nearest)
                logging.info(f"  Added {nearest.id}")
            else:
                logging.info(f"  Cannot add {nearest.id} (would exceed max distance)")
                break
        
        logging.info(f"Finalized group: {[t.id for t in group]}")
        groups.append(group)
    
    return groups


# ============================================================================
# CONSTRAINT VALIDATION
# ============================================================================

def validate_task_sequence(tasks: List[Task], starting_inventory: dict) -> Tuple[bool, dict]:
    """
    Validate that a sequence of tasks respects game rules:
    - Can't carry more than 2 items at once
    - Must pickup before delivery
    
    Returns (is_valid, ending_inventory)
    """
    inventory = starting_inventory.copy()
    
    for task in tasks:
        if 'pickup' in task.type:
            total_cargo = sum(inventory.values())
            if total_cargo >= 2:
                return False, {}
            inventory[task.color] = inventory.get(task.color, 0) + 1
            
        elif 'delivery' in task.type:
            if inventory.get(task.color, 0) <= 0:
                return False, {}
            inventory[task.color] -= 1
    
    return True, inventory


# ============================================================================
# CYCLE ORDERING
# ============================================================================

def order_groups_into_route(groups: List[List[Task]], zeus_coord: Tuple[int, int], traversable: set) -> List[List[Task]]:
    """
    Order groups and tasks within groups to minimize travel distance.
    Ensures constraints are satisfied across the entire route.
    """
    logging.info("Ordering groups into route...")
    
    ordered_route = []
    remaining = groups[:]
    current_pos = zeus_coord
    current_inventory = {}  # Ensure this is always a dict, never None
    cycle_num = 1
    
    while remaining:
        best_group = None
        best_ordering = None
        best_distance = float('inf')
        best_ending_inventory = None
        
        logging.info(f"\nSelecting cycle {cycle_num} (inventory: {current_inventory})")
        
        # Try each remaining group
        for group in remaining:
            valid_count = 0
            
            # Try all possible orderings of tasks within the group
            for ordering in permutations(group):
                # Check if this ordering is valid given current inventory
                # Ensure current_inventory is always a dict, never None
                inventory_for_validation = current_inventory if current_inventory is not None else {}
                is_valid, ending_inventory = validate_task_sequence(list(ordering), inventory_for_validation)
                if not is_valid:
                    continue
                
                valid_count += 1
                
                # Calculate total distance for this ordering
                distance = bfs_distance(current_pos, ordering[0].coord, traversable)
                for i in range(len(ordering) - 1):
                    distance += bfs_distance(ordering[i].coord, ordering[i + 1].coord, traversable)
                
                # Keep track of best option
                if distance < best_distance:
                    best_distance = distance
                    best_group = group
                    best_ordering = list(ordering)
                    best_ending_inventory = ending_inventory
            
            logging.info(f"  Group {[t.id for t in group]}: {valid_count} valid orderings")
        
        if best_ordering is None:
            logging.error("No valid ordering found!")
            logging.error(f"Current inventory: {current_inventory}")
            for group in remaining:
                logging.error(f"  Remaining: {[(t.id, t.type, t.color) for t in group]}")
            raise ValueError("Cannot find valid route - check task constraints")
        
        logging.info(f"Selected: {[t.id for t in best_ordering]} (distance: {best_distance})")
        
        ordered_route.append(best_ordering)
        current_pos = best_ordering[-1].coord
        current_inventory = best_ending_inventory
        if best_group is not None:
            remaining.remove(best_group)
        cycle_num += 1
    
    logging.info("Route ordering complete\n")
    return ordered_route


# ============================================================================
# SHRINE COLLECTION
# ============================================================================

def add_shrines_to_route(route: List[List[Task]], zeus_coord: Tuple[int, int], 
                        shrine_coords: List[Tuple[int, int]], traversable: set) -> Tuple[List, int]:
    """
    Add shrine visits to the route, collecting exactly 3 shrines.
    Prioritizes using wasted moves within turns (3 moves per turn).
    """
    logging.info("Adding shrine collection to route...")
    
    final_route = []
    current_pos = zeus_coord
    total_moves = 0
    shrines_collected = []
    available_shrines = shrine_coords[:]
    
    # Process each cycle
    for cycle_idx, cycle in enumerate(route):
        logging.info(f"Processing cycle {cycle_idx + 1}")
        
        for task in cycle:
            # Move to and complete task
            moves = bfs_distance(current_pos, task.coord, traversable)
            total_moves += moves
            final_route.append(('task', task))
            current_pos = task.coord
            
            # Check if we can collect a shrine using wasted moves
            if len(shrines_collected) < 3 and available_shrines:
                moves_in_turn = total_moves % 3
                if moves_in_turn > 0:
                    wasted_moves = 3 - moves_in_turn
                    
                    # Find closest shrine within wasted move budget
                    best_shrine = None
                    best_dist = float('inf')
                    
                    for shrine in available_shrines:
                        dist = bfs_distance(current_pos, shrine, traversable)
                        if dist <= wasted_moves and dist < best_dist:
                            best_dist = dist
                            best_shrine = shrine
                    
                    if best_shrine:
                        logging.info(f"  Collecting shrine at {best_shrine} using {best_dist} wasted moves")
                        total_moves += best_dist
                        final_route.append(('shrine', best_shrine))
                        shrines_collected.append(best_shrine)
                        available_shrines.remove(best_shrine)
                        current_pos = best_shrine
    
    # Add any remaining shrines needed
    shrines_needed = 3 - len(shrines_collected)
    if shrines_needed > 0:
        logging.info(f"Need {shrines_needed} more shrines, adding dedicated visits")
    
    for _ in range(shrines_needed):
        if not available_shrines:
            break
        
        # Find closest remaining shrine
        best_shrine = min(available_shrines, key=lambda s: bfs_distance(current_pos, s, traversable))
        dist = bfs_distance(current_pos, best_shrine, traversable)
        
        logging.info(f"  Visiting shrine at {best_shrine} (distance: {dist})")
        total_moves += dist
        final_route.append(('shrine', best_shrine))
        shrines_collected.append(best_shrine)
        available_shrines.remove(best_shrine)
        current_pos = best_shrine
    
    # Return to Zeus
    dist_to_zeus = bfs_distance(current_pos, zeus_coord, traversable)
    total_moves += dist_to_zeus
    final_route.append(('return', zeus_coord))
    
    total_turns = (int)(total_moves + 2) // 3  # Ceiling division
    
    logging.info(f"Collected {len(shrines_collected)} shrines")
    logging.info(f"Total moves: {total_moves}, Total turns: {total_turns}\n")
    
    return final_route, total_turns


# ============================================================================
# TASK SELECTION
# ============================================================================

def select_tasks_from_map(data: dict, colors: List[str]) -> Tuple[List[Task], set, List[Tuple[int, int]], Tuple[int, int]]:
    """
    Load map and select one tile per task type per color.
    Returns: (tasks, traversable_tiles, shrine_coords, zeus_coord)
    """
    # Map file terminology to internal task types
    TYPE_MAP = {
        'statue_source': 'statue_pickup',
        'statue_island': 'statue_delivery',
        'offering': 'offering_pickup',
        'temple': 'offering_delivery',
        'monster': 'monster'
    }
    
    traversable = set()
    shrine_coords = []
    zeus_coord = None
    tiles_by_type = {}  # task_type -> color -> [(tile_id, coords), ...]
    
    # Collect all tiles organized by type and color
    for tile in data['tiles']:
        coords = tuple(tile['coords'])
        tile_type = tile['type']
        tile_id = tile['id']
        
        if tile_type == 'water':
            traversable.add(coords)
        
        if tile_id == data['zeus_tile']:
            zeus_coord = coords
        
        if tile_type == 'shrine':
            shrine_coords.append(coords)
        
        if tile_type in TYPE_MAP:
            task_type = TYPE_MAP[tile_type]
            for color in tile.get('colours', []):
                if color in colors:
                    if task_type not in tiles_by_type:
                        tiles_by_type[task_type] = {}
                    if color not in tiles_by_type[task_type]:
                        tiles_by_type[task_type][color] = []
                    tiles_by_type[task_type][color].append((tile_id, coords))
    
    # Sort tiles by ID for deterministic selection
    for task_type in tiles_by_type:
        for color in tiles_by_type[task_type]:
            tiles_by_type[task_type][color].sort(key=lambda x: x[0])
    
    # Select one tile per (task_type, color), preferring unique tiles
    selected = {}
    used_tiles = set()
    
    task_order = ['monster', 'offering_pickup', 'offering_delivery', 'statue_pickup', 'statue_delivery']
    
    # First pass: try to use unique tiles for each color
    for task_type in task_order:
        if task_type not in tiles_by_type:
            continue
        selected[task_type] = {}
        for color in colors:
            if color in tiles_by_type[task_type]:
                available = [t for t in tiles_by_type[task_type][color] if t[0] not in used_tiles]
                if available:
                    tile_id, coords = available[0]
                    selected[task_type][color] = (tile_id, coords)
                    used_tiles.add(tile_id)
    
    # Second pass: fill gaps with any available tile
    for task_type in task_order:
        if task_type not in tiles_by_type:
            continue
        for color in colors:
            if color not in selected[task_type] and color in tiles_by_type[task_type]:
                tile_id, coords = tiles_by_type[task_type][color][0]
                selected[task_type][color] = (tile_id, coords)
    
    # Create Task objects
    tasks = []
    for task_type in task_order:
        if task_type in selected:
            for color in colors:
                if color in selected[task_type]:
                    tile_id, coords = selected[task_type][color]
                    tasks.append(Task(tile_id, coords, task_type, color))
    
    logging.info(f"Selected {len(tasks)} tasks: {[(t.id, t.type, t.color) for t in tasks]}\n")
    
    if zeus_coord is None:
        raise ValueError("Zeus tile not found in map")
    
    return tasks, traversable, shrine_coords, zeus_coord


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Load map
    with open('../data/maps/map1.json', 'r') as f:
        data = json.load(f)
    
    # Configuration
    colors = ['pink', 'blue', 'green']
    max_group_distance = 6
    
    # Select tasks
    tasks, traversable, shrine_coords, zeus_coord = select_tasks_from_map(data, colors)
    
    if zeus_coord is None:
        raise ValueError("Zeus tile not found in map")
    
    # Create groups (cycles)
    groups = create_task_groups(tasks, zeus_coord, max_group_distance, traversable)
    
    # Order groups into route
    ordered_route = order_groups_into_route(groups, zeus_coord, traversable)
    
    # Display cycles
    logging.info("=" * 60)
    for i, cycle in enumerate(ordered_route):
        logging.info(f"Cycle {i + 1}: {[(t.id, t.type, t.color) for t in cycle]}")
    
    # Add shrines
    logging.info("\n" + "=" * 60)
    final_route, total_turns = add_shrines_to_route(ordered_route, zeus_coord, shrine_coords, traversable)
    
    # Display final route
    logging.info("=" * 60)
    logging.info("FINAL ROUTE:")
    for step_type, location in final_route:
        if step_type == 'task':
            logging.info(f"  Task: {location.id} ({location.type}, {location.color}) at {location.coord}")
        elif step_type == 'shrine':
            logging.info(f"  Shrine at {location}")
        elif step_type == 'return':
            logging.info(f"  Return to Zeus at {location}")
    
    logging.info("\n" + "=" * 60)
    logging.info(f"TOTAL TURNS: {total_turns}")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()