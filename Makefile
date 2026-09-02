.PHONY: install up logs down seed

install:
	export PATH="$$HOME/.local/bin:$$PATH"; \
	command -v mise >/dev/null 2>&1 || curl https://mise.run | sh; \
	mise install; \
	mise exec -- uv sync

up:
	docker compose up --build -d

logs:
	docker compose logs -f

down:
	docker compose down

seed:
	docker compose exec app uv run python manage.py seed
