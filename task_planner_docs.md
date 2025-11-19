# Task Planner Code Documentation

## Introduction

This document explains how the task planner code works.
---

## Part 1: Storing Information About Tasks

### The Task Class

```python
class Task:
    def __init__(self, id: str, coord: Tuple[int, int], type: str, color: str):
        self.id = id
        self.coord = coord
        self.type = type
        self.color = color
```

**What this does**: Creates a template for storing information about one task.

**Why we need it**: The computer needs to remember multiple pieces of information about each task. Instead of keeping separate lists for tile IDs, locations, types, and colors, we bundle them together.

**How it works**: 
- `class Task:` means "here's a template called Task"
- `def __init__` is a special function that runs when you create a new Task
- `self.id = id` stores the tile name (like "tile_042") 
- `self.coord = coord` stores where it is on the map (like row 5, column 3)
- `self.type = type` stores what kind of task (like "monster" or "statue_pickup")
- `self.color = color` stores which color (like "pink")

**Example**: When we write `Task("tile_020", (6, 2), "monster", "pink")`, we're creating a bundle of information about fighting the pink monster at tile_020.

**New concepts**:
- **Class**: A template for creating bundles of related information
- **self**: Refers to the specific Task being created
- **Tuple**: A pair of numbers in parentheses, like (6, 2), representing a location

---

## Part 2: Understanding the Hexagonal Map

### Hex Grid Constants

```python
HEX_OFFSETS_EVEN = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
HEX_OFFSETS_ODD = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
```

**What this does**: Stores the 6 directions you can move from any hex tile.

**Why we need it**: Hexagonal tiles don't work like a regular grid (up/down/left/right). Each hex has 6 neighbors, and finding them requires math. These lists contain the math shortcuts.

**How it works**: 
- Each `(x, y)` pair represents how to get to one neighbor
- Even rows and odd rows have slightly different neighbor positions (this is how hex grids work)
- For example, `(-1, 0)` means "move left 1 column, stay in same row"

**Why two lists**: Because of how hexagons fit together, the neighbors of a tile in row 2 are in different positions than neighbors of a tile in row 3. Even-numbered rows use one pattern, odd-numbered rows use another.

**New concepts**:
- **List**: A collection of items in square brackets `[item1, item2, item3]`
- **Constant**: A value that never changes while the program runs

---

## Part 3: Calculating Distances

This is the most important part - everything else depends on being able to measure how far apart things are.

### Finding Adjacent Water Tiles

```python
def get_adjacent_water_tiles(tile: Tuple[int, int], traversable: set) -> List[Tuple[int, int]]:
    q, r = tile
    offsets = HEX_OFFSETS_EVEN if r % 2 == 0 else HEX_OFFSETS_ODD
    return [(q + dq, r + dr) for dq, dr in offsets if (q + dq, r + dr) in traversable]
```

**What this does**: Given a tile location, finds all the water tiles next to it.

**Why we need it**: You can't land on task tiles (like monster tiles or statue islands) - only on water tiles next to them. This function finds those water tiles.

**How it works step by step**:
1. `q, r = tile` splits the location into column (q) and row (r)
2. `r % 2 == 0` checks if row number is even (the `%` symbol means "remainder after division")
3. `if r % 2 == 0 else` picks which offset list to use
4. For each offset, adds it to the tile position to get a neighbor location
5. Only keeps neighbors that are water tiles (in the `traversable` collection)

**Why it matters**: Before calculating distances, we need to know which tiles we're trying to reach.

**New concepts**:
- **Function**: A reusable piece of code that takes inputs and produces an output
- **Set**: A collection where each item appears only once, good for quick "is this in here?" checks
- **%** (modulo): Gives the remainder after division. `5 % 2 = 1` because 5 ÷ 2 = 2 remainder 1
- **if/else**: Choose one thing or another based on a condition
- **List comprehension**: `[... for ... in ... if ...]` creates a list by transforming each item that meets a condition

### Calculating Shortest Path (BFS)

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

**What this does**: Calculates the shortest distance (in tile moves) from one location to another.

**Why we need it**: We need to know how far apart things are to plan efficient routes. We can't just measure straight-line distance because you have to go around land and obstacles.

**How it works** (BFS = Breadth-First Search):

