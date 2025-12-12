.PHONY: install dev build up down logs shell restart clean test format lint

# Install dependencies using Poetry
install:
	@echo "Installing dependencies..."
	poetry install

# Run in development mode with auto-reload
dev:
	@echo "Starting development server..."
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Build Docker image
build:
	@echo "Building Docker image..."
	docker compose build

# Start services with Docker Compose
up:
	@echo "Starting services..."
	docker compose up -d
	@echo "Services started. Check status with: make logs"

# Stop services
down:
	@echo "Stopping services..."
	docker compose down

# View logs
logs:
	@echo "Showing logs (Ctrl+C to exit)..."
	docker compose logs -f

# Access container shell
shell:
	@echo "Opening shell in container..."
	docker compose exec aima-checker /bin/bash

# Restart services
restart:
	@echo "Restarting services..."
	docker compose restart

# Clean up (remove containers, volumes, and database)
clean:
	@echo "Cleaning up..."
	docker compose down -v
	rm -rf data/*.db
	@echo "Cleanup complete"

# Run tests (if implemented)
test:
	@echo "Running tests..."
	poetry run pytest

# Format code with black
format:
	@echo "Formatting code..."
	poetry run black app/

# Lint code
lint:
	@echo "Linting code..."
	poetry run flake8 app/

# Show service status
status:
	@echo "Service status:"
	docker compose ps

# View application logs only
app-logs:
	docker compose logs -f aima-checker

# Help
help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies with Poetry"
	@echo "  make dev        - Run development server with auto-reload"
	@echo "  make build      - Build Docker image"
	@echo "  make up         - Start services in background"
	@echo "  make down       - Stop services"
	@echo "  make logs       - View logs"
	@echo "  make shell      - Access container shell"
	@echo "  make restart    - Restart services"
	@echo "  make clean      - Remove containers, volumes, and database"
	@echo "  make status     - Show service status"
	@echo "  make test       - Run tests"
	@echo "  make help       - Show this help message"
