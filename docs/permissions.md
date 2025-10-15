## Permission Model Overview

The API now distinguishes between learner access, path owners, and global editors.

### User Flags

`accounts.models.UserProfile` exposes two Boolean flags:

- `can_create_learning_paths`: user may create new learning paths for themselves.
- `can_manage_all_learning_paths`: user has global editorial access (create/update/delete across all learning paths).

These flags surface in JWT claims (`can_create_learning_paths`, `can_manage_all_learning_paths`) and in the login response under `profile`.

### Learning Path Ownership

Each `LearningPath` has an `owner` (`UserProfile`). Ownership is set automatically on creation and used to gate write operations.

- Owners can update or delete their own learning paths even without the global flag.
- Global editors bypass ownership checks.

### REST Framework Permission

`learning.permissions.CanManageLearningPaths` enforces the rules:

- `SAFE_METHODS` (GET/HEAD/OPTIONS) behave as before.
- `POST` requires `can_create_learning_paths` **or** `can_manage_all_learning_paths`.
- `PUT/PATCH/DELETE` require either `can_manage_all_learning_paths` or ownership of the target path.

If the request user lacks a `UserProfile`, the permission denies write access.
