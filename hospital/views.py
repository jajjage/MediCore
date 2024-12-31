from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsSuperuser
from .services import TenantCreationService
from .serializers import CreateTenantRequestSerializer, HospitalProfileSerializer
import logging

logger = logging.getLogger(__name__)


class CreateTenantAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperuser]

    def post(self, request):
        """
        Create a new tenant with associated hospital profile and admin user.
        """
        serializer = CreateTenantRequestSerializer(data=request.data)

        try:
            # Validate input data
            serializer.is_valid(raise_exception=True)

            # Create tenant and related objects
            hospital_profile = TenantCreationService.create_tenant(
                serializer.validated_data
            )

            # Prepare response
            response_serializer = HospitalProfileSerializer(hospital_profile)
            return Response(
                {
                    "status": "success",
                    "message": "Hospital tenant created successfully",
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Tenant creation failed: {str(e)}", exc_info=True)
            return Response(
                {
                    "status": "error",
                    "message": "Failed to create hospital tenant",
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
