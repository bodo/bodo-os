## Learning Path Management

### Overview

`LearningPathViewSet` now supports full CRUD. Permissions ensure learners can still browse public/assigned content while editorial users manage their own or all paths.

### Listing and Retrieval

- Anonymous users see only `is_public=True`.
- Authenticated users see:
  - Public paths.
  - Paths explicitly assigned to them.
  - Paths they own.
  - All paths if their profile has `can_manage_all_learning_paths`.

`owner` is included in the serializer output as a profile ID for auditability.

### Creating

- Request must be authenticated.
- `CanManageLearningPaths` checks that the profile has at least `can_create_learning_paths`.
- The `owner` field is auto-populated from the request user and ignored if supplied.

### Updating / Deleting

- Owners can update or delete their own learning paths.
- Global editors (`can_manage_all_learning_paths`) can update/delete any path.
- All other users receive `403`.

### Future Extensions?

- To share ownership, introduce a `LearningPathEditor` join that grants additional collaborators. Current checks expect single-owner semantics.
- Granular permission groups can be layered on top of the Boolean flags if necessary.
