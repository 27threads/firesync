class CalendarError(ValueError):
    """Application error independent of its eventual HTTP representation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
