import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters import rest_framework as django_filters
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.staff.permissions import TenantModelPermission
from apps.staff.utils.exceptions import BusinessLogicError
from apps.staff.utils.response_handlers import APIResponse

logger = logging.getLogger(__name__)

class BaseViewSet(viewsets.ModelViewSet, APIResponse):
    permission_classes = [TenantModelPermission]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    queryset = None

    def handle_exception(self, exc):  # noqa: PLR0911
        """Enhanced exception handling with specific error responses."""
        # Handle Django validation errors
        if isinstance(exc, DjangoValidationError):
            return APIResponse.validation_error(exc.message_dict)

        # Handle DRF validation errors
        if isinstance(exc, DRFValidationError):
            if hasattr(exc.detail, "items"):
                return APIResponse.validation_error(exc.detail)
            return APIResponse.error(str(exc.detail))

        # Handle permission errors
        if isinstance(exc, PermissionDenied):
            return APIResponse.error(
                message="You do not have permission to perform this action",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Handle authentication errors
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            return APIResponse.error(
                message="Authentication credentials were not provided",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Handle business logic errors
        if isinstance(exc, BusinessLogicError):
            return APIResponse.error(
                message=exc.message,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Handle any other unexpected errors
        return APIResponse.error(
            message="eror occur at unexpexted here",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return self.success(
                data=serializer.data,
                message=f"Successfully retrieved {self.basename} list"
            )
        except (DjangoValidationError, DRFValidationError, BusinessLogicError) as ble:
            logger.exception(f"Business logic error in end_assignment: {ble!s}")
            return self.handle_exception(ble)
        except Exception as e:
            logger.exception(f"Unexpected error in end_assignment: {e!s}")
            return APIResponse.error(
                message="An unexpected error occurred while ending the assignment",
                error_code="UNEXPECTED_ERROR",
                status_code=500
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return self.success(
                data=serializer.data,
                message=f"Successfully retrieved {self.basename}"
            )
        except (DjangoValidationError, DRFValidationError, BusinessLogicError) as e:
            return self.handle_exception(e)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return self.success(
                data=serializer.data,
                message=f"Successfully created {self.basename}",
                status_code=status.HTTP_201_CREATED
            )
        except (DjangoValidationError, DRFValidationError, BusinessLogicError) as e:
            return self.handle_exception(e)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return self.success(
                data=serializer.data,
                message=f"Successfully updated {self.basename}"
            )
        except (DjangoValidationError, DRFValidationError, BusinessLogicError) as e:
            return self.handle_exception(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return self.success(
                message=f"Successfully deleted {self.basename}",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except (DjangoValidationError, DRFValidationError, BusinessLogicError) as e:
            return self.handle_exception(e)
