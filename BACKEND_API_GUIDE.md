# Backend API Guide

This document describes the HTTP contract between the Vue SPA and the Django backend. All endpoints live under the `/api/` prefix and exchange JSON unless explicitly stated. The default permission class requires an authenticated user (`Authorization: Bearer <access_token>`); endpoints that allow anonymous access are marked explicitly.

## Authentication & User Accounts

### Register `POST /api/auth/register/` _(public)_
Create a new user and its associated profile.

Request body:
```json
{
  "username": "alex",
  "email": "alex@example.com",
  "password": "strong-password",
  "display_name": "Alex Doe"        // optional
}
```

Response body (201):
```json
{
  "id": 12,
  "username": "alex",
  "email": "alex@example.com",
  "display_name": "Alex Doe"
}
```

Password must be ≥8 characters. A matching `UserProfile` is created automatically; missing profile is considered an error for other endpoints.
Editorial flags (`can_create_learning_paths`, `can_manage_all_learning_paths`) default to `false` and can be toggled in Django admin.

### Obtain JWT `POST /api/auth/token/` _(public)_
Authenticate with username & password to receive JWT credentials.

Request:
```json
{
  "username": "alex",
  "password": "strong-password"
}
```

Response (200):
```json
{
  "refresh": "<jwt-refresh-token>",
  "access": "<jwt-access-token>"
}
```

Send the `access` token as `Authorization: Bearer ...` for protected requests.

Additional fields are returned for convenience:

```json
{
  "user": {
    "id": 12,
    "username": "alex",
    "email": "alex@example.com"
  },
  "profile": {
    "id": 7,
    "display_name": "Alex Doe",
    "can_create_learning_paths": false,
    "can_manage_all_learning_paths": false
  }
}
```

The same permission flags are embedded inside the JWT as custom claims so the SPA can toggle editor UX without an extra request.

### Refresh JWT `POST /api/auth/token/refresh/`
Request:
```json
{
  "refresh": "<jwt-refresh-token>"
}
```

Response:
```json
{
  "access": "<new-access-token>"
}
```

## Learning Paths

Learning paths expose nested content (steps and blocks). Image blocks return a relative URL that must be resolved against the backend host. All timestamps are ISO 8601.

### Schema Summary

```jsonc
LearningPath {
  id: number
  title: string
  description: string
  is_public: boolean
  owner: number | null           // UserProfile ID
  steps: LearningPathStep[]
  created_at: string
  updated_at: string
}

LearningPathStep {
  id: number
  title: string
  order: number
  blocks: LearningPathStepBlock[]
  created_at: string
  updated_at: string
}

LearningPathStepBlock {
  id: number
  order: number
  block_type: "text" | "image"
  text: string             // present for text blocks
  image: string | null     // media URL for image blocks
  caption: string
  created_at: string
  updated_at: string
}
```

### List Accessible Paths `GET /api/learning-paths/`
Requires authentication. Returns:

- Public paths.
- Private paths assigned to the current user.
- Paths owned by the current user.
- All paths when `can_manage_all_learning_paths` is true.

### Public Catalogue `GET /api/learning-paths/public/` _(public)_
Returns every public learning path. Use this for landing pages or anonymous browsing.

### Assigned Paths `GET /api/learning-paths/assigned/`
Authenticated endpoint returning private paths explicitly assigned to the user.

### Started Paths `GET /api/learning-paths/started/`
Authenticated endpoint that filters to learning paths where the user has begun or completed at least one step.

### Retrieve Path `GET /api/learning-paths/{id}/`
Authenticated. Works for:

- Public paths.
- Private paths assigned to the user.
- Paths owned by the user.
- Any path when `can_manage_all_learning_paths` is true.

### Create Path `POST /api/learning-paths/`
Requires authentication and either `can_create_learning_paths` or `can_manage_all_learning_paths`.

The request body mirrors the serializer (currently `title`, `description`, `is_public`). `owner` is ignored by the API; it is automatically set to the authenticated user’s profile.

### Update Path `PUT/PATCH /api/learning-paths/{id}/`
Requires ownership of the target path or the global manage flag. Returns the full learning path representation.

### Delete Path `DELETE /api/learning-paths/{id}/`
Same permission rules as update. Returns `204 No Content` on success.

