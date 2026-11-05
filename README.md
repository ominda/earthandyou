# Earth&You

Premium Sri Lankan gemstone e-commerce platform.

## Repository structure

```
earthandyou/
├── backend/                  # Django + Django REST Framework API
│   ├── app/                  # Django project root
│   │   ├── catalog/          # Gemstone species, varieties, products
│   │   ├── config/           # Django settings, URLs, WSGI
│   │   │   └── settings/
│   │   │       ├── base.py       # Shared settings
│   │   │       ├── local.py      # Local development
│   │   │       └── production.py # Production
│   │   └── manage.py
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Next.js + TypeScript storefront
│   ├── src/app/
│   ├── Dockerfile
│   ├── next.config.js
│   ├── package.json
│   └── tsconfig.json
├── infrastructure/           # Terraform (AWS ECS/Fargate)
│   ├── bootstrap/            # One-time remote state setup
│   ├── environments/
│   │   ├── staging/
│   │   └── production/
│   └── modules/              # Reusable Terraform modules
├── scripts/                  # Developer utility scripts
├── .github/workflows/        # GitHub Actions CI/CD
└── docker-compose.yml
```

---

## Prerequisites (WSL2)

Install the following inside WSL2:

- Docker Desktop with WSL2 backend enabled
- Python 3.12+
- Node.js 20+
- Terraform 1.7+
- AWS CLI v2

> All commands below must be run inside WSL2, not from Windows cmd or PowerShell.

---

## Local development setup

### 1. Clone the repository

```bash
git clone <your-repo-url> earthandyou
cd earthandyou
```

### 2. Create the backend environment file

```bash
cp backend/.env.example backend/.env
```

The default values in `.env.example` work as-is for local development.

### 3. Build and start all services

```bash
docker compose up --build
```

This starts:

| Service  | URL                          |
|----------|------------------------------|
| Backend API | http://localhost:8000     |
| Frontend    | http://localhost:3000     |
| Django Admin | http://localhost:8000/admin |
| PostgreSQL | localhost:5432             |
| Redis      | localhost:6379             |

### 4. Run database migrations

```bash
docker compose exec backend python app/manage.py migrate
```

### 5. Create a superuser (admin login)

```bash
docker compose exec backend python app/manage.py createsuperuser
```

Enter a username, email, and password when prompted.

### 6. Seed Sri Lankan gemstone data

```bash
docker compose exec backend python app/manage.py seed_gemstone_species
```

This loads 6 gemstone species and 29 varieties into the database.
The command is safe to run multiple times — it will not create duplicates.

### 7. Verify everything is working

- Open http://localhost:3000 — frontend should show **API connected**
- Open http://localhost:8000/health/ — should return `{"status": "ok", "service": "earthandyou-api"}`
- Open http://localhost:8000/admin — log in with the superuser credentials you created

---

## Daily development workflow

### Start services

```bash
docker compose up
```

### Start services in background

```bash
docker compose up -d
```

### Stop services

```bash
docker compose down
```

### View logs

```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend only
docker compose logs -f frontend
```

### Rebuild after dependency changes

```bash
# After changing requirements.txt or package.json
docker compose up --build
```

---

## Backend commands

All Django management commands follow this pattern:

```bash
docker compose exec backend python app/manage.py <command>
```

### Common commands

```bash
# Create and apply new migrations after model changes
docker compose exec backend python app/manage.py makemigrations
docker compose exec backend python app/manage.py migrate

# Run all tests
docker compose exec backend python app/manage.py test

# Run tests for a specific app
docker compose exec backend python app/manage.py test catalog

# Open Django shell
docker compose exec backend python app/manage.py shell

# Seed gemstone species and varieties
docker compose exec backend python app/manage.py seed_gemstone_species

# Seed with a clean slate (clears existing data first)
docker compose exec backend python app/manage.py seed_gemstone_species --clear
```

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | change before production |
| `DJANGO_SETTINGS_MODULE` | Settings module to use | `config.settings.local` |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DB_NAME` | PostgreSQL database name | `earthandyou` |
| `DB_USER` | PostgreSQL user | `earthandyou` |
| `DB_PASSWORD` | PostgreSQL password | `earthandyou_dev` |
| `DB_HOST` | PostgreSQL host | `db` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |

---

## Infrastructure bootstrap (first time only)

Run this once before any Terraform commands. Requires AWS CLI configured.

```bash
cd scripts
chmod +x bootstrap_terraform_state.sh
./bootstrap_terraform_state.sh
```

This creates:
- S3 bucket `earthandyou-terraform-state` (versioned, encrypted, private)
- DynamoDB table `earthandyou-terraform-locks` for state locking

After bootstrap:

```bash
cd infrastructure/environments/staging
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

---

## Environments

| Environment | Branch | Trigger | Infrastructure |
|-------------|--------|---------|----------------|
| Local | — | `docker compose up` | Docker Compose |
| Staging | `develop` | Push to `develop` | AWS ECS/Fargate |
| Production | `main` | Push to `main` | AWS ECS/Fargate |

---

## Implementation progress

| Phase | Module | Status |
|-------|--------|--------|
| 0.1 | Repo & folder structure | ✅ Done |
| 0.2 | Django project scaffold | ✅ Done |
| 0.3 | PostgreSQL + Docker Compose | ✅ Done |
| 0.4 | Redis + Docker Compose | ✅ Done |
| 0.5 | Next.js scaffold | ✅ Done |
| 0.6 | Terraform scaffold | ✅ Done |
| 1.1 | Gemstone species & variety model | ✅ Done |
| 1.2 | Flexible gemstone attribute model | ✅ Done |
| 1.3 | Physical gemstone + unique ID | ✅ Done |
| 1.4 | Inventory item model | ✅ Done |
| 1.5 | Inventory lifecycle & audit | ✅ Done |
| 1.6 | Certification model | ✅ Done |
| 1.7 | Provenance model | ✅ Done |
| 1.8 | Product & catalog model | ✅ Done |
| 1.9 | Media model | ✅ Done |
| 2.1 | Catalog list API | ✅ Done |
| 2.2 | Product detail API | ✅ Done |
| 2.3 | Search & advanced filters | ✅ Done |
| 2.4 | Signed media URLs | ✅ Done |
| 3.1 | Customer registration & login | ✅ Done |
| 3.2 | Customer profile & addresses | ✅ Done |
| 3.3 | Admin user & RBAC | ✅ Done |
| 4.1 | Cart | ✅ Done |
| 4.2 | Reservation | ✅ Done |
| 4.3 | Checkout | ✅ Done |
| 4.4 | Order model & lifecycle | ✅ Done |
| 4.5 | Payment abstraction | ✅ Done |
| 4.6 | WEBXPAY adapter | ✅ Done |
| 4.7 | Payment webhook handler | ✅ Done |
| 4.8 | Refund model | ✅ Done |
| 5.1 | Shipping configuration | ✅ Done |
| 5.2 | Shipment model | ✅ Done |
| 5.3 | Order tracking API | ✅ Done |
| 5.4 | Export & compliance records | ✅ Done |
| 6.1 | Notification service scaffold | ✅ Done |
| 6.2 | Order notifications | ✅ Done |
| 6.3 | Reservation notifications | ✅ Done |
| 7.1 | Design system & layout | ✅ Done |
| 7.2 | Catalog page | ✅ Done |
| 7.3 | Product detail page | ✅ Done |
| 7.4 | Cart & checkout UI | ⏳ Pending |
| 7.5 | Customer auth UI | ⏳ Pending |
| 7.6 | Order history & tracking UI | ⏳ Pending |
