"""Hex-grid visualisation for map1.json with hardcoded tile positions."""

from __future__ import annotations
from typing import Iterable, Sequence
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as patheffects
from hexalattice.hexalattice import plot_single_lattice_custom_colors
from matplotlib.patches import Circle, Polygon
import math

from .grid import HexGrid, Tile, TileType

HEX_MIN_DIAMETER = 0.9 # Minimum diameter of hex tiles
HEX_COLUMN_SPACING = 1.15 # Gap between tiles


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

CYCLE_COLOURS = (
    "#E98809",
    "#F00606",
    "#0FF7E8",
    "#F1C40F",
    "#9B59B6",
    "#1ABC9C",
    "#E67E22",
)

def calculate_tile_position(col: int, row: int) -> tuple[float, float]:
    """Calculate (x, y) position for a hex tile from its axial coordinates."""
    x = col * HEX_COLUMN_SPACING + (row % 2) * (HEX_COLUMN_SPACING / 2)
    y = row * HEX_MIN_DIAMETER
    return (x, y)

class HexGridVisualiser:
    """Draw the map and optional overlays."""

    def __init__(self, grid: HexGrid) -> None:
        self.grid = grid
        self.min_diameter = HEX_MIN_DIAMETER
        self.tile_ids = list(grid.tiles)

        # Calculate positions from tile coordinates
        centres = [calculate_tile_position(*tile.coords) for tile_id in self.tile_ids if (tile := self.grid.get_tile(tile_id))]
        self.centres = np.array(centres, dtype=float) if centres else np.empty((0, 2))
        self.id_to_index = {tile_id: idx for idx, tile_id in enumerate(self.tile_ids)}

    def show_all_visualisations(
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

        points = []
        for tid in (route or []):
            tile = self.grid.get_tile(tid)
            if tile:
                points.append(calculate_tile_position(*tile.coords))
        
        if len(points) >= 2:
            xs, ys = zip(*points)
            ax.plot(xs, ys, color="#FF6B6B", linewidth=2.0, alpha=0.85)
            ax.scatter(*points[0], color="#2ECC71", s=40, zorder=6)
            ax.scatter(*points[-1], color="#E74C3C", s=40, zorder=6)
            
            # Draw step numbers on route
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

        # Compute cycle entry/exit indices from route on-demand
        route_list = list(route)
        
        for idx, cycle in enumerate(cycles):
            cycle_colour = CYCLE_COLOURS[idx % len(CYCLE_COLOURS)]
            
            # Outline task tiles
            task_ids = [task.tile_id for task in cycle.tasks]
            self._outline_tiles(ax, task_ids, cycle_colour, linewidth=2.6, alpha=0.9)

            # Draw cycle route with minimal offset to avoid overlaps
            internal_route = cycle.internal_route
            if len(internal_route) >= 2:
                offset_distance = 0.08 * idx
                angle = (idx * 60) * (math.pi / 180)
                points = []
                for tile_id in internal_route:
                    tile = self.grid.get_tile(tile_id)
                    if tile:
                        x, y = calculate_tile_position(*tile.coords)
                        x += offset_distance * math.cos(angle)
                        y += offset_distance * math.sin(angle)
                        points.append((x, y))
                
                if len(points) >= 2:
                    xs, ys = zip(*points)
                    ax.plot(
                        xs, ys, color=cycle_colour, linewidth=2.2, alpha=0.75,
                        solid_capstyle="round", zorder=5 + idx,
                        path_effects=[
                            patheffects.Stroke(linewidth=3.6, foreground="white"),
                            patheffects.Normal(),
                        ],
                    )
            
            # Draw step numbers for this cycle
            if internal_route:
                self._draw_route_arrows(ax, internal_route, color=cycle_colour, alpha=0.85)

            # Label cycle
            anchor_tile = task_ids[0] if task_ids else None
            if anchor_tile:
                tile = self.grid.get_tile(anchor_tile)
                if tile:
                    cx, cy = calculate_tile_position(*tile.coords)
                    ax.text(
                        cx, cy + self.min_diameter * 0.35, f"C{idx + 1}",
                        ha="center", va="center", fontsize=8, color=cycle_colour, zorder=8,
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, linewidth=0),
                    )

        # Mark which route indices are covered by cycles
        # Build a map of which route indices belong to which cycles
        route_to_cycles = {}  # route_index -> list of cycle indices
        
        for cycle_idx, cycle in enumerate(cycles):
            if not cycle.internal_route:
                continue
            try:
                # Find where this cycle's route appears in the full route
                entry_tile = cycle.internal_route[0]
                entry_route_idx = route_list.index(entry_tile)
                
                # Map each tile in the cycle's internal route to route indices
                for i, tile_id in enumerate(cycle.internal_route):
                    # Find this tile in the route starting from entry point
                    search_from = entry_route_idx
                    try:
                        route_idx = route_list.index(tile_id, search_from)
                        if route_idx not in route_to_cycles:
                            route_to_cycles[route_idx] = []
                        route_to_cycles[route_idx].append(cycle_idx)
                    except ValueError:
                        pass
            except ValueError:
                pass
        
        covered_indices = set(route_to_cycles.keys())
        
        # Draw connectors for uncovered segments
        connector_segments = []
        current_segment = []
        
        for i, tile_id in enumerate(route_list):
            if i not in covered_indices:
                current_segment.append(tile_id)
            else:
                if len(current_segment) > 1:
                    connector_segments.append(current_segment)
                current_segment = []
        
        # Don't forget the last segment
        if len(current_segment) > 1:
            connector_segments.append(current_segment)
        
        # Draw all connector segments as dotted lines
        for segment in connector_segments:
            points = []
            for tid in segment:
                tile = self.grid.get_tile(tid)
                if tile:
                    points.append(calculate_tile_position(*tile.coords))
            if len(points) >= 2:
                xs, ys = zip(*points)
                ax.plot(
                    xs, ys, color="#666666", linewidth=1.2, linestyle=(0, (4, 4)),
                    alpha=0.5, zorder=15,
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

        # Add legend/key
        lines = ["Key"] + [f"{abbr} = {label}" for _, abbr, label in TILE_KEY_ENTRIES] + ["", "Colour dots show tile colours"]
        ax.text(
            1.04, 0.96, "\n".join(lines), transform=ax.transAxes, ha="left", va="top", fontsize=7, color="#1F2933",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, linewidth=0.5), zorder=8, clip_on=False
        )

        return fig, ax

    def _draw_colour_markers(self, ax, centre: tuple[float, float], colours: Sequence[str]) -> None:
        if not colours:
            return
        
        # Hardcoded positions for 1-3 colours (map1.json has max 3). Change number to change dot size
        radius = self.min_diameter * 0.08
        
        for i, colour in enumerate(colours[:3]):
            if i == 0 and len(colours) == 1:
                offset = (0.0, -0.20)
            elif i < 2:
                offset = ((-0.14, -0.20), (0.14, -0.20))[i]
            else:
                offset = (0.0, -0.06)
            
            colour_hex = PLAYER_COLOURS.get(colour, "#2C3E50")
            ax.add_patch(Circle(
                (centre[0] + offset[0] * self.min_diameter, centre[1] + offset[1] * self.min_diameter),
                radius, facecolor=colour_hex, edgecolor="none", linewidth=0, zorder=7.6
            ))

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

        # Pre-compute hex vertex angles and radius
        angles = [math.pi / 2 + k * math.pi / 3 for k in range(6)]
        radius = self.min_diameter * 0.62

        for tile_id in tile_ids:
            idx = self.id_to_index.get(tile_id)
            if idx is None:
                continue
            
            cx, cy = self.centres[idx]
            vertices = [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in angles]
            
            ax.add_patch(Polygon(
                vertices, closed=True, fill=False, edgecolor=colour,
                linewidth=linewidth, alpha=alpha, zorder=6.8, joinstyle="round",
                path_effects=[
                    patheffects.Stroke(linewidth=linewidth + 1.4, foreground="#FFFFFF"),
                    patheffects.Normal(),
                ]
            ))

    def _draw_route_arrows(self, ax, route: Sequence[str], color: str = "#1F2933", alpha: float = 0.7) -> None:
        """Draw sequential step numbers on route tiles."""
        # Collect all indices for each tile
        tile_indices: dict[str, list[int]] = {}
        for i, tile_id in enumerate(route):
            if tile_id not in tile_indices:
                tile_indices[tile_id] = []
            tile_indices[tile_id].append(i + 1)
        
        # Draw all indices for each tile
        for tile_id, indices in tile_indices.items():
            tile = self.grid.get_tile(tile_id)
            if not tile:
                continue
            
            cx, cy = calculate_tile_position(*tile.coords)
            label = ",".join(str(idx) for idx in indices)
            ax.text(
                cx, cy, label,
                ha="center", va="center", fontsize=8,
                color=color, alpha=alpha, weight="bold", zorder=7.5,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.7, linewidth=0),
            )

def tile_label(tile: Tile, zeus_id: str) -> str:
    if tile.id == zeus_id:
        return "Z"
    if tile.tile_type == TileType.WATER:
        return ""
    return TILE_ABBREVIATIONS.get(tile.tile_type, "")
