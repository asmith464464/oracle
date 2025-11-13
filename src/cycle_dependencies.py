"""
Cycle dependency analysis and topological sorting.
"""

from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque

from .map_model import TileType
from .heuristic_models import TaskCycle


class CycleDependencyAnalyzer:
    """Analyzes cargo dependencies between cycles and performs topological sorting."""
    
    @staticmethod
    def analyze_dependencies(cycles: List[TaskCycle]) -> Tuple[Dict[int, Set[int]], 
                                                                Dict[int, Set[str]], 
                                                                Dict[int, Set[str]]]:
        """
        Analyze cargo dependencies between cycles.
        
        Returns:
            Tuple of (dependency_graph, cycle_produces, cycle_requires)
            - dependency_graph: Maps cycle index to set of cycle indices it depends on
            - cycle_produces: Maps cycle index to set of cargo types it produces (e.g., "statue:red")
            - cycle_requires: Maps cycle index to set of cargo types it requires
        """
        cycle_produces: Dict[int, Set[str]] = defaultdict(set)
        cycle_requires: Dict[int, Set[str]] = defaultdict(set)
        
        # Analyze what each cycle produces and requires
        for cycle_idx, cycle in enumerate(cycles):
            for task in cycle.tasks:
                if task.task_type == TileType.STATUE_SOURCE:
                    cycle_produces[cycle_idx].add(f"statue:{task.colour}")
                elif task.task_type == TileType.OFFERING:
                    cycle_produces[cycle_idx].add(f"offering:{task.colour}")
                elif task.task_type == TileType.STATUE_ISLAND:
                    cycle_requires[cycle_idx].add(f"statue:{task.colour}")
                elif task.task_type == TileType.TEMPLE:
                    cycle_requires[cycle_idx].add(f"offering:{task.colour}")
        
        # Build dependency graph: cycle A depends on cycle B if A requires what B produces
        dependency_graph: Dict[int, Set[int]] = defaultdict(set)
        
        for cycle_idx in range(len(cycles)):
            required_cargo = cycle_requires.get(cycle_idx, set())
            
            for cargo_type in required_cargo:
                # Find which cycle produces this cargo
                for producer_idx in range(len(cycles)):
                    if producer_idx != cycle_idx and \
                       cargo_type in cycle_produces.get(producer_idx, set()):
                        dependency_graph[cycle_idx].add(producer_idx)
        
        return dependency_graph, cycle_produces, cycle_requires
    
    @staticmethod
    def topological_sort(cycles: List[TaskCycle]) -> List[TaskCycle]:
        """
        Sort cycles in dependency order using Kahn's algorithm.
        Cycles that produce cargo must come before cycles that consume it.
        
        Args:
            cycles: List of TaskCycle objects
            
        Returns:
            List of TaskCycle objects in dependency-respecting order
        """
        if not cycles:
            return []
        
        dependency_graph, _, _ = CycleDependencyAnalyzer.analyze_dependencies(cycles)
        
        # Build reverse graph: reverse_graph[i] = set of cycles that depend on cycle i
        reverse_graph: Dict[int, Set[int]] = defaultdict(set)
        for cycle_idx, dependencies in dependency_graph.items():
            for depends_on in dependencies:
                reverse_graph[depends_on].add(cycle_idx)
        
        # Calculate in-degree for each cycle (number of dependencies)
        in_degree = {i: len(dependency_graph.get(i, set())) for i in range(len(cycles))}
        
        # Kahn's algorithm
        queue = deque([i for i in range(len(cycles)) if in_degree[i] == 0])
        sorted_indices = []
        
        while queue:
            # For deterministic results, sort candidates before processing
            current_batch = sorted(queue)
            queue.clear()
            
            for current in current_batch:
                sorted_indices.append(current)
                
                # Reduce in-degree for cycles that depend on this one
                for dependent_cycle in reverse_graph[current]:
                    in_degree[dependent_cycle] -= 1
                    if in_degree[dependent_cycle] == 0:
                        queue.append(dependent_cycle)
        
        # Check for cycles in the dependency graph
        if len(sorted_indices) != len(cycles):
            # Circular dependencies detected - fall back to original order
            return cycles
        
        # Return cycles in sorted order
        return [cycles[i] for i in sorted_indices]
