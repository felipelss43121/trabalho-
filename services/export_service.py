"""
Service Layer: geração dos arquivos de exportação (CSV e Excel).

Consulta o banco de dados para a data solicitada e gera os arquivos
nas saídas configuradas.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import settings
from database.connection import obter_sessao
from database.models import FatoEmpenho, FatoFichaFinanceira
from exporters.csv_exporter import CsvExporter
from exporters.excel_exporter import ExcelExporter
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ExportService:
    """
    Gera arquivos CSV e/ou Excel a partir dos dados persistidos no banco.
    """

    def __init__(self) -> None:
        export_dir = settings.export.diretorio
        self._csv = CsvExporter(export_dir)
        self._excel = ExcelExporter(export_dir)

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def exportar(self, data_coleta: date | None = None) -> list[Path]:
        """
        Gera arquivos de exportação para a data de coleta informada.

        Args:
            data_coleta: Data dos dados a exportar (padrão: hoje).

        Returns:
            Lista dos arquivos gerados.
        """
        data_coleta = data_coleta or date.today()
        logger.info("Iniciando exportação para data_coleta=%s…", data_coleta)

        df_empenho = self._carregar_empenhos(data_coleta)
        df_ficha = self._carregar_fichas(data_coleta)
        df_consolidado = self._gerar_consolidado(df_empenho)

        arquivos: list[Path] = []

        if settings.export.gerar_csv:
            arquivos += self._exportar_csvs(df_empenho, df_ficha, df_consolidado)

        if settings.export.gerar_excel:
            arquivos.append(
                self._exportar_excel(df_empenho, df_ficha, df_consolidado)
            )

        logger.info(
            "Exportação concluída: %d arquivo(s) gerado(s).", len(arquivos)
        )
        return arquivos

    # ------------------------------------------------------------------
    # Carga de dados
    # ------------------------------------------------------------------

    @staticmethod
    def _carregar_empenhos(data_coleta: date) -> pd.DataFrame:
        """Carrega fato_empenho para a data especificada."""
        with obter_sessao() as session:
            from sqlalchemy import select
            stmt = select(FatoEmpenho).where(FatoEmpenho.data_coleta == data_coleta)
            rows = session.scalars(stmt).all()

        if not rows:
            logger.warning("Sem registros de empenho para %s.", data_coleta)
            return pd.DataFrame()

        dados: list[dict[str, Any]] = [
            {
                "id":                   r.id,
                "data_coleta":          r.data_coleta,
                "unidade_gestora":      r.unidade_gestora,
                "acao":                 r.acao,
                "subacao":              r.subacao,
                "data_empenho":         r.data_empenho,
                "credor":               r.credor,
                "valor_empenhado_item": float(r.valor_empenhado_item),
                "valor_empenhado":      float(r.valor_empenhado),
                "valor_liquidado":      float(r.valor_liquidado),
                "valor_pago":           float(r.valor_pago),
            }
            for r in rows
        ]
        return pd.DataFrame(dados)

    @staticmethod
    def _carregar_fichas(data_coleta: date) -> pd.DataFrame:
        """Carrega fato_ficha_financeira para a data especificada."""
        with obter_sessao() as session:
            from sqlalchemy import select
            stmt = select(FatoFichaFinanceira).where(
                FatoFichaFinanceira.data_coleta == data_coleta
            )
            rows = session.scalars(stmt).all()

        if not rows:
            logger.warning("Sem registros de ficha para %s.", data_coleta)
            return pd.DataFrame()

        dados: list[dict[str, Any]] = [
            {
                "id":                   r.id,
                "data_coleta":          r.data_coleta,
                "ficha_id":             r.ficha_id,
                "exercicio":            r.exercicio,
                "unidade_gestora":      r.unidade_gestora,
                "gestao":               r.gestao,
                "grupo_despesa":        r.grupo_despesa,
                "fonte_recurso":        r.fonte_recurso,
                "natureza_despesa":     r.natureza_despesa,
                "dea":                  r.dea,
                "detalhamento_despesa": r.detalhamento_despesa,
                "destinacao_recurso":   r.destinacao_recurso,
                "situacao":             r.situacao,
                "dotacao_inicial":      float(r.dotacao_inicial),
                "dotacao_atual":        float(r.dotacao_atual),
                "valor_empenhado":      float(r.valor_empenhado),
                "valor_liquidado":      float(r.valor_liquidado),
                "valor_pago":           float(r.valor_pago),
                "saldo":                float(r.saldo),
            }
            for r in rows
        ]
        return pd.DataFrame(dados)

    # ------------------------------------------------------------------
    # Consolidado (view Power BI)
    # ------------------------------------------------------------------

    @staticmethod
    def _gerar_consolidado(df_empenho: pd.DataFrame) -> pd.DataFrame:
        """
        Recria localmente a lógica da view vw_execucao_orcamentaria.
        """
        if df_empenho.empty:
            return pd.DataFrame()

        grp = (
            df_empenho.groupby(
                ["unidade_gestora", "acao", "subacao", "data_coleta"],
                as_index=False,
            )
            .agg(
                total_empenhado=("valor_empenhado", "sum"),
                total_liquidado=("valor_liquidado", "sum"),
                total_pago=("valor_pago", "sum"),
            )
        )
        grp["saldo"] = grp["total_empenhado"] - grp["total_pago"]
        grp["pct_execucao"] = grp.apply(
            lambda r: round(r["total_pago"] / r["total_empenhado"] * 100, 2)
            if r["total_empenhado"] > 0
            else 0.0,
            axis=1,
        )
        return grp

    # ------------------------------------------------------------------
    # Geração de arquivos
    # ------------------------------------------------------------------

    def _exportar_csvs(
        self,
        df_empenho: pd.DataFrame,
        df_ficha: pd.DataFrame,
        df_consolidado: pd.DataFrame,
    ) -> list[Path]:
        arquivos: list[Path] = []
        arquivos.append(self._csv.exportar(df_empenho, "fato_empenho"))
        arquivos.append(self._csv.exportar(df_ficha, "fato_ficha_financeira"))
        arquivos.append(self._csv.exportar(df_consolidado, "consolidado_powerbi"))
        return arquivos

    def _exportar_excel(
        self,
        df_empenho: pd.DataFrame,
        df_ficha: pd.DataFrame,
        df_consolidado: pd.DataFrame,
    ) -> Path:
        return self._excel.exportar(
            {
                "Empenhos":      df_empenho,
                "Fichas":        df_ficha,
                "Consolidado":   df_consolidado,
            },
            nome_base="efisco_analitico",
        )
