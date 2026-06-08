"""
Repository Pattern: camada de acesso a dados isolada da lógica de negócio.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database.connection import obter_sessao
from database.models import FatoEmpenho, FatoFichaFinanceira
from database.schemas import EmpenhoSchema, FichaFinanceiraSchema
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _validar_empenhos(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Valida cada registro via Pydantic, descartando os inválidos."""
    validos: list[dict[str, Any]] = []
    for i, rec in enumerate(registros):
        try:
            validos.append(EmpenhoSchema(**rec).model_dump())
        except ValidationError as exc:
            logger.warning("Registro de empenho %d inválido (descartado): %s", i, exc)
    return validos


def _validar_fichas(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Valida cada registro via Pydantic, descartando os inválidos."""
    validos: list[dict[str, Any]] = []
    for i, rec in enumerate(registros):
        try:
            validos.append(FichaFinanceiraSchema(**rec).model_dump())
        except ValidationError as exc:
            logger.warning("Registro de ficha %d inválido (descartado): %s", i, exc)
    return validos


class EmpenhoRepository:
    """Operações de persistência para a tabela fato_empenho."""

    @staticmethod
    def upsert(registros: list[dict[str, Any]]) -> int:
        """
        Insere novos registros ou atualiza os existentes pela chave de negócio.

        A chave composta é (data_coleta, unidade_gestora, acao, subacao,
        data_empenho, credor) — definida pela constraint uq_empenho_chave_negocio.

        Args:
            registros: Lista de dicionários com os campos de FatoEmpenho.

        Returns:
            Quantidade de linhas afetadas.
        """
        if not registros:
            return 0

        registros = _validar_empenhos(registros)
        if not registros:
            logger.warning("Nenhum registro de empenho válido após validação.")
            return 0

        with obter_sessao() as session:
            stmt = insert(FatoEmpenho).values(registros)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_empenho_chave_negocio",
                set_={
                    "valor_empenhado_item": stmt.excluded.valor_empenhado_item,
                    "valor_empenhado": stmt.excluded.valor_empenhado,
                    "valor_liquidado": stmt.excluded.valor_liquidado,
                    "valor_pago": stmt.excluded.valor_pago,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            result = session.execute(stmt)
            afetados = result.rowcount
            logger.info("fato_empenho: %d registros upserted.", afetados)
            return afetados

    @staticmethod
    def listar_por_data(data_coleta: date) -> list[FatoEmpenho]:
        """Retorna todos os registros de uma data de coleta específica."""
        with obter_sessao() as session:
            stmt = select(FatoEmpenho).where(FatoEmpenho.data_coleta == data_coleta)
            return list(session.scalars(stmt).all())

    @staticmethod
    def remover_duplicatas() -> int:
        """
        Remove registros duplicados mantendo apenas o de menor id para cada
        chave de negócio. Útil para limpeza manual do banco.

        Returns:
            Quantidade de linhas removidas.
        """
        sql = """
        DELETE FROM fato_empenho
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM fato_empenho
            GROUP BY data_coleta, unidade_gestora, acao, subacao,
                     data_empenho, credor
        )
        """
        with obter_sessao() as session:
            result = session.execute(__import__("sqlalchemy").text(sql))
            removidos = result.rowcount
            logger.info("fato_empenho: %d duplicatas removidas.", removidos)
            return removidos


class FichaFinanceiraRepository:
    """Operações de persistência para a tabela fato_ficha_financeira."""

    @staticmethod
    def upsert(registros: list[dict[str, Any]]) -> int:
        """
        Insere novos registros ou atualiza os existentes pela chave de negócio.

        A chave é (data_coleta, ficha_id, exercicio).

        Args:
            registros: Lista de dicionários com os campos de FatoFichaFinanceira.

        Returns:
            Quantidade de linhas afetadas.
        """
        if not registros:
            return 0

        registros = _validar_fichas(registros)
        if not registros:
            logger.warning("Nenhum registro de ficha válido após validação.")
            return 0

        with obter_sessao() as session:
            stmt = insert(FatoFichaFinanceira).values(registros)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_ficha_chave_negocio",
                set_={
                    "unidade_gestora": stmt.excluded.unidade_gestora,
                    "gestao": stmt.excluded.gestao,
                    "grupo_despesa": stmt.excluded.grupo_despesa,
                    "fonte_recurso": stmt.excluded.fonte_recurso,
                    "natureza_despesa": stmt.excluded.natureza_despesa,
                    "dea": stmt.excluded.dea,
                    "detalhamento_despesa": stmt.excluded.detalhamento_despesa,
                    "destinacao_recurso": stmt.excluded.destinacao_recurso,
                    "situacao": stmt.excluded.situacao,
                    "dotacao_inicial": stmt.excluded.dotacao_inicial,
                    "dotacao_atual": stmt.excluded.dotacao_atual,
                    "valor_empenhado": stmt.excluded.valor_empenhado,
                    "valor_liquidado": stmt.excluded.valor_liquidado,
                    "valor_pago": stmt.excluded.valor_pago,
                    "saldo": stmt.excluded.saldo,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            result = session.execute(stmt)
            afetados = result.rowcount
            logger.info("fato_ficha_financeira: %d registros upserted.", afetados)
            return afetados

    @staticmethod
    def listar_por_data(data_coleta: date) -> list[FatoFichaFinanceira]:
        """Retorna todos os registros de uma data de coleta específica."""
        with obter_sessao() as session:
            stmt = select(FatoFichaFinanceira).where(
                FatoFichaFinanceira.data_coleta == data_coleta
            )
            return list(session.scalars(stmt).all())

    @staticmethod
    def remover_duplicatas() -> int:
        """Remove registros duplicados mantendo apenas o de menor id."""
        sql = """
        DELETE FROM fato_ficha_financeira
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM fato_ficha_financeira
            GROUP BY data_coleta, ficha_id, exercicio
        )
        """
        with obter_sessao() as session:
            result = session.execute(__import__("sqlalchemy").text(sql))
            removidos = result.rowcount
            logger.info(
                "fato_ficha_financeira: %d duplicatas removidas.", removidos
            )
            return removidos
