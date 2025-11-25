import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml
from shapely.geometry import CAP_STYLE, JOIN_STYLE, LineString, Point, Polygon

FENCE_HALF_THICKNESS_FT = 0.164  # ~2 inch thickness treated as thin vertical surface


@dataclass
class Location:
    latitude: float
    longitude: float
    timezone: str


@dataclass
class Bounds:
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    padding_ft: float = 6.56


@dataclass
class SceneObject:
    type: str
    name: str
    height_ft: float
    geometry: Any
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    location: Location
    orientation_deg_cw_from_north: float
    objects: List[SceneObject]
    bounds: Optional[Bounds] = None

    def resolved_bounds(self, default_padding_ft: float = 6.56) -> Tuple[float, float, float, float]:
        """Compute bounds using explicit values when provided, otherwise infer from geometry."""
        padding = self.bounds.padding_ft if self.bounds else default_padding_ft

        if not self.objects:
            if not self.bounds:
                raise ValueError("Scene without objects requires explicit bounds.")
            required = [self.bounds.x_min, self.bounds.x_max, self.bounds.y_min, self.bounds.y_max]
            if any(v is None for v in required):
                raise ValueError(
                    "Explicit bounds must include x_min, x_max, y_min, and y_max when no objects are present."
                )
            # mypy/pylance do not narrow Optional values through the list check above.
            assert self.bounds.x_min is not None
            assert self.bounds.x_max is not None
            assert self.bounds.y_min is not None
            assert self.bounds.y_max is not None
            return (
                float(self.bounds.x_min),
                float(self.bounds.x_max),
                float(self.bounds.y_min),
                float(self.bounds.y_max),
            )

        xs = []
        ys = []
        for obj in self.objects:
            minx, miny, maxx, maxy = obj.geometry.bounds
            xs.extend([minx, maxx])
            ys.extend([miny, maxy])

        inferred = (
            min(xs),
            max(xs),
            min(ys),
            max(ys),
        )

        x_min = (
            self.bounds.x_min
            if self.bounds and self.bounds.x_min is not None
            else inferred[0] - padding
        )
        x_max = (
            self.bounds.x_max
            if self.bounds and self.bounds.x_max is not None
            else inferred[1] + padding
        )
        y_min = (
            self.bounds.y_min
            if self.bounds and self.bounds.y_min is not None
            else inferred[2] - padding
        )
        y_max = (
            self.bounds.y_max
            if self.bounds and self.bounds.y_max is not None
            else inferred[3] + padding
        )
        return x_min, x_max, y_min, y_max


def _validate_coordinates(
    coords: Sequence[Sequence[float]], name: str
) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for entry in coords:
        if not isinstance(entry, Sequence) or len(entry) != 2:
            raise ValueError(f"{name} coordinates must be [x, y] pairs.")
        x, y = float(entry[0]), float(entry[1])
        points.append((x, y))
    return points


def _parse_structure(data: Dict[str, Any]) -> SceneObject:
    footprint_raw = data.get("footprint")
    if footprint_raw is None:
        raise ValueError("structure/deck requires 'footprint'.")
    footprint = _validate_coordinates(footprint_raw, "footprint")
    polygon = Polygon(footprint)
    if not polygon.is_valid or polygon.is_empty:
        raise ValueError(f"Invalid polygon footprint for object '{data.get('name', '')}'.")
    return SceneObject(
        type=data["type"],
        name=data.get("name", data["type"]),
        height_ft=float(data["height_ft"]),
        geometry=polygon,
        raw=data,
    )


def _parse_fence(data: Dict[str, Any]) -> SceneObject:
    polyline_raw = data.get("polyline")
    if polyline_raw is None:
        raise ValueError("fence requires 'polyline'.")
    points = _validate_coordinates(polyline_raw, "polyline")
    line = LineString(points)
    if line.is_empty:
        raise ValueError(f"Invalid fence polyline for '{data.get('name', '')}'.")
    polygon = line.buffer(
        FENCE_HALF_THICKNESS_FT,
        cap_style=CAP_STYLE.flat,
        join_style=JOIN_STYLE.mitre,
    )
    return SceneObject(
        type=data["type"],
        name=data.get("name", data["type"]),
        height_ft=float(data["height_ft"]),
        geometry=polygon,
        raw=data,
    )


def _parse_tree(data: Dict[str, Any]) -> SceneObject:
    center = data.get("center")
    if not isinstance(center, Sequence) or len(center) != 2:
        raise ValueError("tree requires 'center' as [x, y].")
    radius = float(data.get("radius_ft", 0.0))
    if radius <= 0:
        raise ValueError("tree requires a positive 'radius_ft'.")
    height = float(data["height_ft"])
    point = Point(float(center[0]), float(center[1]))
    circle = point.buffer(radius, resolution=32)
    return SceneObject(
        type=data["type"],
        name=data.get("name", data["type"]),
        height_ft=height,
        geometry=circle,
        raw=data,
    )


def _parse_object(entry: Dict[str, Any]) -> SceneObject:
    required = ["type", "height_ft"]
    for key in required:
        if key not in entry:
            raise ValueError(f"Scene object missing required key '{key}'.")

    obj_type = entry["type"].lower()
    if obj_type in ("structure", "deck"):
        return _parse_structure(entry)
    if obj_type == "fence":
        return _parse_fence(entry)
    if obj_type == "tree":
        return _parse_tree(entry)
    raise ValueError(f"Unsupported object type '{obj_type}'.")


def _load_raw_scene(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Scene file not found: {path}")
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError("Scene file must be YAML or JSON.")


def load_scene(path: str) -> Scene:
    """Load a scene definition from YAML or JSON."""
    raw = _load_raw_scene(Path(path))
    if raw is None:
        raise ValueError("Scene file is empty.")

    location_raw = raw.get("location")
    if not location_raw:
        raise ValueError("Scene requires a 'location' section.")
    location = Location(
        latitude=float(location_raw["latitude"]),
        longitude=float(location_raw["longitude"]),
        timezone=str(location_raw["timezone"]),
    )

    orientation = float(raw.get("orientation_deg_cw_from_north", 0.0))

    bounds_raw = raw.get("bounds")
    bounds = None
    if bounds_raw:
        bounds = Bounds(
            x_min=bounds_raw.get("x_min"),
            x_max=bounds_raw.get("x_max"),
            y_min=bounds_raw.get("y_min"),
            y_max=bounds_raw.get("y_max"),
            padding_ft=float(bounds_raw.get("padding_ft", 6.56)),
        )

    objects_raw = raw.get("objects", [])
    if not isinstance(objects_raw, list):
        raise ValueError("'objects' must be a list.")

    objects = [_parse_object(obj) for obj in objects_raw]
    return Scene(
        location=location,
        orientation_deg_cw_from_north=orientation,
        objects=objects,
        bounds=bounds,
    )
