"""
Configuração centralizada de logging com rotação de arquivos.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com handlers de console e arquivo rotativo.

    Args:
        name: Nome do módulo/componente para identificar a origem dos logs.

    Returns:
        Instância configurada de logging.Logger.
    """
    log_dir: Path = settings.log.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(settings.log.level)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # Arquivo com rotação (10 MB, 5 backups)
    file_handler = RotatingFileHandler(
        log_dir / "efisco_coleta.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
