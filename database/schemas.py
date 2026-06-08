"""
DTOs Pydantic para validação e serialização de dados antes da persistência.

Garante que nenhum registro malformado chegue ao banco de dados.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EmpenhoSchema(BaseModel):
    """Valida e normaliza uma linha da consulta Despesa Empenhada por UG."""

    data_coleta: date
    unidade_gestora: str = Field(min_length=1, max_length=20)
    acao: str = Field(min_length=1, max_length=20)
    subacao: str = Field(min_length=1, max_length=20)
    data_empenho: Optional[date] = None
    credor: Optional[str] = Field(default=None, max_length=500)
    valor_empenhado_item: Decimal = Field(default=Decimal("0"), ge=0)
    valor_empenhado: Decimal = Field(default=Decimal("0"), ge=0)
    valor_liquidado: Decimal = Field(default=Decimal("0"), ge=0)
    valor_pago: Decimal = Field(default=Decimal("0"), ge=0)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("unidade_gestora", "acao", "subacao", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("credor", mode="before")
    @classmethod
    def sanitize_credor(cls, v: Optional[str]) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        return str(v).strip()[:500]

    model_config = {"arbitrary_types_allowed": True}


class FichaFinanceiraSchema(BaseModel):
    """Valida e normaliza uma linha da Ficha Financeira Detalhada."""

    data_coleta: date
    ficha_id: str = Field(min_length=1, max_length=50)
    exercicio: str = Field(min_length=1, max_length=10)
    unidade_gestora: Optional[str] = Field(default=None, max_length=200)
    gestao: Optional[str] = Field(default=None, max_length=200)
    grupo_despesa: Optional[str] = Field(default=None, max_length=200)
    fonte_recurso: Optional[str] = Field(default=None, max_length=200)
    natureza_despesa: Optional[str] = Field(default=None, max_length=200)
    dea: Optional[str] = Field(default=None, max_length=200)
    detalhamento_despesa: Optional[str] = Field(default=None, max_length=500)
    destinacao_recurso: Optional[str] = Field(default=None, max_length=200)
    situacao: Optional[str] = Field(default=None, max_length=100)
    dotacao_inicial: Decimal = Field(default=Decimal("0"))
    dotacao_atual: Decimal = Field(default=Decimal("0"))
    valor_empenhado: Decimal = Field(default=Decimal("0"), ge=0)
    valor_liquidado: Decimal = Field(default=Decimal("0"), ge=0)
    valor_pago: Decimal = Field(default=Decimal("0"), ge=0)
    saldo: Decimal = Field(default=Decimal("0"))
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator(
        "unidade_gestora", "gestao", "grupo_despesa", "fonte_recurso",
        "natureza_despesa", "dea", "detalhamento_despesa",
        "destinacao_recurso", "situacao",
        mode="before",
    )
    @classmethod
    def sanitize_optional_str(cls, v: Optional[str]) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    model_config = {"arbitrary_types_allowed": True}
