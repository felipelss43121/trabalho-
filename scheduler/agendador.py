"""
Agendador de coleta diária usando APScheduler.

Permite rodar a aplicação como serviço contínuo que dispara
automaticamente no horário configurado sem depender de cron externo.

Uso:
    python scheduler/agendador.py
    python scheduler/agendador.py --hora 07 --minuto 30
"""
from __future__ import annotations

import argparse
import signal
import sys
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from services.coleta_service import ColetaService
from services.export_service import ExportService
from utils.logger import setup_logger

logger = setup_logger("agendador")

_scheduler = BlockingScheduler(timezone="America/Recife")


def _job_coleta() -> None:
    """Job principal: coleta completa + exportação."""
    logger.info(">>> Job de coleta iniciado pelo agendador <<<")
    try:
        ColetaService().executar_coleta_completa()
        ExportService().exportar()
        logger.info(">>> Job de coleta concluído com sucesso <<<")
    except Exception as exc:
        logger.exception(">>> Erro no job de coleta: %s <<<", exc)


def _sinal_saida(signum, frame) -> None:  # noqa: ANN001
    logger.info("Sinal de encerramento recebido. Parando agendador…")
    _scheduler.shutdown(wait=False)
    sys.exit(0)


def iniciar(hora: int = 6, minuto: int = 0) -> None:
    """
    Registra o job e inicia o loop bloqueante do agendador.

    Args:
        hora:    Hora (0-23) de disparo diário.
        minuto:  Minuto (0-59) de disparo.
    """
    signal.signal(signal.SIGTERM, _sinal_saida)
    signal.signal(signal.SIGINT, _sinal_saida)

    trigger = CronTrigger(hour=hora, minute=minuto, timezone="America/Recife")
    _scheduler.add_job(
        _job_coleta,
        trigger=trigger,
        id="coleta_efisco",
        name="Coleta diária e-Fisco",
        replace_existing=True,
        misfire_grace_time=3600,  # Até 1h de tolerância se o servidor estiver down
    )

    logger.info(
        "Agendador iniciado — próxima execução: %s (diário %02d:%02d BRT)",
        _scheduler.get_job("coleta_efisco").next_run_time,
        hora,
        minuto,
    )

    _scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agendador de coleta diária do e-Fisco Pernambuco"
    )
    parser.add_argument(
        "--hora", type=int, default=6, help="Hora de execução diária (padrão: 6)"
    )
    parser.add_argument(
        "--minuto", type=int, default=0, help="Minuto de execução (padrão: 0)"
    )
    parser.add_argument(
        "--executar-agora",
        action="store_true",
        help="Executa o job imediatamente antes de entrar no loop",
    )
    args = parser.parse_args()

    if args.executar_agora:
        logger.info("Executando job imediatamente conforme --executar-agora…")
        _job_coleta()

    iniciar(hora=args.hora, minuto=args.minuto)


if __name__ == "__main__":
    main()
