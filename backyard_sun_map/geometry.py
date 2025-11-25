from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
from shapely.geometry import LineString, Point

from .scene import Scene, SceneObject


@dataclass
class InternalGeometry:
    objects: List[SceneObject]


def build_objects(scene: Scene) -> InternalGeometry:
    """Adapter hook for future geometry processing."""
    return InternalGeometry(objects=scene.objects)


def _ray_intersection_distance(
    geom,
    origin: Tuple[float, float],
    direction: Tuple[float, float],
    max_dist: float = 1e6,
) -> Optional[float]:
    """Return distance s along ray origin + s*direction to first intersection."""
    ox, oy = origin
    dx, dy = direction
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        # Straight up/down: only shaded if footprint contains origin.
        if geom.contains(Point(ox, oy)):
            return 0.0
        return None

    target = (ox + dx * max_dist, oy + dy * max_dist)
    ray = LineString([origin, target])

    boundary = geom.boundary if hasattr(geom, "boundary") else geom
    intersection = boundary.intersection(ray)
    if intersection.is_empty:
        return None

    points: List[Tuple[float, float]] = []
    geom_type = intersection.geom_type
    if geom_type == "Point":
        px, py = intersection.x, intersection.y
        points.append((px, py))
    elif geom_type in ("MultiPoint", "GeometryCollection"):
        for g in getattr(intersection, "geoms", []):
            if g.geom_type == "Point":
                points.append((g.x, g.y))
    elif geom_type in ("LineString", "LinearRing"):
        points.extend([(x, y) for x, y in intersection.coords])
    elif geom_type == "MultiLineString":
        for line in intersection.geoms:
            points.extend([(x, y) for x, y in line.coords])

    if not points:
        return None

    best: Optional[float] = None
    for px, py in points:
        if abs(dx) >= abs(dy):
            if abs(dx) < 1e-12:
                continue
            s = (px - ox) / dx
        else:
            if abs(dy) < 1e-12:
                continue
            s = (py - oy) / dy
        if s < 0:
            continue
        if best is None or s < best:
            best = s
    return best


def is_point_shaded(
    x: float | np.floating,
    y: float | np.floating,
    z_ft: float | np.floating,
    sun_dir: Sequence[float],
    geometry: InternalGeometry,
) -> bool:
    """Return True if any object occludes the sun at this point."""
    dx, dy, dz = (float(c) for c in sun_dir)
    z_val = float(z_ft)
    if dz <= 0:
        return True

    origin = (float(x), float(y))
    ray_dir = (-dx, -dy)
    for obj in geometry.objects:
        if obj.geometry.contains(Point(origin)) and obj.height_ft >= z_val:
            return True
        s = _ray_intersection_distance(obj.geometry, origin, ray_dir)
        if s is None:
            continue
        z_at_s = z_val - s * dz
        if 0 <= z_at_s <= obj.height_ft:
            return True
    return False
