# Custom Cycles Feature

## Overview

The custom cycles feature allows you to manually specify how tasks should be grouped into cycles, bypassing the automatic clustering algorithm. This is useful for testing specific scenarios or when you have domain knowledge about optimal task groupings.

## Usage

### Command-Line Arguments

You can specify custom cycles in two ways:

1. **Direct JSON input** (via `--cycles`):
   ```bash
   python main.py --cycles '[["tile_042","tile_033"],["tile_014","tile_015"]]'
   ```
   
   **Note**: Due to PowerShell's JSON escaping issues, this method can be problematic on Windows. Use the file-based approach instead.

2. **JSON file input** (via `--cycles-file`):
   ```bash
   python main.py --cycles-file path/to/cycles.json
   ```
   
   This is the recommended method, especially on Windows with PowerShell.

### JSON Format

The cycles specification should be a JSON array of arrays, where:
- The outer array contains all cycles
- Each inner array contains tile IDs for tasks in that cycle
- Tile IDs must be valid task tiles from the selected colours

Example `cycles.json`:
```json
[
  ["tile_042", "tile_033", "tile_006"],
  ["tile_014", "tile_015"],
  ["tile_058", "tile_053", "tile_000"]
]
```

This creates:
- Cycle 1: 3 tasks at tiles 042, 033, and 006
- Cycle 2: 2 tasks at tiles 014 and 015
- Cycle 3: 3 tasks at tiles 058, 053, and 000

## How It Works

1. **Task Lookup**: The solver converts each tile ID to the corresponding Task object(s)
2. **Validation**: Ensures all specified tiles are valid task tiles in the selected colours
3. **Route Building**: Creates a route that visits all tasks in each cycle before moving to the next
4. **Proximity Ordering**: Within each cycle, tasks are visited in order of proximity (shortest path)
5. **Visualization**: Cycles are color-coded and displayed with the same visual style as automatic clustering

## Example Test File

A test file `test_cycles.json` has been created in the project root:

```json
[
  ["tile_042", "tile_033", "tile_006"],
  ["tile_014", "tile_015"],
  ["tile_058", "tile_053", "tile_000"]
]
```

Test it with:
```bash
python main.py --generate-map --seed 42 --cycles-file test_cycles.json --visualize
```

## Error Handling

The system will report errors for:
- **Invalid JSON syntax**: Malformed JSON structure
- **Missing tiles**: Tile IDs that don't exist or aren't task tiles
- **Wrong colours**: Tiles that exist but aren't in the selected colours
- **File not found**: If the specified JSON file doesn't exist

## Known Limitations

1. **Simulation failures**: Since cargo/dependency logic was removed for visualization clarity, route simulation will typically fail. This is expected behavior.

2. **PowerShell JSON escaping**: Direct JSON input via `--cycles` has issues with PowerShell's quote handling. Always use `--cycles-file` on Windows.

3. **No validation of cycle quality**: The system doesn't verify that your cycles are spatially coherent. You can create cycles with distant tasks, though this defeats the purpose of cycle-based routing.

## Comparison with Automatic Clustering

| Feature | Automatic Clustering | Custom Cycles |
|---------|---------------------|---------------|
| Ease of use | Automatic, no input needed | Requires manual tile ID specification |
| Spatial coherence | Guaranteed (CYCLE_DISTANCE_THRESHOLD=6) | User's responsibility |
| Cycle sizes | Balanced (MAX_CYCLE_TASKS=5) | User-defined |
| Testing | Great for general use | Great for specific scenarios |
| Determinism | Deterministic with seed | Fully deterministic |

## Implementation Notes

- Custom cycles are handled by `solve_with_custom_cycles()` in `src/heuristic.py`
- The method creates TaskCycle objects with the same structure as automatic clustering
- Route visualization (including connectors, step numbers, and cycle colors) works identically
- The `--cycles` and `--cycles-file` arguments are mutually exclusive (file takes precedence)
