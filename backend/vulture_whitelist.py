"""Public entry points used by tests and future HTTP composition.

Vulture excludes tests, so it cannot see these callers. This file is read only
by static analysis; it is not part of the installed backend package.
"""
from backend.adapters.outbound.postgres.history import PostgresHistoryRepository
from backend.application.calendar import CalendarService
from backend.adapters.inbound.http.app import create_app

PostgresHistoryRepository  # Instantiated in PostGIS integration tests.
CalendarService.calculate  # Called by application, unit and integration tests.
create_app  # Uvicorn --factory entry point, also used by TestClient.
itersize  # noqa: F821 - psycopg reads it: rows per fetch of the export's server-side cursor.
guard  # noqa: F821 - FastAPI middleware registration calls this closure.
health  # noqa: F821 - FastAPI GET /health registration calls this closure.
export  # noqa: F821 - FastAPI POST /export registration calls this closure.
