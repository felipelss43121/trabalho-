"""
Testes unitários para database/schemas.py (validação Pydantic)
"""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from database.schemas import EmpenhoSchema, FichaFinanceiraSchema


class TestEmpenhoSchema:
    _base = dict(
        data_coleta=date.today(),
        unidade_gestora="123456",
        acao="1234",
        subacao="001",
    )

    def test_valido_minimo(self):
        schema = EmpenhoSchema(**self._base)
        assert schema.unidade_gestora == "123456"
        assert schema.valor_empenhado == Decimal("0")

    def test_strip_campos_string(self):
        schema = EmpenhoSchema(**{**self._base, "unidade_gestora": "  123456  "})
        assert schema.unidade_gestora == "123456"

    def test_credor_vazio_vira_none(self):
        schema = EmpenhoSchema(**{**self._base, "credor": "   "})
        assert schema.credor is None

    def test_credor_truncado_em_500(self):
        schema = EmpenhoSchema(**{**self._base, "credor": "A" * 600})
        assert len(schema.credor) == 500

    def test_valor_negativo_rejeitado(self):
        with pytest.raises(ValidationError):
            EmpenhoSchema(**{**self._base, "valor_empenhado": Decimal("-1")})

    def test_unidade_gestora_vazia_rejeitada(self):
        with pytest.raises(ValidationError):
            EmpenhoSchema(**{**self._base, "unidade_gestora": ""})

    def test_model_dump_serializavel(self):
        schema = EmpenhoSchema(**self._base)
        dump = schema.model_dump()
        assert isinstance(dump, dict)
        assert "data_coleta" in dump


class TestFichaFinanceiraSchema:
    _base = dict(
        data_coleta=date.today(),
        ficha_id="F-001",
        exercicio="2024",
    )

    def test_valido_minimo(self):
        schema = FichaFinanceiraSchema(**self._base)
        assert schema.ficha_id == "F-001"

    def test_campos_opcionais_nulos(self):
        schema = FichaFinanceiraSchema(**{**self._base, "gestao": "  "})
        assert schema.gestao is None

    def test_saldo_pode_ser_negativo(self):
        schema = FichaFinanceiraSchema(**{**self._base, "saldo": Decimal("-500")})
        assert schema.saldo == Decimal("-500")

    def test_ficha_id_vazio_rejeitado(self):
        with pytest.raises(ValidationError):
            FichaFinanceiraSchema(**{**self._base, "ficha_id": ""})
