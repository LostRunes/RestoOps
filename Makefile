.PHONY: up down status logs api worker test migrate

up:
	docker compose up -d

down:
	docker compose down

status:
	docker compose ps

logs:
	docker compose logs -f

api:
	cd apps/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd apps/api && celery -A app.jobs.celery_app.celery_app worker --loglevel=info

test:
	cd apps/api && pytest

migrate:
	cd apps/api && alembic upgrade head
