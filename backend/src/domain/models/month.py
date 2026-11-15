from dataclasses import dataclass
from datetime import date
import re

from .error import CalendarError

# The one source of the satellite that counts on each day (agregar.py in data-pipeline keeps a copy, checked by a
# test). Before the first switch: Aqua. S-NPP stopped on 2026-11-02, so November 2026 is already NOAA-20.
SATELLITE_SWITCHES = ((date(2012, 2, 1), "SNPP"), (date(2026, 11, 1), "N20"))


def satellite_on(day):
    current = "Aqua"
    for start, satellite in SATELLITE_SWITCHES:
        if day >= start:
            current = satellite
    return current


@dataclass(frozen=True, order=True, slots=True)
class Month:
    year: int
    month: int

    def __post_init__(self):
        try:
            date(self.year, self.month, 1)
        except (TypeError, ValueError):
            raise CalendarError("invalid_period", "Invalid calendar month.") from None

    @classmethod
    def parse(cls, value: str):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
            raise CalendarError("invalid_period", "Use YYYY-MM.")
        return cls(int(value[:4]), int(value[5:]))

    @property
    def start(self):
        return date(self.year, self.month, 1)

    @property
    def satellite(self):
        return satellite_on(self.start)

    @property
    def source(self):
        return "estimated_modis" if self.satellite == "Aqua" else "observed_viirs"

    def next(self):
        return Month(self.year + self.month // 12, self.month % 12 + 1)

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}"
