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
	@echo "  make planilha         Injeta dados na planilha operacional"
	@echo "  make docker-agendador Inicia agendador no container"

# -----------------------------------------------------------------------
install:
	$(PIP) install -r requirements.txt

install-browsers:
	python3 -m playwright install chromium || \
	  (echo "⚠  Download do Chromium bloqueado pela rede." && \
	   echo "   Usando binário local: $$(cat .env | grep PLAYWRIGHT_CHROME_PATH | cut -d= -f2)" && \
	   python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True,args=['--no-sandbox'],executable_path='$$(grep PLAYWRIGHT_CHROME_PATH .env | cut -d= -f2)'); b.close(); p.stop(); print('   Chromium OK.')" 2>/dev/null || \
	   echo "   PLAYWRIGHT_CHROME_PATH não configurado — configure o .env na máquina local.")

setup: install install-browsers

# -----------------------------------------------------------------------
db-init:
	$(PYTHON) main.py --inicializar-db

coleta:
	$(PYTHON) main.py

agendador:
	$(PYTHON) scheduler/agendador.py

planilha:
	$(PYTHON) main.py --exportar-planilha

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
