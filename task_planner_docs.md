# Task Planner Code Documentation

## Overview

This document explains how the task planner code works. The code finds an efficient route to complete all tasks and return to Zeus.

---

## Core Data Structures

### Task Class
```python
class Task:
    def __init__(self, id: str, coord: Tuple[int, int], type: str, color: str):
        self.id = id
        self.coord = coord
        self.type = type
        self.color = color
```

**What it is**: A container that stores information about one task.

**Fields**:
- `id`: The tile name (e.g., "tile_042")
- `coord`: The tile's position as coordinates (e.g., (5, 3))
- `type`: What kind of task (monster, statue_pickup, statue_delivery, offering_pickup, offering_delivery)
- `color`: Which color (pink, blue, green)

**Example**: `Task("tile_020", (6, 2), "monster", "pink")` represents fighting the pink monster at tile_020.

### Hexagonal Grid Constants
```python
HEX_OFFSETS_EVEN = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
HEX_OFFSETS_ODD = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
```

**What they are**: Lists of coordinate offsets to find a hex tile's 6 neighbors.

**Why two lists**: Hexagonal grids are arranged in an offset pattern. Even rows and odd rows have different neighbor positions.

**How they work**: Add these offsets to a tile's coordinates to get all adjacent tiles.

---

## Distance Calculation (BFS)

### get_adjacent_water_tiles()
```python
def get_adjacent_water_tiles(tile: Tuple[int, int], traversable: set) -> List[Tuple[int, int]]:
    q, r = tile
    offsets = HEX_OFFSETS_EVEN if r % 2 == 0 else HEX_OFFSETS_ODD
    return [(q + dq, r + dr) for dq, dr in offsets if (q + dq, r + dr) in traversable]
```

**What it does**: Finds all water tiles next to a given tile.

**How it works**:
1. Splits the tile coordinates into `q` (column) and `r` (row)
2. Chooses the correct offset list: even rows use `HEX_OFFSETS_EVEN`, odd rows use `HEX_OFFSETS_ODD`
3. For each offset, adds it to the tile coordinates to get a neighbor position
4. Keeps only neighbors that are water tiles (in the `traversable` set)

**Why needed**: You can't land on task tiles, only water tiles adjacent to them.

**Programming concepts**:
- `r % 2 == 0`: The `%` (modulo) operator gives the remainder when dividing by 2. If remainder is 0, the number is even.
- `if r % 2 == 0 else`: This is a "ternary operator" - a short way to pick one value or another based on a condition.
- List comprehension: `[... for ... in ... if ...]` creates a new list by applying an operation to each item that meets a condition.

### bfs_distance()
```python
def bfs_distance(start: Tuple[int, int], end: Tuple[int, int], traversable: set) -> int:
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
```

**What it does**: Calculates the shortest distance from one position to another.

**How it works** (BFS = Breadth-First Search):
1. First finds all valid water tiles next to the destination
2. Creates a `queue` (waiting list) starting with the start position at distance 0
3. **The BFS loop**:
   - Takes the first position from the queue with `popleft()`
   - If this position is adjacent to the destination, we've found the shortest path - return the distance
   - If we've already checked this position, skip it with `continue`
   - Mark this position as visited
   - Add all unvisited neighboring water tiles to the queue with distance + 1
4. The queue processes positions in order of distance (all distance 1, then all distance 2, etc.)

**Why BFS**: BFS explores positions layer by layer, guaranteeing the first time it reaches the target is the shortest path.

**Programming concepts**:
- `deque`: A double-ended queue from Python's `collections` module. You can efficiently add to the end with `append()` and remove from the front with `popleft()`.
- `set`: An unordered collection with very fast membership testing (`if item in set`).
- `while queue:`: Loops while the queue is not empty.
- `continue`: Skips the rest of the current loop iteration and moves to the next one.
- `return`: Immediately exits the function and sends a value back to the caller.

---

## Task Grouping (Cycle Creation)

