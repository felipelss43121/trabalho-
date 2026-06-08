"""
Exportação de DataFrames para Excel (.xlsx) via OpenPyXL.
Gera planilha formatada com cabeçalho destacado e colunas ajustadas.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from utils.helpers import garantir_diretorio, timestamp_arquivo
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Cores do cabeçalho (verde escuro do padrão Sefaz-PE)
COR_FUNDO_CABECALHO = "1F4E79"
COR_TEXTO_CABECALHO = "FFFFFF"


class ExcelExporter:
    """Exporta DataFrames Pandas para planilhas Excel formatadas."""

    def __init__(self, diretorio: Path) -> None:
        self._dir = garantir_diretorio(diretorio)

    def exportar(
        self,
        dataframes: dict[str, pd.DataFrame],
        nome_base: str,
    ) -> Path:
        """
        Salva múltiplos DataFrames em abas de uma única planilha Excel.

        Args:
            dataframes: Dicionário {nome_aba: DataFrame}.
            nome_base:  Prefixo do arquivo (sem extensão).

        Returns:
            Path do arquivo gerado.
        """
        caminho = self._dir / f"{nome_base}_{timestamp_arquivo()}.xlsx"

        wb = Workbook()
        wb.remove(wb.active)  # Remove aba padrão vazia

        for nome_aba, df in dataframes.items():
            ws = wb.create_sheet(title=nome_aba[:31])  # Excel limita a 31 chars
            self._escrever_aba(ws, df)

        wb.save(caminho)
        logger.info(
            "Excel exportado: %s (%d abas)",
            caminho,
            len(dataframes),
        )
        return caminho

    # ------------------------------------------------------------------
    # Formatação interna
    # ------------------------------------------------------------------

    @staticmethod
    def _escrever_aba(ws, df: pd.DataFrame) -> None:
        """Escreve cabeçalho formatado e dados de *df* na worksheet *ws*."""
        if df.empty:
            ws.append(["(sem dados)"])
            return

        # Cabeçalho
        cabecalho_fill = PatternFill(
            fill_type="solid", fgColor=COR_FUNDO_CABECALHO
        )
        cabecalho_font = Font(color=COR_TEXTO_CABECALHO, bold=True)

        for col_idx, coluna in enumerate(df.columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=str(coluna))
            cell.fill = cabecalho_fill
            cell.font = cabecalho_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Dados
        for row_data in df.itertuples(index=False, name=None):
            ws.append(list(row_data))

        # Ajusta largura das colunas automaticamente
        for col_idx, coluna in enumerate(df.columns, start=1):
            max_len = max(
                len(str(coluna)),
                df[coluna].astype(str).str.len().max() if not df.empty else 0,
            )
            ws.column_dimensions[get_column_letter(col_idx)].width = min(
                max_len + 4, 60
            )
