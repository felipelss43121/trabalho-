"""
Scraper para a consulta 'Ficha Financeira Detalhada' do e-Fisco.

Fluxo:
    1. Navega até o menu da consulta
    2. Obtém todas as opções do select de Detalhamento da Despesa Gerencial
    3. Para cada opção configurada (ou todas, se TODOS):
       a. Seleciona a opção no select
       b. Clica em Localizar → obtém lista de fichas
       c. Para cada ficha: seleciona e clica em Detalhar
       d. Extrai os dados do detalhamento
    4. Retorna todos os registros coletados
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from scraper.base_scraper import BaseScraper
from utils.helpers import limpar_valor_monetario
from utils.logger import setup_logger

logger = setup_logger(__name__)

# -----------------------------------------------------------------------
# Seletores
# -----------------------------------------------------------------------
SEL_MENU_FICHA       = "a:has-text('Ficha Financeira Detalhada')"
SEL_SELECT_DETALH    = (
    "select#detalhamentoDespesaGerencial, "
    "select[name='detalhamentoDespesaGerencial'], "
    "select#tipoDespesaGerencial, "
    "select[name='tipoDespesaGerencial']"
)
SEL_BTN_LOCALIZAR    = "input[type='submit'][value='Localizar'], button:has-text('Localizar')"
SEL_RADIO_FICHA      = "input[type='radio'][name='fichaId']"
SEL_BTN_DETALHAR     = "input[value='Detalhar'], button:has-text('Detalhar')"
SEL_TABELA_DETALHE   = "table#tabelaDetalhe, table.detalhe-ficha"
SEL_CAMPO_LABEL      = "td.label, th.label"
SEL_CAMPO_VALOR      = "td.valor, td.value"
SEL_BTN_VOLTAR       = "input[value='Voltar'], button:has-text('Voltar'), a:has-text('Voltar')"
SEL_PROXIMA_PAG      = "a[title='Próxima página'], a.proxima-pagina"

# Rótulos do detalhamento → campos internos
_MAPA_LABELS: dict[str, str] = {
    "exercício":                         "exercicio",
    "exercicio":                         "exercicio",
    "unidade gestora":                   "unidade_gestora",
    "gestão":                            "gestao",
    "gestao":                            "gestao",
    "grupo de despesa":                  "grupo_despesa",
    "fonte de recurso":                  "fonte_recurso",
    "natureza da despesa":               "natureza_despesa",
    "dea":                               "dea",
    "detalhamento da despesa gerencial": "detalhamento_despesa",
    "destinação do recurso":             "destinacao_recurso",
    "destinacao do recurso":             "destinacao_recurso",
    "situação":                          "situacao",
    "situacao":                          "situacao",
    "dotação inicial":                   "dotacao_inicial",
    "dotacao inicial":                   "dotacao_inicial",
    "dotação atual":                     "dotacao_atual",
    "dotacao atual":                     "dotacao_atual",
    "valor empenhado":                   "valor_empenhado",
    "valor liquidado":                   "valor_liquidado",
    "valor pago":                        "valor_pago",
    "saldo":                             "saldo",
}

_CAMPOS_MONETARIOS = {
    "dotacao_inicial", "dotacao_atual",
    "valor_empenhado", "valor_liquidado", "valor_pago", "saldo",
}


class FichaFinanceiraScraper:
    """
    Extrai dados da Ficha Financeira Detalhada do e-Fisco.

    Suporta coleta de múltiplos detalhamentos em uma única sessão autenticada.

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
        detalhamentos: list[str] | None = None,
        data_coleta: date | None = None,
    ) -> list[dict]:
        """
        Executa a consulta para cada opção de Detalhamento da Despesa Gerencial.

        Args:
            detalhamentos: Lista de termos a buscar no select. Se contiver
                           'TODOS' (case-insensitive), itera sobre todas as
                           opções disponíveis.
            data_coleta:   Data de referência (padrão: hoje).

        Returns:
            Lista de dicionários prontos para fato_ficha_financeira.
        """
        data_coleta = data_coleta or date.today()
        detalhamentos = detalhamentos or ["TODOS"]
        buscar_todos = any(d.upper() == "TODOS" for d in detalhamentos)

        logger.info(
            "Coletando Ficha Financeira – detalhamentos=%s",
            "TODOS" if buscar_todos else detalhamentos,
        )

        self._navegar_para_consulta()

        # Obtém todas as opções disponíveis no select
        opcoes_disponiveis = self._obter_opcoes_select()
        logger.info(
            "%d opção(ões) disponíveis no select de Detalhamento.", len(opcoes_disponiveis)
        )

        # Decide quais opções processar
        if buscar_todos:
            opcoes_a_coletar = opcoes_disponiveis
        else:
            opcoes_a_coletar = [
                op for op in opcoes_disponiveis
                if any(termo.lower() in op["label"].lower() for termo in detalhamentos)
            ]
            logger.info(
                "%d opção(ões) correspondente(s) aos termos configurados.",
                len(opcoes_a_coletar),
            )

        if not opcoes_a_coletar:
            logger.warning(
                "Nenhuma opção encontrada para os detalhamentos: %s", detalhamentos
            )
            return []

        todos_registros: list[dict] = []
        for opcao in opcoes_a_coletar:
            logger.info("Processando detalhamento: '%s'", opcao["label"])
            registros = self._coletar_para_detalhamento(opcao, data_coleta)
            todos_registros.extend(registros)
            logger.info(
                "  → %d registro(s) coletados para '%s'.",
                len(registros),
                opcao["label"],
            )

        logger.info(
            "Ficha Financeira concluída: %d registro(s) total.", len(todos_registros)
        )
        return todos_registros

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

    # ------------------------------------------------------------------
    # Leitura das opções do select
    # ------------------------------------------------------------------

    def _obter_opcoes_select(self) -> list[dict[str, str]]:
        """
        Extrai todas as opções do select de Detalhamento da Despesa Gerencial.

        Returns:
            Lista de dicts com chaves 'value' e 'label'.
        """
        try:
            self._scraper.aguardar_seletor(SEL_SELECT_DETALH)
        except Exception:
            logger.warning("Select de Detalhamento não encontrado; retornando vazio.")
            return []

        opcoes_els = self._scraper.page.query_selector_all(
            f"{SEL_SELECT_DETALH} option"
        )
        opcoes: list[dict[str, str]] = []
        for el in opcoes_els:
            value = el.get_attribute("value") or ""
            label = el.inner_text().strip()
            # Ignora opção vazia/placeholder
            if not value or not label or label in {"-", "Selecione", "Todos"}:
                if label.lower() in {"todos", "selecione", ""}:
                    continue
            opcoes.append({"value": value, "label": label})

        return opcoes

    # ------------------------------------------------------------------
    # Coleta por detalhamento
    # ------------------------------------------------------------------

    def _coletar_para_detalhamento(
        self,
        opcao: dict[str, str],
        data_coleta: date,
    ) -> list[dict]:
        """
        Seleciona uma opção do select, localiza as fichas e as detalha.
        """
        # Seleciona a opção pelo value
        try:
            self._scraper.page.select_option(SEL_SELECT_DETALH, value=opcao["value"])
        except Exception:
            try:
                self._scraper.page.select_option(SEL_SELECT_DETALH, label=opcao["label"])
            except Exception as exc:
                logger.warning(
                    "Não foi possível selecionar '%s': %s", opcao["label"], exc
                )
                return []

        # Executa busca
        self._scraper.clicar_com_retry(SEL_BTN_LOCALIZAR)
        self._scraper.page.wait_for_load_state("networkidle")

        # Verifica se retornou resultados
        sem_resultado = self._scraper.page.query_selector(
            "td:has-text('Nenhum registro'), div.sem-resultado"
        )
        if sem_resultado:
            logger.debug("Sem fichas para detalhamento '%s'.", opcao["label"])
            return []

        return self._percorrer_fichas(data_coleta)

    def _percorrer_fichas(self, data_coleta: date) -> list[dict]:
        """Percorre a lista de fichas (com paginação) e detalha cada uma."""
        todos: list[dict] = []
        pagina = 1

        while True:
            logger.debug("Página de fichas %d…", pagina)
            ids_fichas = self._obter_ids_fichas_pagina()

            for ficha_id in ids_fichas:
                try:
                    registro = self._detalhar_ficha(ficha_id, data_coleta)
                    if registro:
                        todos.append(registro)
                except Exception as exc:
                    logger.error("Erro ao detalhar ficha %s: %s", ficha_id, exc)
                    self._scraper.capturar_screenshot(f"erro_ficha_{ficha_id}")
                    self._voltar_para_lista()

            if not self._scraper.tem_proxima_pagina(SEL_PROXIMA_PAG):
                break
            self._scraper.ir_para_proxima_pagina(SEL_PROXIMA_PAG)
            pagina += 1

        return todos

    def _obter_ids_fichas_pagina(self) -> list[str]:
        radios = self._scraper.page.query_selector_all(SEL_RADIO_FICHA)
        return [
            r.get_attribute("value") or ""
            for r in radios
            if r.get_attribute("value")
        ]

    def _detalhar_ficha(self, ficha_id: str, data_coleta: date) -> dict | None:
        seletor_radio = f"input[type='radio'][value='{ficha_id}']"
        try:
            self._scraper.page.check(seletor_radio)
        except Exception as exc:
            logger.warning("Não foi possível selecionar ficha %s: %s", ficha_id, exc)
            return None

        self._scraper.clicar_com_retry(SEL_BTN_DETALHAR)
        self._scraper.page.wait_for_load_state("networkidle")

        dados = self._extrair_detalhamento(ficha_id, data_coleta)
        self._voltar_para_lista()
        return dados

    def _extrair_detalhamento(
        self, ficha_id: str, data_coleta: date
    ) -> dict[str, Any]:
        registro: dict[str, Any] = {
            "data_coleta":          data_coleta,
            "ficha_id":             ficha_id,
            "exercicio":            "",
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

        # Pares label/valor
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

        # Fallback: tabela HTML
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
        try:
            self._scraper.clicar_com_retry(SEL_BTN_VOLTAR)
            self._scraper.page.wait_for_load_state("networkidle")
        except Exception as exc:
            logger.warning("Erro ao clicar em Voltar: %s", exc)
            self._scraper.page.go_back()
            self._scraper.page.wait_for_load_state("networkidle")
