"""
Exportação de DataFrames para CSV.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.helpers import garantir_diretorio, timestamp_arquivo
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CsvExporter:
    """Exporta um DataFrame Pandas para arquivo CSV."""

    def __init__(self, diretorio: Path) -> None:
        self._dir = garantir_diretorio(diretorio)

    def exportar(self, df: pd.DataFrame, nome_base: str) -> Path:
        """
        Salva *df* em CSV no diretório configurado.

        Args:
            df:        DataFrame a exportar.
            nome_base: Prefixo do nome do arquivo (sem extensão).

        Returns:
            Path do arquivo gerado.
        """
        if df.empty:
            logger.warning("DataFrame vazio; CSV não será gerado para '%s'.", nome_base)
            return self._dir / f"{nome_base}_vazio.csv"

        caminho = self._dir / f"{nome_base}_{timestamp_arquivo()}.csv"
        df.to_csv(caminho, index=False, encoding="utf-8-sig", sep=";")
        logger.info("CSV exportado: %s (%d linhas)", caminho, len(df))
        return caminho
