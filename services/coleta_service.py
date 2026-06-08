"""
Service Layer: orquestra o fluxo completo de coleta do e-Fisco.

Responsabilidades:
    - Coordenar autenticação, scraping e persistência
    - Iterar sobre todos os pares Ação/Subação configurados
    - Iterar sobre todos os Detalhamentos da Ficha Financeira configurados
    - Isolar a lógica de negócio dos detalhes de infraestrutura
"""
from __future__ import annotations

from datetime import date

from config.settings import settings
from database.repository import EmpenhoRepository, FichaFinanceiraRepository
from scraper.auth import AutenticacaoEFisco
from scraper.base_scraper import BaseScraper
from scraper.despesa_empenhada import DespesaEmpenhadaScraper
from scraper.ficha_financeira import FichaFinanceiraScraper
from utils.helpers import retry
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ColetaService:
    """
    Orquestra a coleta de dados do e-Fisco e a persistência no PostgreSQL.

    Despesa Empenhada: percorre todos os pares (ação, subação) configurados
    em ACOES_SUBACOES, acumulando os registros antes de persistir.

    Ficha Financeira: percorre todos os detalhamentos configurados em
    DETALHAMENTOS_GERENCIAIS, coletando todas as fichas de cada um.
    """

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def executar_coleta_completa(self, data_coleta: date | None = None) -> dict:
        """
        Executa Consulta 1 (Despesa Empenhada) e Consulta 2 (Ficha Financeira)
        em sequência dentro do mesmo browser autenticado.

        Returns:
            Dicionário com contagens: {'empenhos': int, 'fichas': int}
        """
        data_coleta = data_coleta or date.today()
        logger.info("=== Iniciando coleta completa para %s ===", data_coleta)

        resultado: dict[str, int] = {"empenhos": 0, "fichas": 0}

        with BaseScraper() as scraper:
            AutenticacaoEFisco(scraper).autenticar()
            resultado["empenhos"] = self._coletar_despesa_empenhada(scraper, data_coleta)
            resultado["fichas"] = self._coletar_ficha_financeira(scraper, data_coleta)

        logger.info(
            "=== Coleta concluída: empenhos=%d, fichas=%d ===",
            resultado["empenhos"],
            resultado["fichas"],
        )
        return resultado

    def coletar_despesa_empenhada(self, data_coleta: date | None = None) -> int:
        """Executa apenas a Consulta 1 (Despesa Empenhada por UG)."""
        data_coleta = data_coleta or date.today()
        with BaseScraper() as scraper:
            AutenticacaoEFisco(scraper).autenticar()
            return self._coletar_despesa_empenhada(scraper, data_coleta)

    def coletar_ficha_financeira(self, data_coleta: date | None = None) -> int:
        """Executa apenas a Consulta 2 (Ficha Financeira Detalhada)."""
        data_coleta = data_coleta or date.today()
        with BaseScraper() as scraper:
            AutenticacaoEFisco(scraper).autenticar()
            return self._coletar_ficha_financeira(scraper, data_coleta)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _coletar_despesa_empenhada(
        self, scraper: BaseScraper, data_coleta: date
    ) -> int:
        """
        Itera sobre todos os pares (ação, subação) e persiste os registros.

        Unidade Gestora: settings.coleta.unidade_gestora (050501)
        Pares:           settings.coleta.acoes_subacoes
        """
        logger.info("--- Consulta 1: Despesa Empenhada por UG ---")
        sc = settings.coleta
        pares = sc.acoes_subacoes

        if not pares:
            logger.warning("Nenhum par Ação:Subação configurado (ACOES_SUBACOES vazio).")
            return 0

        logger.info(
            "UG=%s | %d par(es) Ação/Subação: %s",
            sc.unidade_gestora,
            len(pares),
            pares,
        )

        todos_registros: list[dict] = []
        s = DespesaEmpenhadaScraper(scraper)

        for acao, subacao in pares:
            logger.info("  Coletando Ação=%s Subação=%s…", acao, subacao)

            def _coletar(a=acao, sb=subacao) -> list[dict]:
                return s.coletar(
                    unidade_gestora=sc.unidade_gestora,
                    acao=a,
                    subacao=sb,
                    data_coleta=data_coleta,
                )

            registros = retry(
                _coletar,
                max_tentativas=settings.playwright.max_tentativas,
                espera_inicial=settings.playwright.espera_entre_tentativas,
            )
            logger.info(
                "  → %d registro(s) para Ação=%s Subação=%s.", len(registros), acao, subacao
            )
            todos_registros.extend(registros)

        afetados = EmpenhoRepository.upsert(todos_registros)
        logger.info("Total persistido em fato_empenho: %d registro(s).", afetados)
        return afetados

    def _coletar_ficha_financeira(
        self, scraper: BaseScraper, data_coleta: date
    ) -> int:
        """
        Coleta fichas financeiras para todos os detalhamentos configurados.

        Se DETALHAMENTOS_GERENCIAIS contiver 'TODOS', itera sobre todas as
        opções disponíveis no select do e-Fisco.
        """
        logger.info("--- Consulta 2: Ficha Financeira Detalhada ---")
        sc = settings.coleta
        detalhamentos = sc.detalhamentos_gerenciais

        logger.info(
            "Detalhamentos configurados: %s",
            "TODOS (todas as opções)" if sc.coletar_todos_detalhamentos else detalhamentos,
        )

        def _coletar() -> list[dict]:
            return FichaFinanceiraScraper(scraper).coletar(
                detalhamentos=detalhamentos,
                data_coleta=data_coleta,
            )

        registros = retry(
            _coletar,
            max_tentativas=settings.playwright.max_tentativas,
            espera_inicial=settings.playwright.espera_entre_tentativas,
        )

        afetados = FichaFinanceiraRepository.upsert(registros)
        logger.info(
            "Total persistido em fato_ficha_financeira: %d registro(s).", afetados
        )
        return afetados
