"""Minimal hex-grid visualization helpers built on hexalattice."""

from __future__ import annotations

from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as patheffects
from hexalattice.hexalattice import plot_single_lattice_custom_colors
from matplotlib.patches import Circle, Polygon
import math

from .map_model import HexGrid, Tile, TileType

BASE_COLOURS = {
    TileType.WATER.value: "#B7C9E2",
    TileType.MONSTER.value: "#F8E3E3",
    TileType.OFFERING.value: "#FFF3C4",
    TileType.STATUE_SOURCE.value: "#E3F8E3",
    TileType.STATUE_ISLAND.value: "#E3F0F8",
    TileType.TEMPLE.value: "#F5E8FF",
    TileType.SHRINE.value: "#FFE7D6",
}

PLAYER_COLOURS = {
    "red": "#E74C3C",
    "blue": "#3498DB",
    "green": "#27AE60",
    "yellow": "#F1C40F",
    "purple": "#9B59B6",
    "orange": "#E67E22",
    "cyan": "#1ABC9C",
    "magenta": "#C2185B",
    "pink": "#EC4899",
    "black": "#111827",
}

TILE_KEY_ENTRIES = [
    (TileType.MONSTER, "MO", "Monster"),
    (TileType.OFFERING, "OF", "Offering"),
    (TileType.STATUE_SOURCE, "SS", "Statue Source"),
    (TileType.STATUE_ISLAND, "SI", "Statue Island"),
    (TileType.TEMPLE, "TE", "Temple"),
    (TileType.SHRINE, "SH", "Shrine"),
]

TILE_ABBREVIATIONS = {tile_type: abbr for tile_type, abbr, _ in TILE_KEY_ENTRIES}

PALETTE = (
    "#E74C3C",
    "#3498DB",
    "#27AE60",
    "#F1C40F",
    "#9B59B6",
    "#1ABC9C",
    "#E67E22",
)


