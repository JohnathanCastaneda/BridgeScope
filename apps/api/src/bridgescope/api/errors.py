from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    type: str | None = None


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | dict[str, Any] | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class ApiValidationError(Exception):
    """Raised when API-level validation spans multiple request fields."""

    def __init__(self, details: list[ErrorDetail]) -> None:
        self.details = details
        super().__init__("Request validation failed.")
