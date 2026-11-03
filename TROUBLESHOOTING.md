# Earth&You — Troubleshooting Guide

---

## Table of Contents

1. [Docker & Services](#docker--services)
2. [Database & Migrations](#database--migrations)
3. [Authentication & Admin](#authentication--admin)
4. [Backend API](#backend-api)
5. [Frontend](#frontend)
6. [AWS & S3](#aws--s3)

---

## Docker & Services

### Services won't start

**Symptom:** `docker compose up` fails or containers exit immediately.

**Steps:**
1. Check logs: `docker compose logs -f`
2. Ensure Docker Desktop is running with WSL2 backend enabled
3. Confirm you are running commands inside WSL2, not Windows cmd/PowerShell
4. Try a clean rebuild: `docker compose down && docker compose up --build`

---

### Backend container keeps restarting

**Symptom:** Backend container restarts in a loop.

**Steps:**
1. Check backend logs: `docker compose logs -f backend`
2. Common causes:
   - Missing or invalid `backend/.env` file — copy from example: `cp backend/.env.example backend/.env`
   - `DJANGO_SECRET_KEY` not set in `.env`
   - Database not ready yet — wait a few seconds and retry

---

### Port already in use

**Symptom:** `Error: bind: address already in use` on port 8000, 3000, 5432, or 6379.

**Steps:**
1. Find the process using the port (e.g. port 8000):
   ```bash
   lsof -i :8000
   ```
2. Stop the conflicting process or change the port mapping in `docker-compose.yml`

---

### Changes to requirements.txt not taking effect

**Symptom:** Newly added Python package is not found inside the container.

**Fix:** Rebuild the backend image:
```bash
docker compose up --build -d
```

---

## Database & Migrations

### `InconsistentMigrationHistory` error on migrate

**Symptom:**
```
django.db.migrations.exceptions.InconsistentMigrationHistory:
Migration admin.0001_initial is applied before its dependency customers.0001_customer_model
```

**Cause:** `AUTH_USER_MODEL` was changed after the initial migrations were already applied to the database.

**Fix:** Reset the database (development only — all data will be lost):
```bash
docker compose down -v
docker compose up -d
docker compose exec backend python app/manage.py migrate
docker compose exec backend python app/manage.py createsuperuser
```

---

### `manage.py` not found

**Symptom:** `python manage.py` gives `No such file or directory`.

**Cause:** `manage.py` lives at `backend/app/manage.py`, not at the project root.

**Fix:** Always use the full path inside the container:
```bash
docker compose exec backend python app/manage.py <command>
```

---

### Migrations not detected after model changes

**Symptom:** `python app/manage.py migrate` says `No migrations to apply` after changing a model.

**Fix:** Run `makemigrations` first:
```bash
docker compose exec backend python app/manage.py makemigrations
docker compose exec backend python app/manage.py migrate
```

---

### `duplicate column` or `relation already exists` error

**Symptom:** Migration fails with a PostgreSQL error about duplicate columns or relations.

**Cause:** Migration was partially applied or the migration file was regenerated after being applied.

**Fix (development only):**
```bash
docker compose down -v
docker compose up -d
docker compose exec backend python app/manage.py migrate
```

---

### Duplicate `staticfiles` in settings error

**Symptom:** `django.core.exceptions.ImproperlyConfigured: ... staticfiles`.

**Cause:** `INSTALLED_APPS` has `django.contrib.staticfiles` listed twice (once in `base.py` and once in `local.py`).

**Fix:** Ensure `local.py` only contains:
```python
from .base import *
DEBUG = True
```

---

## Authentication & Admin

### Cannot log in to Django Admin after database reset

**Symptom:** Admin login fails with valid credentials after running `docker compose down -v`.

**Cause:** The database was wiped — the superuser no longer exists.

**Fix:** Create a new superuser:
```bash
docker compose exec backend python app/manage.py createsuperuser
```

---

### JWT token returns 401 Unauthorized

**Symptom:** API requests with `Authorization: Bearer <token>` return 401.

**Steps:**
1. Check the token has not expired (access tokens expire after 60 minutes)
2. Refresh the token: `POST /api/v1/auth/token/refresh/` with `{"refresh": "<refresh_token>"}`
3. Ensure the `Authorization` header format is exactly `Bearer <token>` (capital B, single space)
4. Confirm `DEFAULT_AUTHENTICATION_CLASSES` includes `JWTAuthentication` in `settings/base.py`

---

### Email verification token is invalid or expired

**Symptom:** `POST /api/v1/auth/verify-email/` returns 400.

**Causes & fixes:**
- Token already used — request a new one by re-registering or (once Phase 6 is built) via resend endpoint
- Token expired — default expiry is 24 hours, configurable via `EMAIL_VERIFICATION_EXPIRY_HOURS` in `.env`
- Token string is not a valid UUID — ensure the full token value is being submitted

---

## Backend API

### `ModuleNotFoundError: No module named 'pytest'`

**Symptom:** Tests fail with `ModuleNotFoundError: No module named 'pytest'`.

**Cause:** Tests were written using `pytest` fixtures but the project uses Django's built-in test runner.

**Fix:** Use `django.test.TestCase` instead of `pytest`. Run tests with:
```bash
docker compose exec backend python app/manage.py test <app>
```

---

### `NameError` on admin class referencing an inline

**Symptom:** `NameError: name 'SomeInline' is not defined` when starting Django.

**Cause:** The inline class is defined *after* the `ModelAdmin` that references it.

**Fix:** Always define inline classes *before* the `ModelAdmin` class that uses them.

---

### Ordering filter returns wrong order for decimal fields

**Symptom:** Price ordering returns results in lexicographic order (`1500 < 3000 < 500`) instead of numeric order.

**Cause:** Comparing decimal strings with Python's `sorted()` sorts lexicographically.

**Fix:** Cast to `float` before comparing in tests:
```python
prices = [float(r["price_usd"]) for r in response.data["results"]]
```

---

### `CORS` errors in browser

**Symptom:** Frontend gets `Access-Control-Allow-Origin` errors when calling the API.

**Fix:** Add the frontend origin to `CORS_ALLOWED_ORIGINS` in `backend/.env`:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## Frontend

### Frontend shows "API not connected"

**Symptom:** Next.js frontend cannot reach the backend API.

**Steps:**
1. Confirm backend is running: `curl http://localhost:8000/health/`
2. Check `NEXT_PUBLIC_API_URL` is set correctly in `docker-compose.yml` (should be `http://localhost:8000`)
3. Restart frontend: `docker compose restart frontend`

---

## AWS & S3

### Signed media URLs return `null`

**Symptom:** `POST /api/v1/catalog/media/sign/` returns `null` for all keys.

**Cause:** `MEDIA_S3_BUCKET` is not set — this is expected in local development.

**Fix for production:** Set the following in your environment:
```
MEDIA_S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-southeast-1
```

---

### Terraform state errors

**Symptom:** `terraform init` fails with S3 backend errors.

**Cause:** The S3 bucket and DynamoDB table for remote state have not been created yet.

**Fix:** Run the bootstrap script once:
```bash
cd scripts
chmod +x bootstrap_terraform_state.sh
./bootstrap_terraform_state.sh
```

---

## General Tips

- Always run commands inside WSL2, not Windows cmd or PowerShell
- After any `requirements.txt` change, run `docker compose up --build`
- After any model change, run `makemigrations` then `migrate`
- After `docker compose down -v`, recreate the superuser with `createsuperuser`
- Run the full test suite before committing: `docker compose exec backend python app/manage.py test`