### find_nearest_task_to_position()
```python
def find_nearest_task_to_position(position: Tuple[int, int], tasks: List[Task], traversable: set) -> Task:
    return min(tasks, key=lambda t: bfs_distance(position, t.coord, traversable))
```

**What it does**: Finds which task is closest to a position.

**How it works**:
- `min()` finds the smallest value in a collection
- `key=lambda t: ...` tells `min()` what to measure for each task
- `lambda t: bfs_distance(...)` is a small function that calculates distance for task `t`
- Returns the task with the smallest distance

**Programming concepts**:
- `lambda`: A way to create a small, unnamed function. `lambda t: expression` means "a function that takes `t` and returns the result of `expression`".
- `key` parameter: Many Python functions accept a `key` to specify what to measure when comparing items.

### find_nearest_task_to_group()
```python
def find_nearest_task_to_group(group: List[Task], ungrouped: List[Task], traversable: set) -> Task:
    return min(ungrouped, key=lambda t: min(bfs_distance(g.coord, t.coord, traversable) for g in group))
```

**What it does**: Finds the ungrouped task closest to any task already in a group.

**How it works**:
- For each ungrouped task `t`, calculates distance to every task `g` in the group
- Takes the minimum of those distances (the closest group member)
- Returns the ungrouped task with the smallest minimum distance

**Programming concepts**:
- Nested `min()`: The outer `min()` finds the closest ungrouped task; the inner `min()` finds the closest group member for each ungrouped task.
- Generator expression: `(...for g in group)` is like a list comprehension but doesn't create a list - it generates values one at a time, saving memory.

### is_group_too_spread_out()
```python
def is_group_too_spread_out(group: List[Task], max_distance: int, traversable: set) -> bool:
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            dist1 = bfs_distance(group[i].coord, group[j].coord, traversable)
            dist2 = bfs_distance(group[j].coord, group[i].coord, traversable)
            if min(dist1, dist2) > max_distance:
                return True
    return False
```

**What it does**: Checks if any two tasks in a group are too far apart.

**How it works**:
1. Uses nested loops to check every pair of tasks
2. `range(len(group))` creates numbers from 0 to group size - 1
3. `range(i + 1, len(group))` starts from i+1 to avoid checking the same pair twice
4. Calculates distance both directions (sometimes differs due to routing around obstacles)
5. If ANY pair exceeds max distance, returns `True` (too spread out)
6. If all pairs are okay, returns `False`

**Programming concepts**:
- `len()`: Returns the length (number of items) in a list.
- `range()`: Creates a sequence of numbers. `range(5)` gives 0, 1, 2, 3, 4.
- Nested loops: One loop inside another to check all combinations.
- `return True/False`: Exits the function immediately with a boolean value.

### create_task_groups()
```python
def create_task_groups(tasks: List[Task], zeus_coord: Tuple[int, int], max_distance: int, traversable: set) -> List[List[Task]]:
    logging.info(f"Creating task groups from {len(tasks)} tasks")
    
    ungrouped = tasks[:]
    groups = []
    
    while ungrouped:
        initial = find_nearest_task_to_position(zeus_coord, ungrouped, traversable)
        logging.info(f"Starting new group with {initial.id}")
        
        group = [initial]
        ungrouped.remove(initial)
        
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
```

**What it does**: Main function that creates all task groups (cycles).

**How it works**:
1. Starts with all tasks ungrouped
2. **Outer loop** (`while ungrouped`): Keeps creating groups until all tasks are grouped
3. For each new group:
   - Picks the closest task to Zeus as the starting point
   - Removes it from `ungrouped` and adds to new `group`
4. **Inner loop** (`while ungrouped`): Keeps adding tasks to current group
   - Finds the nearest ungrouped task to the current group
   - Tests if adding it would make the group too spread out
   - If okay, removes from `ungrouped` and adds to `group`
   - If too spread out, stops adding to this group with `break`
5. Adds the finalized group to the `groups` list
6. Returns all groups

