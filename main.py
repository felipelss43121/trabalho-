"""
Ponto de entrada da aplicação e-Fisco Coletor.

Modos de execução:
    python main.py                        # coleta completa (hoje)
    python main.py --data 2024-06-01      # coleta para data específica
    python main.py --apenas-empenho       # somente Despesa Empenhada
    python main.py --apenas-ficha         # somente Ficha Financeira
    python main.py --apenas-exportar      # apenas exporta dados já coletados
    python main.py --inicializar-db       # cria tabelas no banco
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime

from config.settings import settings
from database.connection import criar_tabelas, testar_conexao
from services.coleta_service import ColetaService
from services.export_service import ExportService
from utils.helpers import garantir_diretorio
from utils.logger import setup_logger

logger = setup_logger("main")


def _parse_data(valor: str) -> date:
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Data inválida: {valor!r}. Use o formato AAAA-MM-DD."
        )


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coletor automatizado de dados do e-Fisco Pernambuco",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data",
        type=_parse_data,
        default=date.today(),
        metavar="AAAA-MM-DD",
        help="Data de referência para coleta/exportação (padrão: hoje)",
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--apenas-empenho",
        action="store_true",
        help="Executa somente a consulta de Despesa Empenhada por UG",
    )
    grupo.add_argument(
        "--apenas-ficha",
        action="store_true",
        help="Executa somente a consulta de Ficha Financeira Detalhada",
    )
    grupo.add_argument(
        "--apenas-exportar",
        action="store_true",
        help="Gera apenas os arquivos de exportação CSV/Excel (sem coletar)",
    )
    grupo.add_argument(
        "--exportar-planilha",
        action="store_true",
        help="Injeta os dados na planilha operacional existente (base/planilha_base.xlsx)",
    )
    grupo.add_argument(
        "--inicializar-db",
        action="store_true",
        help="Cria as tabelas no banco de dados e encerra",
    )
    parser.add_argument(
        "--planilha-base",
        type=Path,
        default=None,
        metavar="ARQUIVO.xlsx",
        help="Caminho da planilha-base (padrão: base/planilha_base.xlsx)",
    )
    parser.add_argument(
        "--planilha-saida",
        type=Path,
        default=None,
        metavar="ARQUIVO.xlsx",
        help="Caminho de saída da planilha (padrão: exports/efisco_dados.xlsx)",
    )
    return parser


def main() -> int:
    """
    Ponto de entrada principal.

    Returns:
        0 em caso de sucesso, 1 em caso de erro.
    """
    # Garante que os diretórios de saída existem
    garantir_diretorio(settings.log.log_dir)
    garantir_diretorio(settings.log.screenshot_dir)
    garantir_diretorio(settings.export.diretorio)

    parser = _construir_parser()
    args = parser.parse_args()
    data_coleta: date = args.data

    logger.info("=" * 60)
    logger.info("e-Fisco Coletor — data_coleta=%s", data_coleta)
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Inicialização do banco
    # ------------------------------------------------------------------
    if args.inicializar_db:
        if not testar_conexao():
            logger.error("Não foi possível conectar ao banco. Verifique o .env.")
            return 1
        criar_tabelas()
        logger.info("Banco de dados inicializado.")
        return 0

    # Valida conexão antes de qualquer operação
    if not testar_conexao():
        logger.error(
            "Banco de dados inacessível. Verifique as configurações em .env "
            "e execute: python main.py --inicializar-db"
        )
        return 1

    from services.planilha_service import PlanilhaService

    coleta_service = ColetaService()
    export_service = ExportService()

    # ------------------------------------------------------------------
    # Coleta de dados
    # ------------------------------------------------------------------
    try:
        if args.exportar_planilha:
            logger.info("Modo: exportar para planilha operacional")
            from pathlib import Path as _Path
            base = args.planilha_base or _Path("base/planilha_base.xlsx")
            svc = PlanilhaService(
                planilha_base=base,
                planilha_saida=args.planilha_saida,
            )
            caminho = svc.exportar(data_coleta)
            logger.info("Planilha gerada: %s", caminho)
            return 0
        elif args.apenas_exportar:
            logger.info("Modo: apenas exportação CSV/Excel")
        elif args.apenas_empenho:
            logger.info("Modo: apenas Despesa Empenhada")
            qtd = coleta_service.coletar_despesa_empenhada(data_coleta)
            logger.info("Empenhos persistidos: %d", qtd)
        elif args.apenas_ficha:
            logger.info("Modo: apenas Ficha Financeira")
            qtd = coleta_service.coletar_ficha_financeira(data_coleta)
            logger.info("Fichas persistidas: %d", qtd)
        else:
            logger.info("Modo: coleta completa")
            resultado = coleta_service.executar_coleta_completa(data_coleta)
            logger.info("Resultado coleta: %s", resultado)

        # ------------------------------------------------------------------
        # Exportação
        # ------------------------------------------------------------------
        arquivos = export_service.exportar(data_coleta)
        if arquivos:
            logger.info("Arquivos gerados:")
            for arq in arquivos:
                logger.info("  %s", arq)

    except KeyboardInterrupt:
        logger.warning("Execução interrompida pelo usuário.")
        return 1
    except Exception as exc:
        logger.exception("Erro não tratado durante a execução: %s", exc)
        return 1

    logger.info("Execução concluída com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
