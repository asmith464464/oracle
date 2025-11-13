"""Shared data models for the cycle heuristic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .tasks import Task


@dataclass
class TaskCycle:
    """Collection of nearby or related tasks treated as a single cycle."""

    tasks: List[Task]
    center_position: Optional[str] = None
    internal_route: List[str] = field(default_factory=list)
    connector_to_next: List[str] = field(default_factory=list)
    total_distance: int = 0
    entry_tile: Optional[str] = None
    exit_tile: Optional[str] = None
    entry_index: Optional[int] = None
    exit_index: Optional[int] = None

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def get_task_tile_ids(self) -> List[str]:
        return [task.tile_id for task in self.tasks]
