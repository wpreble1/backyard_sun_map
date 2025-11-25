import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import Polygon

from .scene import Scene, SceneObject


def plot_heatmap(x_grid, y_grid, exposure, output_path: str):
    fig, ax = plt.subplots(figsize=(8, 6))
    extent = (x_grid[0], x_grid[-1], y_grid[0], y_grid[-1])
    im = ax.imshow(
        exposure,
        origin="lower",
        extent=extent,
        cmap="inferno",
        aspect="equal",
    )
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Minutes of direct sun")
    ax.set_xlabel("x_local (ft)")
    ax.set_ylabel("y_local (ft)")
    ax.set_title("Sun exposure heatmap")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _draw_object(ax, obj: SceneObject):
    geom = obj.geometry
    if isinstance(geom, Polygon):
        patch = MplPolygon(list(geom.exterior.coords), facecolor="none", edgecolor="blue")
        ax.add_patch(patch)
        for interior in geom.interiors:
            hole = MplPolygon(
                list(interior.coords), facecolor="none", edgecolor="gray", linestyle="--"
            )
            ax.add_patch(hole)
    else:
        xs, ys = geom.exterior.xy if hasattr(geom, "exterior") else geom.xy
        ax.plot(xs, ys, label=obj.name)


def plot_scene_overhead(scene: Scene, output_path: str):
    fig, ax = plt.subplots(figsize=(6, 6))
    for obj in scene.objects:
        _draw_object(ax, obj)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x_local (ft)")
    ax.set_ylabel("y_local (ft)")
    ax.set_title("Scene overhead view")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
