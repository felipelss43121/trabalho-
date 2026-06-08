.PHONY: install install-browsers setup db-init coleta agendador teste lint docker-up docker-down docker-coleta docker-agendador help

PYTHON := python3
PIP    := python3 -m pip
PYTEST := python3 -m pytest

# -----------------------------------------------------------------------
help:
	@echo "Comandos disponíveis:"
	@echo "  make install          Instala dependências Python"
	@echo "  make install-browsers Instala browsers do Playwright"
	@echo "  make setup            install + install-browsers"
	@echo "  make db-init          Cria tabelas no banco de dados"
	@echo "  make coleta           Executa coleta completa (hoje)"
	@echo "  make agendador        Inicia agendador diário"
	@echo "  make teste            Executa suite de testes"
	@echo "  make lint             Verifica tipagem com mypy"
	@echo "  make docker-up        Sobe PostgreSQL via Docker"
	@echo "  make docker-down      Para e remove containers"
	@echo "  make docker-coleta    Executa coleta no container"
	@echo "  make docker-agendador Inicia agendador no container"

# -----------------------------------------------------------------------
install:
	$(PIP) install -r requirements.txt

install-browsers:
	playwright install chromium

setup: install install-browsers

# -----------------------------------------------------------------------
db-init:
	$(PYTHON) main.py --inicializar-db

coleta:
	$(PYTHON) main.py

agendador:
	$(PYTHON) scheduler/agendador.py

# -----------------------------------------------------------------------
teste:
	$(PYTEST) tests/unit/ -v --tb=short

teste-integracao:
	$(PYTEST) tests/integration/ -v --tb=short

teste-tudo:
	$(PYTEST) -v

lint:
	$(PYTHON) -m mypy . --ignore-missing-imports --no-strict-optional

# -----------------------------------------------------------------------
docker-up:
	docker compose up postgres -d

docker-down:
	docker compose down -v

docker-coleta:
	docker compose --profile coleta up coletor --build

docker-agendador:
	docker compose --profile agendador up agendador -d --build
