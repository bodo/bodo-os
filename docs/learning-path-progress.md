## Learning Path Progress API

The progress endpoints remain focused on authenticated learners, but they benefit from ownership metadata:

- `GET /api/learning-paths/{id}/progress/` auto-creates a `LearningPathProgress` for the requesting user if missing.
- `LearningPathProgressViewSet` (`/api/progress/`) restricts records to the current profile.
- Step-level updates still validate that all steps belong to the same learning path.

### Relationship to Permissions

`LearningPathProgressViewSet` continues to enforce access via `_user_can_access`, which allows private paths only when the learner is assigned. Editorial flags do not bypass learner-side checks; editors must still be assigned if they want to simulate learner progress.

### Data Integrity Helpers

- `LearningPathProgress.ensure_all_step_progress_entries()` backfills missing steps before serialization.
- `refresh_completion_state()` recalculates `is_completed` whenever step statuses change.
