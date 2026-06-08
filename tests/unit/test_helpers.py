"""
Testes unitários para utils/helpers.py
"""
from decimal import Decimal
from datetime import date

import pytest

from utils.helpers import limpar_valor_monetario, limpar_data, retry


class TestLimparValorMonetario:
    def test_valor_simples(self):
        assert limpar_valor_monetario("1234,56") == Decimal("1234.56")

    def test_valor_com_milhar(self):
        assert limpar_valor_monetario("1.234.567,89") == Decimal("1234567.89")

    def test_valor_com_prefixo_real(self):
        assert limpar_valor_monetario("R$ 1.000,00") == Decimal("1000.00")

    def test_valor_vazio(self):
        assert limpar_valor_monetario("") == Decimal("0")

    def test_valor_traco(self):
        assert limpar_valor_monetario("-") == Decimal("0")

    def test_valor_zero_formatado(self):
        assert limpar_valor_monetario("0,00") == Decimal("0.00")

    def test_valor_inteiro(self):
        assert limpar_valor_monetario("500") == Decimal("500")


class TestLimparData:
    def test_formato_brasileiro(self):
        assert limpar_data("15/06/2024") == date(2024, 6, 15)

    def test_formato_iso(self):
        assert limpar_data("2024-06-15") == date(2024, 6, 15)

    def test_formato_hifen_br(self):
        assert limpar_data("15-06-2024") == date(2024, 6, 15)

    def test_vazio_retorna_none(self):
        assert limpar_data("") is None

    def test_traco_retorna_none(self):
        assert limpar_data("-") is None

    def test_formato_invalido_retorna_none(self):
        assert limpar_data("não é uma data") is None

    def test_strip_espacos(self):
        assert limpar_data("  15/06/2024  ") == date(2024, 6, 15)


class TestRetry:
    def test_sucesso_na_primeira_tentativa(self):
        chamadas = []

        def func():
            chamadas.append(1)
            return "ok"

        resultado = retry(func, max_tentativas=3, espera_inicial=0)
        assert resultado == "ok"
        assert len(chamadas) == 1

    def test_sucesso_apos_falhas(self):
        chamadas = []

        def func():
            chamadas.append(1)
            if len(chamadas) < 3:
                raise ValueError("falha simulada")
            return "ok"

        resultado = retry(func, max_tentativas=3, espera_inicial=0)
        assert resultado == "ok"
        assert len(chamadas) == 3

    def test_lanca_ultima_excecao(self):
        def func():
            raise RuntimeError("sempre falha")

        with pytest.raises(RuntimeError, match="sempre falha"):
            retry(func, max_tentativas=2, espera_inicial=0)
