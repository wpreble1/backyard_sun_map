import os
from datetime import datetime
from typing import Tuple

import numpy as np

from .geometry import build_objects, is_point_shaded
from .scene import Scene
from .solar import compute_solar_positions, generate_times, sun_vector_local


def run_simulation(
    scene: Scene,
    height_ft: float,
    grid_res_ft: float,
    start: datetime,
    end: datetime,
    step_minutes: int,
    output_prefix: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run sun/shade simulation using feet units. Returns x_grid, y_grid, exposure_minutes."""
    objects = build_objects(scene)
    x_min, x_max, y_min, y_max = scene.resolved_bounds()

    x_grid = np.arange(x_min, x_max + grid_res_ft, grid_res_ft)
    y_grid = np.arange(y_min, y_max + grid_res_ft, grid_res_ft)
    exposure = np.zeros((len(y_grid), len(x_grid)), dtype=float)

    times = generate_times(start, end, step_minutes, scene.location.timezone)
    positions = compute_solar_positions(scene, times)

    for position in positions:
        if position.alt_deg <= 0:
            continue
        sun_dir = sun_vector_local(
            position.alt_deg, position.az_deg, scene.orientation_deg_cw_from_north
        )
        for yi, y in enumerate(y_grid):
            for xi, x in enumerate(x_grid):
                if not is_point_shaded(x, y, height_ft, sun_dir, objects):
                    exposure[yi, xi] += step_minutes

    # Ensure output directories exist
    output_dir = os.path.dirname(output_prefix)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    return x_grid, y_grid, exposure
