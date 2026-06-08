"""
Scraper para a consulta 'Ficha Financeira Detalhada' do e-Fisco.

Fluxo:
    1. Navega até o menu da consulta
    2. Seleciona o Tipo de Despesa Gerencial
    3. Clica em Localizar → obtém lista de fichas
    4. Para cada ficha: seleciona e clica em Detalhar
    5. Extrai os dados do detalhamento (cabeçalho + valores financeiros)
    6. Retorna e itera para a próxima ficha
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from config.settings import settings
from scraper.base_scraper import BaseScraper
from utils.helpers import limpar_valor_monetario
from utils.logger import setup_logger

logger = setup_logger(__name__)

# -----------------------------------------------------------------------
# Seletores
# -----------------------------------------------------------------------
SEL_MENU_FICHA       = "a:has-text('Ficha Financeira Detalhada')"
SEL_TIPO_DESPESA     = "select#tipoDespesaGerencial, select[name='tipoDespesaGerencial']"
SEL_BTN_LOCALIZAR    = "input[type='submit'][value='Localizar'], button:has-text('Localizar')"
SEL_TABELA_FICHAS    = "table#tabelaFichas, table.lista-fichas"
SEL_RADIO_FICHA      = "input[type='radio'][name='fichaId']"
SEL_BTN_DETALHAR     = "input[value='Detalhar'], button:has-text('Detalhar')"
SEL_TABELA_DETALHE   = "table#tabelaDetalhe, table.detalhe-ficha"
SEL_CAMPO_LABEL      = "td.label, th.label"
SEL_CAMPO_VALOR      = "td.valor, td.value"
SEL_BTN_VOLTAR       = "input[value='Voltar'], button:has-text('Voltar'), a:has-text('Voltar')"
SEL_PROXIMA_PAG      = "a[title='Próxima página'], a.proxima-pagina"

# Rótulos esperados na tela de detalhamento (normalizado para lower)
_MAPA_LABELS: dict[str, str] = {
    "exercício":                   "exercicio",
    "exercicio":                   "exercicio",
    "unidade gestora":             "unidade_gestora",
    "gestão":                      "gestao",
    "gestao":                      "gestao",
    "grupo de despesa":            "grupo_despesa",
    "fonte de recurso":            "fonte_recurso",
    "natureza da despesa":         "natureza_despesa",
    "dea":                         "dea",
    "detalhamento da despesa gerencial": "detalhamento_despesa",
    "destinação do recurso":       "destinacao_recurso",
    "destinacao do recurso":       "destinacao_recurso",
    "situação":                    "situacao",
    "situacao":                    "situacao",
    "dotação inicial":             "dotacao_inicial",
    "dotacao inicial":             "dotacao_inicial",
    "dotação atual":               "dotacao_atual",
    "dotacao atual":               "dotacao_atual",
    "valor empenhado":             "valor_empenhado",
    "valor liquidado":             "valor_liquidado",
    "valor pago":                  "valor_pago",
    "saldo":                       "saldo",
}

_CAMPOS_MONETARIOS = {
    "dotacao_inicial", "dotacao_atual",
    "valor_empenhado", "valor_liquidado", "valor_pago", "saldo",
}


class FichaFinanceiraScraper:
    """
    Extrai dados da Ficha Financeira Detalhada do e-Fisco.

    Args:
        scraper: Instância de BaseScraper já autenticada.
    """

    def __init__(self, scraper: BaseScraper) -> None:
        self._scraper = scraper

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def coletar(
        self,
        tipo_despesa_gerencial: str = "TODAS",
        data_coleta: date | None = None,
    ) -> list[dict]:
        """
        Executa a consulta de Ficha Financeira Detalhada.

        Args:
            tipo_despesa_gerencial: Valor do select de tipo de despesa.
            data_coleta:            Data de referência (padrão: hoje).

        Returns:
            Lista de dicionários prontos para persistência em
            fato_ficha_financeira.
        """
        data_coleta = data_coleta or date.today()
        logger.info(
            "Coletando Ficha Financeira – Tipo=%s", tipo_despesa_gerencial
        )

        self._navegar_para_consulta()
        self._selecionar_tipo_despesa(tipo_despesa_gerencial)
        self._executar_busca()

        registros = self._percorrer_fichas(data_coleta)

        logger.info(
            "Coleta de fichas concluída: %d registros.", len(registros)
        )
        return registros

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _navegar_para_consulta(self) -> None:
        logger.debug("Navegando para Ficha Financeira Detalhada…")
        try:
            self._scraper.aguardar_seletor(SEL_MENU_FICHA, timeout=15_000)
            self._scraper.clicar_com_retry(SEL_MENU_FICHA)
            self._scraper.page.wait_for_load_state("networkidle")
        except Exception as exc:
            self._scraper.capturar_screenshot("erro_menu_ficha")
            raise RuntimeError(
                f"Não foi possível navegar até Ficha Financeira: {exc}"
            ) from exc

    def _selecionar_tipo_despesa(self, tipo: str) -> None:
        logger.debug("Selecionando tipo de despesa gerencial: %s", tipo)
        try:
            self._scraper.aguardar_seletor(SEL_TIPO_DESPESA)
            self._scraper.page.select_option(SEL_TIPO_DESPESA, label=tipo)
        except Exception:
            # Tenta por value se label não funcionar
            try:
                self._scraper.page.select_option(SEL_TIPO_DESPESA, value=tipo)
            except Exception as exc:
                logger.warning(
                    "Não foi possível selecionar tipo de despesa %r: %s", tipo, exc
                )

    def _executar_busca(self) -> None:
        logger.debug("Executando busca de fichas…")
        self._scraper.clicar_com_retry(SEL_BTN_LOCALIZAR)
        self._scraper.page.wait_for_load_state("networkidle")

    # ------------------------------------------------------------------
    # Iteração sobre fichas
    # ------------------------------------------------------------------

    def _percorrer_fichas(self, data_coleta: date) -> list[dict]:
        """
        Percorre todas as fichas listadas (com paginação) e detalha cada uma.
        """
        todos: list[dict] = []
        pagina = 1

        while True:
            logger.info("Processando lista de fichas – página %d…", pagina)
            ids_fichas = self._obter_ids_fichas_pagina()

            for ficha_id in ids_fichas:
                try:
                    registro = self._detalhar_ficha(ficha_id, data_coleta)
                    if registro:
                        todos.append(registro)
                except Exception as exc:
                    logger.error(
                        "Erro ao detalhar ficha %s: %s", ficha_id, exc
                    )
                    self._scraper.capturar_screenshot(f"erro_ficha_{ficha_id}")
                    # Tenta retornar para a lista de fichas
                    self._voltar_para_lista()

            if not self._scraper.tem_proxima_pagina(SEL_PROXIMA_PAG):
                break
            self._scraper.ir_para_proxima_pagina(SEL_PROXIMA_PAG)
            pagina += 1

        return todos

    def _obter_ids_fichas_pagina(self) -> list[str]:
        """
        Coleta os valores dos radio buttons da lista de fichas na página atual.
        """
        radios = self._scraper.page.query_selector_all(SEL_RADIO_FICHA)
        ids = [
            r.get_attribute("value") or ""
            for r in radios
            if r.get_attribute("value")
        ]
        logger.debug("Fichas encontradas na página: %s", ids)
        return ids

    def _detalhar_ficha(self, ficha_id: str, data_coleta: date) -> dict | None:
        """
        Seleciona uma ficha pelo radio button, clica em Detalhar e extrai dados.

        Returns:
            Dicionário com os dados ou None se não for possível extrair.
        """
        logger.debug("Detalhando ficha: %s", ficha_id)

        # Seleciona o radio da ficha
        seletor_radio = f"input[type='radio'][value='{ficha_id}']"
        try:
            self._scraper.page.check(seletor_radio)
        except Exception as exc:
            logger.warning("Não foi possível selecionar ficha %s: %s", ficha_id, exc)
            return None

        # Clica em Detalhar
        self._scraper.clicar_com_retry(SEL_BTN_DETALHAR)
        self._scraper.page.wait_for_load_state("networkidle")

        # Extrai os dados do detalhamento
        dados = self._extrair_detalhamento(ficha_id, data_coleta)

        # Retorna para a lista de fichas
        self._voltar_para_lista()

        return dados

    def _extrair_detalhamento(
        self, ficha_id: str, data_coleta: date
    ) -> dict[str, Any]:
        """
        Lê os campos label/valor da tela de detalhamento da ficha.

        Estratégia: busca pares (label, valor) em células da tabela e
        também tenta extrair a tabela de movimentações financeiras.
        """
        registro: dict[str, Any] = {
            "data_coleta": data_coleta,
            "ficha_id":    ficha_id,
            "exercicio":   "",
            "unidade_gestora":      None,
            "gestao":               None,
            "grupo_despesa":        None,
            "fonte_recurso":        None,
            "natureza_despesa":     None,
            "dea":                  None,
            "detalhamento_despesa": None,
            "destinacao_recurso":   None,
            "situacao":             None,
            "dotacao_inicial":      limpar_valor_monetario("0"),
            "dotacao_atual":        limpar_valor_monetario("0"),
            "valor_empenhado":      limpar_valor_monetario("0"),
            "valor_liquidado":      limpar_valor_monetario("0"),
            "valor_pago":           limpar_valor_monetario("0"),
            "saldo":                limpar_valor_monetario("0"),
            "updated_at":           datetime.now(),
        }

        # Extrai pares label/valor de toda a página
        todos_labels = self._scraper.page.query_selector_all(SEL_CAMPO_LABEL)
        todos_valores = self._scraper.page.query_selector_all(SEL_CAMPO_VALOR)

        for label_el, valor_el in zip(todos_labels, todos_valores):
            label_txt = label_el.inner_text().strip().lower().rstrip(":")
            valor_txt = valor_el.inner_text().strip()

            campo = _MAPA_LABELS.get(label_txt)
            if not campo:
                continue

            if campo in _CAMPOS_MONETARIOS:
                registro[campo] = limpar_valor_monetario(valor_txt)
            else:
                registro[campo] = valor_txt or None

        # Tenta também extrair via tabela HTML se existir
        linhas_tabela = self._scraper.extrair_tabela_html(SEL_TABELA_DETALHE)
        for linha in linhas_tabela:
            for chave_html, valor_html in linha.items():
                campo = _MAPA_LABELS.get(chave_html.lower().rstrip(":"))
                if not campo:
                    continue
                if campo in _CAMPOS_MONETARIOS:
                    registro[campo] = limpar_valor_monetario(valor_html)
                else:
                    registro[campo] = valor_html.strip() or None

        return registro

    def _voltar_para_lista(self) -> None:
        """Retorna para a tela de listagem de fichas."""
        try:
            self._scraper.clicar_com_retry(SEL_BTN_VOLTAR)
            self._scraper.page.wait_for_load_state("networkidle")
        except Exception as exc:
            logger.warning("Erro ao clicar em Voltar: %s", exc)
            # Fallback: usa histórico do browser
            self._scraper.page.go_back()
            self._scraper.page.wait_for_load_state("networkidle")
