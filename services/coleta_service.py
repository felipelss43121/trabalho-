"""
Service Layer: orquestra o fluxo completo de coleta do e-Fisco.

Responsabilidades:
    - Coordenar autenticação, scraping e persistência
    - Isolar a lógica de negócio dos detalhes de infraestrutura
    - Garantir log e tratamento de erros de ponta a ponta
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

    Cada método público executa uma consulta independente. O método
    `executar_coleta_completa` executa as duas em sequência dentro de uma
    única sessão de browser.
    """

    def __init__(self) -> None:
        self._empenho_repo = EmpenhoRepository()
        self._ficha_repo = FichaFinanceiraRepository()

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def executar_coleta_completa(self, data_coleta: date | None = None) -> dict:
        """
        Executa as consultas 1 (Despesa Empenhada) e 2 (Ficha Financeira)
        em sequência dentro do mesmo browser autenticado.

        Args:
            data_coleta: Data de referência (padrão: hoje).

        Returns:
            Dicionário com contagens de registros persistidos por consulta.
        """
        data_coleta = data_coleta or date.today()
        logger.info("=== Iniciando coleta completa para %s ===", data_coleta)

        resultado: dict[str, int] = {
            "empenhos": 0,
            "fichas": 0,
        }

        with BaseScraper() as scraper:
            auth = AutenticacaoEFisco(scraper)
            auth.autenticar()

            resultado["empenhos"] = self._coletar_despesa_empenhada(
                scraper, data_coleta
            )
            resultado["fichas"] = self._coletar_ficha_financeira(
                scraper, data_coleta
            )

        logger.info(
            "=== Coleta concluída: empenhos=%d, fichas=%d ===",
            resultado["empenhos"],
            resultado["fichas"],
        )
        return resultado

    def coletar_despesa_empenhada(self, data_coleta: date | None = None) -> int:
        """
        Executa apenas a consulta de Despesa Empenhada por UG.

        Returns:
            Quantidade de registros persistidos.
        """
        data_coleta = data_coleta or date.today()
        with BaseScraper() as scraper:
            AutenticacaoEFisco(scraper).autenticar()
            return self._coletar_despesa_empenhada(scraper, data_coleta)

    def coletar_ficha_financeira(self, data_coleta: date | None = None) -> int:
        """
        Executa apenas a consulta de Ficha Financeira Detalhada.

        Returns:
            Quantidade de registros persistidos.
        """
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
        """Executa scraping e persistência da Despesa Empenhada."""
        logger.info("--- Consulta 1: Despesa Empenhada por UG ---")
        sc = settings.coleta

        def _coletar() -> list[dict]:
            s = DespesaEmpenhadaScraper(scraper)
            return s.coletar(
                unidade_gestora=sc.unidade_gestora,
                acao=sc.acao,
                subacao=sc.subacao,
                data_coleta=data_coleta,
            )

        registros = retry(
            _coletar,
            max_tentativas=settings.playwright.max_tentativas,
            espera_inicial=settings.playwright.espera_entre_tentativas,
        )

        afetados = EmpenhoRepository.upsert(registros)
        return afetados

    def _coletar_ficha_financeira(
        self, scraper: BaseScraper, data_coleta: date
    ) -> int:
        """Executa scraping e persistência da Ficha Financeira."""
        logger.info("--- Consulta 2: Ficha Financeira Detalhada ---")

        def _coletar() -> list[dict]:
            s = FichaFinanceiraScraper(scraper)
            return s.coletar(
                tipo_despesa_gerencial=settings.coleta.tipo_despesa_gerencial,
                data_coleta=data_coleta,
            )

        registros = retry(
            _coletar,
            max_tentativas=settings.playwright.max_tentativas,
            espera_inicial=settings.playwright.espera_entre_tentativas,
        )

        afetados = FichaFinanceiraRepository.upsert(registros)
        return afetados
