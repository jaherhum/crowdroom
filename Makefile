.PHONY: up up-sqlite down logs ps shell migrate

up:
	docker compose --profile postgres up --build -d --wait

up-sqlite:
	docker compose --profile sqlite up --build -d --wait

down:
	docker compose --profile postgres --profile sqlite down

down-clean:
	docker compose --profile postgres --profile sqlite down -v

logs:
	docker compose logs -f app

ps:
	docker compose ps

shell:
	docker compose exec app sh

migrate:
	docker compose exec app alembic upgrade head
