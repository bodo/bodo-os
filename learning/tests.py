from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathProgress,
    LearningPathStep,
    LearningPathStepProgress,
)


class LearningPathAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="learner",
            email="learner@example.com",
            password="pass1234",
        )
        self.profile = self.user.profile
        self.public_path = LearningPath.objects.create(
            title="Public Path",
            description="Public description",
            is_public=True,
        )
        self.private_path = LearningPath.objects.create(
            title="Private Path",
            description="Private description",
            is_public=False,
        )
        LearningPathEnrollment.objects.create(
            learning_path=self.private_path,
            user_profile=self.profile,
        )

        self.step_public = LearningPathStep.objects.create(
            learning_path=self.public_path,
            title="Public Step",
            order=1,
        )
        self.step_private_1 = LearningPathStep.objects.create(
            learning_path=self.private_path,
            title="Private Step 1",
            order=1,
        )
        self.step_private_2 = LearningPathStep.objects.create(
            learning_path=self.private_path,
            title="Private Step 2",
            order=2,
        )

    def test_public_learning_paths_list_accessible(self):
        url = reverse("learning-path-public")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.public_path.title)

    def test_assigned_learning_paths_requires_authentication(self):
        url = reverse("learning-path-assigned")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.private_path.title)

    def test_progress_create_and_update_flow(self):
        self.client.force_authenticate(self.user)
        url = reverse("learning-path-progress-list")
        payload = {
            "learning_path": self.private_path.id,
            "last_step": self.step_private_1.id,
            "step_progress_entries": [
                {"step": self.step_private_1.id, "status": LearningPathStepProgress.Status.IN_PROGRESS},
                {"step": self.step_private_2.id, "status": LearningPathStepProgress.Status.UNSTARTED},
            ],
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        progress_id = response.data["id"]

        progress = LearningPathProgress.objects.get(id=progress_id)
        self.assertEqual(progress.last_step, self.step_private_1)
        step_statuses = {
            entry.step_id: entry.status
            for entry in progress.step_progress_entries.all()
        }
        self.assertEqual(step_statuses[self.step_private_1.id], LearningPathStepProgress.Status.IN_PROGRESS)

        detail_url = reverse("learning-path-progress-detail", args=[progress_id])
        update_payload = {
            "last_step": self.step_private_2.id,
            "step_progress_entries": [
                {"step": self.step_private_1.id, "status": LearningPathStepProgress.Status.COMPLETED},
                {"step": self.step_private_2.id, "status": LearningPathStepProgress.Status.IN_PROGRESS},
            ],
        }
        response = self.client.patch(detail_url, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress.refresh_from_db()
        self.assertEqual(progress.last_step, self.step_private_2)
        self.assertTrue(progress.step_progress_entries.filter(
            step=self.step_private_1,
            status=LearningPathStepProgress.Status.COMPLETED,
        ).exists())

        progress_endpoint = reverse("learning-path-progress", args=[self.private_path.id])
        response = self.client.get(progress_endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["learning_path"], self.private_path.id)
        self.assertEqual(len(response.data["step_progress_entries"]), 2)