Think of it like ripples spreading in a pond:
1. Start at your current position (distance 0)
2. Check all tiles 1 move away
3. Check all tiles 2 moves away
4. Keep expanding until you reach the destination
5. The first time you reach it is the shortest path

**The algorithm in detail**:
1. Find all water tiles next to the destination
2. Create a "waiting list" (queue) starting with your current position at distance 0
3. **Loop**: Take the first position from the waiting list
   - If this position is next to the destination, we found the shortest path - return the distance
   - If we've already checked this position, skip it
   - Otherwise, mark it as checked
   - Add all neighboring water tiles to the waiting list with distance + 1
4. Keep going until we reach the destination

**Why this finds the shortest path**: Because we process tiles in order of distance (all distance 1, then all distance 2, etc.), the first time we reach the destination is guaranteed to be via the shortest route.

**Why return 999999**: This large number represents "unreachable" - if no path exists.

**New concepts**:
- **deque** (pronounced "deck"): A special list where you can efficiently add items to the end and remove from the front
- **while**: Keep repeating code as long as a condition is true
- **return**: Stop the function and send a value back
- **continue**: Skip the rest of this loop and move to the next item
- **in**: Check if an item is in a collection
- **.popleft()**: Remove and get the first item from a deque
- **.add()**: Add an item to a set
- **.append()**: Add an item to the end of a list

---

## Part 4: Creating Task Groups (Cycles)

Now that we can measure distances, we can group nearby tasks together.

### Finding Closest Task to a Position

```python
def find_nearest_task_to_position(position: Tuple[int, int], tasks: List[Task], traversable: set) -> Task:
    return min(tasks, key=lambda t: bfs_distance(position, t.coord, traversable))
```

**What this does**: Given a location and a list of tasks, finds which task is closest.

**Why we need it**: When starting a new group, we want to begin with the task closest to Zeus (minimizes wasted travel at the start).

**How it works**:
- `min(tasks, ...)` finds the smallest value in the list
- `key=lambda t: ...` tells it what to measure for each task
- `lambda t:` creates a tiny function that takes a task `t`
- `bfs_distance(...)` calculates how far that task is
- The task with the smallest distance wins

**New concepts**:
- **min()**: Built-in function that finds the smallest item
- **lambda**: A way to create a small, throwaway function without giving it a name
- **key parameter**: Tells min/max/sorted what to measure when comparing items

### Finding Closest Task to a Group

```python
def find_nearest_task_to_group(group: List[Task], ungrouped: List[Task], traversable: set) -> Task:
    return min(ungrouped, key=lambda t: min(bfs_distance(g.coord, t.coord, traversable) for g in group))
```

**What this does**: Finds which ungrouped task is closest to any task already in the group.

**Why we need it**: When building a group, we keep adding the nearest available task to keep the group compact.

**How it works**:
- For each ungrouped task, measure distance to every task in the group
- Take the minimum of those distances (closest group member)
- Return the ungrouped task with the smallest minimum distance

**New concepts**:
- **Nested min()**: Using min inside min - the inner one finds closest group member, outer one finds closest ungrouped task
- **Generator expression**: `(... for g in group)` creates values one at a time without making a full list (saves memory)

### Checking if Group is Too Spread Out

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

**What this does**: Checks if any two tasks in a group are too far apart.

**Why we need it**: If a group gets too spread out, you waste time traveling back and forth. This prevents that.

**How it works**:
1. Use nested loops to check every pair of tasks
2. `range(len(group))` creates numbers 0, 1, 2, ... up to group size
3. `range(i + 1, len(group))` starts from i+1 to avoid checking the same pair twice
4. Calculate distance both directions (sometimes routes differ due to obstacles)
5. If ANY pair exceeds max distance, return True (too spread out)
6. If all pairs are okay, return False (acceptable)

**New concepts**:
- **for loop**: Repeat code for each item in a collection
- **range()**: Creates a sequence of numbers. `range(5)` gives 0, 1, 2, 3, 4
- **len()**: Returns how many items are in a list
- **Nested loops**: A loop inside another loop, used to check all combinations
- **bool**: True or False value

### Creating All Task Groups

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

**What this does**: The main function that organizes all tasks into groups of nearby tasks.

**Why we need it**: This implements the "cycle method" - grouping nearby tasks so you don't zigzag all over the map.

**How it works step by step**:

