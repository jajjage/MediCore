from __future__ import annotations

from typing import Any

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.patients.models.core import Patient
from base_permission.view_permission import RolePermission

# Base Classes and Mixins

class BaseResponseMixin:
    """Mixin to standardize API responses."""

    def success_response(self, data: Any = None, message: str = "Success", status_code: int = status.HTTP_200_OK) -> Response:
        response_data = {
            "status": status_code,
            "message": message,
            "data": data
        }
        return Response(response_data, status=status_code)
    def error_response(self, message: str, code: str | None = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
        response_data = {
            "status": status_code,
            "message": message
        }
        if code:
            response_data["code"] = code
        return Response(response_data, status=status_code)

class PatientRelatedMixin:
    """Mixin for ViewSets related to patient records."""

    def get_patient_id(self) -> str:
        return self.kwargs.get("patient__pk")

    def validate_patient(self) -> None:
        patient_id = self.get_patient_id()
        if not patient_id:
            raise ValidationError("Patient ID is required")
        if not Patient.objects.filter(pk=patient_id).exists():
            raise NotFound("Patient not found")

class BaseViewSet(ModelViewSet, BaseResponseMixin, PatientRelatedMixin):
    """Base ViewSet for patient-related models with standardized CRUD operations."""

    permission_classes = [RolePermission]

    def create(self, request, *args, **kwargs):
        """
        Standardized create method with proper error handling and response format.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            return self.success_response(
                data=serializer.data,
                message=f"{self.get_model_name()} created successfully",
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return self.error_response(
                message=str(e),
                code="validation_error",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except (TypeError, AttributeError, PermissionError) as e:
            return self.error_response(
                message=f"Failed to create {self.get_model_name().lower()}: {str(e)!s}",
                code="creation_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        Standardized update method with proper error handling and response format.
        """
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return self.success_response(
                data=serializer.data,
                message=f"{self.get_model_name()} updated successfully"
            )
        except ValidationError as e:
            return self.error_response(
                message=str(e),
                code="validation_error",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except (PermissionError, AttributeError, TypeError) as e:
            return self.error_response(
                message=f"Failed to update {self.get_model_name().lower()}: {str(e)!s}",
                code="update_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """
        Standardized delete method with proper error handling and response format.
        """
        try:
            instance = self.get_object()
            self.perform_destroy(instance)

            return self.success_response(
                message=f"{self.get_model_name()} deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except (Http404, PermissionError, ValidationError) as e:
            return self.error_response(
                message=f"Failed to delete {self.get_model_name().lower()}: {str(e)!s}",
                code="deletion_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def list(self, request, *args, **kwargs):
        """
        Standardized list method with proper error handling and response format.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return self.success_response(
                data=serializer.data,
                message=f"{self.get_model_name()} list retrieved successfully"
            )
        except (ValidationError, PermissionError):
            return self.error_response(
                message=f"Failed to retrieve {self.get_model_name().lower()} list",
                code="list_retrieval_failed",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except (TypeError, AttributeError) as e:
            return self.error_response(
                message=f"Error processing {self.get_model_name().lower()} list: {str(e)!s}",
                code="list_processing_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        """
        Standardized retrieve method with proper error handling and response format.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return self.success_response(
                data=serializer.data,
                message=f"{self.get_model_name()} retrieved successfully"
            )
        except Http404:
            return self.error_response(
                message=f"{self.get_model_name()} not found",
                code="not_found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except (ValidationError, PermissionError) as e:
            return self.error_response(
                message=str(e),
                code="retrieval_failed",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def get_model_name(self) -> str:
        """AHelper method to get the model name for messages."""
        return self.__class__.__name__.replace("ViewSet", "")
