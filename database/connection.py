"""
Gerenciamento de conexão com o PostgreSQL via SQLAlchemy 2.x.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from database.models import Base
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Engine singleton (thread-safe com pool interno)
_engine = create_engine(
    settings.database.url,
    pool_pre_ping=True,      # Valida conexões do pool antes de usar
    pool_size=5,
    max_overflow=10,
    echo=False,
)

_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


def criar_tabelas() -> None:
    """Cria todas as tabelas mapeadas caso ainda não existam."""
    logger.info("Verificando/criando tabelas no banco de dados…")
    Base.metadata.create_all(_engine)
    logger.info("Estrutura de tabelas OK.")


def testar_conexao() -> bool:
    """
    Executa um SELECT 1 para validar conectividade.

    Returns:
        True se a conexão estiver operacional, False caso contrário.
    """
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com banco de dados estabelecida com sucesso.")
        return True
    except Exception as exc:
        logger.error("Falha ao conectar no banco de dados: %s", exc)
        return False


@contextmanager
def obter_sessao() -> Generator[Session, None, None]:
    """
    Context manager que fornece uma Session transacional.

    Faz rollback automaticamente em caso de exceção e fecha a sessão ao sair.

    Yields:
        Session ativa.
    """
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
