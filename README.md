# Bodo OS Backend

This Django project implements the API for a mentoring/learning platform with user-managed learning paths and progress tracking.

## Project structure

- `main/` – Django project settings and URL routing.
- `accounts/` – User profile model and signals (one-to-one with `auth.User`).
- `learning/` – Learning path domain models, DRF viewsets, serializers, and admin customisations.
- `BACKEND_API_GUIDE.md` – Endpoint reference for the frontend (authentication, learning paths, progress operations).

## Requirements

- Python 3.12
- Poetry for dependency management
- PostgreSQL (recommended for production; SQLite remains the default fallback)

## Initial setup

```bash
poetry install
cp .env.example .env         # adjust secrets, database settings, CORS, etc.
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
```

The API listens on `http://127.0.0.1:8000/`. With `DEBUG=True`, CORS is open to all origins to simplify local frontend development.

## Key commands

- `poetry run python manage.py test` – Run backend tests.
- `poetry run python manage.py makemigrations` – Create schema migrations after model changes.
- `poetry run python manage.py runserver` – Start the development server.

## Next steps

1. Load sample learning paths via the Django admin and confirm public/private visibility.
2. Integrate the Vue SPA against the documented endpoints in `BACKEND_API_GUIDE.md`.
3. Configure production environment variables (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, etc.) before deploying.
