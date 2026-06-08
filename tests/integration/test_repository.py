"""
Testes de integração para database/repository.py

Requerem banco PostgreSQL acessível com as variáveis de ambiente do .env.
Execute com:  pytest tests/integration/ -v --tb=short
"""
from datetime import date
from decimal import Decimal

import pytest

from database.connection import criar_tabelas, testar_conexao
from database.repository import EmpenhoRepository, FichaFinanceiraRepository


@pytest.fixture(scope="module", autouse=True)
def banco_disponivel():
    """Pula todos os testes de integração se o banco não estiver acessível."""
    if not testar_conexao():
        pytest.skip("Banco de dados não acessível — testes de integração ignorados.")
    criar_tabelas()


@pytest.fixture
def data_teste():
    # Usa data fictícia distante para não conflitar com dados reais
    return date(1900, 1, 1)


@pytest.fixture(autouse=True)
def limpar_dados_teste(data_teste):
    """Remove registros de teste antes e depois de cada teste."""
    from database.connection import obter_sessao
    from database.models import FatoEmpenho, FatoFichaFinanceira
    from sqlalchemy import delete

    def _limpar():
        with obter_sessao() as s:
            s.execute(
                delete(FatoEmpenho).where(FatoEmpenho.data_coleta == data_teste)
            )
            s.execute(
                delete(FatoFichaFinanceira).where(
                    FatoFichaFinanceira.data_coleta == data_teste
                )
            )

    _limpar()
    yield
    _limpar()


class TestEmpenhoRepository:
    def _registro(self, data_teste, credor="FORNECEDOR A"):
        return {
            "data_coleta": data_teste,
            "unidade_gestora": "TEST001",
            "acao": "0001",
            "subacao": "001",
            "data_empenho": data_teste,
            "credor": credor,
            "valor_empenhado_item": Decimal("1000.00"),
            "valor_empenhado": Decimal("2000.00"),
            "valor_liquidado": Decimal("500.00"),
            "valor_pago": Decimal("300.00"),
        }

    def test_inserir_e_listar(self, data_teste):
        EmpenhoRepository.upsert([self._registro(data_teste)])
        resultado = EmpenhoRepository.listar_por_data(data_teste)
        assert len(resultado) == 1
        assert resultado[0].credor == "FORNECEDOR A"

    def test_upsert_atualiza_valor(self, data_teste):
        EmpenhoRepository.upsert([self._registro(data_teste)])

        atualizado = self._registro(data_teste)
        atualizado["valor_pago"] = Decimal("999.00")
        EmpenhoRepository.upsert([atualizado])

        resultado = EmpenhoRepository.listar_por_data(data_teste)
        assert len(resultado) == 1  # não duplicou
        assert resultado[0].valor_pago == Decimal("999.00")

    def test_multiplos_credores(self, data_teste):
        registros = [
            self._registro(data_teste, credor=f"FORNECEDOR {i}")
            for i in range(5)
        ]
        EmpenhoRepository.upsert(registros)
        resultado = EmpenhoRepository.listar_por_data(data_teste)
        assert len(resultado) == 5

    def test_lista_vazia_retorna_zero(self, data_teste):
        assert EmpenhoRepository.upsert([]) == 0


class TestFichaFinanceiraRepository:
    def _registro(self, data_teste, ficha_id="F-TEST-001"):
        return {
            "data_coleta": data_teste,
            "ficha_id": ficha_id,
            "exercicio": "1900",
            "unidade_gestora": "SETEST",
            "dotacao_inicial": Decimal("100000.00"),
            "dotacao_atual": Decimal("95000.00"),
            "valor_empenhado": Decimal("50000.00"),
            "valor_liquidado": Decimal("30000.00"),
            "valor_pago": Decimal("20000.00"),
            "saldo": Decimal("75000.00"),
        }

    def test_inserir_e_listar(self, data_teste):
        FichaFinanceiraRepository.upsert([self._registro(data_teste)])
        resultado = FichaFinanceiraRepository.listar_por_data(data_teste)
        assert len(resultado) == 1
        assert resultado[0].ficha_id == "F-TEST-001"

    def test_upsert_atualiza_saldo(self, data_teste):
        FichaFinanceiraRepository.upsert([self._registro(data_teste)])

        atualizado = self._registro(data_teste)
        atualizado["saldo"] = Decimal("12345.00")
        FichaFinanceiraRepository.upsert([atualizado])

        resultado = FichaFinanceiraRepository.listar_por_data(data_teste)
        assert len(resultado) == 1
        assert resultado[0].saldo == Decimal("12345.00")
