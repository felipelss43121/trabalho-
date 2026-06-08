"""
Testes unitários para services/export_service.py
"""
from decimal import Decimal

import pandas as pd
import pytest

from services.export_service import ExportService


class TestGerarConsolidado:
    def test_consolidado_basico(self):
        df = pd.DataFrame([
            {
                "unidade_gestora": "UG001",
                "acao": "1234",
                "subacao": "001",
                "data_coleta": "2024-01-01",
                "valor_empenhado": 10000.0,
                "valor_liquidado": 5000.0,
                "valor_pago": 3000.0,
            },
            {
                "unidade_gestora": "UG001",
                "acao": "1234",
                "subacao": "001",
                "data_coleta": "2024-01-01",
                "valor_empenhado": 5000.0,
                "valor_liquidado": 2000.0,
                "valor_pago": 1000.0,
            },
        ])
        consolidado = ExportService._gerar_consolidado(df)

        assert len(consolidado) == 1
        assert consolidado.iloc[0]["total_empenhado"] == 15000.0
        assert consolidado.iloc[0]["total_pago"] == 4000.0
        assert consolidado.iloc[0]["saldo"] == 11000.0
        # pct_execucao = 4000 / 15000 * 100 ≈ 26.67
        assert consolidado.iloc[0]["pct_execucao"] == pytest.approx(26.67, abs=0.01)

    def test_consolidado_empenhado_zero_nao_divide(self):
        """Não deve lançar ZeroDivisionError quando empenhado = 0."""
        df = pd.DataFrame([
            {
                "unidade_gestora": "UG002",
                "acao": "9999",
                "subacao": "001",
                "data_coleta": "2024-01-01",
                "valor_empenhado": 0.0,
                "valor_liquidado": 0.0,
                "valor_pago": 0.0,
            }
        ])
        consolidado = ExportService._gerar_consolidado(df)
        assert consolidado.iloc[0]["pct_execucao"] == 0.0

    def test_consolidado_vazio_retorna_df_vazio(self):
        consolidado = ExportService._gerar_consolidado(pd.DataFrame())
        assert consolidado.empty

    def test_consolidado_agrupa_multiplas_ugs(self):
        df = pd.DataFrame([
            {
                "unidade_gestora": "UG001", "acao": "1234", "subacao": "001",
                "data_coleta": "2024-01-01",
                "valor_empenhado": 1000.0, "valor_liquidado": 500.0, "valor_pago": 200.0,
            },
            {
                "unidade_gestora": "UG002", "acao": "5678", "subacao": "002",
                "data_coleta": "2024-01-01",
                "valor_empenhado": 2000.0, "valor_liquidado": 1000.0, "valor_pago": 800.0,
            },
        ])
        consolidado = ExportService._gerar_consolidado(df)
        assert len(consolidado) == 2
