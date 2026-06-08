"""
Classe base para todos os scrapers do e-Fisco.
Encapsula criação do browser, tratamento de erros e captura de screenshots.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from config.settings import settings
from utils.helpers import garantir_diretorio, timestamp_arquivo
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseScraper:
    """
    Fornece browser Playwright configurado, retry automático e captura de
    screenshots de erro para todos os scrapers especializados.
    """

    # URL base do portal e-Fisco Pernambuco
    URL_BASE = "https://efisco.sefaz.pe.gov.br"

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._screenshot_dir: Path = garantir_diretorio(
            settings.log.screenshot_dir
        )

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def iniciar(self) -> None:
        """Inicia o Playwright e abre um contexto de browser."""
        logger.info("Iniciando Playwright (headless=%s)…", settings.playwright.headless)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=settings.playwright.headless,
            slow_mo=settings.playwright.slow_mo,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Recife",
        )
        self._context.set_default_timeout(settings.playwright.timeout)
        self._context.set_default_navigation_timeout(
            settings.playwright.timeout_navegacao
        )
        self._page = self._context.new_page()
        logger.info("Browser iniciado com sucesso.")

    def encerrar(self) -> None:
        """Fecha browser e libera recursos do Playwright."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as exc:
            logger.warning("Erro ao encerrar Playwright: %s", exc)
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
        logger.info("Playwright encerrado.")

    def __enter__(self) -> "BaseScraper":
        self.iniciar()
        return self

    def __exit__(self, *_: Any) -> None:
        self.encerrar()

    # ------------------------------------------------------------------
    # Utilitários de página
    # ------------------------------------------------------------------

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Scraper não iniciado. Use .iniciar() ou o context manager.")
        return self._page

    def capturar_screenshot(self, nome: str = "erro") -> Path:
        """
        Salva screenshot da página atual.

        Args:
            nome: Prefixo do arquivo (sem extensão).

        Returns:
            Path do arquivo salvo.
        """
        caminho = self._screenshot_dir / f"{nome}_{timestamp_arquivo()}.png"
        try:
            self.page.screenshot(path=str(caminho), full_page=True)
            logger.info("Screenshot salvo: %s", caminho)
        except Exception as exc:
            logger.warning("Não foi possível capturar screenshot: %s", exc)
        return caminho

    def aguardar_seletor(self, seletor: str, timeout: int | None = None) -> None:
        """Espera o seletor ficar visível na página."""
        t = timeout or settings.playwright.timeout
        self.page.wait_for_selector(seletor, state="visible", timeout=t)

    def clicar_com_retry(
        self,
        seletor: str,
        max_tentativas: int | None = None,
    ) -> None:
        """Tenta clicar em *seletor* com retry em caso de falha."""
        tentativas = max_tentativas or settings.playwright.max_tentativas
        for i in range(1, tentativas + 1):
            try:
                self.page.click(seletor)
                return
            except Exception as exc:
                logger.warning(
                    "Clique em %r falhou (tentativa %d/%d): %s",
                    seletor,
                    i,
                    tentativas,
                    exc,
                )
                if i == tentativas:
                    self.capturar_screenshot(f"erro_clique_{i}")
                    raise
                time.sleep(settings.playwright.espera_entre_tentativas)

    def preencher_campo(self, seletor: str, valor: str) -> None:
        """Limpa e preenche um campo de formulário."""
        self.page.fill(seletor, "")
        self.page.fill(seletor, valor)

    def extrair_tabela_html(self, seletor_tabela: str) -> list[dict[str, str]]:
        """
        Extrai todas as linhas de uma tabela HTML como lista de dicionários.

        O cabeçalho da tabela (thead > th) define as chaves; cada tr em tbody
        gera um dicionário.

        Args:
            seletor_tabela: Seletor CSS para o elemento <table>.

        Returns:
            Lista de dicionários representando as linhas da tabela.
        """
        tabela = self.page.query_selector(seletor_tabela)
        if not tabela:
            logger.warning("Tabela não encontrada: %s", seletor_tabela)
            return []

        cabecalhos: list[str] = [
            th.inner_text().strip()
            for th in tabela.query_selector_all("thead th, thead td")
        ]
        if not cabecalhos:
            # Tenta cabeçalho inline no primeiro tr
            primeiro_tr = tabela.query_selector("tr")
            if primeiro_tr:
                cabecalhos = [
                    td.inner_text().strip()
                    for td in primeiro_tr.query_selector_all("th, td")
                ]

        linhas: list[dict[str, str]] = []
        for tr in tabela.query_selector_all("tbody tr"):
            celulas = [td.inner_text().strip() for td in tr.query_selector_all("td")]
            if not any(celulas):
                continue  # Ignora linhas vazias
            # Mapeia pelo índice; colunas extras viram "colN"
            registro: dict[str, str] = {}
            for i, valor in enumerate(celulas):
                chave = cabecalhos[i] if i < len(cabecalhos) else f"col{i}"
                registro[chave] = valor
            linhas.append(registro)

        logger.debug("Tabela extraída: %d linhas.", len(linhas))
        return linhas

    def tem_proxima_pagina(
        self,
        seletor_proximo: str = "a[title='Próxima página'], a:has-text('Próxima')",
    ) -> bool:
        """Verifica se existe botão/link de próxima página habilitado."""
        elemento = self.page.query_selector(seletor_proximo)
        if not elemento:
            return False
        # Considera desabilitado se tiver classe 'disabled' ou atributo disabled
        classes = elemento.get_attribute("class") or ""
        if "disabled" in classes:
            return False
        return True

    def ir_para_proxima_pagina(
        self,
        seletor_proximo: str = "a[title='Próxima página'], a:has-text('Próxima')",
    ) -> None:
        """Clica no link de próxima página e aguarda carregamento."""
        self.clicar_com_retry(seletor_proximo)
        self.page.wait_for_load_state("networkidle")
