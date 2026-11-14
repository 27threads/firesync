from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from .error import CalendarError


@dataclass(frozen=True, slots=True)
class Area:
    type: str
    region_id: int | None = None
    geometry: Mapping | None = None
    lat: float | None = None
    lon: float | None = None
    radius_km: float | None = None

    def __post_init__(self):
        if self.type == "region":
            valid = type(self.region_id) is int and self.region_id > 0 and all(
                x is None for x in (self.geometry, self.lat, self.lon, self.radius_km))
        elif self.type == "geojson":
            valid = isinstance(self.geometry, Mapping) and all(
                x is None for x in (self.region_id, self.lat, self.lon, self.radius_km))
        elif self.type == "point":
            values = (self.lat, self.lon, self.radius_km)
            valid = all(type(x) in (int, float) and isfinite(x) for x in values)
            valid = valid and -90 <= self.lat <= 90 and -180 <= self.lon <= 180 and 1 <= self.radius_km <= 200
            valid = valid and self.region_id is None and self.geometry is None
        else:
            valid = False
        if not valid:
            raise CalendarError("invalid_geometry", "Invalid area selection.")
