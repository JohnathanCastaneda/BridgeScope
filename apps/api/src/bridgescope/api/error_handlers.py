import logging
from collections.abc import Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from bridgescope.api.errors import (
    ApiErrorBody,
    ApiErrorResponse,
    ApiValidationError,
    ErrorDetail,
)
from bridgescope.services.errors import ActiveDatasetNotFoundError, BridgeNotFoundError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        BridgeNotFoundError,
        bridge_not_found_handler,
    )
    app.add_exception_handler(
        ActiveDatasetNotFoundError,
        active_dataset_not_found_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,
    )
    app.add_exception_handler(
        ApiValidationError,
        api_validation_error_handler,
    )
    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )


async def bridge_not_found_handler(
    request: Request,
    exc: BridgeNotFoundError,
) -> JSONResponse:
    return _error_response(
        status_code=404,
        code="BRIDGE_NOT_FOUND",
        message="Bridge not found.",
    )


async def active_dataset_not_found_handler(
    request: Request,
    exc: ActiveDatasetNotFoundError,
) -> JSONResponse:
    return _error_response(
        status_code=503,
        code="ACTIVE_DATASET_NOT_FOUND",
        message="Bridge data is currently unavailable.",
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        ErrorDetail(
            field=_format_validation_location(error.get("loc", ())),
            message=str(error.get("msg", "Invalid request value.")),
            type=error.get("type"),
        )
        for error in exc.errors()
    ]

    return _validation_error_response(details)


async def api_validation_error_handler(
    request: Request,
    exc: ApiValidationError,
) -> JSONResponse:
    return _validation_error_response(exc.details)


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled API exception", exc_info=exc)

    return _error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred.",
    )


def _validation_error_response(details: list[ErrorDetail]) -> JSONResponse:
    return _error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=details,
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | dict | None = None,
) -> JSONResponse:
    response = ApiErrorResponse(
        error=ApiErrorBody(
            code=code,
            message=message,
            details=details,
        )
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


def _format_validation_location(location: Sequence[object]) -> str | None:
    if not location:
        return None

    return ".".join(str(part) for part in location)
