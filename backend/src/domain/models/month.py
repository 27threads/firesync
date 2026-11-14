from dataclasses import dataclass
from datetime import date
import re

from .error import CalendarError


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
        if self < Month(2012, 2):
            return "Aqua"
        return "SNPP" if self < Month(2026, 11) else "N20"

    @property
    def source(self):
        return "estimated_modis" if self.satellite == "Aqua" else "observed_viirs"

    def next(self):
        return Month(self.year + self.month // 12, self.month % 12 + 1)

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}"
