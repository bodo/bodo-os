from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LearningPathProgressViewSet, LearningPathViewSet

router = DefaultRouter()
router.register(r"learning-paths", LearningPathViewSet, basename="learning-path")
router.register(r"progress", LearningPathProgressViewSet, basename="learning-path-progress")

urlpatterns = [
    path("", include(router.urls)),
]
