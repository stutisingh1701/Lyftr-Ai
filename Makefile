.PHONY: up down build test clean logs

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

test:
	cd backend && pytest tests/ -v

logs:
	docker compose logs -f

clean:
	docker compose down -v
