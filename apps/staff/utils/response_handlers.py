from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response


class APIResponse:
    """
    Standardized API response handler for consistent frontend responses.
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
        extra: dict | None = None
    ) -> Response:
        """
        Success response with standardized format.
        """
        response_data = {
            "status": "success",
            "message": message,
            "data": data
        }
        if extra:
            response_data.update(extra)
        return Response(response_data, status=status_code)

    @staticmethod
    def error(
        message: str = "An error occurred",
        errors: dict | list | str | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str | None = None
    ) -> Response:
        """
        Error response with standardized format.
        """
        response_data = {
            "status": "error",
            "message": message,
            "errors": errors if errors is not None else []
        }
        if error_code:
            response_data["error_code"] = error_code
        return Response(response_data, status=status_code)

    @staticmethod
    def validation_error(errors: dict) -> Response:
        """
        AValidation error response with field-specific errors.
        """
        return APIResponse.error(
            message="Validation failed",
            errors=errors,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR"
        )

    @staticmethod
    def not_found(
        message: str = "Resource not found",
        resource_type: str | None = None
    ) -> Response:
        """
        Not found error response.
        """
        error_message = f"{resource_type} not found" if resource_type else message
        return APIResponse.error(
            message=error_message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND"
        )
