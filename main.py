"""
Oracle Heuristic Route Planner - Main Entry Point

This module serves as the main entry point for the Oracle Heuristic Route Planner.
It loads/generates maps, assigns colours, runs the heuristic, simulates routes,
and optionally displays visualisations.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

from src.map_model import HexGrid
from src.tasks import TaskManager
from src.heuristic import CycleHeuristic
from src.simulator import RouteSimulator
from shrine_optimiser import ShrineOptimiser
from visualiser import HexGridVisualiser
from src.utils import (
    setup_logging, generate_random_colours, create_example_map,
    load_map_from_json, format_route_summary, calculate_efficiency_metrics,
    export_results_to_json, generate_unique_id,
    create_colour_assignment_report, find_colours_with_required_tasks
)


def create_argument_parser() -> argparse.ArgumentParser:
    """Configure command-line arguments for the route planner."""
    parser = argparse.ArgumentParser(
        description="Oracle Heuristic Route Planner - Optimize routes on hex-grid maps"
    )
    
    # Input options
    parser.add_argument('--map', type=str, 
                       help='Path to JSON map file (if not provided, generates example map)')
    parser.add_argument('--colours', nargs=3, 
                       help='Three colours to use (e.g., red blue green)')
    
    # Generation options
    parser.add_argument('--generate-map', action='store_true',
                       help='Generate a new random map')
    parser.add_argument('--map-width', type=int, default=12,
                       help='Width of generated map (default: 12)')
    parser.add_argument('--map-height', type=int, default=10,
                       help='Height of generated map (default: 10)')
    parser.add_argument('--water-ratio', type=float, default=0.6,
                       help='Ratio of water tiles (default: 0.6)')
    
    # Algorithm options
    parser.add_argument('--max-shrines', type=int, default=3,
                       help='Maximum number of shrines to build (default: 3)')
    parser.add_argument('--seed', type=int,
                       help='Random seed for reproducible results')
    parser.add_argument('--cycles', type=str,
                       help='Custom cycles as JSON array of arrays of tile IDs')
    parser.add_argument('--cycles-file', type=str,
                       help='Path to JSON file containing custom cycle specification')
    
    # Output options
    parser.add_argument('--visualize', action='store_true',
                       help='Show visualisation windows')
    parser.add_argument('--view-only', action='store_true',
                       help='View map without running solver or validation (requires --map)')
    parser.add_argument('--save-results', type=str,
                       help='Save results to JSON file')
    parser.add_argument('--save-map', type=str,
                       help='Save generated map to JSON file')
    
    # Logging options
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    parser.add_argument('--log-file', type=str,
                       help='Save logs to file')
    
    return parser


def main():
    """Main function to run the Oracle Heuristic Route Planner."""
    args = create_argument_parser().parse_args()
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Set random seed if provided
        if args.seed is not None:
            import random
            random.seed(args.seed)
            logger.info(f"Using random seed: {args.seed}")
        
        # Load or generate map
        if args.map:
            logger.info(f"Loading map from {args.map}")
            grid = load_map_from_json(args.map)
        else:
            logger.info("Generating example map")
            grid = create_example_map(
                width=args.map_width,
                height=args.map_height,
                water_ratio=args.water_ratio
            )
            
        # Save generated map if requested
        if args.save_map:
            grid.to_json(args.save_map)
            logger.info(f"Saved map to {args.save_map}")
        
        # View-only mode: just visualise and exit
        if args.view_only:
            if not args.map:
                logger.error("--view-only requires --map argument")
                return 1
            logger.info("View-only mode: displaying map without validation")
            visualiser = HexGridVisualiser(grid)
            visualiser.visualise_grid_only()
            return 0
        
        # Validate grid
        issues = grid.validate_grid()
        if len(grid.get_available_colours()) < 3:
            issues.append(f"Insufficient colours available: {len(grid.get_available_colours())} (need at least 3)")
        if issues:
            logger.error(f"Invalid grid: {issues}")
            return 1
            
        logger.info(f"Loaded grid: {grid}")
        
        valid_colours = find_colours_with_required_tasks(grid)
        if len(valid_colours) < 3:
            raise ValueError(
                "Map does not contain enough colours with required tasks to run the scenario"
            )

        # Assign colours
        if args.colours:
            colours = args.colours
            missing = [colour for colour in colours if colour not in valid_colours]
            if missing:
                raise ValueError(
                    f"Specified colours lack required task tiles: {missing}. "
                    f"Valid options are: {valid_colours}"
                )
            logger.info(f"Using specified colours: {colours}")
        else:
            # Use deterministic selection when seed is set
            colours = generate_random_colours(3, valid_colours, deterministic=(args.seed is not None))
            logger.info(f"Generated random colours: {colours}")
        
        # Create colour assignment report
        colour_report = create_colour_assignment_report(grid, colours)
        logger.info("Colour assignment report:")
        for colour, distribution in colour_report['distribution'].items():
            logger.info(f"  {colour}: {distribution}")
        
        # Set up task management
        task_manager = TaskManager(grid)
        task_manager.assign_colours(colours)
        selected_tasks = task_manager.select_tasks_for_colours()
        
        logger.info(f"Selected {len(task_manager.tasks)} tasks across {len(colours)} colours")
        
        # Run heuristic algorithm
        logger.info("Running cycle-based heuristic...")
        heuristic = CycleHeuristic(grid, task_manager)
        
        # Check if custom cycles provided
        if args.cycles or args.cycles_file:
            import json
            try:
                if args.cycles_file:
                    logger.info(f"Reading custom cycles from file: {args.cycles_file}")
                    with open(args.cycles_file, 'r') as f:
                        custom_cycle_tiles = json.load(f)
                else:
                    logger.debug(f"Raw cycles argument: {repr(args.cycles)}")
                    custom_cycle_tiles = json.loads(args.cycles)
                logger.info(f"Using custom cycles: {custom_cycle_tiles}")
                route, stats = heuristic.solve_with_custom_cycles(custom_cycle_tiles)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON for --cycles argument: {e}")
                if args.cycles:
                    logger.error(f"Received: {repr(args.cycles)}")
                return 1
            except FileNotFoundError as e:
                logger.error(f"Cycles file not found: {e}")
                return 1
            except ValueError as e:
                logger.error(f"Invalid cycle specification: {e}")
                return 1
        else:
            route, stats = heuristic.solve()
        
        logger.info(f"Generated route with {len(route)} positions")
        logger.info(f"Statistics: {stats}")
        
        # Optimise shrine placement
        logger.info("Optimising shrine placement...")
        shrine_optimiser = ShrineOptimiser(grid, task_manager)
        optimised_route, shrine_positions = shrine_optimiser.optimise_shrine_placement(
            route, args.max_shrines
        )
        
        logger.info(f"Optimised route with {len(shrine_positions)} shrines")
        
        # Simulate route execution
        logger.info("Simulating route execution...")
        simulator = RouteSimulator(grid, task_manager)
        simulation_result = simulator.simulate_route(optimised_route, shrine_positions)
        
        if simulation_result.success:
            logger.info("Route simulation successful!")
        else:
            logger.error(f"Route simulation failed: {simulation_result.errors}")
            
        # Calculate efficiency metrics
        efficiency_metrics = calculate_efficiency_metrics(
            simulation_result.total_moves,
            simulation_result.total_turns,
            len(simulation_result.completed_tasks),
            len(simulation_result.shrines_built)
        )
        
        # Display results
        print("\n" + "="*50)
        print("ORACLE HEURISTIC ROUTE PLANNER RESULTS")
        print("="*50)
        
        summary = format_route_summary(
            optimised_route,
            simulation_result.total_moves,
            simulation_result.total_turns,
            simulation_result.completed_tasks,
            simulation_result.shrines_built
        )
        print(summary)
        
        print("\nEfficiency Metrics:")
        for metric, value in efficiency_metrics.items():
            print(f"  {metric}: {value:.3f}")
        
        if simulation_result.errors:
            print(f"\nWarnings/Errors:")
            for error in simulation_result.errors:
                print(f"  - {error}")
        
        # Prepare results for export
        completed_task_tiles = [
            task_manager.tasks[task_id].tile_id
            for task_id in simulation_result.completed_tasks
            if task_id in task_manager.tasks
        ]

        selected_task_tiles = sorted({task.tile_id for task in task_manager.tasks.values()})

        results = {
            'run_id': generate_unique_id(),
            'input': {
                'colours': colours,
                'max_shrines': args.max_shrines,
                'seed': args.seed
            },
            'route': {
                'path': optimised_route,
                'total_moves': simulation_result.total_moves,
                'total_turns': simulation_result.total_turns,
                'length': len(optimised_route)
            },
            'tasks': {
                'completed': simulation_result.completed_tasks,
                'completed_tiles': completed_task_tiles,
                'selected_tiles': selected_task_tiles,
                'total_selected': len(task_manager.tasks)
            },
            'shrines': {
                'built': simulation_result.shrines_built,
                'positions': shrine_positions
            },
            'statistics': stats,
            'efficiency_metrics': efficiency_metrics,
            'cycles': heuristic.get_cycle_summary(),
            'simulation_success': simulation_result.success,
            'errors': simulation_result.errors
        }
        
        # Save results if requested
        if args.save_results:
            export_results_to_json(results, args.save_results)
            logger.info(f"Results saved to {args.save_results}")
        
        # Show visualisations if requested
        if args.visualize:
            logger.info("Displaying visualisations...")
            try:
                visualiser = HexGridVisualiser(grid)
                visualiser.show_all_visualisations(
                    optimised_route,
                    heuristic.cycles,
                    {**stats, 'efficiency_metrics': efficiency_metrics},
                    completed_task_tiles,
                    simulation_result.shrines_built,
                    selected_task_tiles,
                    colours
                )
            except Exception as e:
                logger.warning(f"Visualisation failed: {e}")
                print("Note: Visualisation requires matplotlib and may not work in all environments")
        
        print(f"\nRun completed successfully! (ID: {results['run_id']})")
        return 0
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())