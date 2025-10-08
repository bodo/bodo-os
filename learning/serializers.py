from __future__ import annotations

from typing import Any, Iterable

from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import UserProfile

from .models import (
    LearningPath,
    LearningPathProgress,
    LearningPathStep,
    LearningPathStepBlock,
    LearningPathStepProgress,
)


class LearningPathStepBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPathStepBlock
        fields = (
            "id",
            "order",
            "block_type",
            "text",
            "image",
            "caption",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class LearningPathStepSerializer(serializers.ModelSerializer):
    blocks = LearningPathStepBlockSerializer(many=True, read_only=True)

    class Meta:
        model = LearningPathStep
        fields = ("id", "title", "order", "blocks", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class LearningPathSerializer(serializers.ModelSerializer):
    steps = LearningPathStepSerializer(many=True, read_only=True)

    class Meta:
        model = LearningPath
        fields = (
            "id",
            "title",
            "description",
            "is_public",
            "steps",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = UserProfile
        fields = ("id", "user", "display_name", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


class LearningPathStepProgressSerializer(serializers.ModelSerializer):
    step_order = serializers.IntegerField(source="step.order", read_only=True)

    class Meta:
        model = LearningPathStepProgress
        fields = (
            "id",
            "step",
            "step_order",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "step_order")


class LearningPathProgressSerializer(serializers.ModelSerializer):
    learning_path = serializers.PrimaryKeyRelatedField(
        queryset=LearningPath.objects.all()
    )
    last_step = serializers.PrimaryKeyRelatedField(
        queryset=LearningPathStep.objects.all(),
        allow_null=True,
        required=False,
    )
    step_progress_entries = LearningPathStepProgressSerializer(
        many=True, required=False
    )

    class Meta:
        model = LearningPathProgress
        fields = (
            "id",
            "learning_path",
            "last_step",
            "is_completed",
            "step_progress_entries",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_completed", "created_at", "updated_at")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        learning_path: LearningPath = attrs.get("learning_path") or (
            self.instance.learning_path if self.instance else None
        )
        last_step: LearningPathStep | None = attrs.get("last_step")

        if last_step and learning_path and last_step.learning_path_id != learning_path.id:
            raise serializers.ValidationError(
                {"last_step": "Selected step must belong to the learning path."}
            )

        step_progress_data: Iterable[dict[str, Any]] = attrs.get(
            "step_progress_entries", []
        )
        for step_data in step_progress_data or []:
            step = step_data.get("step")
            if step and learning_path and step.learning_path_id != learning_path.id:
                raise serializers.ValidationError(
                    {"step_progress_entries": "All steps must belong to the learning path."}
                )
        return attrs

    def _get_user_profile(self) -> UserProfile:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        try:
            return request.user.profile
        except UserProfile.DoesNotExist as exc:
            raise serializers.ValidationError(
                "User profile is missing. Please contact support."
            ) from exc

    def _sync_step_progress(
        self,
        progress: LearningPathProgress,
        step_progress_data: Iterable[dict[str, Any]],
    ) -> None:
        existing = {
            item.step_id: item
            for item in progress.step_progress_entries.select_related("step")
        }
        for progress_item in step_progress_data or []:
            step = progress_item["step"]
            status = progress_item.get(
                "status", LearningPathStepProgress.Status.UNSTARTED
            )
            entry = existing.get(step.id)
            if entry:
                if entry.status != status:
                    entry.status = status
                    entry.save(update_fields=["status", "updated_at"])
            else:
                LearningPathStepProgress.objects.create(
                    progress=progress,
                    step=step,
                    status=status,
                )

    def create(self, validated_data: dict[str, Any]) -> LearningPathProgress:
        step_progress_data = validated_data.pop("step_progress_entries", [])
        user_profile = self._get_user_profile()
        learning_path = validated_data["learning_path"]
        last_step = validated_data.get("last_step")

        with transaction.atomic():
            progress, created = LearningPathProgress.objects.get_or_create(
                user_profile=user_profile,
                learning_path=learning_path,
                defaults={"last_step": last_step},
            )
            if not created and last_step:
                progress.last_step = last_step
                progress.save(update_fields=["last_step", "updated_at"])
            self._sync_step_progress(progress, step_progress_data)
            progress.refresh_completion_state()
        return progress

    def update(
        self, instance: LearningPathProgress, validated_data: dict[str, Any]
    ) -> LearningPathProgress:
        step_progress_data = validated_data.pop("step_progress_entries", [])
        last_step = validated_data.get("last_step")

        with transaction.atomic():
            if last_step is not None:
                instance.last_step = last_step
                instance.save(update_fields=["last_step", "updated_at"])
            self._sync_step_progress(instance, step_progress_data)
            instance.refresh_from_db()
            instance.refresh_completion_state()
        return instance

    def to_representation(self, instance: LearningPathProgress) -> dict[str, Any]:
        instance.ensure_all_step_progress_entries()
        return super().to_representation(instance)


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
            "password",
            "display_name",
        )
        read_only_fields = ("id",)

    def create(self, validated_data: dict[str, Any]):
        display_name = validated_data.pop("display_name", "")
        user_model = get_user_model()
        user = user_model.objects.create_user(**validated_data)
        if display_name:
            profile = getattr(user, "profile", None)
            if profile:
                profile.display_name = display_name
                profile.save(update_fields=["display_name", "updated_at"])
        return user
