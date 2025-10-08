from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import LearningPathProgressViewSet, LearningPathViewSet, RegistrationView

router = DefaultRouter()
router.register(r"learning-paths", LearningPathViewSet, basename="learning-path")
router.register(r"progress", LearningPathProgressViewSet, basename="learning-path-progress")

urlpatterns = [
    path("auth/register/", RegistrationView.as_view(), name="auth-register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("", include(router.urls)),
]
