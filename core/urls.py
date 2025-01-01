from django.urls import path
from .views import (
    CookieTokenObtainPairView, 
    CookieTokenRefreshView,
    CookieTokenVerifyView,
    LogoutView
)

urlpatterns = [
    path('token/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', CookieTokenVerifyView.as_view(), name='token_verify'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]