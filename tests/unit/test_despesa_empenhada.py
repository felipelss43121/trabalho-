"""
Testes unitários para scraper/despesa_empenhada.py
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scraper.despesa_empenhada import DespesaEmpenhadaScraper


def _scraper_mock():
    """Retorna um BaseScraper completamente mockado."""
    scraper = MagicMock()
    scraper.page = MagicMock()
    scraper.page.query_selector.return_value = None  # sem "sem resultados"
    return scraper


class TestDespesaEmpenhadaScraper:
    def test_mapear_linha_valida(self):
        scraper = DespesaEmpenhadaScraper(_scraper_mock())
        linha = {
            "Data do Empenho": "10/03/2024",
            "Credor": "FORNECEDOR LTDA",
            "Valor Empenhado no Item de Gasto": "R$ 1.000,00",
            "Valor Empenhado Atual": "R$ 2.000,00",
            "Valor Liquidado Atual": "R$ 500,00",
            "Valor Pago Atual": "R$ 300,00",
        }
        resultado = scraper._mapear_linha(
            linha, "UG001", "1234", "001", date(2024, 3, 10)
        )
        assert resultado is not None
        assert resultado["credor"] == "FORNECEDOR LTDA"
        assert resultado["valor_empenhado"] == Decimal("2000.00")
        assert resultado["valor_pago"] == Decimal("300.00")
        assert resultado["data_empenho"] == date(2024, 3, 10)

    def test_mapear_linha_total_ignorada(self):
        """Linhas com 'total' na data devem ser descartadas."""
        scraper = DespesaEmpenhadaScraper(_scraper_mock())
        linha = {
            "Data do Empenho": "Total Geral",
            "Credor": "",
            "Valor Empenhado no Item de Gasto": "100.000,00",
            "Valor Empenhado Atual": "100.000,00",
            "Valor Liquidado Atual": "50.000,00",
            "Valor Pago Atual": "30.000,00",
        }
        resultado = scraper._mapear_linha(
            linha, "UG001", "1234", "001", date.today()
        )
        assert resultado is None

    def test_mapear_linha_valores_vazios_viram_zero(self):
        scraper = DespesaEmpenhadaScraper(_scraper_mock())
        linha = {
            "Data do Empenho": "10/03/2024",
            "Credor": "ABC",
            "Valor Empenhado no Item de Gasto": "-",
            "Valor Empenhado Atual": "",
            "Valor Liquidado Atual": "N/A",
            "Valor Pago Atual": "0,00",
        }
        resultado = scraper._mapear_linha(
            linha, "UG001", "1234", "001", date.today()
        )
        assert resultado["valor_empenhado_item"] == Decimal("0")
        assert resultado["valor_empenhado"] == Decimal("0")
        assert resultado["valor_liquidado"] == Decimal("0")
        assert resultado["valor_pago"] == Decimal("0.00")
