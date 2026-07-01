import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    incoming_request_id = request.headers.get("x-request-id")

    if incoming_request_id:
        return incoming_request_id

    return str(uuid.uuid4())


def sanitize_error_detail(detail):
    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        return detail

    if isinstance(detail, dict):
        return detail

    return "Request failed."


def register_error_handlers(app: FastAPI) -> None:
    settings = get_settings()

    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        request_id = get_request_id(request)

        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": sanitize_error_detail(exc.detail),
                    "status_code": exc.status_code,
                    "request_id": request_id,
                }
            },
            headers=exc.headers,
        )

        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ):
        request_id = get_request_id(request)

        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": sanitize_error_detail(exc.detail),
                    "status_code": exc.status_code,
                    "request_id": request_id,
                }
            },
        )

        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        request_id = get_request_id(request)

        logger.warning(
            "Validation error | request_id=%s | path=%s | errors=%s",
            request_id,
            request.url.path,
            exc.errors(),
        )

        if settings.is_production:
            message = "Invalid request payload."
        else:
            message = exc.errors()

        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "message": message,
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "request_id": request_id,
                }
            },
        )

        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        request_id = get_request_id(request)

        logger.exception(
            "Unhandled exception | request_id=%s | path=%s",
            request_id,
            request.url.path,
        )

        if settings.is_production:
            message = "Internal server error."
        else:
            message = str(exc)

        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": message,
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "request_id": request_id,
                }
            },
        )

        response.headers["x-request-id"] = request_id
        return response