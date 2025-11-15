# Modifying Cycles

This guide shows you how to experiment with different cycle orderings to optimize the route.

## What Are Cycles?

Cycles are groups of geographically close tasks. The boat visits all tiles in Cycle 1, then Cycle 2, then Cycle 3, then visits shrines (count configurable), then returns to Zeus.

## How Colours Work

**Cycles are assigned colours automatically in order:**
- Cycle 1 = pink
- Cycle 2 = blue  
- Cycle 3 = green

When you modify `CYCLE_DEFINITIONS`, the tasks are generated dynamically based on:
1. The tile IDs in each cycle
2. The tile types defined in `map1.json` (monster, offering, statue, island, temple)
3. The colour assigned to that cycle

**You only need to update the tile IDs in `cycles.py` - the task colours update automatically!**

## Cargo Constraints

The boat has 2 cargo slots. Some tasks require specific items:

```
Task Type         | Action           | Cargo Requirement
------------------|------------------|----------------------------------
Monster           | Fight            | None
Offering          | Pick up          | Needs empty slot (1 slot used)
Statue Source     | Pick up statue   | Needs empty slot (1 slot used)
Statue Island     | Deliver statue   | Must have statue of same color
Temple            | Deliver offering | Must have offering of same color
```

**Critical Rules:**
- Statue Source tiles MUST come before Statue Island tiles (same color)
- Offering tiles MUST come before Temple tiles (same color)
- You can only carry 2 items at once

## Where To Modify

Edit the file: **`src/cycles.py`**

### Modifying Cycles

Look for the section marked `MODIFY CYCLES HERE`. You'll see 3 lists:

## Example: Swap Cycle Order

To visit Blue tasks before Pink tasks, swap Cycle 2 and Cycle 3:


## Changing Number of Shrines

To visit more or fewer shrines, add or remove tiles from the `SHRINE_TILES` array in `src/cycles.py`:

**To visit 5 shrines instead of 3:**
```python
SHRINE_TILES = ["tile_003", "tile_016", "tile_023", "tile_029", "tile_050"]
```

**To visit no shrines:**
```python
SHRINE_TILES = []
```

## Example: Move a Task Between Cycles

To move Blue monster (tile_028) to Cycle 2:

**Before:**
```python
CYCLE_DEFINITIONS = [
    ["tile_105", "tile_009", "tile_007", "tile_108", "tile_005"],
    ["tile_020", "tile_053", "tile_071", "tile_063", "tile_112"],
    ["tile_028", "tile_061", "tile_094", "tile_077", "tile_015"],
]
```

**After:**
```python
CYCLE_DEFINITIONS = [
    ["tile_105", "tile_009", "tile_007", "tile_108", "tile_005"],
    ["tile_020", "tile_053", "tile_071", "tile_063", "tile_112", "tile_028"],  # Added
    ["tile_061", "tile_094", "tile_077", "tile_015"],  # Removed tile_028
]
```

## How To Test Your Changes

1. Save your changes to `src/cycles.py`
2. Run the solver:
   ```bash
   python main.py
   ```
3. Check the output:
   - Total moves and turns
   - Visualization showing your new route
4. Compare with previous results to see if your changes improved the route

## Common Errors

**Error: "Task dependency not satisfied"**
- Cause: You tried to deliver before picking up (e.g., island before statue)
- Fix: Move the pickup task before the delivery task

**Error: "Cargo capacity exceeded"**
- Cause: You're trying to pick up more than 2 items without delivering
- Fix: Deliver items before picking up more

**Error: "Tile not found"**
- Cause: You typed a tile ID incorrectly
- Fix: Check tile IDs match exactly (e.g., "tile_105" not "tile105")

## Understanding the Output

After running `python main.py`, you'll see:

```
Route: 156 moves, 52 turns
Tasks: 15/15 completed
Shrines: 3/3 built
```

Lower move/turn counts mean more efficient routes. The visualization shows your route as a red line connecting the tiles in order.
