from __future__ import annotations


class BusinessLogicError(Exception):
    """ACustom exception for business logic violations."""

    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
