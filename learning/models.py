from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import UserProfile


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LearningPath(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    owner = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        related_name="owned_learning_paths",
        null=True,
        blank=True,
    )
    assigned_profiles = models.ManyToManyField(
        UserProfile,
        through="LearningPathEnrollment",
        related_name="learning_paths",
        blank=True,
    )

    def __str__(self) -> str:
        return self.title


class LearningPathEnrollment(TimeStampedModel):
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("learning_path", "user_profile")
        verbose_name = _("Learning Path Enrollment")
        verbose_name_plural = _("Learning Path Enrollments")

    def __str__(self) -> str:
        return f"{self.user_profile} -> {self.learning_path}"


class LearningPathStep(TimeStampedModel):
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    title = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("learning_path", "order")

    def __str__(self) -> str:
        return self.title or f"{self.learning_path} - Step {self.order}"


class LearningPathStepBlock(TimeStampedModel):
    class BlockType(models.TextChoices):
        TEXT = "text", _("Text")
        IMAGE = "image", _("Image")

    step = models.ForeignKey(
        LearningPathStep,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    order = models.PositiveIntegerField(default=0)
    block_type = models.CharField(
        max_length=16,
        choices=BlockType.choices,
    )
    text = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="learning_path_blocks/",
        blank=True,
        null=True,
    )
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("step", "order")

    def clean(self) -> None:
        super().clean()
        if self.block_type == self.BlockType.TEXT and not self.text:
            raise ValidationError(_("Text blocks require text content."))
        if self.block_type == self.BlockType.IMAGE and not self.image:
            raise ValidationError(_("Image blocks require an image file."))

    def __str__(self) -> str:
        return f"{self.get_block_type_display()} block #{self.order} for {self.step}"


class LearningPathProgress(TimeStampedModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    last_step = models.ForeignKey(
        LearningPathStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user_profile", "learning_path")
        verbose_name = _("Learning Path Progress")
        verbose_name_plural = _("Learning Path Progress Records")

    def __str__(self) -> str:
        return f"{self.user_profile} progress on {self.learning_path}"

    def clean(self) -> None:
        super().clean()
        if self.last_step and self.last_step.learning_path_id != self.learning_path_id:
            raise ValidationError(_("Last step must belong to the learning path."))

    def refresh_completion_state(self) -> None:
        qs = self.step_progress_entries.all()
        if qs.exists():
            all_completed = not qs.exclude(
                status=LearningPathStepProgress.Status.COMPLETED
            ).exists()
            if self.is_completed != all_completed:
                self.is_completed = all_completed
                self.save(update_fields=["is_completed", "updated_at"])
        else:
            if self.is_completed:
                self.is_completed = False
                self.save(update_fields=["is_completed", "updated_at"])

    def ensure_all_step_progress_entries(self):
        existing_step_ids = set(
            self.step_progress_entries.values_list("step_id", flat=True)
        )
        missing_steps = self.learning_path.steps.exclude(id__in=existing_step_ids)
        LearningPathStepProgress.objects.bulk_create(
            [
                LearningPathStepProgress(
                    progress=self,
                    step=step,
                    status=LearningPathStepProgress.Status.UNSTARTED,
                )
                for step in missing_steps
            ],
            ignore_conflicts=True,
        )
        return self.step_progress_entries.select_related("step")


class LearningPathStepProgress(TimeStampedModel):
    class Status(models.TextChoices):
        UNSTARTED = "unstarted", _("Unstarted")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")

    progress = models.ForeignKey(
        LearningPathProgress,
        on_delete=models.CASCADE,
        related_name="step_progress_entries",
    )
    step = models.ForeignKey(
        LearningPathStep,
        on_delete=models.CASCADE,
        related_name="step_progress_records",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNSTARTED,
    )

    class Meta:
        unique_together = ("progress", "step")
        ordering = ("step__order", "id")

    def __str__(self) -> str:
        return f"{self.step} - {self.get_status_display()}"

    def clean(self) -> None:
        super().clean()
        if self.step.learning_path_id != self.progress.learning_path_id:
            raise ValidationError(_("Step does not belong to the learning path."))