**Programming concepts**:
- `tasks[:]`: Creates a copy of the list. The `[:]` slice notation means "all items from start to end".
- `.remove(item)`: Removes the first occurrence of an item from a list.
- `.append(item)`: Adds an item to the end of a list.
- `not`: Boolean operator that inverts True/False. `not True` is `False`.
- `break`: Exits the current loop immediately.
- `logging.info()`: Prints informational messages to help track what the code is doing.
- `f"string {variable}"`: An f-string allows embedding variables directly in strings.

---

## Constraint Validation

### validate_task_sequence()
```python
def validate_task_sequence(tasks: List[Task], starting_inventory: dict) -> Tuple[bool, dict]:
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
```

**What it does**: Validates that a sequence of tasks respects game rules (max 2 cargo, pickup before delivery).

**How it works**:
1. Makes a copy of the starting inventory (what you're already carrying)
2. Goes through each task in order:
   - **For pickups**: 
     - Counts total cargo using `sum(inventory.values())`
     - If already carrying 2 items, returns `False` (invalid)
     - Otherwise adds 1 to the count for that color
   - **For deliveries**:
     - Checks if you have at least 1 of that color
     - If not, returns `False` (can't deliver what you don't have)
     - Otherwise subtracts 1 from the count
3. If all tasks pass, returns `True` and the final inventory state

**Programming concepts**:
- `dict`: A dictionary is a collection of key-value pairs. `{'pink': 2, 'blue': 1}` means 2 pink items and 1 blue item.
- `.copy()`: Creates a copy of a dictionary so changes don't affect the original.
- `.values()`: Returns all the values in a dictionary (without the keys).
- `sum()`: Adds up all numbers in a collection.
- `'pickup' in task.type`: Checks if the string 'pickup' appears anywhere in `task.type`. Works for 'statue_pickup' and 'offering_pickup'.
- `.get(key, default)`: Gets a value from a dictionary, returning `default` if the key doesn't exist. Safer than `dict[key]` which crashes if key is missing.
- `elif`: Short for "else if". Checks another condition if the first `if` was False.
- `Tuple[bool, dict]`: A type hint indicating the function returns two values: a boolean and a dictionary.

---

## Cycle Ordering

### order_groups_into_route()
```python
def order_groups_into_route(groups: List[List[Task]], zeus_coord: Tuple[int, int], traversable: set) -> List[List[Task]]:
    logging.info("Ordering groups into route...")
    
    ordered_route = []
    remaining = groups[:]
    current_pos = zeus_coord
    current_inventory = {}
    cycle_num = 1
    
    while remaining:
        best_group = None
        best_ordering = None
        best_distance = float('inf')
        best_ending_inventory = None
        
        logging.info(f"\nSelecting cycle {cycle_num} (inventory: {current_inventory})")
        
        for group in remaining:
            valid_count = 0
            
            for ordering in permutations(group):
                is_valid, ending_inventory = validate_task_sequence(list(ordering), current_inventory)
                if not is_valid:
                    continue
                
                valid_count += 1
                
                distance = bfs_distance(current_pos, ordering[0].coord, traversable)
                for i in range(len(ordering) - 1):
                    distance += bfs_distance(ordering[i].coord, ordering[i + 1].coord, traversable)
                
                if distance < best_distance:
                    best_distance = distance
                    best_group = group
                    best_ordering = list(ordering)
                    best_ending_inventory = ending_inventory
            
            logging.info(f"  Group {[t.id for t in group]}: {valid_count} valid orderings")
        
        if best_ordering is None:
            logging.error("No valid ordering found!")
            raise ValueError("Cannot find valid route - check task constraints")
        
        logging.info(f"Selected: {[t.id for t in best_ordering]} (distance: {best_distance})")
        
        ordered_route.append(best_ordering)
        current_pos = best_ordering[-1].coord
        current_inventory = best_ending_inventory
        remaining.remove(best_group)
        cycle_num += 1
    
    logging.info("Route ordering complete\n")
    return ordered_route
```

**What it does**: Orders the groups and tasks within groups to minimize distance while respecting constraints.

**How it works**:
1. Starts at Zeus with empty inventory
2. **Main loop** (`while remaining`): Processes groups one by one
3. For each remaining group:
   - **Tests all possible orderings**: `permutations(group)` generates every possible order
   - For each ordering:
     - Validates it with `validate_task_sequence()` using current inventory
     - If invalid, skips it with `continue`
     - If valid, calculates total distance (from current position to first task, then between consecutive tasks)
     - Keeps track of the ordering with the shortest distance
4. Selects the best valid ordering
5. Updates position to the end of that group
6. Updates inventory to reflect what you're carrying after that group
7. Removes the group from remaining groups
8. Repeats until all groups are ordered

**Why inventory tracking matters**: You can't deliver a statue in cycle 2 if you pick it up in cycle 3. The inventory tracking ensures pickups always come before their deliveries across the entire route.

**Programming concepts**:
- `float('inf')`: Represents infinity. Used to initialize `best_distance` so any real distance will be smaller.
- `permutations(group)`: From `itertools` module, generates all possible orderings. For 3 items [A,B,C], it generates: ABC, ACB, BAC, BCA, CAB, CBA (6 total, which is 3! = 3×2×1).
- `list[-1]`: Negative indexing gets items from the end. `-1` is the last item, `-2` is second-to-last, etc.
- `raise ValueError()`: Stops the program and displays an error message. Used when something goes wrong that can't be recovered from.
- `logging.error()`: Like `logging.info()` but for error messages.

---

## Shrine Collection

### add_shrines_to_route()
```python
def add_shrines_to_route(route: List[List[Task]], zeus_coord: Tuple[int, int], 
                        shrine_coords: List[Tuple[int, int]], traversable: set) -> Tuple[List, int]:
    logging.info("Adding shrine collection to route...")
    
    final_route = []
    current_pos = zeus_coord
    total_moves = 0
    shrines_collected = []
    available_shrines = shrine_coords[:]
    
    for cycle_idx, cycle in enumerate(route):
        logging.info(f"Processing cycle {cycle_idx + 1}")
        
        for task in cycle:
            moves = bfs_distance(current_pos, task.coord, traversable)
            total_moves += moves
            final_route.append(('task', task))
            current_pos = task.coord
            
            if len(shrines_collected) < 3 and available_shrines:
                moves_in_turn = total_moves % 3
                if moves_in_turn > 0:
                    wasted_moves = 3 - moves_in_turn
                    
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
    
    shrines_needed = 3 - len(shrines_collected)
    if shrines_needed > 0:
        logging.info(f"Need {shrines_needed} more shrines, adding dedicated visits")
    
    for _ in range(shrines_needed):
        if not available_shrines:
            break
        
        best_shrine = min(available_shrines, key=lambda s: bfs_distance(current_pos, s, traversable))
        dist = bfs_distance(current_pos, best_shrine, traversable)
        
        logging.info(f"  Visiting shrine at {best_shrine} (distance: {dist})")
        total_moves += dist
        final_route.append(('shrine', best_shrine))
        shrines_collected.append(best_shrine)
        available_shrines.remove(best_shrine)
        current_pos = best_shrine
    
    dist_to_zeus = bfs_distance(current_pos, zeus_coord, traversable)
    total_moves += dist_to_zeus
    final_route.append(('return', zeus_coord))
    
    total_turns = (total_moves + 2) // 3
    
    logging.info(f"Collected {len(shrines_collected)} shrines")
    logging.info(f"Total moves: {total_moves}, Total turns: {total_turns}\n")
    
    return final_route, total_turns
```

**What it does**: Adds shrine visits to the route, collecting exactly 3 shrines efficiently.

**How it works**:

**Part 1 - Opportunistic collection (using wasted moves)**:
1. Goes through each cycle and each task
2. Calculates distance to the task and adds to `total_moves`
3. After completing each task, checks if we need more shrines and have wasted moves:
   - `total_moves % 3` gives position within current turn (0, 1, or 2)
   - If > 0, we have wasted moves before the turn ends
   - Searches for the closest shrine within the wasted move budget
   - If found, visits it (efficient - uses moves that would otherwise be wasted)

**Part 2 - Dedicated visits (for remaining shrines)**:
1. Calculates how many more shrines we need (3 - collected)
2. For each needed shrine:
   - Finds the closest available shrine
   - Travels there (these are dedicated trips, not using wasted moves)
   - Marks it as collected

**Part 3 - Return to Zeus**:
1. Calculates distance back to Zeus
2. Adds return to the route
3. Calculates total turns: `(total_moves + 2) // 3`

**Why this formula for turns**: `//` is floor division (rounds down). Adding 2 before dividing by 3 rounds up. Examples: 7 moves = (7+2)//3 = 3 turns; 9 moves = (9+2)//3 = 3 turns; 10 moves = (10+2)//3 = 4 turns.

**Programming concepts**:
- `enumerate()`: When looping through a list, `enumerate()` provides both the index and the item. `for i, item in enumerate(list)` gives you both.
- `tuple`: An immutable sequence. `('task', task)` is a tuple with two items. Used here to store the step type and location.
- `and`: Boolean operator. Both conditions must be True for the whole expression to be True.
- `for _ in range(n)`: When you need to loop n times but don't care about the counter, use `_` as the variable name.
- `//`: Floor division operator. Divides and rounds down to the nearest integer.

---

## Task Selection

### select_tasks_from_map()
```python
def select_tasks_from_map(data: dict, colors: List[str]) -> Tuple[List[Task], set, List[Tuple[int, int]], Tuple[int, int]]:
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
    tiles_by_type = {}
    
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
    
    for task_type in tiles_by_type:
        for color in tiles_by_type[task_type]:
            tiles_by_type[task_type][color].sort(key=lambda x: x[0])
    
    selected = {}
    used_tiles = set()
    
    task_order = ['monster', 'offering_pickup', 'offering_delivery', 'statue_pickup', 'statue_delivery']
    
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
    
    for task_type in task_order:
        if task_type not in tiles_by_type:
            continue
        for color in colors:
            if color not in selected[task_type] and color in tiles_by_type[task_type]:
                tile_id, coords = tiles_by_type[task_type][color][0]
                selected[task_type][color] = (tile_id, coords)
    
    tasks = []
    for task_type in task_order:
        if task_type in selected:
            for color in colors:
                if color in selected[task_type]:
                    tile_id, coords = selected[task_type][color]
                    tasks.append(Task(tile_id, coords, task_type, color))
    
    logging.info(f"Selected {len(tasks)} tasks: {[(t.id, t.type, t.color) for t in tasks]}\n")
    
    return tasks, traversable, shrine_coords, zeus_coord
```

**What it does**: Loads the map file and selects one tile per task type per color.

**How it works**:

**Step 1 - Map tile types**: Converts map file terminology to internal task types.
- Map uses 'statue_source', 'statue_island', etc.
- Code uses 'statue_pickup', 'statue_delivery', etc.

**Step 2 - Collect all tiles**: Loops through map data and organizes tiles by type and color into `tiles_by_type` dictionary.

**Step 3 - Sort tiles**: Sorts each list of tiles by ID for deterministic selection (same tiles chosen every time).

**Step 4 - Select tiles (two-pass approach)**:
- **First pass**: Try to assign unique tiles for each color (avoid using same tile for multiple colors)
  - Tracks `used_tiles` to prevent reuse
  - Picks the first available unused tile for each (type, color) combination
- **Second pass**: Fill in any gaps with whatever tiles are available
  - If first pass couldn't find unique tiles, use any available tile

**Step 5 - Create Task objects**: Converts selected tiles into Task objects in a fixed order.

**Why two passes**: Preferring unique tiles prevents issues with the same physical tile appearing multiple times in the route for different colors.

**Programming concepts**:
- `tuple()`: Converts a list to a tuple (immutable).
- `.get('key', default)`: Dictionary method that returns a default value if the key doesn't exist.
- `.sort(key=...)`: Sorts a list in-place. The `key` parameter specifies what to sort by.
- `if key not in dict`: Checks if a key doesn't exist in a dictionary.
- List indexing: `list[0]` gets the first item, `list[1]` gets the second, etc.
- Multiple return values: `return a, b, c, d` returns four values as a tuple.

---

## Main Function

```python
def main():
    with open('data/maps/map1.json', 'r') as f:
        data = json.load(f)
    
    colors = ['pink', 'blue', 'green']
    max_group_distance = 6
    
    tasks, traversable, shrine_coords, zeus_coord = select_tasks_from_map(data, colors)
    
    if zeus_coord is None:
        raise ValueError("Zeus tile not found in map")
    
    groups = create_task_groups(tasks, zeus_coord, max_group_distance, traversable)
    
    ordered_route = order_groups_into_route(groups, zeus_coord, traversable)
    
    logging.info("=" * 60)
    for i, cycle in enumerate(ordered_route):
        logging.info(f"Cycle {i + 1}: {[(t.id, t.type, t.color) for t in cycle]}")
    
    logging.info("\n" + "=" * 60)
    final_route, total_turns = add_shrines_to_route(ordered_route, zeus_coord, shrine_coords, traversable)
    
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
```

**What it does**: Main entry point that runs all planning steps and displays results.

**How it works**:
1. **Load map**: Opens and reads the JSON file
2. **Set configuration**: Defines which colors to use and max group distance
3. **Select tasks**: Calls `select_tasks_from_map()` to pick tiles
4. **Validate**: Checks that Zeus was found in the map
5. **Create groups**: Calls `create_task_groups()` to build cycles
6. **Order route**: Calls `order_groups_into_route()` to sequence everything
7. **Display cycles**: Logs each cycle's tasks
8. **Add shrines**: Calls `add_shrines_to_route()` to complete the route
9. **Display final route**: Logs every step including shrines and return to Zeus
10. **Display turn count**: Shows total turns needed

**Programming concepts**:
- `with open(...) as f:`: A "context manager" that opens a file and automatically closes it when done, even if an error occurs. The `'r'` means "read mode".
- `json.load()`: Parses JSON (JavaScript Object Notation) text and converts it into Python dictionaries and lists.
- `if __name__ == "__main__":`: This special check ensures `main()` only runs when the file is executed directly, not when imported as a module.
- String multiplication: `"=" * 60` creates a string of 60 equal signs.
- `\n`: A newline character that creates a line break in text.

---

## Configuration Options

You can adjust these values in `main()` to change behavior:

### `colors`
```python
colors = ['pink', 'blue', 'green']
```
- **What it controls**: Which three colors to complete tasks for
- **Options**: Any three from: pink, blue, green, red, black, yellow
- **Example**: Change to `['red', 'black', 'yellow']` for different colors

### `max_group_distance`
```python
max_group_distance = 6
```
- **What it controls**: Maximum distance between any two tasks in a group (cycle)
- **Effect of increasing**: Larger groups, fewer cycles, but more back-and-forth within each cycle
- **Effect of decreasing**: Smaller groups, more cycles, but tighter groupings
- **Default**: 6 tiles

---

## Key Programming Concepts Summary

### Data Types
- **int**: Whole numbers (1, 42, -5)
- **float**: Decimal numbers (3.14, -0.5)
- **str**: Text strings ("hello", 'tile_042')
- **bool**: True or False values
- **list**: Ordered collection that can be modified `[1, 2, 3]`
- **tuple**: Ordered collection that cannot be modified `(1, 2, 3)`
- **set**: Unordered collection with no duplicates `{1, 2, 3}`
- **dict**: Key-value pairs `{'pink': 2, 'blue': 1}`

### Operators
- **Arithmetic**: `+` (add), `-` (subtract), `*` (multiply), `/` (divide), `//` (floor divide), `%` (modulo)
- **Comparison**: `==` (equal), `!=` (not equal), `<` (less than), `>` (greater than), `<=` (less or equal), `>=` (greater or equal)
- **Boolean**: `and` (both True), `or` (at least one True), `not` (invert True/False)
- **Membership**: `in` (check if item in collection), `not in` (check if item not in collection)

### Control Flow
- **if/elif/else**: Make decisions based on conditions
- **for loop**: Repeat code for each item in a collection
- **while loop**: Repeat code while a condition is True
- **break**: Exit a loop early
- **continue**: Skip to next iteration of a loop
- **return**: Exit a function and optionally return a value

### Functions
- **def function_name(parameters)**: Define a function
- **lambda**: Create small anonymous functions
- **return**: Send a value back to the caller

### Common Built-in Functions
- **len()**: Get length of a collection
- **min()**: Find smallest value
- **max()**: Find largest value
- **sum()**: Add up all numbers in a collection
- **range()**: Create a sequence of numbers
- **enumerate()**: Loop with both index and item
- **sorted()**: Return a sorted copy of a collection

### List Operations
- **list[index]**: Access item at position (0-based)
- **list[-1]**: Access last item (negative indexing from end)
- **list[start:end]**: Slice - get items from start to end
- **list[:]**: Get all items (makes a copy)
- **list.append(item)**: Add item to end
- **list.remove(item)**: Remove first occurrence of item
- **list.sort()**: Sort list in place

### Dictionary Operations
- **dict[key]**: Access value for key (crashes if key missing)
- **dict.get(key, default)**: Access value for key (returns default if missing)
- **dict.keys()**: Get all keys
- **dict.values()**: Get all values
- **dict.items()**: Get all key-value pairs

### Set Operations
- **set.add(item)**: Add item to set
- **set.remove(item)**: Remove item from set
- **item in set**: Very fast membership check

### List Comprehensions
```python
[expression for item in collection if condition]
```
Creates a new list by applying an expression to filtered items. Example:
```python
[x * 2 for x in numbers if x > 0]  # Double all positive numbers
```

### Generator Expressions
```python
(expression for item in collection if condition)
```
Like list comprehensions but generates values one at a time (saves memory).

### F-strings
```python
f"text {variable} more text"
```
Embeds variables directly into strings. Example:
```python
name = "Alice"
print(f"Hello {name}!")  # Prints: Hello Alice!
```

### Type Hints
```python
def function(param: int) -> str:
```
Optional annotations that document what types are expected. Don't affect how code runs, just help readability and tools.

---

## How the Algorithm Works (High Level)

1. **Load Map**: Read all tiles, identify Zeus, shrines, and task tiles

2. **Select Tasks**: For each color, pick one tile of each type:
   - 1 monster (from 2 options)
   - 1 statue source for pickup (from 1 option)
   - 1 statue island for delivery (from 3 options)
   - 1 offering for pickup (from 2 options)
   - 1 temple for delivery (from 1 option)
   - Total: 5 tasks × 3 colors = 15 tasks

3. **Create Groups (Cycles)**: Group nearby tasks together
   - Start from tasks closest to Zeus
   - Keep adding nearest tasks until group gets too spread out
   - Repeat until all tasks are grouped

4. **Order Groups**: Determine sequence of groups and tasks
   - Try all possible orderings of tasks within each group
   - Pick valid orderings that respect cargo constraints
   - Select ordering with shortest travel distance
   - Track inventory across groups

5. **Add Shrines**: Collect 3 shrines efficiently
   - Look for wasted moves (leftover moves at end of turns)
   - Visit shrines during wasted moves when possible
   - Add dedicated shrine visits if needed to reach 3 total

6. **Return to Zeus**: Complete the route

7. **Calculate Turns**: Total moves ÷ 3 (rounded up)

---

## Understanding the Output

When you run the code, you'll see several sections:

### Task Selection
```
Selected 15 tasks: [('tile_020', 'monster', 'pink'), ...]
```
Shows which tiles were chosen for each task type and color.

### Group Creation
```
Creating task groups from 15 tasks
Starting new group with tile_053
  Added tile_073
  Cannot add tile_005 (would exceed max distance)
Finalized group: ['tile_053', 'tile_073', 'tile_071']
```
Shows how tasks are grouped into cycles.

### Route Ordering
```
Selecting cycle 1 (inventory: {})
  Group ['tile_053', 'tile_073', 'tile_071']: 6 valid orderings
Selected: ['tile_053', 'tile_073', 'tile_071'] (distance: 12)
```
Shows which group is selected for each cycle and why.

### Cycles Summary
```
Cycle 1: [('tile_053', 'offering_pickup', 'pink'), ('tile_073', 'statue_delivery', 'blue'), ...]
Cycle 2: [('tile_020', 'monster', 'pink'), ...]
```
Shows the final ordered sequence of cycles.

### Shrine Collection
```
Processing cycle 1
  Collecting shrine at (4, 3) using 1 wasted moves
Need 1 more shrines, adding dedicated visits
  Visiting shrine at (10, 7) (distance: 3)
```
Shows when and how shrines are collected.

### Final Route
```
FINAL ROUTE:
  Task: tile_053 (offering_pickup, pink) at (5, 5)
  Shrine at (4, 3)
  Task: tile_073 (statue_delivery, blue) at (4, 7)
  ...
  Return to Zeus at (7, 4)

TOTAL TURNS: 19
```
Complete step-by-step route with final turn count.

---

## Tips for Understanding the Code

1. **Read functions top to bottom**: Each function has a clear purpose stated at the top

2. **Follow the data flow**: 
   - Map file → Tasks → Groups → Ordered route → Final route with shrines

3. **Understand BFS first**: It's the foundation for all distance calculations

4. **Focus on constraints**: The cargo limit and pickup-before-delivery rules drive much of the complexity

5. **Run with different configurations**: Try changing `max_group_distance` or `colors` to see how output changes

6. **Use the logging output**: The messages show exactly what the code is doing at each step

7. **Test small changes**: Modify one thing at a time to see its effect

---

## Common Questions

**Q: Why does the code use BFS instead of calculating straight-line distance?**  
A: You can only travel on water tiles, so you need to find the actual shortest path around land obstacles.

**Q: Why do we need two passes for tile selection?**  
A: To prefer unique tiles for each color when possible, avoiding situations where the same tile appears multiple times in the route.

**Q: What happens if no valid route exists?**  
A: The code will raise a `ValueError` with an error message explaining the constraint violation.

**Q: Can I use this for more or fewer than 3 colors?**  
A: Yes! Just modify the `colors` list in `main()`. The code works for any number of colors.

**Q: Why sort tiles by ID?**  
A: To ensure deterministic behavior - the same tiles are always selected, making results reproducible.

**Q: What's the difference between a group and a cycle?**  
A: These terms are used interchangeably. A "group" or "cycle" is a collection of nearby tasks completed together.

**Q: How does the code ensure we don't carry 3 items at once?**  
A: The `validate_task_sequence()` function checks cargo before each pickup and rejects any sequence that would exceed 2 items.

---

## Glossary

- **Task**: An action to complete (fight monster, pickup/deliver statue or offering)
- **Cycle/Group**: A collection of nearby tasks completed together
- **Route**: The complete sequence of cycles
- **Inventory**: What items you're currently carrying
- **Traversable**: Water tiles you can move through
- **BFS**: Breadth-First Search - algorithm for finding shortest paths
- **Permutation**: One possible ordering of a collection of items
- **Constraint**: A rule that must be followed (cargo limit, pickup before delivery)
- **Wasted moves**: Leftover moves at the end of a turn that can be used for shrines
- **Deterministic**: Produces the same result every time with the same input