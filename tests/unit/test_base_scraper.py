"""
Testes unitários para scraper/base_scraper.py
Usa mocks para não depender de browser real.
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scraper.base_scraper import BaseScraper


@pytest.fixture
def scraper_mockado():
    """Retorna um BaseScraper com o Playwright completamente mockado."""
    with patch("scraper.base_scraper.sync_playwright") as mock_pw:
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright

        mock_browser = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        s = BaseScraper()
        s.iniciar()
        yield s, mock_page
        s.encerrar()


class TestBaseScraper:
    def test_page_disponivel_apos_iniciar(self, scraper_mockado):
        scraper, _ = scraper_mockado
        assert scraper.page is not None

    def test_page_indisponivel_antes_de_iniciar(self):
        s = BaseScraper()
        with pytest.raises(RuntimeError, match="não iniciado"):
            _ = s.page

    def test_preencher_campo_chama_fill(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        scraper.preencher_campo("input#campo", "valor")
        assert mock_page.fill.call_count == 2  # limpa + preenche

    def test_extrair_tabela_html_sem_tabela(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        mock_page.query_selector.return_value = None
        resultado = scraper.extrair_tabela_html("table#inexistente")
        assert resultado == []

    def test_tem_proxima_pagina_false_sem_elemento(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        mock_page.query_selector.return_value = None
        assert scraper.tem_proxima_pagina() is False

    def test_tem_proxima_pagina_false_quando_disabled(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        elemento = MagicMock()
        elemento.get_attribute.return_value = "btn disabled"
        mock_page.query_selector.return_value = elemento
        assert scraper.tem_proxima_pagina() is False

    def test_tem_proxima_pagina_true(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        elemento = MagicMock()
        elemento.get_attribute.return_value = "btn proxima"
        mock_page.query_selector.return_value = elemento
        assert scraper.tem_proxima_pagina() is True

    def test_clicar_com_retry_sucesso(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        scraper.clicar_com_retry("button#ok", max_tentativas=3)
        mock_page.click.assert_called_once_with("button#ok")

    def test_clicar_com_retry_falha_levanta_excecao(self, scraper_mockado):
        scraper, mock_page = scraper_mockado
        mock_page.click.side_effect = Exception("elemento não encontrado")

        with pytest.raises(Exception, match="elemento não encontrado"):
            scraper.clicar_com_retry("button#inexistente", max_tentativas=2)

        assert mock_page.click.call_count == 2


class TestExtrairTabelaHtml:
    """Testa a extração de tabela HTML com estrutura mockada."""

    def test_extrai_linhas_corretamente(self, scraper_mockado):
        scraper, mock_page = scraper_mockado

        # Monta estrutura da tabela fake
        mock_table = MagicMock()

        th1, th2 = MagicMock(), MagicMock()
        th1.inner_text.return_value = "Data"
        th2.inner_text.return_value = "Valor"
        mock_table.query_selector_all.side_effect = lambda sel: (
            [th1, th2] if "thead" in sel else _linhas_mock()
        )

        mock_page.query_selector.return_value = mock_table

        resultado = scraper.extrair_tabela_html("table")
        assert len(resultado) == 2
        assert resultado[0]["Data"] == "01/01/2024"
        assert resultado[0]["Valor"] == "1.000,00"


def _linhas_mock():
    """Cria duas linhas de tabela mockadas."""
    linhas = []
    for data, valor in [("01/01/2024", "1.000,00"), ("02/01/2024", "2.000,00")]:
        tr = MagicMock()
        td1, td2 = MagicMock(), MagicMock()
        td1.inner_text.return_value = data
        td2.inner_text.return_value = valor
        tr.query_selector_all.return_value = [td1, td2]
        tr.inner_text.return_value = f"{data} {valor}"
        linhas.append(tr)
    return linhas
