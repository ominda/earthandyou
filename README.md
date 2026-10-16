# Earth&You

Premium Sri Lankan gemstone e-commerce platform.

## Repository structure

```
earthandyou/
├── backend/            # Django + Django REST Framework API
├── frontend/           # Next.js + TypeScript storefront
├── infrastructure/     # Terraform (AWS ECS/Fargate)
│   ├── bootstrap/      # One-time remote state setup
│   ├── environments/   # staging / production
│   └── modules/        # Reusable Terraform modules
├── scripts/            # Developer utility scripts
└── .github/workflows/  # GitHub Actions CI/CD
```

## Prerequisites (WSL2)

- Docker Desktop with WSL2 backend enabled
- Python 3.12+
- Node.js 20+
- Terraform 1.7+
- AWS CLI v2

## Quick start (local development)

```bash
# 1. Copy environment files
cp backend/.env.example backend/.env

# 2. Start all services
docker compose up --build

# 3. Run migrations
docker compose exec backend python manage.py migrate

# 4. Create superuser
docker compose exec backend python manage.py createsuperuser
```

Services:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- Django Admin: http://localhost:8000/admin

## Infrastructure bootstrap (first time only)

```bash
cd scripts
chmod +x bootstrap_terraform_state.sh
./bootstrap_terraform_state.sh
```

See `infrastructure/bootstrap/README.md` for details.

## Environments

| Environment | Branch | URL |
|-------------|--------|-----|
| Local | — | localhost |
| Staging | `develop` | TBD |
| Production | `main` | TBD |
