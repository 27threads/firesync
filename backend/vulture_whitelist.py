"""Public entry points used by tests and future HTTP composition.

Vulture excludes tests, so it cannot see these callers. This file is read only
by static analysis; it is not part of the installed backend package.
"""
from backend.adapters.outbound.postgres.history import PostgresHistoryRepository
from backend.application.calendar import CalendarService

PostgresHistoryRepository  # Instantiated in PostGIS integration tests.
CalendarService.calculate  # Called by application, unit and integration tests.
