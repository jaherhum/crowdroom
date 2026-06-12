.PHONY: up down down-clean logs ps shell migrate

up:
	docker compose up --build -d --wait

down:
	docker compose down

down-clean:
	docker compose down -v

logs:
	docker compose logs -f app

ps:
	docker compose ps

shell:
	docker compose exec app sh

migrate:
	docker compose exec app alembic upgrade head
