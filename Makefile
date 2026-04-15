.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate migrate-fresh

# Default target
help:
	@echo "FastAPI Starter - Available commands:"
	@echo ""
	@echo "  make install         - Install dependencies with Poetry"
	@echo "  make dev             - Run development server with auto-reload"
	@echo "  make run             - Run production server"
	@echo "  make test            - Run tests"
	@echo "  make test-cov        - Run tests with coverage"
	@echo "  make lint            - Run linters (ruff, mypy)"
	@echo "  make format          - Format code (black, isort)"
	@echo "  make format-check    - Check code formatting"
	@echo "  make migrate         - Create and apply new migration"
	@echo "  make migrate-up      - Apply pending migrations"
	@echo "  make migrate-down    - Rollback last migration"
	@echo "  make migrate-fresh   - Drop database and re-run migrations (dev only)"
	@echo "  make clean           - Clean cache and build files"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-up       - Start services with docker-compose"
	@echo "  make docker-down     - Stop docker-compose services"
	@echo ""

# Installation
install:
	@echo "Installing dependencies..."
	poetry install

# Development
dev:
	@echo "Starting development server..."
	poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000

run:
	@echo "Starting production server..."
	poetry run python main.py

# Testing
test:
	@echo "Running tests..."
	poetry run pytest

test-cov:
	@echo "Running tests with coverage..."
	poetry run pytest --cov=src --cov-report=html --cov-report=term

# Code Quality
lint:
	@echo "Running ruff..."
	poetry run ruff check src/ tests/
	@echo "Running mypy..."
	poetry run mypy src/

format:
	@echo "Formatting code with black..."
	poetry run black src/ tests/
	@echo "Sorting imports with isort..."
	poetry run isort src/ tests/

format-check:
	@echo "Checking code formatting..."
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/

# Database Migrations
migrate:
	@read -p "Migration description: " desc; \
	poetry run alembic revision --autogenerate -m "$$desc"
	poetry run alembic upgrade head

migrate-up:
	@echo "Applying migrations..."
	poetry run alembic upgrade head

migrate-down:
	@echo "Rolling back last migration..."
	poetry run alembic downgrade -1

migrate-fresh:
	@echo "Dropping database and re-running migrations..."
	poetry run python src/scripts/migrate_fresh.py

# Cleanup
clean:
	@echo "Cleaning cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '*.log' -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
	@echo "Clean complete!"

# Docker
docker-build:
	@echo "Building Docker image..."
	docker build -t fastapi-starter .

docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	docker-compose logs -f api
