"""
Configurações centralizadas da aplicação via variáveis de ambiente.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _int(key: str, default: int) -> int:
    return int(os.getenv(key, default))


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: _int("DB_PORT", 5432))
    name: str = field(default_factory=lambda: os.getenv("DB_NAME", "efisco_analitico"))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))

    @property
    def url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class GovBrConfig:
    cpf: str = field(default_factory=lambda: os.getenv("GOVBR_CPF", ""))
    senha: str = field(default_factory=lambda: os.getenv("GOVBR_SENHA", ""))


@dataclass(frozen=True)
class ColetaConfig:
    unidade_gestora: str = field(
        default_factory=lambda: os.getenv("UNIDADE_GESTORA", "")
    )
    # "1313:2115,4685:1958,4685:1959,4685:1960,3929:0000"
    _acoes_subacoes_raw: str = field(
        default_factory=lambda: os.getenv("ACOES_SUBACOES", "")
    )
    # "subsidios,credito de vale transporte,Prog. Parcerias Público Privadas,TODOS"
    _detalhamentos_raw: str = field(
        default_factory=lambda: os.getenv("DETALHAMENTOS_GERENCIAIS", "TODOS")
    )

    @property
    def acoes_subacoes(self) -> list[tuple[str, str]]:
        """
        Retorna lista de pares (acao, subacao) parseados da variável de ambiente.

        Formato: ACAO:SUBACAO,ACAO:SUBACAO,...
        """
        if not self._acoes_subacoes_raw:
            return []
        pares: list[tuple[str, str]] = []
        for item in self._acoes_subacoes_raw.split(","):
            partes = item.strip().split(":")
            if len(partes) == 2:
                pares.append((partes[0].strip(), partes[1].strip()))
            else:
                pass  # Formato inválido — ignorado
        return pares

    @property
    def detalhamentos_gerenciais(self) -> list[str]:
        """
        Retorna lista de termos de busca para o Detalhamento da Despesa Gerencial.

        'TODOS' instrui o scraper a iterar sobre todas as opções do select.
        """
        return [d.strip() for d in self._detalhamentos_raw.split(",") if d.strip()]

    @property
    def coletar_todos_detalhamentos(self) -> bool:
        """True quando 'TODOS' está na lista de detalhamentos."""
        return any(d.upper() == "TODOS" for d in self.detalhamentos_gerenciais)


@dataclass(frozen=True)
class PlaywrightConfig:
    headless: bool = field(default_factory=lambda: _bool("HEADLESS", True))
    timeout: int = field(default_factory=lambda: _int("TIMEOUT_PADRAO", 30_000))
    timeout_navegacao: int = field(
        default_factory=lambda: _int("TIMEOUT_NAVEGACAO", 60_000)
    )
    slow_mo: int = field(default_factory=lambda: _int("SLOW_MO", 0))
    max_tentativas: int = field(default_factory=lambda: _int("MAX_TENTATIVAS", 3))
    espera_entre_tentativas: int = field(
        default_factory=lambda: _int("ESPERA_ENTRE_TENTATIVAS", 5)
    )


@dataclass(frozen=True)
class ExportConfig:
    diretorio: Path = field(
        default_factory=lambda: BASE_DIR / os.getenv("DIRETORIO_EXPORTS", "exports")
    )
    gerar_csv: bool = field(default_factory=lambda: _bool("GERAR_CSV", True))
    gerar_excel: bool = field(default_factory=lambda: _bool("GERAR_EXCEL", True))


@dataclass(frozen=True)
class LogConfig:
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = field(
        default_factory=lambda: BASE_DIR / os.getenv("LOG_DIR", "logs")
    )
    screenshot_dir: Path = field(
        default_factory=lambda: BASE_DIR / os.getenv("SCREENSHOT_DIR", "screenshots")
    )


@dataclass(frozen=True)
class Settings:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    govbr: GovBrConfig = field(default_factory=GovBrConfig)
    coleta: ColetaConfig = field(default_factory=ColetaConfig)
    playwright: PlaywrightConfig = field(default_factory=PlaywrightConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    log: LogConfig = field(default_factory=LogConfig)


# Singleton de configurações utilizado por toda a aplicação
settings = Settings()
