from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserProfile


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "password", "display_name")
        read_only_fields = ("id",)

    def create(self, validated_data: dict[str, Any]):
        display_name = validated_data.pop("display_name", "")
        user_model = get_user_model()
        user = user_model.objects.create_user(**validated_data)
        profile = getattr(user, "profile", None)
        if profile and display_name:
            profile.display_name = display_name
            profile.save(update_fields=["display_name", "updated_at"])
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        profile = getattr(user, "profile", None)
        if profile:
            token["can_create_learning_paths"] = profile.can_create_learning_paths
            token["can_manage_all_learning_paths"] = (
                profile.can_manage_all_learning_paths
            )
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        profile = getattr(self.user, "profile", None)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.get_username(),
            "email": self.user.email,
        }
        if profile:
            data["profile"] = {
                "id": profile.id,
                "display_name": profile.display_name,
                "can_create_learning_paths": profile.can_create_learning_paths,
                "can_manage_all_learning_paths": profile.can_manage_all_learning_paths,
            }
        else:
            data["profile"] = None
        return data
