from dataclasses import dataclass
from math import isfinite

from backend.domain.models.error import CalendarError


@dataclass(frozen=True)
class MapQuery:
    bbox: tuple[float, float, float, float]
    hours: int
    zoom: int
    mode: str

    @classmethod
    def parse(cls, bbox, hours='24', zoom='4', mode='auto'):
        try:
            bounds = tuple(float(value) for value in bbox.split(','))
            west, south, east, north = bounds
            if not all(isfinite(value) for value in bounds) or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            raise CalendarError('invalid_bbox', 'Use west,south,east,north in WGS84.') from None
        if str(hours) not in ('24', '72', '168'):
            raise CalendarError('invalid_hours', 'Hours must be 24, 72 or 168.')
        try:
            level = int(zoom)
            if str(level) != str(zoom) or not 0 <= level <= 22 or mode not in ('auto', 'hexagons', 'points'):
                raise ValueError
        except (TypeError, ValueError):
            raise CalendarError('invalid_mode', 'Use auto, hexagons or points and an integer zoom from 0 to 22.') from None
        return cls(bounds, int(hours), level, mode)

    @property
    def points(self):
        return self.mode == 'points' or self.mode == 'auto' and self.zoom >= 8

    @property
    def resolution(self):
        return 4 if self.zoom <= 4 else 5 if self.zoom <= 6 else 6
