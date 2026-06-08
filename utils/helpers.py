"""
Funções utilitárias compartilhadas entre os módulos.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, TypeVar

from utils.logger import setup_logger

logger = setup_logger(__name__)
T = TypeVar("T")


def limpar_valor_monetario(texto: str) -> Decimal:
    """
    Converte string formatada em moeda brasileira para Decimal.

    Exemplos:
        "R$ 1.234.567,89"  ->  Decimal("1234567.89")
        "1.234,56"         ->  Decimal("1234.56")
        "-"                ->  Decimal("0")
    """
    if not texto or texto.strip() in {"-", "", "N/A"}:
        return Decimal("0")
    limpo = re.sub(r"[R$\s]", "", texto)
    limpo = limpo.replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo)
    except InvalidOperation:
        logger.warning("Não foi possível converter valor monetário: %r", texto)
        return Decimal("0")


def limpar_data(texto: str) -> date | None:
    """
    Converte string de data no formato DD/MM/AAAA para objeto date.

    Returns:
        date ou None se a conversão falhar.
    """
    if not texto or texto.strip() in {"-", "", "N/A"}:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Formato de data não reconhecido: %r", texto)
    return None


def retry(
    func: Callable[..., T],
    *args,
    max_tentativas: int = 3,
    espera_inicial: int = 5,
    **kwargs,
) -> T:
    """
    Executa *func* repetindo em caso de exceção com backoff exponencial.

    Args:
        func: Callable a ser executado.
        max_tentativas: Número máximo de tentativas.
        espera_inicial: Segundos de espera antes da segunda tentativa.
        *args / **kwargs: Repassados para *func*.

    Returns:
        Valor de retorno de *func* na primeira execução bem-sucedida.

    Raises:
        Exception: A última exceção lançada após esgotar as tentativas.
    """
    ultima_excecao: Exception | None = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            ultima_excecao = exc
            espera = espera_inicial * (2 ** (tentativa - 1))
            logger.warning(
                "Tentativa %d/%d falhou (%s). Aguardando %ds…",
                tentativa,
                max_tentativas,
                exc,
                espera,
            )
            time.sleep(espera)
    raise ultima_excecao  # type: ignore[misc]


def garantir_diretorio(caminho: Path) -> Path:
    """Cria o diretório (e pais) se não existir. Retorna o mesmo caminho."""
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def timestamp_arquivo() -> str:
    """Retorna string com data/hora atual adequada para nomes de arquivo."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