class HexGridVisualizer:
    """Draw the map and optional overlays with minimal ceremony."""

    def __init__(self, grid: HexGrid, min_diameter: float = 0.9) -> None:
        self.grid = grid
        self.min_diameter = max(0.4, min_diameter)
        self.tile_ids = list(grid.tiles)
        centres = [self._hex_to_pixel(grid.tiles[t].coords) for t in self.tile_ids]
        self.centres = np.array(centres, dtype=float) if centres else np.empty((0, 2))
        self.id_to_index = {tile_id: idx for idx, tile_id in enumerate(self.tile_ids)}

    def show_all_visualizations(
        self,
        route: Sequence[str],
        cycles,
        stats,
        completed_tasks: Sequence[str],
        shrines_built: Sequence[str],
        selected_task_tiles: Sequence[str] | None,
        highlight_colours: Iterable[str] | None,
    ) -> None:
        figures = [
            self.plot_map(highlight_colours, selected_task_tiles),
            self.plot_route(route, completed_tasks, shrines_built, selected_task_tiles, highlight_colours),
        ]
        if cycles:
            figures.append(self.plot_cycles(route, cycles, highlight_colours))
        if stats:
            figures.append(self.plot_statistics(stats))

        figures.reverse()

        for fig in figures:
            plt.show(block=True)
            plt.close(fig)

    def plot_map(
        self,
        highlight_colours: Iterable[str] | None = None,
        selected_task_tiles: Sequence[str] | None = None,
    ):
        fig, ax = self._render_base(highlight_colours)
        if selected_task_tiles:
            self._outline_tiles(
                ax,
                selected_task_tiles,
                "#2563EB",
                linewidth=2.6,
                alpha=0.95,
            )
        return fig

    def plot_route(
        self,
        route: Sequence[str] | None = None,
        completed: Sequence[str] | None = None,
        shrines: Sequence[str] | None = None,
        selected: Sequence[str] | None = None,
        highlight_colours: Iterable[str] | None = None,
    ):
        fig, ax = self._render_base(highlight_colours)

        if selected:
            self._outline_tiles(
                ax,
                selected,
                "#3B82F6",
                linewidth=2.4,
                alpha=0.9,
            )

        points = [self._centre_for(tid) for tid in (route or []) if tid in self.id_to_index]
        if len(points) >= 2:
            xs, ys = zip(*points)
            ax.plot(xs, ys, color="#FF6B6B", linewidth=2.0, alpha=0.85)
            ax.scatter(*points[0], color="#2ECC71", s=40, zorder=6)
            ax.scatter(*points[-1], color="#E74C3C", s=40, zorder=6)
            
            # Draw directional arrows on route
            if route:
                self._draw_route_arrows(ax, route, color="#1F2933", alpha=0.8)

        self._outline_tiles(ax, completed or (), "#10B981", linewidth=2.2, alpha=0.9)
        self._outline_tiles(ax, shrines or (), "#F59E0B", linewidth=2.2, alpha=0.9)

        return fig

    def plot_cycles(
        self,
        route: Sequence[str],
        cycles,
        highlight_colours: Iterable[str] | None = None,
    ):
        fig, ax = self._render_base(highlight_colours)

        for idx, cycle in enumerate(cycles):
            # Use PALETTE color for cycle visualization
            cycle_color = PALETTE[idx % len(PALETTE)]
            
            # Outline task tiles in cycle color
            task_ids = [task.tile_id for task in getattr(cycle, "tasks", [])]
            self._outline_tiles(ax, task_ids, cycle_color, linewidth=2.6, alpha=0.9)

            # Draw cycle route using stored internal_route with offset for overlaps
            internal_route = getattr(cycle, "internal_route", [])
            points = self._get_offset_points(internal_route, idx)
            if len(points) >= 2:
                xs, ys = zip(*points)
                ax.plot(
                    xs,
                    ys,
                    color=cycle_color,
                    linewidth=2.2,
                    alpha=0.75,
                    solid_capstyle="round",
                    zorder=5 + idx,
                    path_effects=[
                        patheffects.Stroke(linewidth=3.6, foreground="white"),
                        patheffects.Normal(),
                    ],
                )
            
            # Draw directional arrows for this cycle
            if internal_route:
                self._draw_route_arrows(ax, internal_route, color=cycle_color, alpha=0.85)

            anchor_tile = getattr(cycle, "center_position", None) or (task_ids[0] if task_ids else None)
            if anchor_tile and anchor_tile in self.id_to_index:
                cx, cy = self._centre_for(anchor_tile)
                ax.text(
                    cx,
                    cy + self.min_diameter * 0.35,
                    f"C{idx + 1}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=cycle_color,
                    zorder=8,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, linewidth=0),
                )

        # Draw Zeus to first cycle connector
        if cycles and len(route) > 0:
            first_cycle_start = getattr(cycles[0], "entry_index", 0)
            if first_cycle_start is not None and first_cycle_start > 0:
                connector = route[0:first_cycle_start + 1]
                points = [self._centre_for(tid) for tid in connector if tid in self.id_to_index]
                if len(points) >= 2:
                    xs, ys = zip(*points)
                    ax.plot(
                        xs, ys,
                        color="#2C3E50",
                        linewidth=1.5,
                        linestyle=(0, (3, 4)),
                        alpha=0.6,
                        zorder=3,
                        path_effects=[
                            patheffects.Stroke(linewidth=3.0, foreground="white", alpha=0.8),
                            patheffects.Normal(),
                        ],
                    )
        
        # Draw connectors between cycles using stored connector_to_next
        for idx in range(len(cycles) - 1):
            connector = getattr(cycles[idx], "connector_to_next", [])
            points = [self._centre_for(tid) for tid in connector if tid in self.id_to_index]
            
            if len(points) >= 2:
                xs, ys = zip(*points)
                ax.plot(
                    xs,
                    ys,
                    color="#2C3E50",
                    linewidth=1.5,
                    linestyle=(0, (3, 4)),
                    alpha=0.6,
                    zorder=3,
                    path_effects=[
                        patheffects.Stroke(linewidth=3.0, foreground="white", alpha=0.8),
                        patheffects.Normal(),
                    ],
                )
        
        # Draw last cycle to Zeus connector
        if cycles and len(route) > 0:
            last_cycle_end = getattr(cycles[-1], "exit_index", len(route) - 1)
            if last_cycle_end is not None and last_cycle_end < len(route) - 1:
                connector = route[last_cycle_end:len(route)]
                points = [self._centre_for(tid) for tid in connector if tid in self.id_to_index]
                if len(points) >= 2:
                    xs, ys = zip(*points)
                    ax.plot(
                        xs, ys,
                        color="#2C3E50",
                        linewidth=1.5,
                        linestyle=(0, (3, 4)),
                        alpha=0.6,
                        zorder=3,
                        path_effects=[
                            patheffects.Stroke(linewidth=3.0, foreground="white", alpha=0.8),
                            patheffects.Normal(),
                        ],
                    )

        return fig

    def plot_statistics(self, stats: dict):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        
        labels = ["Moves", "Turns", "Route", "Cycles"]
        values = [stats.get(k, 0) for k in ["total_moves", "total_turns", "route_length", "cycles_formed"]]
        axes[0].bar(labels, values, color="#5DA5DA")
        axes[0].set_title("Core Metrics")

        cycle_counts = stats.get("tasks_per_cycle", [])
        if cycle_counts:
            axes[1].bar(range(1, len(cycle_counts) + 1), cycle_counts, color="#FAA43A")
            axes[1].set_title("Tasks per Cycle")
            axes[1].set_xlabel("Cycle")
            axes[1].set_ylabel("Tasks")

        fig.tight_layout()
        return fig

    def _render_base(self, highlight_colours: Iterable[str] | None):
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.subplots_adjust(right=0.78)
        ax.set_aspect("equal")
        ax.axis("off")

        if not self.tile_ids:
            return fig, ax

        tiles = [self.grid.tiles[t] for t in self.tile_ids]
        faces = np.array([
            "#F9E79F" if tile.id == self.grid.zeus_tile_id else BASE_COLOURS.get(tile.tile_type.value, "#D5D8DC")
            for tile in tiles
        ])
        edges = np.array(["#2C3E50"] * len(tiles), dtype=object)

        if highlight_colours:
            highlight_set = set(highlight_colours)
            for idx, tile in enumerate(tiles):
                if any(colour in highlight_set for colour in tile.colours):
                    edges[idx] = "#111827"

        plot_single_lattice_custom_colors(
            coord_x=self.centres[:, 0],
            coord_y=self.centres[:, 1],
            face_color=faces,
            edge_color=edges,
            min_diam=self.min_diameter,
            h_ax=ax,
            plotting_gap=0.0,
            rotate_deg=0.0,
            line_width=1.5,
            background_color="#FFFFFF",
        )

        pad = self.min_diameter
        xs, ys = self.centres[:, 0], self.centres[:, 1]
        ax.set_xlim(xs.min() - pad, xs.max() + pad)
        ax.set_ylim(ys.min() - pad, ys.max() + pad)

        for idx, tile in enumerate(tiles):
            if tile.tile_type == TileType.WATER:
                continue

            centre = (self.centres[idx, 0], self.centres[idx, 1])
            label = tile_label(tile, self.grid.zeus_tile_id)
            if label:
                ax.text(
                    centre[0],
                    centre[1] + self.min_diameter * 0.16,
                    label,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#1F2933",
                    zorder=6,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, linewidth=0),
                )

            if tile.id == self.grid.zeus_tile_id:
                continue

            self._draw_colour_markers(ax, centre, tile.colours)

        self._draw_tile_key(ax)

        return fig, ax

    def _draw_colour_markers(self, ax, centre: tuple[float, float], colours: Sequence[str]) -> None:
        valid_colours = [PLAYER_COLOURS.get(colour, "#2C3E50") for colour in colours]
        if not valid_colours:
            return

        radius = self.min_diameter * 0.065
        positions = {
            1: [(0.0, -0.20)],
            2: [(-0.14, -0.20), (0.14, -0.20)],
            3: [(-0.16, -0.20), (0.16, -0.20), (0.0, -0.06)],
        }

        dots = positions.get(len(valid_colours), [
            (0.3 * math.cos(2 * math.pi * i / len(valid_colours)), 0.3 * math.sin(2 * math.pi * i / len(valid_colours)) - 0.1)
            for i in range(len(valid_colours))
        ])

        for (offset_x, offset_y), colour in zip(dots, valid_colours):
            ax.add_patch(Circle(
                (centre[0] + offset_x * self.min_diameter, centre[1] + offset_y * self.min_diameter),
                radius, facecolor=colour, edgecolor="#1F2933", linewidth=0.4, zorder=7.6
            ))

    def _draw_tile_key(self, ax) -> None:
        lines = ["Key"] + [f"{abbr} = {label}" for _, abbr, label in TILE_KEY_ENTRIES] + ["", "Colour dots show tile colours"]
        ax.text(
            1.04, 0.96, "\n".join(lines), transform=ax.transAxes, ha="left", va="top", fontsize=7, color="#1F2933",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, linewidth=0.5), zorder=8, clip_on=False
        )

    def _outline_tiles(
        self,
        ax,
        tile_ids: Sequence[str],
        colour: str,
        *,
        linewidth: float = 2.4,
        alpha: float = 0.9,
    ) -> None:
        if not tile_ids:
            return

        vertex_angles = [math.pi / 2 + k * (math.pi / 3) for k in range(6)]
        radius = self.min_diameter * 0.62

        for tile_id in tile_ids:
            idx = self.id_to_index.get(tile_id)
            if idx is None:
                continue
            cx, cy = self.centres[idx]
            vertices = [
                (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
                for angle in vertex_angles
            ]
            patch = Polygon(
                vertices,
                closed=True,
                fill=False,
                edgecolor=colour,
                linewidth=linewidth,
                alpha=alpha,
                zorder=6.8,
                joinstyle="round",
                path_effects=[
                    patheffects.Stroke(linewidth=linewidth + 1.4, foreground="#FFFFFF"),
                    patheffects.Normal(),
                ],
            )
            ax.add_patch(patch)

    def _centre_for(self, tile_id: str) -> tuple[float, float]:
        return tuple(self.centres[self.id_to_index[tile_id]])
    
    def _get_offset_points(self, route: Sequence[str], cycle_idx: int) -> list[tuple[float, float]]:
        """Get route points with small offset to avoid overlapping lines."""
        points = []
        offset_distance = 0.08 * cycle_idx  # Small offset based on cycle index
        
        for tile_id in route:
            if tile_id not in self.id_to_index:
                continue
            x, y = self._centre_for(tile_id)
            # Apply circular offset based on cycle index
            angle = (cycle_idx * 60) * (math.pi / 180)  # 60 degrees per cycle
            x_offset = offset_distance * math.cos(angle)
            y_offset = offset_distance * math.sin(angle)
            points.append((x + x_offset, y + y_offset))
        
        return points

    def _draw_route_arrows(self, ax, route: Sequence[str], color: str = "#1F2933", alpha: float = 0.7) -> None:
        """Draw sequential step numbers on route tiles."""
        # Track which tiles are visited and at which steps
        tile_steps = {}  # tile_id -> list of step numbers
        
        for i, tile_id in enumerate(route):
            if tile_id not in self.id_to_index:
                continue
            
            step_num = i + 1  # 1-indexed
            if tile_id not in tile_steps:
                tile_steps[tile_id] = []
            tile_steps[tile_id].append(step_num)
        
        # Draw step numbers on tiles
        for tile_id, steps in tile_steps.items():
            idx = self.id_to_index[tile_id]
            cx, cy = self.centres[idx]
            
            # If tile visited multiple times, show all step numbers
            if len(steps) > 1:
                # Show first few steps if many visits
                if len(steps) <= 3:
                    label = ",".join(str(s) for s in steps)
                else:
                    label = f"{steps[0]},{steps[1]}..."
                fontsize = 7
            else:
                label = str(steps[0])
                fontsize = 8
            
            ax.text(
                cx,
                cy,
                label,
                ha="center",
                va="center",
                fontsize=fontsize,
                color=color,
                alpha=alpha,
                weight="bold",
                zorder=7.5,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.7, linewidth=0),
            )

    def _hex_to_pixel(self, coord) -> tuple[float, float]:
        col, row = coord
        parity = row & 1
        column_spacing = 1.15  # widen columns slightly so borders are visible
        x = self.min_diameter * column_spacing * (col + 0.5 * parity)
        y = self.min_diameter * row
        return float(x), float(y)

def tile_label(tile: Tile, zeus_id: str) -> str:
    if tile.id == zeus_id:
        return "Z"
    if tile.tile_type == TileType.WATER:
        return ""
    return TILE_ABBREVIATIONS.get(tile.tile_type, "")
