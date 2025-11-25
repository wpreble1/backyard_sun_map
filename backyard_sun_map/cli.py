from datetime import datetime
from zoneinfo import ZoneInfo

import click

from .plotting import plot_heatmap, plot_scene_overhead
from .scene import load_scene
from .simulation import run_simulation


def _parse_local_time(value: str, timezone: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid datetime format: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(timezone))
    return dt.astimezone(ZoneInfo(timezone))


@click.command()
@click.option(
    "--scene",
    "scene_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    help="Path to scene YAML or JSON.",
)
@click.option("--start", required=True, help='Start datetime "YYYY-MM-DDTHH:MM" (local).')
@click.option("--end", required=True, help='End datetime "YYYY-MM-DDTHH:MM" (local).')
@click.option(
    "--step-minutes", default=15, show_default=True, help="Step size in minutes.", type=int
)
@click.option(
    "--height-ft",
    required=True,
    type=float,
    help="Height above ground to evaluate (feet).",
)
@click.option(
    "--grid-resolution-ft",
    default=0.82,
    show_default=True,
    type=float,
    help="Grid spacing in feet.",
)
@click.option("--output-prefix", required=True, help="Prefix for outputs.")
@click.option(
    "--save-scene-overhead",
    is_flag=True,
    help="Save overhead scene rendering for sanity checking.",
)
def main(
    scene_path: str,
    start: str,
    end: str,
    step_minutes: int,
    height_ft: float,
    grid_resolution_ft: float,
    output_prefix: str,
    save_scene_overhead: bool,
) -> None:
    """Backyard sun exposure simulation."""
    scene = load_scene(scene_path)

    start_dt = _parse_local_time(start, scene.location.timezone)
    end_dt = _parse_local_time(end, scene.location.timezone)
    if end_dt < start_dt:
        raise SystemExit("End time must be after start time.")

    x_grid, y_grid, exposure = run_simulation(
        scene,
        height_ft=height_ft,
        grid_res_ft=grid_resolution_ft,
        start=start_dt,
        end=end_dt,
        step_minutes=step_minutes,
        output_prefix=output_prefix,
    )

    heatmap_path = f"{output_prefix}_heatmap_{height_ft}ft.png"
    plot_heatmap(x_grid, y_grid, exposure, heatmap_path)
    click.echo(f"Heatmap saved to {heatmap_path}")

    if save_scene_overhead:
        overhead_path = f"{output_prefix}_scene_overhead.png"
        plot_scene_overhead(scene, overhead_path)
        click.echo(f"Scene overhead saved to {overhead_path}")


if __name__ == "__main__":
    main()