### Get Progress Snapshot `GET /api/learning-paths/{id}/progress/`
Authenticated. Creates a `LearningPathProgress` record on-demand (if missing) and returns the user’s current status for the path.

Response example:
```json
{
  "id": 5,
  "learning_path": 42,
  "last_step": 133,                  // null until the learner touches a step
  "is_completed": false,
  "step_progress_entries": [
    {
      "id": 70,
      "step": 133,
      "step_order": 1,
      "status": "in_progress",
      "created_at": "2025-10-08T12:21:00Z",
      "updated_at": "2025-10-08T12:24:00Z"
    },
    {
      "id": 71,
      "step": 134,
      "step_order": 2,
      "status": "unstarted",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

## Progress Management (`/api/progress/`)

This viewset manages the learner’s state across all assigned paths. All routes require authentication.

### List `GET /api/progress/`
Returns every `LearningPathProgress` owned by the current user.

### Create `POST /api/progress/`
Upserts progress for a given path. If the record already exists, the backend updates `last_step` and any provided step statuses.

Request body:
```json
{
  "learning_path": 42,
  "last_step": 133,                          // optional, null allowed
  "step_progress_entries": [
    { "step": 133, "status": "in_progress" },
    { "step": 134, "status": "unstarted" }
  ]
}
```

- `status` must be one of `unstarted`, `in_progress`, or `completed`.
- Every referenced `step` must belong to the same `learning_path`.
- Missing steps are automatically backfilled as `"unstarted"` in responses, so the frontend can always rely on a complete list.

Response (201) matches the snapshot format shown earlier.

### Retrieve `GET /api/progress/{id}/`
Fetch a specific progress record by its ID. Only records owned by the current user are visible.

### Update / Patch `PUT|PATCH /api/progress/{id}/`
Payload is identical to `POST`. Use to mark progress, update `last_step`, or set completion flags.

## Error Handling

- `401 Unauthorized`: missing/invalid JWT for protected endpoints.
- `403 Forbidden`: authenticated but lacking the required assignment/ownership/editor flag, or the user profile is missing.
- `400 Bad Request`: validation errors (e.g., mismatched step IDs, missing password).

Errors return the standard DRF error shape:
```json
{
  "detail": "You do not have access to this learning path."
}
```
or field-specific messages, e.g.:
```json
{
  "step_progress_entries": ["All steps must belong to the learning path."]
}
```

## Media & Static Assets

Image blocks expose `image` as a relative path under `/media/learning_path_blocks/`. During development, Django serves media when `DEBUG` is true. In production, route media hosting via your CDN or object storage and ensure the frontend prepends the correct base URL.

## Sync Considerations

- The backend is authoritative for progress state; clients can work offline and push updates later. When the frontend sends `step_progress_entries`, only the statuses in the payload change—omitted steps retain their previous state.
- Reading progress via `/api/learning-paths/{id}/progress/` or `/api/progress/` always returns the merged view (including auto-created “unstarted” entries), which is safe to cache locally.

## Quick Reference

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/auth/register/` | POST | No | Create user + profile |
| `/api/auth/token/` | POST | No | Obtain JWT pair |
| `/api/auth/token/refresh/` | POST | No | Refresh access token |
| `/api/learning-paths/public/` | GET | No | List public paths |
| `/api/learning-paths/` | GET | Yes | List accessible (public + assigned) paths |
| `/api/learning-paths/{id}/` | GET | Yes | Retrieve a specific path |
| `/api/learning-paths/assigned/` | GET | Yes | Paths explicitly assigned to user |
| `/api/learning-paths/started/` | GET | Yes | Paths with in-progress/completed steps |
| `/api/learning-paths/{id}/progress/` | GET | Yes | Progress snapshot (auto-creates record) |
| `/api/progress/` | GET | Yes | List all progress records |
| `/api/progress/` | POST | Yes | Create/update progress for a path |
| `/api/progress/{id}/` | GET | Yes | Retrieve progress by ID |
| `/api/progress/{id}/` | PUT/PATCH | Yes | Update progress by ID |

Use this guide to generate integration prompts or automate client-side SDK generation. The JSON examples are representative; field ordering may vary.
