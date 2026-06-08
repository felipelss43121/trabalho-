"""
Scraper para a consulta 'Despesa Empenhada por Unidade Gestora' do e-Fisco.

Fluxo:
    1. Navega até o menu da consulta
    2. Preenche UG, seleciona Empenho, informa Ação e Subação
    3. Clica em Localizar
    4. Percorre todas as páginas capturando as linhas
    5. Captura os totais do rodapé
"""
from __future__ import annotations

from datetime import date, datetime

from config.settings import settings
from scraper.base_scraper import BaseScraper
from utils.helpers import limpar_data, limpar_valor_monetario
from utils.logger import setup_logger

logger = setup_logger(__name__)

# -----------------------------------------------------------------------
# Seletores (ajustar conforme o HTML real do e-Fisco)
# -----------------------------------------------------------------------
SEL_MENU_DESPESA   = "a:has-text('Despesa Empenhada por Unidade Gestora')"
SEL_CAMPO_UG       = "input#unidadeGestora, input[name='unidadeGestora']"
SEL_RADIO_EMPENHO  = "input[type='radio'][value='empenho'], input#tipoEmpenho"
SEL_CAMPO_ACAO     = "input#acao, input[name='acao']"
SEL_CAMPO_SUBACAO  = "input#subacao, input[name='subacao']"
SEL_BTN_LOCALIZAR  = "input[type='submit'][value='Localizar'], button:has-text('Localizar')"
SEL_TABELA         = "table#tabelaResultado, table.resultado, table.tabela-empenho"
SEL_RODAPE_TOTAIS  = "tr.totais, tr.rodape, tfoot tr"
SEL_PROXIMA_PAG    = "a[title='Próxima página'], a.proxima-pagina, a:has-text('Próxima')"

# Mapeamento de cabeçalhos HTML → campos internos
_MAPA_COLUNAS: dict[str, str] = {
    "Data do Empenho":                "data_empenho",
    "Credor":                         "credor",
    "Valor Empenhado no Item de Gasto": "valor_empenhado_item",
    "Valor Empenhado Atual":          "valor_empenhado",
    "Valor Liquidado Atual":          "valor_liquidado",
    "Valor Pago Atual":               "valor_pago",
}


