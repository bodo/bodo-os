from django.contrib import admin

from .models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathProgress,
    LearningPathStep,
    LearningPathStepBlock,
    LearningPathStepProgress,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "display_name")


class LearningPathStepInline(admin.StackedInline):
    model = LearningPathStep
    extra = 0
    ordering = ("order",)
    fields = ("title", "order")


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "is_public", "created_at", "updated_at")
    list_filter = ("is_public",)
    search_fields = ("title",)
    inlines = [LearningPathStepInline]


class LearningPathStepBlockInline(admin.TabularInline):
    model = LearningPathStepBlock
    extra = 0
    ordering = ("order",)


@admin.register(LearningPathStep)
class LearningPathStepAdmin(admin.ModelAdmin):
    list_display = ("learning_path", "order", "title")
    ordering = ("learning_path", "order")
    inlines = [LearningPathStepBlockInline]


@admin.register(LearningPathEnrollment)
class LearningPathEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("learning_path", "user_profile", "is_active", "created_at")
    list_filter = ("is_active", "learning_path")
    search_fields = (
        "learning_path__title",
        "user_profile__user__username",
    )


@admin.register(LearningPathStepProgress)
class LearningPathStepProgressAdmin(admin.ModelAdmin):
    list_display = ("progress", "step", "status", "updated_at")
    list_filter = ("status", "progress__learning_path")
    search_fields = (
        "progress__user_profile__user__username",
        "step__learning_path__title",
    )


@admin.register(LearningPathProgress)
class LearningPathProgressAdmin(admin.ModelAdmin):
    list_display = (
        "learning_path",
        "user_profile",
        "last_step",
        "is_completed",
        "updated_at",
    )
    list_filter = ("is_completed", "learning_path")
    search_fields = (
        "learning_path__title",
        "user_profile__user__username",
    )
