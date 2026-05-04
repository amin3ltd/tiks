COMPOSE ?= docker compose
SERVICE ?= web
PROD_COMPOSE ?= docker compose -f docker-compose.production.yml
PROD_ENV ?= .env.production
LOCAL_CONFIG ?= .tiks/local.cfg
PRODUCTION_CONFIG ?= .tiks/production.cfg
VENV_PYTHON ?= .venv/bin/python
VENV_GUNICORN ?= .venv/bin/gunicorn

.PHONY: install install-quick install-custom install-venv install-production run-local run-production migrate-local migrate-production shell-local createsuperuser-local doctor repo-check docker-install docker-start docker-stop docker-restart docker-logs docker-shell docker-createsuperuser docker-migrate docker-rebuild prod-init prod-config prod-build prod-start prod-stop prod-logs prod-shell prod-createsuperuser prod-migrate

install: install-quick

install-quick:
	@if command -v python3.11 >/dev/null 2>&1; then \
		python3 scripts/install.py --mode local --quick; \
	else \
		echo "python3.11 was not found, so local Docker install will be used instead."; \
		echo "Install Python 3.11 and run 'make install-venv' if you specifically want a virtualenv."; \
		$(COMPOSE) build; \
		$(COMPOSE) up -d db redis; \
		$(COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) migrate --noinput; \
	fi

install-custom:
	python3 scripts/install.py --mode local

install-venv:
	python3 scripts/install.py --mode local

install-production:
	python3 scripts/install.py --mode production

run-local:
	PRETIX_CONFIG_FILE=$(LOCAL_CONFIG) $(VENV_PYTHON) -m pretix runserver 0.0.0.0:8000

run-production:
	PRETIX_CONFIG_FILE=$(PRODUCTION_CONFIG) $(VENV_GUNICORN) pretix.wsgi --bind 127.0.0.1:8000 --workers 3 --max-requests 1200 --max-requests-jitter 50

migrate-local:
	PRETIX_CONFIG_FILE=$(LOCAL_CONFIG) $(VENV_PYTHON) -m pretix migrate --noinput

migrate-production:
	PRETIX_CONFIG_FILE=$(PRODUCTION_CONFIG) $(VENV_PYTHON) -m pretix migrate --noinput

shell-local:
	PRETIX_CONFIG_FILE=$(LOCAL_CONFIG) $(VENV_PYTHON) -m pretix shell

createsuperuser-local:
	PRETIX_CONFIG_FILE=$(LOCAL_CONFIG) $(VENV_PYTHON) -m pretix createsuperuser

docker-install:
	$(COMPOSE) build
	$(COMPOSE) up -d db redis
	$(COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) migrate --noinput

docker-start:
	$(COMPOSE) up -d

docker-stop:
	$(COMPOSE) down

docker-restart:
	$(COMPOSE) restart

docker-logs:
	$(COMPOSE) logs -f --tail=200

docker-shell:
	$(COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) shell

docker-createsuperuser:
	$(COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) createsuperuser

docker-migrate:
	$(COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) migrate --noinput

docker-rebuild:
	$(COMPOSE) build --no-cache

doctor:
	@echo "Host Python:"
	@python3 --version || true
	@if command -v python3.11 >/dev/null 2>&1; then python3.11 --version; else echo "python3.11: not found"; fi
	@echo "Node.js and npm:"
	@node --version || true
	@npm --version || true
	@echo "Docker:"
	@docker --version || true
	@$(COMPOSE) version || true
	@echo
	@echo "Run 'make install' for a quick local SQLite setup."
	@echo "Run 'make install-custom' if you want PostgreSQL or custom settings."
	@echo "The venv installer requires Python 3.11. Docker remains available as a fallback."

repo-check:
	python3 scripts/check_repo_ready.py

prod-init:
	@test -f .env.production || cp .env.production.example .env.production
	@echo "Created .env.production if it did not exist. Edit passwords and SMTP settings before prod-start."

prod-config:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) config

prod-build:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) build

prod-start:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) up -d

prod-stop:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) down

prod-logs:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) logs -f --tail=200

prod-shell:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) shell

prod-createsuperuser:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) createsuperuser

prod-migrate:
	TIKS_ENV_FILE=$(PROD_ENV) $(PROD_COMPOSE) run --rm -e AUTOMIGRATE=skip $(SERVICE) migrate --noinput
