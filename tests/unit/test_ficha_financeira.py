"""
Testes unitários para scraper/ficha_financeira.py
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scraper.ficha_financeira import FichaFinanceiraScraper


def _scraper_mock(opcoes_select: list[dict] | None = None):
    """Retorna BaseScraper mockado com select pré-configurado."""
    scraper = MagicMock()
    scraper.page = MagicMock()
    # _obter_opcoes_select retorna as opções injetadas
    scraper.page.query_selector_all.return_value = []
    return scraper


class TestFichaFinanceiraScraper:
    def test_coletar_todos_chama_todas_opcoes(self):
        """Quando TODOS está na lista, deve processar todas as opções do select."""
        scraper_mock = _scraper_mock()
        s = FichaFinanceiraScraper(scraper_mock)

        opcoes_fake = [
            {"value": "1", "label": "Subsídios"},
            {"value": "2", "label": "Vale Transporte"},
            {"value": "3", "label": "Parcerias"},
        ]

        with patch.object(s, "_navegar_para_consulta"), \
             patch.object(s, "_obter_opcoes_select", return_value=opcoes_fake), \
             patch.object(s, "_coletar_para_detalhamento", return_value=[]):

            resultado = s.coletar(detalhamentos=["TODOS"], data_coleta=date.today())
            assert s._coletar_para_detalhamento.call_count == 3

    def test_coletar_filtrado_por_termo(self):
        """Filtragem por correspondência parcial case-insensitive."""
        scraper_mock = _scraper_mock()
        s = FichaFinanceiraScraper(scraper_mock)

        opcoes_fake = [
            {"value": "1", "label": "Subsídios"},
            {"value": "2", "label": "Crédito de Vale Transporte"},
            {"value": "3", "label": "Parcerias Público Privadas"},
            {"value": "4", "label": "Pessoal"},
        ]

        with patch.object(s, "_navegar_para_consulta"), \
             patch.object(s, "_obter_opcoes_select", return_value=opcoes_fake), \
             patch.object(s, "_coletar_para_detalhamento", return_value=[]):

            # "subsidios" bate com "Subsídios" — não, pois não tem acento
            # Usa lowercase simples: "subsídios".lower() contém "subs"
            # Testamos com um termo que bate claramente
            s.coletar(
                detalhamentos=["Vale Transporte", "Parcerias"],
                data_coleta=date.today(),
            )
            # Deve chamar apenas para "Vale Transporte" e "Parcerias"
            assert s._coletar_para_detalhamento.call_count == 2

    def test_sem_opcoes_retorna_vazio(self):
        scraper_mock = _scraper_mock()
        s = FichaFinanceiraScraper(scraper_mock)

        with patch.object(s, "_navegar_para_consulta"), \
             patch.object(s, "_obter_opcoes_select", return_value=[]):

            resultado = s.coletar(detalhamentos=["TODOS"], data_coleta=date.today())
            assert resultado == []

    def test_nenhuma_opcao_correspondente_retorna_vazio(self):
        scraper_mock = _scraper_mock()
        s = FichaFinanceiraScraper(scraper_mock)

        opcoes_fake = [{"value": "1", "label": "Pessoal"}]

        with patch.object(s, "_navegar_para_consulta"), \
             patch.object(s, "_obter_opcoes_select", return_value=opcoes_fake), \
             patch.object(s, "_coletar_para_detalhamento", return_value=[]):

            resultado = s.coletar(
                detalhamentos=["subsidios"],  # não bate com "Pessoal"
                data_coleta=date.today(),
            )
            assert resultado == []
            s._coletar_para_detalhamento.assert_not_called()

    def test_todos_junto_com_especifico_coleta_tudo(self):
        """TODOS na lista → coleta todas as opções, ignora os outros termos."""
        scraper_mock = _scraper_mock()
        s = FichaFinanceiraScraper(scraper_mock)

        opcoes_fake = [
            {"value": "1", "label": "A"},
            {"value": "2", "label": "B"},
            {"value": "3", "label": "C"},
        ]

        with patch.object(s, "_navegar_para_consulta"), \
             patch.object(s, "_obter_opcoes_select", return_value=opcoes_fake), \
             patch.object(s, "_coletar_para_detalhamento", return_value=[]):

            s.coletar(
                detalhamentos=["subsidios", "TODOS"],
                data_coleta=date.today(),
            )
            assert s._coletar_para_detalhamento.call_count == 3
