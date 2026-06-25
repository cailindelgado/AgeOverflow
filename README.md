[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-2972f46106e565e64193e422d61a12cf1da4916b45550586e14ef0a7c637dd04.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=22969256)
# CSSE6400 Cloud Infrastructure Assignment
## AgeOverflow (GCAS — Generation Cohort Analysis System)

A Flask REST API that accepts headshot images and returns a generation cohort analysis (`silent`, `baby_boomers`, `x`, `y`, `z`, `alpha`). Image processing is delegated to an external `engine` binary.

## Running the Application

**Docker (recommended):**
```bash
docker-compose up --build
```
Starts Flask on port 8080 and PostgreSQL.

**Local development:**
```bash
poetry install
SQLALCHEMY_DATABASE_URI=sqlite:///db.sqlite poetry run flask --app GCAS run --port 8080 --debug
```

## Running Tests

Ensure the application is running on port 8080 first, then:
```bash
cd ageoverflow-tests
poetry install
poetry run pytest

# Against a different host:
TEST_HOST=http://localhost:8080/api/v1 poetry run pytest

# Single test file:
poetry run pytest functionality/test_requests.py
```

## API

**Base URL:** `/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analysis/<customer_id>/requests` | Submit images for analysis |
| GET | `/analysis/<customer_id>/requests` | List requests for a customer |
| GET | `/analysis/<customer_id>/requests/<request_id>` | Get a specific request |
| DELETE | `/analysis/<customer_id>/requests/<request_id>` | Delete a request |
| GET | `/health` | Health check |

Images are submitted as base64-encoded strings. Responses include a generation breakdown and a primary generation.

**Valid generations:** `silent`, `baby_boomers`, `x`, `y`, `z`, `alpha`

**Request statuses:** `pending`, `success`, `failed`

## Project Structure

```
.
├── GCAS/                  # Flask application
│   ├── __init__.py        # App factory
│   ├── models/            # SQLAlchemy models (Requests, Results, Photos)
│   └── views/routes.py    # Route handlers
├── terraform/             # AWS infrastructure (ECS, RDS, ALB, ECR, SQS)
├── Dockerfile
├── Dockerfile.worker
├── docker-compose.yml
└── pyproject.toml
```

## Infrastructure

Terraform config in `terraform/` deploys to AWS with ECS (Fargate), RDS (PostgreSQL), an Application Load Balancer, ECR, and SQS.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```