1. **Setup**:
   - `ungrouped = tasks[:]` creates a copy of all tasks (the `[:]` means "all items")
   - `groups = []` creates an empty list to store finished groups

2. **Outer loop** (`while ungrouped:`): Keeps creating groups until all tasks are grouped

3. **Start new group**:
   - Find the closest ungrouped task to Zeus
   - Create a new group with just that task
   - Remove it from the ungrouped list

4. **Inner loop** (`while ungrouped:`): Keep adding tasks to current group
   - Find the nearest ungrouped task to the group
   - Test if adding it would make the group too spread out
   - If okay: remove from ungrouped, add to group
   - If too spread out: stop adding to this group with `break`

5. **Finish group**: Add the completed group to the groups list

6. **Return**: Send back all the groups

**Why this order matters**: Starting groups with tasks closest to Zeus minimizes initial travel. Always adding the nearest task keeps groups compact.

**New concepts**:
- **list[:]**: Creates a copy of a list
- **.remove(item)**: Removes an item from a list
- **.append(item)**: Adds an item to the end of a list
- **not**: Reverses True/False. `not True` becomes `False`
- **break**: Exits the current loop immediately
- **logging.info()**: Prints messages to help track what the program is doing
- **f"text {variable}"**: F-string - embeds variables in text. `f"Hello {name}"` might print "Hello Alice"
- **while**: Repeats code as long as condition is True

---

## Part 5: Validating Task Order (Checking Game Rules)

Before we can order the groups, we need a way to check if a sequence of tasks is legal.

### Validation Function

```python
def validate_task_sequence(tasks: List[Task], starting_inventory: dict) -> Tuple[bool, dict]:
    inventory = starting_inventory.copy()
    
    for task in tasks:
        if 'pickup' in task.type:
            total_cargo = sum(inventory.values())
            if total_cargo >= 2:
                return False, {}
            key = (task.type, task.color)
            inventory[key] = inventory.get(key, 0) + 1
            
        elif 'delivery' in task.type:
            if 'statue' in task.type:
                key = ('statue_pickup', task.color)
            elif 'offering' in task.type:
                key = ('offering_pickup', task.color)
            else:
                return False, {}
            
            if inventory.get(key, 0) <= 0:
                return False, {}
            inventory[key] -= 1
    
    return True, inventory
```

**What this does**: Checks if a sequence of tasks follows the game rules (max 2 cargo, must pickup before delivery).

**Why we need it**: Not all task orderings are valid. You can't deliver something you haven't picked up, and you can't carry more than 2 items. This function catches violations.

**How it works**:

