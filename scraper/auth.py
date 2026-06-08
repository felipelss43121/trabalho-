"""
Módulo de autenticação no Gov.br e no portal e-Fisco Pernambuco.

O fluxo segue o login federado:
    1. Acessa o e-Fisco  →  redireciona para Gov.br
    2. Preenche CPF e senha no Gov.br
    3. Confirma segundo fator (se solicitado) ou continua
    4. Retorna autenticado ao e-Fisco
"""
from __future__ import annotations

import time

from config.settings import settings
from scraper.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Seletores Gov.br (sujeitos a mudanças pelo provedor)
SEL_CPF_INPUT     = "input#accountId, input[name='accountId'], input[id*='cpf']"
SEL_SENHA_INPUT   = "input#password, input[name='password'], input[type='password']"
SEL_BTN_CONTINUAR = "button#next, button[type='submit']:has-text('Continuar')"
SEL_BTN_ENTRAR    = "button#submit-password, button[type='submit']:has-text('Entrar')"

# Seletores e-Fisco (área logada)
SEL_MENU_PRINCIPAL = "div#menu-principal, nav.menu-lateral, ul.menu-nav"
SEL_BTN_GOVBR      = "a:has-text('Entrar com Gov.br'), button:has-text('Gov.br')"


class AutenticacaoEFisco:
    """
    Realiza login no e-Fisco via Gov.br.

    Exemplo de uso:
        with BaseScraper() as scraper:
            auth = AutenticacaoEFisco(scraper)
            auth.autenticar()
            # navegação pós-login…
    """

    def __init__(self, scraper: BaseScraper) -> None:
        self._scraper = scraper

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def autenticar(self) -> None:
        """
        Executa o fluxo completo de autenticação.

        Raises:
            RuntimeError: Se não for possível confirmar o login bem-sucedido.
        """
        logger.info("Iniciando autenticação no e-Fisco Pernambuco…")
        self._acessar_portal()
        self._clicar_govbr()
        self._preencher_cpf()
        self._preencher_senha()
        self._aguardar_redirecionamento()
        logger.info("Autenticação concluída com sucesso.")

    # ------------------------------------------------------------------
    # Passos internos
    # ------------------------------------------------------------------

    def _acessar_portal(self) -> None:
        """Carrega a página inicial do e-Fisco."""
        url = f"{BaseScraper.URL_BASE}/siga/index.do"
        logger.debug("Acessando portal: %s", url)
        self._scraper.page.goto(url)
        self._scraper.page.wait_for_load_state("domcontentloaded")

    def _clicar_govbr(self) -> None:
        """Clica no botão de acesso via Gov.br, se presente."""
        try:
            self._scraper.aguardar_seletor(SEL_BTN_GOVBR, timeout=10_000)
            self._scraper.clicar_com_retry(SEL_BTN_GOVBR)
            self._scraper.page.wait_for_load_state("networkidle")
            logger.debug("Botão Gov.br clicado.")
        except Exception:
            # Pode já estar na tela de login ou o seletor mudou
            logger.debug("Botão Gov.br não encontrado; continuando…")

    def _preencher_cpf(self) -> None:
        """Preenche o CPF no formulário Gov.br."""
        cpf = settings.govbr.cpf
        if not cpf:
            raise ValueError(
                "CPF não configurado. Defina GOVBR_CPF no arquivo .env"
            )
        logger.debug("Preenchendo CPF…")
        self._scraper.aguardar_seletor(SEL_CPF_INPUT)
        self._scraper.preencher_campo(SEL_CPF_INPUT, cpf)
        self._scraper.clicar_com_retry(SEL_BTN_CONTINUAR)
        self._scraper.page.wait_for_load_state("networkidle")

    def _preencher_senha(self) -> None:
        """Preenche a senha no formulário Gov.br."""
        senha = settings.govbr.senha
        if not senha:
            raise ValueError(
                "Senha não configurada. Defina GOVBR_SENHA no arquivo .env"
            )
        logger.debug("Preenchendo senha…")
        self._scraper.aguardar_seletor(SEL_SENHA_INPUT)
        self._scraper.preencher_campo(SEL_SENHA_INPUT, senha)
        self._scraper.clicar_com_retry(SEL_BTN_ENTRAR)
        self._scraper.page.wait_for_load_state("networkidle")

    def _aguardar_redirecionamento(self) -> None:
        """
        Aguarda o redirecionamento de volta ao e-Fisco e confirma autenticação
        verificando a presença do menu principal.
        """
        max_espera = 30
        intervalo = 2
        decorrido = 0

        while decorrido < max_espera:
            url_atual = self._scraper.page.url
            if BaseScraper.URL_BASE in url_atual:
                # Confirma que o menu do sistema está presente
                menu = self._scraper.page.query_selector(SEL_MENU_PRINCIPAL)
                if menu:
                    return
            time.sleep(intervalo)
            decorrido += intervalo

        # Captura screenshot para diagnóstico
        self._scraper.capturar_screenshot("erro_autenticacao")
        raise RuntimeError(
            "Autenticação falhou: o menu principal do e-Fisco não foi encontrado "
            f"após {max_espera}s. Verifique as credenciais e o screenshot salvo."
        )