class DespesaEmpenhadaScraper:
    """
    Extrai dados da consulta Despesa Empenhada por Unidade Gestora.

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
        unidade_gestora: str,
        acao: str,
        subacao: str,
        data_coleta: date | None = None,
    ) -> list[dict]:
        """
        Executa a consulta completa e retorna todos os registros coletados.

        Args:
            unidade_gestora: Código da UG a pesquisar.
            acao:            Código da Ação orçamentária.
            subacao:         Código da Subação.
            data_coleta:     Data de referência (padrão: hoje).

        Returns:
            Lista de dicionários prontos para persistência na fato_empenho.
        """
        data_coleta = data_coleta or date.today()
        logger.info(
            "Coletando Despesa Empenhada – UG=%s, Ação=%s, Subação=%s",
            unidade_gestora, acao, subacao,
        )

        self._navegar_para_consulta()
        self._preencher_formulario(unidade_gestora, acao, subacao)
        self._executar_busca()

        registros = self._percorrer_paginas(
            unidade_gestora, acao, subacao, data_coleta
        )

        logger.info(
            "Coleta concluída: %d registros extraídos.", len(registros)
        )
        return registros

    # ------------------------------------------------------------------
    # Navegação e formulário
    # ------------------------------------------------------------------

    def _navegar_para_consulta(self) -> None:
        """Clica no item de menu da consulta."""
        logger.debug("Navegando para Despesa Empenhada por UG…")
        try:
            self._scraper.aguardar_seletor(SEL_MENU_DESPESA, timeout=15_000)
            self._scraper.clicar_com_retry(SEL_MENU_DESPESA)
            self._scraper.page.wait_for_load_state("networkidle")
        except Exception as exc:
            self._scraper.capturar_screenshot("erro_menu_despesa")
            raise RuntimeError(
                f"Não foi possível navegar até a consulta de Despesa Empenhada: {exc}"
            ) from exc

    def _preencher_formulario(
        self, unidade_gestora: str, acao: str, subacao: str
    ) -> None:
        """Preenche todos os campos do formulário de pesquisa."""
        logger.debug("Preenchendo formulário de Despesa Empenhada…")

        self._scraper.aguardar_seletor(SEL_CAMPO_UG)
        self._scraper.preencher_campo(SEL_CAMPO_UG, unidade_gestora)

        # Seleciona o radio 'Empenho'
        try:
            self._scraper.page.check(SEL_RADIO_EMPENHO)
        except Exception:
            logger.warning("Não foi possível marcar radio 'Empenho'; tentando continuar…")

        self._scraper.preencher_campo(SEL_CAMPO_ACAO, acao)
        self._scraper.preencher_campo(SEL_CAMPO_SUBACAO, subacao)

    def _executar_busca(self) -> None:
        """Clica em Localizar e aguarda o carregamento dos resultados."""
        logger.debug("Clicando em Localizar…")
        self._scraper.clicar_com_retry(SEL_BTN_LOCALIZAR)
        self._scraper.page.wait_for_load_state("networkidle")

        # Verifica se houve mensagem de "sem resultados"
        sem_resultado = self._scraper.page.query_selector(
            "td:has-text('Nenhum registro'), div.sem-resultado"
        )
        if sem_resultado:
            logger.warning("Consulta retornou sem resultados para os filtros informados.")

    # ------------------------------------------------------------------
    # Extração de dados com paginação
    # ------------------------------------------------------------------

    def _percorrer_paginas(
        self,
        unidade_gestora: str,
        acao: str,
        subacao: str,
        data_coleta: date,
    ) -> list[dict]:
        """
        Percorre todas as páginas de resultado e acumula os registros.
        """
        todos: list[dict] = []
        pagina = 1

        while True:
            logger.info("Extraindo página %d…", pagina)
            linhas = self._extrair_pagina_atual(
                unidade_gestora, acao, subacao, data_coleta
            )
            todos.extend(linhas)

            if not self._scraper.tem_proxima_pagina(SEL_PROXIMA_PAG):
                break
            self._scraper.ir_para_proxima_pagina(SEL_PROXIMA_PAG)
            pagina += 1

        return todos

    def _extrair_pagina_atual(
        self,
        unidade_gestora: str,
        acao: str,
        subacao: str,
        data_coleta: date,
    ) -> list[dict]:
        """
        Lê a tabela da página atual e converte para dicionários de domínio.
        """
        linhas_html = self._scraper.extrair_tabela_html(SEL_TABELA)
        if not linhas_html:
            logger.warning("Nenhuma linha encontrada na tabela desta página.")
            return []

        registros: list[dict] = []
        for linha in linhas_html:
            registro = self._mapear_linha(
                linha, unidade_gestora, acao, subacao, data_coleta
            )
            if registro:
                registros.append(registro)

        return registros

    def _mapear_linha(
        self,
        linha: dict[str, str],
        unidade_gestora: str,
        acao: str,
        subacao: str,
        data_coleta: date,
    ) -> dict | None:
        """
        Converte um dicionário de linha HTML para o schema de fato_empenho.

        Retorna None se a linha parecer um rodapé de totais.
        """
        # Ignora linhas de total/rodapé que normalmente têm "Total" na data
        data_texto = linha.get(_col("Data do Empenho"), linha.get("Data do Empenho", ""))
        if "total" in data_texto.lower():
            return None

        return {
            "data_coleta":          data_coleta,
            "unidade_gestora":      unidade_gestora,
            "acao":                 acao,
            "subacao":              subacao,
            "data_empenho":         limpar_data(data_texto),
            "credor":               _texto(linha, "Credor"),
            "valor_empenhado_item": limpar_valor_monetario(
                _texto(linha, "Valor Empenhado no Item de Gasto")
            ),
            "valor_empenhado":      limpar_valor_monetario(
                _texto(linha, "Valor Empenhado Atual")
            ),
            "valor_liquidado":      limpar_valor_monetario(
                _texto(linha, "Valor Liquidado Atual")
            ),
            "valor_pago":           limpar_valor_monetario(
                _texto(linha, "Valor Pago Atual")
            ),
            "updated_at":           datetime.now(),
        }


# -----------------------------------------------------------------------
# Helpers locais
# -----------------------------------------------------------------------

def _col(nome: str) -> str:
    """Retorna o nome mapeado ou o próprio nome se não estiver no mapa."""
    return _MAPA_COLUNAS.get(nome, nome)


def _texto(linha: dict[str, str], chave: str) -> str:
    """Busca valor pelo cabeçalho original ou mapeado."""
    return linha.get(chave, linha.get(_MAPA_COLUNAS.get(chave, ""), "")).strip()
