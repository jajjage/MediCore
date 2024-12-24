from django.urls import path
from .views import CreateTenantAPIView

urlpatterns = [
    path('tenant/create/', CreateTenantAPIView.as_view(), name='create_tenant'),
]