1. **Setup**: Make a copy of the starting inventory (what you're already carrying)

2. **Check each task**:
   
   **For pickups**:
   - Count how many items you're currently carrying with `sum(inventory.values())`
   - If already carrying 2, return False (invalid)
   - Create a key: `(task.type, task.color)` - example: `('statue_pickup', 'pink')`
   - Add 1 to the count for that key

   **For deliveries**:
   - Figure out which pickup type this delivery needs
   - For statue delivery, need statue_pickup of same color
   - For offering delivery, need offering_pickup of same color
   - Check if you have at least 1 of that item
   - If not, return False (can't deliver what you don't have)
   - Subtract 1 from the count

3. **Return result**: If all tasks passed, return True and the final inventory

**Why we use (type, color) keys**: Without this, a pink offering could be confused with a pink statue! The key `('statue_pickup', 'pink')` is different from `('offering_pickup', 'pink')`.

**New concepts**:
- **dict** (dictionary): A collection of key-value pairs, like a phone book. `{'Alice': 5551234, 'Bob': 5555678}`
- **.copy()**: Makes a copy so changes don't affect the original
- **.values()**: Gets all the values from a dictionary (ignoring the keys)
- **sum()**: Adds up all numbers in a collection
- **'text' in variable**: Checks if text appears anywhere in a string
- **.get(key, default)**: Gets value from dictionary, returns default if key doesn't exist
- **elif**: Short for "else if" - checks another condition if first if was False
- **Tuple of values**: `return True, inventory` returns two things at once

---

## Part 6: Ordering Groups into a Route

Now we order the groups and decide which tasks within each group to do in what order.

### Main Ordering Function

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
            logging.error(f"Current inventory: {current_inventory}")
            for group in remaining:
                logging.error(f"  Remaining: {[(t.id, t.type, t.color) for t in group]}")
            raise ValueError("Cannot find valid route - check task constraints")
        
        logging.info(f"Selected: {[t.id for t in best_ordering]} (distance: {best_distance})")
        logging.info(f"Ending inventory: {best_ending_inventory}")
        
        ordered_route.append(best_ordering)
        current_pos = best_ordering[-1].coord
        current_inventory = best_ending_inventory
        remaining.remove(best_group)
        cycle_num += 1
    
    logging.info("Route ordering complete\n")
    return ordered_route
```

**What this does**: Orders the groups and the tasks within each group to minimize distance while following game rules.

**Why we need it**: We have groups, but don't know: (1) which order to visit groups, (2) which order to do tasks within each group. This figures out both.

**How it works**:

1. **Setup**:
   - Start at Zeus with empty inventory
   - Track which groups haven't been visited yet

2. **Main loop** (for each cycle to select):
   - Reset "best so far" tracking variables
   
3. **Try each remaining group**:
   - **Try all possible task orderings** within that group
   - `permutations(group)` generates every possible order
   - For example, [A, B, C] generates: ABC, ACB, BAC, BCA, CAB, CBA (6 total)
   
4. **For each ordering**:
   - Check if it's valid with current inventory
   - If not valid, skip it with `continue`
   - If valid, calculate total distance:
     - Distance from current position to first task
     - Plus distance between each consecutive pair of tasks
   - If this is the shortest valid ordering so far, remember it

5. **After trying all groups**:
   - If no valid ordering found, stop with an error message
   - Otherwise, select the best ordering
   - Update position to end of that group
   - Update inventory to reflect what you're carrying after that group
   - Remove that group from remaining
   - Move to next cycle

6. **Return**: The ordered list of cycles

**Why inventory tracking matters**: You can't deliver a pink statue in cycle 2 if you pick it up in cycle 4. Tracking inventory across cycles ensures pickups always come before their deliveries.

**Why try all permutations**: For a group of 4 tasks, there are 24 possible orderings (4×3×2×1). Some might violate rules, some might be longer. We try them all to find the best valid one.

**New concepts**:
- **float('inf')**: Represents infinity - used to initialize best_distance so any real distance will be smaller
- **permutations()**: From the `itertools` library, generates all possible orderings
- **continue**: Skip rest of loop and move to next item
- **list[-1]**: Negative indexing gets items from the end. `-1` is last, `-2` is second-to-last
- **raise ValueError()**: Stop the program with an error message
- **logging.error()**: Like logging.info but for error messages
- **\n**: Creates a new line in text

---

## Part 7: Adding Shrines to the Route

### Shrine Collection Function

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

**What this does**: Adds shrine collection to the route, trying to collect them during "wasted moves" when possible.

**Why we need it**: You must collect 3 shrines, but when you collect them affects efficiency. This finds opportunities to collect shrines without adding extra turns.

**Understanding "wasted moves"**: 
- Each turn = 3 moves
- If you complete a task on move 2, you have 1 "wasted" move left in that turn
- We can use that wasted move to visit a nearby shrine for free

**How it works**:

**Part 1 - Process each cycle and task**:
1. For each task:
   - Calculate how many moves to reach it
   - Add task to final route
   - Update position

2. Check for shrine opportunities:
   - If we still need shrines, check if we're at the end of a turn
   - `total_moves % 3` tells us position in current turn (0, 1, or 2)
   - If not at position 0, we have wasted moves
   - Calculate how many: `3 - position`
   - Look for a shrine within that distance
   - If found, visit it (efficient - uses moves that would be wasted anyway)

**Part 2 - Add remaining shrines**:
1. Calculate how many more shrines we need (3 minus collected so far)
2. For each needed shrine:
   - Find the closest available shrine
   - Travel there (these are dedicated trips, not wasted moves)
   - Mark it as collected

**Part 3 - Return to Zeus**:
1. Calculate distance back to Zeus
2. Add to route
3. Calculate total turns: `(total_moves + 2) // 3`

**Why this turn calculation formula**: 
- `//` means "divide and round down"
- Adding 2 before dividing rounds up
- Examples: 7 moves = (7+2)//3 = 3 turns; 10 moves = (10+2)//3 = 4 turns

**New concepts**:
- **enumerate()**: When looping, gives you both the index (position number) and the item
- **tuple**: `('task', task)` is an immutable pair of values
- **and**: Both conditions must be true
- **for _ in range(n)**: Loop n times when you don't need the counter
- **//**: Floor division - divides and rounds down

---

## Part 8: Loading the Map and Selecting Tasks

### Task Selection Function

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

**What this does**: Loads the map file and selects exactly one tile per task type per color.

**Why we need it**: The map has multiple options for some tiles (2 monster tiles per color, 3 statue islands per color). We need to pick one of each.

**How it works**:

**Step 1 - Map tile names to task types**:
- The map file uses names like 'statue_source' and 'temple'
- Our code uses 'statue_pickup' and 'offering_delivery'
- TYPE_MAP translates between them

**Step 2 - Collect all tiles from the map**:
- Loop through every tile in the map data
- Extract its location, type, and ID
- Sort tiles into categories:
  - Water tiles → add to `traversable` (tiles we can move on)
  - Zeus tile → save its location
  - Shrine tiles → save their locations
  - Task tiles → organize by type and color

**Step 3 - Sort tiles for deterministic selection**:
- For each task type and color combination, sort the available tiles by ID
- This ensures we always pick the same tiles in the same order
- Without sorting, the selection could vary between runs

**Step 4 - Select tiles (two-pass approach)**:

**First pass** - Try to use unique tiles:
- Go through each task type in a fixed order
- For each color, find tiles that haven't been used yet
- Pick the first unused tile
- Mark that tile as used
- Goal: Avoid using the same physical tile for multiple colors

**Second pass** - Fill in gaps:
- If first pass couldn't find unique tiles (not enough available), use any available tile
- This handles cases where there's only one tile option for a type

**Step 5 - Create Task objects**:
- Convert the selected tiles into Task objects
- Process in a fixed order for consistent results
- Return the tasks along with other map info

**Why two passes**: Imagine tile_005 can deliver both pink and green statues. If we're not careful, we might use it for both, creating a duplicate. The two-pass approach tries to pick tile_005 for pink and tile_080 for green, keeping them separate.

**Why fixed ordering matters**: If we processed colors or task types in random order, we'd get different results each time. Fixed ordering makes the program deterministic (same input → same output).

**New concepts**:
- **dict literal**: `{'key1': 'value1', 'key2': 'value2'}` creates a dictionary
- **None**: Represents "nothing" or "no value"
- **tuple()**: Converts a list to a tuple
- **.get('key', default)**: Get dictionary value, return default if key missing
- **if key not in dict**: Check if key doesn't exist
- **.add()**: Add item to a set
- **.sort()**: Sort a list in place
- **continue**: Skip to next iteration of loop
- **Multiple return values**: Functions can return multiple things at once

---

## Part 9: The Main Function (Putting It All Together)

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


if __name__ == "__main__":
    main()
```

**What this does**: The main entry point that runs all the planning steps in order and displays the results.

**Why we need it**: This orchestrates everything - calling the other functions in the right order to produce the final route.

**How it works**:

1. **Load map file**:
   - `with open(...)` opens the file
   - `json.load()` reads the JSON format and converts to Python data structures
   - The file automatically closes when done

2. **Set configuration**:
   - Which 3 colors to use
   - Maximum distance allowed in a group

3. **Select tasks from map**:
   - Calls `select_tasks_from_map()` to pick tiles
   - Returns 4 things: tasks, water tiles, shrine locations, Zeus location

4. **Validate Zeus was found**:
   - If Zeus location is None, stop with error

5. **Create groups (cycles)**:
   - Calls `create_task_groups()` to cluster nearby tasks

6. **Order the route**:
   - Calls `order_groups_into_route()` to sequence everything

7. **Display cycles**:
   - Print separator line (60 equal signs)
   - Show each cycle with its tasks

8. **Add shrines**:
   - Calls `add_shrines_to_route()` to complete the route
   - Returns final route and total turns

9. **Display final route**:
   - Print separator line
   - Show every step: tasks, shrines, return to Zeus
   - Print total turns needed

10. **The if statement at bottom**:
    - `if __name__ == "__main__":` is a special check
    - Means: "only run main() if this file is being run directly"
    - Allows the code to be imported elsewhere without auto-running

**What the output looks like**:
```
Selected 15 tasks: [...]

Creating task groups from 15 tasks
Starting new group with tile_020
  Added tile_009
  ...

Ordering groups into route...
Selecting cycle 1 (inventory: {})
  ...

============================================================
Cycle 1: [('tile_077', 'offering_pickup', 'blue'), ...]
Cycle 2: [...]
...

============================================================
Adding shrine collection to route...
Processing cycle 1
  Collecting shrine at (10, 5) using 1 wasted moves
  ...

============================================================
FINAL ROUTE:
  Task: tile_077 (offering_pickup, blue) at (9, 7)
  Shrine at (10, 5)
  ...
  Return to Zeus at (7, 4)

============================================================
TOTAL TURNS: 23
============================================================
```

**New concepts**:
- **with statement**: Context manager that automatically handles file closing
- **json.load()**: Parses JSON (JavaScript Object Notation) text into Python data
- **if __name__ == "__main__"**: Special check to see if file is being run directly
- **String multiplication**: `"=" * 60` creates 60 equal signs in a row

---

## Configuration Options

You can modify these values in `main()` to change how the program works:

### Changing Colors

```python
colors = ['pink', 'blue', 'green']
```

**What to change**: Replace with any three colors from: pink, blue, green, red, black, yellow

**Example**: `colors = ['red', 'black', 'yellow']`

**Effect**: The program will plan a route for those three colors instead

### Changing Group Size

```python
max_group_distance = 6
```

**What to change**: Increase or decrease this number

**Effect**: 
- **Higher number** (like 8 or 10): Larger groups with fewer cycles, but more back-and-forth within each group
- **Lower number** (like 4 or 5): Smaller, tighter groups with more cycles

**Recommended**: Keep between 5 and 8 for best results

---

## Understanding the Algorithm Flow

Here's the big picture of what the program does:

1. **Load Map** → Read tile locations and types
2. **Select Tasks** → Pick one tile per task type per color (15 tasks total)
3. **Group Tasks** → Cluster nearby tasks into cycles
4. **Order Groups** → Decide which cycle to do first, second, etc.
5. **Order Within Groups** → Try all task orderings to find shortest valid one
6. **Add Shrines** → Collect 3 shrines using wasted moves when possible
7. **Return to Zeus** → Complete the route
8. **Calculate Turns** → Total moves ÷ 3 (rounded up)

Each step builds on the previous ones - you can't order groups until you've created them, you can't calculate distances until you know tile locations, etc.

---

## Why the Code is Written This Way

### Why Use BFS Instead of Straight Lines?

You might wonder: "Why not just measure straight-line distance?"

**Answer**: You can only travel on water tiles. The straight line might go through land. BFS finds the actual shortest path around obstacles.

### Why Try All Permutations?

You might wonder: "Why try all 24 orderings of 4 tasks? That seems wasteful."

**Answer**: Different orderings have different distances and different constraint violations. The only way to find the best valid ordering is to try them all. For 4 tasks, checking 24 options is fast. (The program gets slower with groups of 6+ tasks since 6! = 720 permutations.)

### Why Two Passes for Tile Selection?

You might wonder: "Why not just pick the first available tile each time?"

**Answer**: Some tiles can serve multiple colors. If we pick tile_005 for pink statues first, and later there's no other option for green statues, tile_005 might appear twice in the route. The two-pass approach tries to keep each physical tile used only once.

### Why Track Inventory Across Cycles?

You might wonder: "Why not just validate each cycle independently?"

**Answer**: You might pick up a pink statue in cycle 1 and still be carrying it in cycle 2. If we only checked cycle 2 alone, we wouldn't know about that pink statue and might incorrectly allow picking up 2 more items. Tracking inventory across cycles ensures global validity.

---

## Common Patterns in the Code

As you read through, you'll notice these patterns repeat:

### Pattern 1: Loop Through and Find Best

```python
best = None
best_value = float('inf')
for item in items:
    value = calculate_something(item)
    if value < best_value:
        best_value = value
        best = item
```

**What it does**: Finds the item with the smallest value

**Where it's used**: Finding nearest tasks, shortest distances, best orderings

### Pattern 2: Nested Loops for Pairs

```python
for i in range(len(items)):
    for j in range(i + 1, len(items)):
        # Compare items[i] and items[j]
```

**What it does**: Checks every pair of items without duplicates

**Where it's used**: Checking if groups are too spread out

### Pattern 3: Validation with Early Exit

```python
for item in items:
    if not valid(item):
        return False
return True
```

**What it does**: Checks each item; returns False as soon as one fails; returns True only if all pass

**Where it's used**: Validating task sequences

### Pattern 4: Building Lists Gradually

```python
result = []
for item in items:
    if condition(item):
        result.append(item)
return result
```

**What it does**: Creates a new list by filtering and transforming items

**Where it's used**: Finding adjacent tiles, creating task lists

---

## Glossary of Programming Terms

**Variable**: A named storage location. Like a labeled box that holds a value.

**Function**: A reusable piece of code with a name. Takes inputs, does something, returns output.

**List**: An ordered collection of items. Can be modified. Written with square brackets: `[1, 2, 3]`

**Tuple**: An ordered collection that can't be modified. Written with parentheses: `(1, 2)`

**Set**: An unordered collection with no duplicates. Fast for checking membership. Written with curly braces: `{1, 2, 3}`

**Dictionary**: A collection of key-value pairs. Like a phone book. Written as: `{'name': 'Alice', 'age': 30}`

**String**: Text data. Written in quotes: `"hello"` or `'hello'`

**Integer**: Whole numbers: `1, 42, -5`

**Float**: Decimal numbers: `3.14, -0.5, 2.0`

**Boolean**: True or False value

**Class**: A template for creating objects that bundle data and behavior

**Loop**: Repeating code multiple times

**Condition**: A test that evaluates to True or False

**Index**: The position of an item in a list (starting from 0)

**Key**: The lookup value in a dictionary

**Value**: The stored data associated with a key

**Return**: Send a result back from a function

**Parameter**: An input to a function

**Argument**: The actual value passed when calling a function

---

## Reading Program Output

When you run the program, here's how to interpret what you see:

### Task Selection
```
Selected 15 tasks: [('tile_020', 'monster', 'pink'), ...]
```
Shows which specific tiles were chosen for each task.

### Group Creation
```
Starting new group with tile_020
  Added tile_009
  Cannot add tile_005 (would exceed max distance)
Finalized group: ['tile_020', 'tile_009', 'tile_007']
```
Shows how tasks are being clustered into groups.

### Route Ordering
```
Selecting cycle 1 (inventory: {})
  Group [...]: 6 valid orderings
Selected: [...] (distance: 11)
Ending inventory: {('offering_pickup', 'blue'): 1}
```
Shows which group was selected for each cycle, how many valid orderings existed, and what you're carrying afterward.

### Shrine Collection
```
Processing cycle 1
  Collecting shrine at (10, 5) using 1 wasted moves
```
Shows when shrines are collected and whether they use wasted moves (efficient) or dedicated trips.

### Final Route
```
FINAL ROUTE:
  Task: tile_077 (offering_pickup, blue) at (9, 7)
  Shrine at (10, 5)
  ...
  Return to Zeus at (7, 4)

TOTAL TURNS: 23
```
The complete step-by-step route with the final turn count.

---

## Troubleshooting

### "No valid ordering found"

**What it means**: The program couldn't find a way to order the remaining tasks that follows the game rules.

**Common causes**:
- A group has too many pickups without enough deliveries
- Trying to deliver before picking up
- Can't stay under 2 item cargo limit

**How to fix**: 
- Try increasing `max_group_distance` to allow more flexible grouping
- Check that the map has correct tile types and colors

### "Zeus tile not found"

**What it means**: The map file doesn't specify which tile is Zeus.

**How to fix**: Check that the map JSON has a `"zeus_tile"` field with a valid tile ID.

### Program runs forever

**What it means**: Probably stuck in a loop trying all permutations of a very large group.

**How to fix**: 
- Reduce `max_group_distance` to create smaller groups
- Groups of 7+ tasks create thousands of permutations (7! = 5040)

---

## Summary

This program solves a complex routing problem by breaking it into manageable steps:

1. **Distance calculation** (BFS) - Foundation for everything else
2. **Grouping** - Cluster nearby tasks
3. **Validation** - Check game rules
4. **Ordering** - Find best sequence
5. **Shrine optimization** - Use wasted moves efficiently

Each function does one specific job and passes its results to the next function. This makes the code easier to understand, test, and modify.

The key insight is that we can't just visit tasks in any order - we must respect the cargo limit and pickup-before-delivery rules. By validating every potential ordering and tracking inventory across cycles, we ensure the final route is actually playable.