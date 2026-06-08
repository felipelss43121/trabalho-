# e-Fisco Coletor — Automação de Dados Orçamentários

Aplicação Python para coleta automatizada de dados do portal **e-Fisco Pernambuco**, armazenamento em PostgreSQL e exportação para Power BI.

---

## Estrutura do Projeto

```
.
├── config/               # Configurações via variáveis de ambiente
├── database/
│   ├── models.py         # Modelos ORM (SQLAlchemy 2.x)
│   ├── connection.py     # Pool de conexões e session factory
│   ├── repository.py     # Repository Pattern (acesso a dados)
│   └── migrations/       # Scripts SQL de migração
├── scraper/
│   ├── base_scraper.py   # Browser Playwright, retry, screenshots
│   ├── auth.py           # Login Gov.br + e-Fisco
│   ├── despesa_empenhada.py
│   └── ficha_financeira.py
├── services/
│   ├── coleta_service.py # Orquestra scraping + persistência
│   └── export_service.py # Gera CSV e Excel
├── exporters/            # Implementações CSV e Excel
├── utils/                # Logger, helpers de conversão e retry
├── views/                # SQL das views para Power BI
├── main.py               # CLI principal
└── .env.example          # Template de variáveis de ambiente
```

---

## Pré-requisitos

- Python 3.12+
- PostgreSQL 14+
- Acesso autorizado ao e-Fisco Pernambuco via Gov.br

---

## Instalação

```bash
# 1. Clone o repositório
git clone <url>
cd efisco-coletor

# 2. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Instale os browsers do Playwright
playwright install chromium

# 5. Configure as variáveis de ambiente
cp .env.example .env
# edite .env com suas credenciais e parâmetros

# 6. Execute a migração do banco
psql -U postgres -d efisco_analitico -f database/migrations/001_initial_schema.sql

# Ou deixe a aplicação criar as tabelas:
python main.py --inicializar-db
```

---

## Uso

```bash
# Coleta completa (ambas as consultas) para hoje
python main.py

# Coleta para uma data específica
python main.py --data 2024-06-01

# Somente Despesa Empenhada
python main.py --apenas-empenho

# Somente Ficha Financeira
python main.py --apenas-ficha

# Apenas gerar exportações (dados já coletados)
python main.py --apenas-exportar

# Inicializar banco de dados
python main.py --inicializar-db
```

---

## Variáveis de Ambiente

| Variável                  | Descrição                              | Padrão         |
|---------------------------|----------------------------------------|----------------|
| `DB_HOST`                 | Host PostgreSQL                        | `localhost`    |
| `DB_PORT`                 | Porta PostgreSQL                       | `5432`         |
| `DB_NAME`                 | Nome do banco                          | `efisco_analitico` |
| `DB_USER`                 | Usuário do banco                       | `postgres`     |
| `DB_PASSWORD`             | Senha do banco                         | —              |
| `GOVBR_CPF`               | CPF para login Gov.br                  | —              |
| `GOVBR_SENHA`             | Senha Gov.br                           | —              |
| `UNIDADE_GESTORA`         | Código da UG a consultar               | —              |
| `ACAO`                    | Código da Ação orçamentária            | —              |
| `SUBACAO`                 | Código da Subação                      | —              |
| `TIPO_DESPESA_GERENCIAL`  | Filtro da Ficha Financeira             | `TODAS`        |
| `HEADLESS`                | Browser sem interface gráfica          | `true`         |
| `TIMEOUT_PADRAO`          | Timeout Playwright (ms)                | `30000`        |
| `MAX_TENTATIVAS`          | Retry máximo por operação              | `3`            |
| `GERAR_CSV`               | Gerar arquivos CSV                     | `true`         |
| `GERAR_EXCEL`             | Gerar arquivo Excel                    | `true`         |
| `LOG_LEVEL`               | Nível de log                           | `INFO`         |

---

## Power BI

Conecte o Power BI diretamente ao PostgreSQL usando as views:

| View                         | Conteúdo                                       |
|------------------------------|------------------------------------------------|
| `vw_execucao_orcamentaria`   | Execução por UG/Ação/Subação (consolidado)     |
| `vw_serie_temporal`          | Evolução diária dos valores                    |
| `vw_top_credores`            | Credores com maior volume empenhado            |
| `vw_fichas_por_natureza`     | Fichas por natureza de despesa                 |

---

## Agendamento interno (APScheduler)

Para rodar como serviço contínuo com disparo automático diário:

```bash
# Disparo às 06:00 (padrão)
python scheduler/agendador.py

# Horário customizado
python scheduler/agendador.py --hora 7 --minuto 30

# Executa imediatamente e depois agenda
python scheduler/agendador.py --executar-agora
```

---

## Docker

```bash
# Sobe apenas o PostgreSQL
make docker-up

# Executa coleta única no container
make docker-coleta

# Inicia agendador diário como serviço
make docker-agendador

# Para tudo
make docker-down
```

---

## Testes

```bash
# Instala dependências e roda testes unitários
make teste

# Testes de integração (requer PostgreSQL)
make teste-integracao

# Toda a suite
make teste-tudo

# Verificação de tipagem
make lint
```

Cobertura atual: helpers, schemas Pydantic, base scraper, scraper de empenho,
service de exportação e repositórios (integração).

---

## Validação de Dados

Antes de persistir, todo registro passa pela validação Pydantic
(`database/schemas.py`):

- Strings obrigatórias não podem ser vazias
- Valores monetários são `Decimal` com `>= 0` onde aplicável
- Strings opcionais em branco são normalizadas para `None`
- Campos de texto são truncados no limite da coluna
- Registros inválidos são descartados com log de warning

---

## Logs e Screenshots

- Logs: `logs/efisco_coleta.log` (rotação automática a cada 10 MB)
- Screenshots de erro: `screenshots/erro_<contexto>_<timestamp>.png`
