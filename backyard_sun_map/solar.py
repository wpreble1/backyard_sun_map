from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence
from zoneinfo import ZoneInfo

import numpy as np

from .scene import Scene


@dataclass
class SunPosition:
    alt_deg: float
    az_deg: float


def generate_times(
    start_dt: datetime, end_dt: datetime, step_minutes: int, timezone: str
) -> List[datetime]:
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive.")

    tzinfo = ZoneInfo(timezone)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tzinfo)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=tzinfo)

    if start_dt > end_dt:
        raise ValueError("start must be before end.")

    times: List[datetime] = []
    current = start_dt
    delta = timedelta(minutes=step_minutes)
    while current <= end_dt:
        times.append(current)
        current += delta
    return times


def _compute_with_pvlib(scene: Scene, times: Sequence[datetime]) -> List[SunPosition]:
    import pandas as pd
    from pvlib.location import Location

    location = Location(
        scene.location.latitude,
        scene.location.longitude,
        tz=scene.location.timezone,
    )
    index: pd.DatetimeIndex = pd.DatetimeIndex(pd.to_datetime(list(times)))
    solpos = location.get_solarposition(index)
    altitudes = np.asarray(solpos["apparent_elevation"], dtype=float)
    azimuths = np.asarray(solpos["azimuth"], dtype=float)
    return [SunPosition(float(a), float(z)) for a, z in zip(altitudes, azimuths)]


def _compute_with_pysolar(scene: Scene, times: Sequence[datetime]) -> List[SunPosition]:
    from pysolar.solar import get_altitude, get_azimuth

    positions: List[SunPosition] = []
    for t in times:
        alt = get_altitude(scene.location.latitude, scene.location.longitude, t)
        az = get_azimuth(scene.location.latitude, scene.location.longitude, t)
        positions.append(SunPosition(float(alt), float(az)))
    return positions


def compute_solar_positions(scene: Scene, times: Sequence[datetime]) -> List[SunPosition]:
    """Compute solar altitude and azimuth for each time."""
    try:
        return _compute_with_pvlib(scene, times)
    except ImportError:
        try:
            return _compute_with_pysolar(scene, times)
        except ImportError as exc:
            raise RuntimeError("pvlib or pysolar is required to compute solar positions.") from exc


def sun_vector_local(alt_deg: float, az_deg: float, orientation_deg: float):
    """Return (dx, dy, dz) direction from origin toward the sun in yard-local coords."""
    alt_rad = np.radians(alt_deg)
    az_rad = np.radians(az_deg)

    dx_world = np.sin(az_rad) * np.cos(alt_rad)  # east
    dy_world = np.cos(az_rad) * np.cos(alt_rad)  # north
    dz_world = np.sin(alt_rad)

    theta = np.radians(orientation_deg)
    x_dir_east = np.sin(theta)
    x_dir_north = np.cos(theta)
    y_dir_east = np.sin(theta - np.pi / 2)
    y_dir_north = np.cos(theta - np.pi / 2)

    dx_local = dx_world * x_dir_east + dy_world * x_dir_north
    dy_local = dx_world * y_dir_east + dy_world * y_dir_north
    return dx_local, dy_local, dz_world
