from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import UserProfile


class CanManageLearningPaths(BasePermission):
    message = "You do not have permission to manage this learning path."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        profile = self._get_profile(request.user)
        if not profile:
            return False
        if profile.can_manage_all_learning_paths:
            return True
        if request.method == "POST":
            return profile.can_create_learning_paths
        # For updates/deletes defer to object-level ownership checks.
        return True

    def has_object_permission(self, request, view, obj: Any):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        profile = self._get_profile(request.user)
        if not profile:
            return False
        if profile.can_manage_all_learning_paths:
            return True

        owner_id = getattr(obj, "owner_id", None)
        return owner_id == profile.id

    @staticmethod
    def _get_profile(user) -> UserProfile | None:
        try:
            return user.profile
        except UserProfile.DoesNotExist:
            return None
