from __future__ import annotations

from django.db.models import Prefetch, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from accounts.models import UserProfile

from .models import (
    LearningPath,
    LearningPathProgress,
    LearningPathStep,
    LearningPathStepProgress,
)
from .serializers import (
    LearningPathProgressSerializer,
    LearningPathSerializer,
    RegistrationSerializer,
)


class LearningPathViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LearningPathSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        base_queryset = (
            LearningPath.objects.all()
            .prefetch_related(
                Prefetch(
                    "steps",
                    queryset=LearningPathStep.objects.order_by("order").prefetch_related(
                        "blocks"
                    ),
                )
            )
            .order_by("title")
        )

        if self.action == "retrieve":
            return base_queryset

        user = self.request.user
        if user.is_authenticated:
            return base_queryset.filter(
                Q(is_public=True) | Q(assigned_profiles__user=user)
            ).distinct()
        return base_queryset.filter(is_public=True)

    def get_object(self):
        learning_path = super().get_object()
        if not learning_path.is_public:
            user = self.request.user
            if not user.is_authenticated:
                raise PermissionDenied("Authentication required.")
            profile = self._get_profile()
            if not learning_path.assigned_profiles.filter(id=profile.id).exists():
                raise PermissionDenied("You do not have access to this learning path.")
        return learning_path

    def _get_profile(self) -> UserProfile:
        try:
            return self.request.user.profile
        except UserProfile.DoesNotExist as exc:
            raise PermissionDenied("User profile not found.") from exc

    @action(
        detail=False,
        permission_classes=[permissions.AllowAny],
        url_path="public",
    )
    def public(self, request):
        queryset = (
            LearningPath.objects.filter(is_public=True)
            .prefetch_related(
                Prefetch(
                    "steps",
                    queryset=LearningPathStep.objects.order_by("order").prefetch_related(
                        "blocks"
                    ),
                )
            )
            .order_by("title")
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        permission_classes=[permissions.IsAuthenticated],
        url_path="assigned",
    )
    def assigned(self, request):
        profile = self._get_profile()
        queryset = (
            LearningPath.objects.filter(assigned_profiles=profile)
            .prefetch_related(
                Prefetch(
                    "steps",
                    queryset=LearningPathStep.objects.order_by("order").prefetch_related(
                        "blocks"
                    ),
                )
            )
            .order_by("title")
            .distinct()
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        permission_classes=[permissions.IsAuthenticated],
        url_path="started",
    )
    def started(self, request):
        profile = self._get_profile()
        queryset = (
            LearningPath.objects.filter(progress_entries__user_profile=profile)
            .filter(
                progress_entries__step_progress_entries__status__in=[
                    LearningPathStepProgress.Status.IN_PROGRESS,
                    LearningPathStepProgress.Status.COMPLETED,
                ]
            )
            .prefetch_related(
                Prefetch(
                    "steps",
                    queryset=LearningPathStep.objects.order_by("order").prefetch_related(
                        "blocks"
                    ),
                )
            )
            .order_by("title")
            .distinct()
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        permission_classes=[permissions.IsAuthenticated],
        url_path="progress",
    )
    def progress(self, request, pk=None):
        learning_path = self.get_object()
        profile = self._get_profile()
        progress, _ = LearningPathProgress.objects.get_or_create(
            user_profile=profile,
            learning_path=learning_path,
        )
        serializer = LearningPathProgressSerializer(
            progress, context=self.get_serializer_context()
        )
        return Response(serializer.data)


class LearningPathProgressViewSet(viewsets.ModelViewSet):
    serializer_class = LearningPathProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch"]

    def get_queryset(self):
        profile = self._get_profile()
        return (
            LearningPathProgress.objects.filter(user_profile=profile)
            .select_related("learning_path", "last_step")
            .prefetch_related(
                Prefetch(
                    "step_progress_entries",
                    queryset=LearningPathStepProgress.objects.select_related("step"),
                )
            )
            .order_by("learning_path__title")
        )

    def _user_can_access(self, learning_path: LearningPath) -> bool:
        if learning_path.is_public:
            return True
        profile = self._get_profile()
        return learning_path.assigned_profiles.filter(pk=profile.pk).exists()

    def _get_profile(self) -> UserProfile:
        try:
            return self.request.user.profile
        except UserProfile.DoesNotExist as exc:
            raise PermissionDenied("User profile not found.") from exc

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        learning_path = serializer.validated_data["learning_path"]
        if not self._user_can_access(learning_path):
            raise PermissionDenied("You do not have access to this learning path.")
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        learning_path = (
            serializer.validated_data.get("learning_path") or instance.learning_path
        )
        if not self._user_can_access(learning_path):
            raise PermissionDenied("You do not have access to this learning path.")
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class RegistrationView(CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]
